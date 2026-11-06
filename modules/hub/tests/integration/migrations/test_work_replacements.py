import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import inspect,text
from tests.integration.migrations.test_default_ai_catalogs import scripts

pytestmark=[pytest.mark.integration,pytest.mark.real_commit]

async def test_replacement_migration_roundtrip_preserves_legacy(session):
    conn=await session.connection()
    def check(connection):
        before=connection.scalar(text('SELECT count(*) FROM work_items'))
        migration=scripts().get_revision('f36a539dc10e').module
        with Operations.context(MigrationContext.configure(connection)):
            migration.downgrade()
            assert 'work_replacement_links' not in inspect(connection).get_table_names()
            migration.upgrade()
        assert connection.scalar(text('SELECT count(*) FROM work_items'))==before
        for table in ('work_replacement_links','work_replacement_acceptances','work_replacement_events','work_replacement_receipts','work_replacement_evidence'):
            assert connection.scalar(text(f'SELECT count(*) FROM {table}'))==0
        assert 'uq_replacement_active_original' in {i['name'] for i in inspect(connection).get_indexes('work_replacement_links')}
        assert scripts().get_heads()==['b582df39e211']
    await conn.run_sync(check)
