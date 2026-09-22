from alembic.migration import MigrationContext
from alembic.operations import Operations
from app_prebuilt_auth.user.models import User
from sqlalchemy import select
from tests.integration.migrations.test_default_ai_catalogs import scripts


async def test_rollback_blocks_unapproved_and_revoked_accounts(session):
    existing = User(firstname="Existing", email="existing@example.com")
    pending = User(firstname="Pending", email="pending@example.com", approval_status="pending")
    revoked = User(firstname="Revoked", email="revoked@example.com", auth_version=2)
    session.add_all([existing, pending, revoked])
    await session.flush()
    connection = await session.connection()

    def roundtrip(sync_connection):
        with Operations.context(MigrationContext.configure(sync_connection)):
            migration = scripts().get_revision("b6f7a8b9c0d1").module
            migration.downgrade()
            migration.upgrade()

    await connection.run_sync(roundtrip)
    session.expire_all()
    users = {user.email: user for user in await session.scalars(select(User))}
    assert users["existing@example.com"].is_active
    assert users["existing@example.com"].approval_status == "approved"
    assert users["existing@example.com"].auth_version == 0
    assert not users["pending@example.com"].is_active
    assert not users["revoked@example.com"].is_active
