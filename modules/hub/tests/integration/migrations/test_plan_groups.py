import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import inspect, text
from tests.integration.features.project_management.work_plans.conftest import setup_work
from tests.integration.features.project_management.work_plans.test_work_plans import create, spec
from tests.integration.migrations.test_default_ai_catalogs import scripts

__all__ = ["setup_work"]
pytestmark = [pytest.mark.integration, pytest.mark.real_commit]


async def test_group_migration_preserves_existing_work_and_defaults_to_null(client, setup_work, session):
    project, _, _, _ = setup_work
    await create(client, project, spec(state="paused", group_key="game-a"))
    connection = await session.connection()

    def roundtrip(conn):
        migration = scripts().get_revision("c58e651b4354").module
        with Operations.context(MigrationContext.configure(conn)):
            migration.downgrade()
            assert "group_key" not in {c["name"] for c in inspect(conn).get_columns("work_plans")}
            assert conn.scalar(text("SELECT count(*) FROM work_plans")) == 1
            assert conn.scalar(text("SELECT count(*) FROM work_items")) == 2
            migration.upgrade()
        row = conn.execute(text("SELECT title, state, group_key FROM work_plans")).one()
        assert tuple(row) == ("Feature", "paused", None)
        assert "ix_work_plans_project_group" in {index["name"] for index in inspect(conn).get_indexes("work_plans")}

    await connection.run_sync(roundtrip)
    await session.commit()
