from pathlib import Path
from uuid import uuid4

import pytest
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory
from app.features.ai_catalogs.models import AICatalog
from app.features.ai_catalogs.policies.daily_quota import DailyQuotaConfig
from app.features.configuration.connectors.models import Connector
from sqlalchemy import select, text

MIGRATIONS = Path(__file__).resolve().parents[3] / "migrations"
SEED_REVISION = "e3c4d5e6f7a8"


def scripts():
    config = Config()
    config.set_main_option("script_location", str(MIGRATIONS))
    return ScriptDirectory.from_config(config)


async def migrate(session, direction="upgrade"):
    connection = await session.connection()

    def run(sync_connection):
        with Operations.context(MigrationContext.configure(sync_connection)):
            revision = scripts().get_revision(SEED_REVISION)
            getattr(revision.module, direction)()

    await connection.run_sync(run)


async def catalogs(session):
    rows = await session.execute(select(AICatalog.__table__).order_by(AICatalog.key))
    return {row["key"]: dict(row) for row in rows.mappings()}


async def test_missing_catalogs_are_seeded_and_reapplication_preserves_them(session):
    await migrate(session)
    seeded = await catalogs(session)
    assert set(seeded) == {"personal-codex", "personal-jules"}
    assert seeded["personal-codex"]["adapter"] == "codex-github-mention"
    jules = seeded["personal-jules"]
    assert jules["kind"] == "jules" and jules["adapter"] == "jules-api"
    assert jules["connector_id"] is None and jules["enabled"]
    assert jules["configured_concurrency"] == 15
    assert DailyQuotaConfig.model_validate(jules["policy_config"]).daily_task_limit == 100
    await migrate(session)
    await migrate(session, "downgrade")
    assert await catalogs(session) == seeded


@pytest.mark.parametrize("existing_key", ["personal-codex", "personal-jules"])
async def test_existing_catalog_and_custom_account_are_untouched(session, existing_key):
    connector = Connector(
        name="Existing Jules",
        provider="jules",
        credentials_ciphertext=b"test-only",
        credentials_nonce=b"123456789012",
        credential_key_version="test-version",
    )
    session.add(connector)
    await session.flush()
    for key in (existing_key, "custom-account"):
        session.add(
            AICatalog(
                key=key,
                name="Operator configured account",
                kind="jules",
                adapter="jules-api",
                connector_id=connector.id,
                enabled=False,
                availability_state="disabled",
                availability_note="Keep this operator hold",
                configured_concurrency=2,
                refresh_jitter_minutes=3,
                policy_config={"daily_task_limit": 7, "window": "rolling", "timezone": "UTC"},
                policy_state={"operator_marker": "preserve"},
                revision=9,
            )
        )
    await session.flush()
    before = await catalogs(session)
    await migrate(session)
    after = await catalogs(session)
    assert set(after) == {"personal-codex", "personal-jules", "custom-account"}
    for key, row in before.items():
        assert after[key] == row


async def test_fresh_postgres_migration_chain_includes_default_catalogs(session):
    connection = await session.connection()
    if connection.dialect.name != "postgresql":
        pytest.skip("Full migration chain requires PostgreSQL")
    # A transaction-local schema exercises the actual migrations instead of the
    # metadata-created fixture tables. Rollback removes the schema and its data.
    async with session.begin_nested() as transaction:
        schema = "catalog_migration_" + uuid4().hex
        await session.execute(text(f'CREATE SCHEMA "{schema}"'))
        await session.execute(text(f'SET LOCAL search_path TO "{schema}"'))

        def run(sync_connection):
            with Operations.context(MigrationContext.configure(sync_connection)):
                for revision in reversed(list(scripts().walk_revisions())):
                    revision.module.upgrade()

        await connection.run_sync(run)
        assert set(await catalogs(session)) == {"personal-codex", "personal-jules"}
        await transaction.rollback()
