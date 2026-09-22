from datetime import timedelta
from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from app.features.ai_catalogs.models import AICatalog, AICatalogSession
from app.features.project_management.connection_tests.models import ConnectionTest
from app.features.scheduling.schedule_configs.models import ScheduleConfig
from app.features.scheduling.schedule_configs.system import MAINTENANCE_ID, ensure_maintenance_schedule
from app.features.scheduling.schedule_jobs.models import ScheduleJob
from app_testing_base import utc_now
from sqlalchemy import select, text
from tests.integration.features.project_management.connection_tests import test_connection_tests as probes
from tests.integration.migrations.test_default_ai_catalogs import scripts

github = probes.github
project = probes.project
start = probes.start
step = probes.step


pytestmark = [pytest.mark.integration, pytest.mark.real_commit]


async def migrate(session, direction):
    connection = await session.connection()

    def run(sync_connection):
        with Operations.context(MigrationContext.configure(sync_connection)):
            getattr(scripts().get_revision("f4d5e6f7a8b9").module, direction)()

    await connection.run_sync(run)
    session.expire_all()


async def test_upgrade_preserves_pending_work_and_history_and_downgrade_restores_workers(client, session, project):
    probe = await start(client, project)
    test_id = UUID(probe["id"])
    catalog = AICatalog(key="migration-jules", name="Jules", kind="jules", adapter="jules-api")
    session.add(catalog)
    await session.flush()
    catalog_id = catalog.id
    sync = ScheduleConfig(
        name="Agent sync: migration-jules",
        task_func="jules.sync_sessions",
        interval_seconds=300,
        payload={"catalog_key": "migration-jules"},
    )
    custom = ScheduleConfig(
        name="Operator sync",
        task_func="jules.sync_sessions",
        interval_seconds=600,
        payload={"catalog_key": "migration-jules"},
        enabled=False,
    )
    old_test = ScheduleConfig(
        id=test_id,
        name="Connection test old",
        task_func="pipeline.connection_test",
        interval_seconds=60,
        payload={"test_id": str(test_id)},
    )
    session.add_all([sync, custom, old_test])
    await session.flush()
    sync_id, custom_id = sync.id, custom.id
    # No Agent Schedule: maintenance must still discover this historical/orphaned session.
    tracked = AICatalogSession(
        ai_catalog_id=catalog_id,
        schedule_config_id=sync_id,
        title="Keep remote work",
        work_type="report",
        state="in_progress",
        external_name="sessions/migration",
    )
    job = ScheduleJob(name="Historical test job", schedule_config_id=test_id, status="success", started_at=utc_now())
    session.add_all([tracked, job])
    await session.flush()
    tracked_id, job_id = tracked.id, job.id
    await session.execute(text("DROP INDEX uq_schedule_configs_system_maintenance"))
    await migrate(session, "upgrade")
    assert await session.get(ScheduleConfig, test_id) is None
    assert await session.get(ScheduleConfig, sync_id) is None
    assert (await session.get(ScheduleConfig, custom_id)).enabled is False
    assert (await session.get(ConnectionTest, test_id)).status == "running"
    stored = await session.get(AICatalogSession, tracked_id)
    assert stored.external_name == "sessions/migration" and stored.schedule_config_id is None
    assert (await session.get(ScheduleJob, job_id)).schedule_config_id is None
    assert (await session.get(ScheduleConfig, MAINTENANCE_ID)).enabled
    await ensure_maintenance_schedule(session)
    maintenance_job = ScheduleJob(
        name="Timed out maintenance",
        schedule_config_id=MAINTENANCE_ID,
        status="failure",
        started_at=utc_now(),
        retry_need=True,
        retry_attempts=1,
    )
    session.add(maintenance_job)
    await session.flush()
    maintenance_job_id = maintenance_job.id
    await migrate(session, "downgrade")
    maintenance_job = await session.get(ScheduleJob, maintenance_job_id)
    assert maintenance_job.schedule_config_id is None and maintenance_job.retry_need is False
    assert UUID((await session.get(ScheduleConfig, test_id)).payload["test_id"]) == test_id
    assert (await session.get(ScheduleConfig, catalog_id)).payload == {"catalog_key": "migration-jules"}
    await migrate(session, "upgrade")
    assert await session.get(ScheduleConfig, test_id) is None
    assert await session.get(ScheduleConfig, catalog_id) is None
    assert (await session.get(ScheduleConfig, custom_id)).name == "Operator sync"
    configs = list(await session.scalars(select(ScheduleConfig).where(ScheduleConfig.task_func == "system.maintain")))
    assert len(configs) == 1
    assert (await session.get(AICatalogSession, tracked_id)).state == "in_progress"


@pytest.mark.parametrize("worker", ["probe", "sync"])
async def test_upgrade_retires_owned_retries_and_preserves_operator_retries(client, session, project, monkeypatch, worker):
    test_id = UUID((await start(client, project))["id"])
    session.add(AICatalog(key="retry-jules", name="Jules", kind="jules", adapter="jules-api"))
    owned = ScheduleConfig(
        id=test_id,
        name="Connection test old" if worker == "probe" else "Agent sync: retry-jules",
        task_func="pipeline.connection_test" if worker == "probe" else "jules.sync_sessions",
        interval_seconds=60,
        payload={"test_id": str(test_id)} if worker == "probe" else {"catalog_key": "retry-jules"},
    )
    custom = ScheduleConfig(
        name="Operator sync",
        task_func="jules.sync_sessions",
        interval_seconds=600,
        next_run_at=utc_now() + timedelta(hours=1),
        payload={"catalog_key": "retry-jules"},
    )
    session.add_all([owned, custom])
    await session.flush()
    jobs = [
        ScheduleJob(
            name=config.name,
            schedule_config_id=config.id,
            status="failure",
            started_at=utc_now(),
            finished_at=utc_now(),
            retry_need=True,
            retry_attempts=1,
            retry_max=3,
        )
        for config in (owned, custom)
    ]
    session.add_all(jobs)
    await session.flush()
    owned_job_id, custom_job_id = (job.id for job in jobs)
    await session.execute(text("DROP INDEX uq_schedule_configs_system_maintenance"))
    await migrate(session, "upgrade")
    detached = await session.get(ScheduleJob, owned_job_id)
    assert detached.schedule_config_id is None and detached.retry_need is False
    assert detached.status == "failure" and detached.retry_attempts == 1
    assert (await session.get(ScheduleJob, custom_job_id)).retry_need is True
    maintenance = await session.get(ScheduleConfig, MAINTENANCE_ID)
    maintenance.next_run_at = utc_now() + timedelta(hours=1)
    await session.commit()

    # No due configs: the dispatcher must still retry operator work without loading a detached config.
    task = AsyncMock()
    monkeypatch.setattr("app.features.execution.dispatchers.services.task_registry.get", lambda name: task)
    response = await client.post("/api/v1/dispatchers/trigger")
    assert response.status_code == 200 and response.json()["dispatched"] == 1
    task.assert_awaited_once()
    response = await client.post("/api/v1/dispatchers/trigger")
    assert response.status_code == 200 and response.json()["dispatched"] == 0
