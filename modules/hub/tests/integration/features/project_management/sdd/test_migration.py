import json
from uuid import UUID

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from app.features.project_management.pipeline_runs.models import ExecutionAttempt, PipelineRun
from sqlalchemy import select, text
from tests.integration.features.project_management.sdd import test_native as native
from tests.integration.migrations.test_default_ai_catalogs import scripts

github = native.github
project = native.project
inspector = native.inspector
run = native.run
unit_branch = native.unit_branch
pytestmark = [pytest.mark.integration, pytest.mark.real_commit]


@pytest.mark.parametrize("state", ["implementing", "completed"])
async def test_migration_preserves_legacy_evidence_and_settles_only_live_work(session, run, state):
    row = await session.get(PipelineRun, UUID(run["id"]))
    legacy = {"mode": "specrig", "cli_version": "specrig version 0.1.2", "spec_dir": native.SPEC}
    row.sdd_snapshot = legacy
    await session.flush()
    attempt = (
        (await session.execute(select(ExecutionAttempt).where(ExecutionAttempt.pipeline_run_id == row.id)))
        .scalars()
        .first()
    )
    attempt.request_snapshot = {"specrig_stage": "integrate"}
    await session.flush()
    connection = await session.connection()

    def migrate(sync):
        with Operations.context(MigrationContext.configure(sync)):
            migration = scripts().get_revision("ba3d1a6089a9").module
            migration.downgrade()
            sync.execute(text("UPDATE pipeline_runs SET state=:state"), {"state": state})
            sync.execute(text("UPDATE execution_attempts SET state='planned', failure_code=NULL"))
            migration.upgrade()
        rows = sync.execute(text("SELECT state, sdd_snapshot FROM pipeline_runs")).mappings().all()
        stored = rows[0]["sdd_snapshot"]
        assert (json.loads(stored) if isinstance(stored, str) else stored) == legacy
        assert rows[0]["state"] == ("canceled" if state == "implementing" else "completed")

    await connection.run_sync(migrate)
    result = (await session.execute(select(ExecutionAttempt.state, ExecutionAttempt.failure_code))).one()
    assert result.state == ("failed" if state == "implementing" else "planned")
    assert result.failure_code == ("SDD_RUNTIME_CHANGED" if state == "implementing" else None)
