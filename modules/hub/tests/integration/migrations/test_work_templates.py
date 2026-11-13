import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import inspect
from tests.integration.migrations.test_default_ai_catalogs import scripts

pytestmark = [pytest.mark.integration, pytest.mark.real_commit]


async def test_template_migration_roundtrip(session):
    connection = await session.connection()
    def roundtrip(conn):
        migration = scripts().get_revision("b582df39e211").module
        with Operations.context(MigrationContext.configure(conn)):
            migration.downgrade()
            assert "work_plan_templates" not in inspect(conn).get_table_names()
            migration.upgrade()
        assert "work_template_requests" in inspect(conn).get_table_names()
        assert scripts().get_heads() == ["c693ea40f322"]
    await connection.run_sync(roundtrip)
