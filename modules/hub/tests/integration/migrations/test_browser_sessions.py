from alembic.migration import MigrationContext
from alembic.operations import Operations
from app_prebuilt_auth.browser.models import BrowserSession
from app_prebuilt_auth.user.models import User
from sqlalchemy import inspect, select
from tests.integration.migrations.test_default_ai_catalogs import scripts


async def test_browser_session_migration_roundtrip_preserves_accounts(session):
    user = User(firstname="Existing", email="migration-browser@example.com")
    session.add(user)
    await session.flush()
    user_id = user.id
    connection = await session.connection()

    def roundtrip(sync_connection):
        with Operations.context(MigrationContext.configure(sync_connection)):
            migration = scripts().get_revision("d83ba105fc29").module
            migration.downgrade()
            assert "browser_sessions" not in inspect(sync_connection).get_table_names()
            migration.upgrade()
        columns = inspect(sync_connection).get_columns("browser_sessions")
        assert {column["name"] for column in columns} == set(BrowserSession.__table__.columns.keys())
        assert all(not column["nullable"] for column in columns)
        assert {index["name"] for index in inspect(sync_connection).get_indexes("browser_sessions")} == {
            "ix_browser_sessions_user_id", "ix_browser_sessions_expires_at"
        }

    await connection.run_sync(roundtrip)
    assert (await session.scalar(select(User).where(User.id == user_id))).email == "migration-browser@example.com"
