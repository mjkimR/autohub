import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import inspect, text

from tests.integration.features.project_management.pipeline_runs.test_discovery import project, github, enroll
from tests.integration.features.project_management.pipeline_runs.test_interactions import ask
from tests.integration.migrations.test_default_ai_catalogs import scripts

__all__ = ["project", "github"]
pytestmark = [pytest.mark.integration, pytest.mark.real_commit]


async def test_discovery_backfill_roundtrip(client, project, github, session):
    run = (await enroll(client, project)).json()
    await ask(client, f"/api/v1/pipeline-runs/{run['id']}")
    connection = await session.connection()
    def roundtrip(conn):
        migration = scripts().get_revision("d14e317ba9be").module
        with Operations.context(MigrationContext.configure(conn)):
            migration.downgrade()
            assert "run_decision_entries" not in inspect(conn).get_table_names()
            migration.upgrade()
        assert conn.scalar(text("SELECT count(*) FROM run_decision_entries")) == 1
        assert conn.scalar(text("SELECT count(*) FROM run_questions")) == 1
        assert "ix_run_decisions_waiting" in {r["name"] for r in inspect(conn).get_indexes("run_decision_entries")}
    await connection.run_sync(roundtrip)
