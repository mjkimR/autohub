from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from alembic.operations import Operations
from app_layer_base.base.models.mixin import Base
from sqlalchemy import UUID, inspect
from tests.integration.migrations.test_default_ai_catalogs import scripts


async def test_run_decisions_migration_roundtrip(session):
    connection = await session.connection()

    def roundtrip(sync):
        with Operations.context(MigrationContext.configure(sync)):
            specrig = scripts().get_revision("a92c095f8798").module
            specrig.downgrade()
            migration = scripts().get_revision("e14a217d0910").module
            migration.downgrade()
            assert "run_questions" not in inspect(sync).get_table_names()
            migration.upgrade()
            specrig.upgrade()
        context = MigrationContext.configure(
            sync,
            opts={
                "compare_type": lambda context, col, meta, reflected, model: (
                    False if context.dialect.name == "sqlite" and isinstance(model, UUID) else None
                ),
                "include_object": lambda obj, name, kind, reflected, compare_to: (
                    name in {"run_questions", "run_answers", "run_resume_receipts"} if kind == "table" else True
                ),
            },
        )
        assert compare_metadata(context, Base.metadata) == []

    await connection.run_sync(roundtrip)
