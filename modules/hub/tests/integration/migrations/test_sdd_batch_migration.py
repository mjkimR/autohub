import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import inspect, text

from tests.integration.migrations.test_default_ai_catalogs import scripts

pytestmark = [pytest.mark.integration, pytest.mark.real_commit]


async def test_sdd_batch_migration_roundtrip_preserves_projects(session):
    connection = await session.connection()

    def roundtrip(conn):
        before = conn.scalar(text("SELECT count(*) FROM projects"))
        migration = scripts().get_revision("e25f428cba0f").module
        with Operations.context(MigrationContext.configure(conn)):
            migration.downgrade()
            assert "sdd_batches" not in inspect(conn).get_table_names()
            migration.upgrade()
        tables = inspect(conn).get_table_names()
        assert all(name in tables for name in ("sdd_batches", "sdd_batch_members", "sdd_activity_claims", "sdd_batch_controls"))
        assert conn.scalar(text("SELECT count(*) FROM projects")) == before
        assert "uq_sdd_batch_exclusion" in {r["name"] for r in inspect(conn).get_indexes("sdd_batches")}
        assert scripts().get_heads() == ["a471ce28d100"]

    await connection.run_sync(roundtrip)
