"""One maintenance job for all pending probes and provider session results."""

import asyncio
from collections.abc import Awaitable, Callable
from uuid import UUID

from app.features.configuration.connectors.crypto import ConnectorCredentialCipher, get_credential_key_provider
from app.features.configuration.connectors.repos import ConnectorRepository
from app.features.configuration.connectors.usecases.token import ReadConnectorTokenUseCase
from app.features.execution.tasks import task
from app.features.execution.tasks.domains.jules.task import _service as jules_service
from app.features.execution.tasks.domains.maintenance.repos import MaintenanceGroup, MaintenanceRepository
from app.features.execution.tasks.domains.maintenance.retention import HistoryRetentionUseCase
from app.features.execution.tasks.domains.pipeline.connection_probe import connection_test_task
from app.features.project_management.connection_tests.schemas import ConnectionTestPayload
from app.features.project_management.pipelines.services import PipelineObservationService
from app.features.project_management.work_plans.issue_sync import WorkIssueSync
from app.features.scheduling.schedule_configs.system import MAINTENANCE_TASK
from app_layer_base.core.database.transaction import AsyncTransaction
from app_layer_base.core.log import logger
from pydantic import BaseModel, ConfigDict


class MaintenancePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")


@task(name=MAINTENANCE_TASK)
async def maintain_task(payload: MaintenancePayload) -> None:
    """Continue work even without an enabled project/schedule. Never create new Jules sessions.

    Probe leases still arbitrate with manual advances. Each item fails independently, and the
    dispatcher owns the overall time budget. Each kind reserves two workers when both have work;
    a single kind can use all four. Persisted cursors rotate attempts across ticks and restarts.
    """
    failures = []
    try:
        await HistoryRetentionUseCase().execute()
    except Exception:
        failures.append("history retention")
        logger.exception("Pruning expired maintenance history failed")
    try:
        observer = PipelineObservationService(
            ReadConnectorTokenUseCase(
                ConnectorRepository(), ConnectorCredentialCipher(get_credential_key_provider())
            ).execute
        )
        await WorkIssueSync(observer).execute()
    except Exception:
        # Outbound record failures must not block execution or provider cleanup.
        logger.exception("Work issue synchronization will retry")
    repo = MaintenanceRepository()
    async with AsyncTransaction() as session:
        test_ids = await repo.pending_tests(session)
        catalog_keys = await repo.pending_catalogs(session)
    # Serialize local cursor transactions, including SQLite's shared in-memory connection in tests.
    # The database row lock also coordinates cursor updates from overlapping ticks on PostgreSQL.
    selection_lock = asyncio.Lock()

    async def consume(group: MaintenanceGroup, pending: list[str], execute: Callable[[str], Awaitable[None]]):
        while True:
            async with selection_lock:
                if not pending:
                    return
                async with AsyncTransaction() as session:
                    item = await repo.next_item(session, group, pending)
                pending.remove(item)
            try:
                await execute(item)
            except Exception:
                failures.append(item)
                logger.exception(f"Maintenance of {group} item {item} failed")

    async def advance_test(test_id: str) -> None:
        await connection_test_task(ConnectionTestPayload(test_id=UUID(test_id)))

    async def sync_catalog(key: str) -> None:
        await jules_service().sync(key)

    pending_tests = sorted(str(id) for id in test_ids)
    pending_catalogs = sorted(catalog_keys)
    # TaskGroup cancels and joins sibling workers if selection fails or the dispatcher cancels this task.
    async with asyncio.TaskGroup() as workers:
        for _ in range(min(len(pending_tests), 2 if pending_catalogs else 4)):
            workers.create_task(consume("tests", pending_tests, advance_test))
        for _ in range(min(len(pending_catalogs), 2 if pending_tests else 4)):
            workers.create_task(consume("catalogs", pending_catalogs, sync_catalog))
    if failures:
        raise RuntimeError(f"System maintenance failed for {len(failures)} item(s); pending work will retry")
