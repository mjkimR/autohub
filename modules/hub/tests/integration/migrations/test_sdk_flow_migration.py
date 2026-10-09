from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from alembic.operations import Operations
from app_layer_base.base.models.mixin import Base
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import create_async_engine

from tests.integration.migrations.test_default_ai_catalogs import scripts


async def test_sdk_flow_migration_roundtrip(session):
    def roundtrip(connection):
        with Operations.context(MigrationContext.configure(connection)):
            migration = scripts().get_revision("d69f762c5465").module
            bridge = scripts().get_revision("e70a873d6576").module
            bridge.downgrade()
            migration.downgrade()
            assert not any(name.startswith("sdk_flow_") for name in inspect(connection).get_table_names())
            migration.upgrade()
            bridge.upgrade()
        context = MigrationContext.configure(connection, opts={
            "include_object": lambda obj, name, kind, reflected, compare_to: name.startswith("sdk_flow_") if kind == "table" else True,
        })
        assert compare_metadata(context, Base.metadata) == []

    if session.get_bind().dialect.name == "sqlite":
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        try:
            async with engine.begin() as connection:
                await connection.run_sync(lambda connection: Base.metadata.create_all(
                    connection, tables=[table for table in Base.metadata.sorted_tables if table.name.startswith("sdk_flow_")]))
                await connection.run_sync(roundtrip)
        finally:
            await engine.dispose()
    else:
        await (await session.connection()).run_sync(roundtrip)
