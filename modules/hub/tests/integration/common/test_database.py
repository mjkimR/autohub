"""Opt-in real PostgreSQL coverage: TEST_SCHEMA_DATABASE_URL must name a disposable DB."""

import asyncio
import os
import subprocess
import sys
import uuid
from pathlib import Path

import pytest
from app.common.database_schema import configure_schema
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.schema import CreateSchema, DropSchema

ROOT = Path(__file__).resolve().parents[3]
URL = os.environ.get("TEST_SCHEMA_DATABASE_URL", "")
pytestmark = pytest.mark.skipif(not URL, reason="set TEST_SCHEMA_DATABASE_URL to an isolated PostgreSQL DB")


def test_schema_migrations_and_transaction_isolation(monkeypatch):
    schema = "schema_test_" + uuid.uuid4().hex
    sibling = "schema_other_" + uuid.uuid4().hex
    engine = create_engine(URL)
    env = {
        **os.environ,
        "DB_SCHEMA": schema,
        "DATABASE_URL": URL,
        "ENV": "__schema_test__",
        "PLANROOT_ENV_FILE": "",
        "APP_SECRETS_JSON": "",
        "FIRST_USER_EMAIL": "test@example.com",
        "FIRST_USER_PASSWORD": "test-only-password",
        "SECRET_KEY": "test-only-signing-key",
    }

    def migrate(*args):
        result = subprocess.run(
            [sys.executable, "-m", "alembic", *args],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        return result.stdout

    try:
        with engine.begin() as connection:
            connection.execute(CreateSchema(sibling))
            connection.execute(text(f'CREATE TABLE "{sibling}".untouched (value integer)'))
            connection.execute(text(f'INSERT INTO "{sibling}".untouched VALUES (42)'))
        migrate("upgrade", "head")
        migrate("upgrade", "head")
        migrate("check")
        with engine.connect() as connection:
            assert "alembic_version" in inspect(connection).get_table_names(schema=schema)
            assert "users" in inspect(connection).get_table_names(schema=schema)
        monkeypatch.setenv("DB_SCHEMA", schema)

        async def runtime():
            runtime_engine = create_async_engine(URL, pool_size=1, max_overflow=0)
            configure_schema(runtime_engine)
            configure_schema(runtime_engine)
            try:
                async with runtime_engine.connect() as connection:
                    for finish in (connection.commit, connection.rollback, connection.commit):
                        assert await connection.scalar(text("SELECT current_schema()")) == schema
                        await connection.execute(text("SELECT count(*) FROM users"))
                        await connection.execute(text(f'SET LOCAL search_path TO "{sibling}"'))
                        await finish()
                    driver = (await connection.get_raw_connection()).driver_connection
                    assert driver is not None
                    assert driver.prepare_threshold is None
            finally:
                await runtime_engine.dispose()

        asyncio.run(runtime())
        monkeypatch.setenv("DB_SCHEMA", "missing_" + uuid.uuid4().hex)

        async def missing_schema():
            missing_engine = create_async_engine(URL)
            configure_schema(missing_engine)
            try:
                with pytest.raises(RuntimeError, match="run Alembic upgrade head"):
                    async with missing_engine.begin():
                        pass
            finally:
                await missing_engine.dispose()

        asyncio.run(missing_schema())
        migrate("downgrade", "base")
        with engine.connect() as connection:
            assert inspect(connection).get_table_names(schema=schema) == ["alembic_version"]
            assert connection.scalar(text(f'SELECT value FROM "{sibling}".untouched')) == 42
        migrate("upgrade", "head")
        migrate("check")
    finally:
        with engine.begin() as connection:
            connection.execute(DropSchema(schema, cascade=True, if_exists=True))
            connection.execute(DropSchema(sibling, cascade=True, if_exists=True))
        engine.dispose()
