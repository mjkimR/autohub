from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from alembic.operations import Operations
from app_layer_base.base.models.mixin import Base
from sqlalchemy import UUID, inspect
from tests.integration.migrations.test_default_ai_catalogs import scripts


async def test_run_pull_observation_migration_roundtrip(session):
    connection = await session.connection()

    def roundtrip(sync):
        with Operations.context(MigrationContext.configure(sync)):
            migration = scripts().get_revision("e81f4c2a9b37").module
            migration.downgrade()
            assert "pull_observation" not in {column["name"] for column in inspect(sync).get_columns("pipeline_runs")}
            migration.upgrade()
        context = MigrationContext.configure(
            sync,
            opts={
                "compare_type": lambda context, col, meta, reflected, model: (
                    False if context.dialect.name == "sqlite" and isinstance(model, UUID) else None
                ),
                "include_object": lambda obj, name, kind, reflected, compare_to: (
                    name == "pipeline_runs" if kind == "table" else True
                ),
            },
        )
        assert compare_metadata(context, Base.metadata) == []

    await connection.run_sync(roundtrip)
    await session.commit()
