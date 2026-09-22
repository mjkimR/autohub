from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from alembic.operations import Operations
from app_layer_base.base.models.mixin import Base
from sqlalchemy import inspect, UUID
from tests.integration.migrations.test_default_ai_catalogs import scripts


async def test_work_plan_migration_roundtrip_matches_metadata(session):
    connection = await session.connection()

    def roundtrip(sync_connection):
        with Operations.context(MigrationContext.configure(sync_connection)):
            migration = scripts().get_revision('c7d8e9f0a1b2').module
            migration.downgrade()
            assert 'work_plans' not in inspect(sync_connection).get_table_names()
            migration.upgrade()
        context = MigrationContext.configure(sync_connection, opts={
            'compare_type': lambda context, col, meta, reflected, model: False if context.dialect.name == 'sqlite' and isinstance(model, UUID) else None,
            'include_object': lambda obj, name, kind, reflected, compare_to: (
                name.startswith('work_') if kind == 'table' else True
            ),
        })
        assert compare_metadata(context, Base.metadata) == []

    await connection.run_sync(roundtrip)
