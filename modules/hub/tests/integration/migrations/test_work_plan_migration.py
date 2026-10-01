from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from alembic.operations import Operations
from app_layer_base.base.models.mixin import Base
from sqlalchemy import inspect, UUID
from sqlalchemy.ext.asyncio import create_async_engine
from tests.integration.migrations.test_default_ai_catalogs import scripts


async def test_work_plan_migration_roundtrip_matches_metadata(session):
    def roundtrip(sync_connection):
        with Operations.context(MigrationContext.configure(sync_connection)):
            groups = scripts().get_revision("c58e651b4354").module
            groups.downgrade()
            activity = scripts().get_revision("b47d540a3243").module
            activity.downgrade()
            schedule = scripts().get_revision("a36c439f2132").module
            schedule.downgrade()
            registration = scripts().get_revision("f25b328e1021").module
            registration.downgrade()
            migration = scripts().get_revision("c7d8e9f0a1b2").module
            migration.downgrade()
            assert "work_plans" not in inspect(sync_connection).get_table_names()
            migration.upgrade()
            registration.upgrade()
            schedule.upgrade()
            activity.upgrade()
            groups.upgrade()
        context = MigrationContext.configure(
            sync_connection,
            opts={
                "compare_type": lambda context, col, meta, reflected, model: (
                    False if context.dialect.name == "sqlite" and isinstance(model, UUID) else None
                ),
                "include_object": lambda obj, name, kind, reflected, compare_to: (
                    name.startswith("work_") if kind == "table" else True
                ),
            },
        )
        assert compare_metadata(context, Base.metadata) == []

    if session.get_bind().dialect.name == "sqlite":
        # SQLite DDL is not reliably rolled back, and historical migrations use
        # PostgreSQL defaults. Keep the roundtrip off the shared application DB.
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        try:
            async with engine.begin() as connection:
                await connection.run_sync(Base.metadata.create_all)
                await connection.run_sync(roundtrip)
        finally:
            await engine.dispose()
    else:
        connection = await session.connection()
        await connection.run_sync(roundtrip)
