"""Schema settings reject unsafe identifiers and leave SQLite untouched."""

import asyncio

import pytest
from app.common.database_schema import configure_schema, database_schema
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


@pytest.mark.parametrize("value", ["bad-name", "x;drop schema public", "x" * 64, "pg_catalog", "extensions"])
def test_invalid_schema(value, monkeypatch):
    monkeypatch.setenv("DB_SCHEMA", value)
    with pytest.raises(ValueError, match="DB_SCHEMA"):
        database_schema("postgresql")
    assert database_schema("sqlite") is None


def test_schema_is_opt_in(monkeypatch):
    monkeypatch.delenv("DB_SCHEMA", raising=False)
    assert database_schema("postgresql") is None
    monkeypatch.setenv("DB_SCHEMA", "app_one")
    assert database_schema("postgresql") == "app_one"


def test_sqlite_ignores_schema(monkeypatch):
    monkeypatch.setenv("DB_SCHEMA", "app_one")

    async def run():
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        configure_schema(engine)
        try:
            async with engine.begin() as connection:
                assert await connection.scalar(text("SELECT 1")) == 1
        finally:
            await engine.dispose()

    asyncio.run(run())
