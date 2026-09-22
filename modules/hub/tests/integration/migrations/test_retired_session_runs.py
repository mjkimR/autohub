from alembic.migration import MigrationContext
from alembic.operations import Operations
from app.features.ai_catalogs.models import AICatalog, AICatalogSession
from app_testing_base import utc_now
from sqlalchemy import select
from tests.integration.migrations.test_default_ai_catalogs import scripts


async def test_rollback_preserves_nonadoption_verdict_and_upgrade_keeps_reports(session):
    catalog = AICatalog(key="retired", name="Jules", kind="jules", adapter="jules-api")
    session.add(catalog)
    await session.flush()
    row = AICatalogSession(
        ai_catalog_id=catalog.id,
        title="Kept",
        state="completed",
        work_type="task",
        pull_request_url="https://github.com/owner/repo/pull/1",
        pipeline_run_retired_at=utc_now(),
        result_summary="Report",
    )
    session.add(row)
    await session.flush()
    row_id = row.id
    connection = await session.connection()

    def roundtrip(sync_connection):
        with Operations.context(MigrationContext.configure(sync_connection)):
            migration = scripts().get_revision("a5e6f7a8b9c0").module
            migration.downgrade()
            migration.upgrade()

    await connection.run_sync(roundtrip)
    session.expire_all()
    restored = await session.scalar(select(AICatalogSession).where(AICatalogSession.id == row_id))
    assert restored.pipeline_run_retired_at is None
    assert "do not re-adopt" in restored.failure_detail
    assert restored.result_summary == "Report"
