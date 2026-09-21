from __future__ import annotations

import asyncio
from datetime import timedelta
from uuid import UUID

from app.features.ai_catalogs.services import AICatalogService
from app.features.project_management.pipeline_runs.adapters.base import DeliveryTarget
from app.features.project_management.pipeline_runs.adapters.registry import (
    resolve_execution_adapter,
)
from app.features.project_management.pipeline_runs.models import (
    ExecutionAttemptState,
    ExecutionDelivery,
    PipelineRunState,
)
from app.features.project_management.pipeline_runs.repos import PipelineRunRepository
from app.features.project_management.pipeline_runs.schemas import (
    ImplementationRequest,
    PipelineRunRead,
)
from app.features.project_management.pipeline_runs.usecases.leases import raise_lease_conflict
from app.features.project_management.pipeline_runs.usecases.transitions import (
    as_utc,
    block_for_project_change,
)
from app.features.project_management.pipelines.services import PipelineConfigurationError, PipelineObservationService
from app.features.project_management.projects.errors import ProjectError
from app.features.project_management.projects.services import ProjectService
from app_layer_base.core.database.transaction import AsyncTransaction
from app_layer_base.utils.time_util import get_current_utc_time

DISPATCH_IO_SECONDS = 30
DISPATCH_LEASE_SECONDS = 90
CATALOG_HOLD_CODE = "CATALOG_HOLD"


class PipelineRunDelivery:
    def __init__(
        self,
        repo: PipelineRunRepository,
        projects: ProjectService,
        observer: PipelineObservationService,
        ai_catalogs: AICatalogService | None,
    ):
        self.repo = repo
        self.projects = projects
        self.observer = observer
        self.ai_catalogs = ai_catalogs

    async def dispatch_implementation(self, run_id: UUID, *, owner: str, token: UUID) -> PipelineRunRead:
        """Reconcile then make one delivery through the catalog's adapter, retaining state across uncertain writes."""
        now = get_current_utc_time()
        async with AsyncTransaction() as session:
            run = await self.repo.get_leased(session, run_id, owner=owner, token=token, now=now)
            if run is None:
                await raise_lease_conflict(self.repo, session, run_id, "dispatch implementation")
            if run.state != PipelineRunState.DISPATCHING:
                return PipelineRunRead.model_validate(run)
            if run.next_action_at is not None and as_utc(run.next_action_at) > now:
                return PipelineRunRead.model_validate(run)
            project = await self.projects.get(session, run.project_id)
            if (
                not project.enabled
                or project.revision != run.project_revision
                or project.github_connector_id is None
                or project.github_repository is None
            ):
                # Checked before admission so a run that can never be delivered takes no catalog capacity.
                return await block_for_project_change(self.repo, session, run, now)
            adapter = await resolve_execution_adapter(session, run.ai_catalog_id)
            attempt = await self.repo.active_attempt(session, run.id)
            if attempt is None:
                raise ProjectError(409, "Pipeline run has no active implementation attempt")
            delivery = await self.repo.latest_delivery(session, attempt.id)
            if delivery is None:
                delivery = await self.repo.create_delivery(
                    session,
                    ExecutionDelivery(
                        execution_attempt_id=attempt.id,
                        delivery_number=1,
                        cause="initial",
                    ),
                )
            elif delivery.external_id is not None:
                delivery = await self.repo.create_delivery(
                    session,
                    ExecutionDelivery(
                        execution_attempt_id=attempt.id,
                        delivery_number=delivery.delivery_number + 1,
                        cause="resume",
                    ),
                )
            # The delivery is settled before admission so the catalog ledger counts it once, however often it retries.
            if self.ai_catalogs is not None:
                admission = await self.ai_catalogs.request_dispatch(
                    session, run.ai_catalog_id, run.id, f"delivery:{delivery.id}", now
                )
                if admission.rejection is not None:
                    # Keep what the policy recorded while rejecting, such as a hold it has just reached.
                    await session.commit()
                    raise ProjectError(409, admission.rejection, code=CATALOG_HOLD_CODE)
            attempt.state = ExecutionAttemptState.DISPATCHING
            request = ImplementationRequest.model_validate(attempt.request_snapshot)
            target = DeliveryTarget(project.github_connector_id, project.github_repository, run.pull_number)
            expected_revision = run.revision

        # Do all adapter I/O outside the transaction. An uncertain delivery leaves the planned delivery
        # intact so the next tick reconciles it before attempting another write.
        try:
            await self._guard_dispatch(run_id, owner, token, expected_revision)
            async with asyncio.timeout(DISPATCH_IO_SECONDS):
                receipt = await adapter.deliver(
                    self.observer,
                    target,
                    request,
                    delivery.delivery_number,
                    authorize=lambda: self._guard_dispatch(run_id, owner, token, expected_revision),
                )
        except TimeoutError:
            raise ProjectError(504, "Delivery exceeded its time budget; reconcile on the next tick") from None
        except PipelineConfigurationError as exc:
            raise ProjectError(422, str(exc)) from None

        posted_at = receipt.posted_at
        async with AsyncTransaction() as session:
            run = await self.repo.get_leased(session, run_id, owner=owner, token=token, now=get_current_utc_time())
            if run is None:
                await raise_lease_conflict(self.repo, session, run_id, "record delivery")
            attempt = await self.repo.active_attempt(session, run.id)
            if attempt is None or attempt.id != delivery.execution_attempt_id:
                raise ProjectError(409, "Pipeline run changed during delivery")
            recorded = await self.repo.latest_delivery(session, attempt.id)
            if recorded is None or recorded.id != delivery.id:
                raise ProjectError(409, "Pipeline delivery changed during delivery")
            recorded.external_id = receipt.external_id
            recorded.posted_at = posted_at
            attempt.state = ExecutionAttemptState.RUNNING
            attempt.external_correlation_id = receipt.external_id
            attempt.external_status = "delivered"
            attempt.conversation_url = receipt.url
            attempt.started_at = attempt.started_at or posted_at
            run.state = PipelineRunState.IMPLEMENTING
            run.next_action_at = None
            run.revision += 1
            if self.ai_catalogs is not None:
                await self.ai_catalogs.record_dispatch_delivered(session, run.ai_catalog_id, posted_at)
            await session.flush()
            return PipelineRunRead.model_validate(run)

    async def _guard_dispatch(self, run_id: UUID, owner: str, token: UUID, expected_revision: int) -> None:
        """Reserve a lease longer than the bounded I/O and recheck authorization before posting."""
        now = get_current_utc_time()
        async with AsyncTransaction() as session:
            run = await self.repo.get_leased(session, run_id, owner=owner, token=token, now=now)
            if run is None:
                await raise_lease_conflict(self.repo, session, run_id, "authorize delivery")
            if run.state != PipelineRunState.DISPATCHING or run.revision != expected_revision:
                raise ProjectError(409, "Pipeline run changed before delivery")
            project = await self.projects.get(session, run.project_id)
            if not project.enabled or project.revision != run.project_revision:
                raise ProjectError(409, "Project changed before delivery")
            if self.ai_catalogs is not None:
                await self.ai_catalogs.require_dispatchable(session, run.ai_catalog_id, now)
            now = get_current_utc_time()
            renewed = await self.repo.renew_lease(
                session,
                run_id,
                owner=owner,
                token=token,
                now=now,
                expires_at=now + timedelta(seconds=DISPATCH_LEASE_SECONDS),
            )
            if renewed is None:
                await raise_lease_conflict(self.repo, session, run_id, "reserve delivery time")
