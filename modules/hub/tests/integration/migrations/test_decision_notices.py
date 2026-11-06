import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import inspect, text
from tests.integration.migrations.test_default_ai_catalogs import scripts

pytestmark = [pytest.mark.integration, pytest.mark.real_commit]


async def test_decision_notice_migration_roundtrip(session):
    connection = await session.connection()

    def roundtrip(conn):
        before = conn.scalar(text("SELECT count(*) FROM notification_channels"))
        migration = scripts().get_revision("a471ce28d100").module
        with Operations.context(MigrationContext.configure(conn)):
            migration.downgrade()
            assert "decision_notices" not in inspect(conn).get_table_names()
            migration.upgrade()
        assert conn.scalar(text("SELECT count(*) FROM notification_channels")) == before
        assert conn.scalar(text("SELECT count(*) FROM decision_subscriptions")) == 0
        assert {"channel_id", "destination_generation", "decision_key", "fingerprint"} == set(
            next(
                x
                for x in inspect(conn).get_unique_constraints("decision_notices")
                if x["name"] == "uq_decision_notice_generation"
            )["column_names"]
        )

    await connection.run_sync(roundtrip)
