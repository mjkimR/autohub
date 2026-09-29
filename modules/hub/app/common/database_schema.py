"""Optional PostgreSQL schema isolation for runtime transactions and Alembic."""

from __future__ import annotations

import os
import re

from sqlalchemy import event, text
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.schema import CreateSchema


def database_schema(dialect: str) -> str | None:
    """SQLite and deployments without DB_SCHEMA retain their existing behavior."""
    if dialect != "postgresql":
        return None
    schema = os.environ.get("DB_SCHEMA", "").strip()
    if not schema:
        return None
    if not re.fullmatch(r"[a-z_][a-z0-9_]{0,62}", schema) or schema.startswith("pg_"):
        raise ValueError("DB_SCHEMA must be a lowercase PostgreSQL identifier (at most 63 characters)")
    if schema in {"information_schema", "extensions", "auth", "storage"}:
        raise ValueError("DB_SCHEMA must name an application schema")
    return schema


def _set_schema_path(connection: Connection) -> None:
    schema = connection.get_execution_options()["app_db_schema"]
    # SET LOCAL is reapplied for every transaction, including after commit/rollback.
    # A missing schema must fail rather than silently fall back to another namespace.
    selected = connection.scalar(
        text(
            "SELECT pg_catalog.set_config('search_path', :path, true) "
            "FROM pg_catalog.pg_namespace WHERE nspname = :schema"
        ),
        {"path": f'"{schema}", extensions', "schema": schema},
    )
    if selected is None:
        raise RuntimeError("DB_SCHEMA does not exist; run Alembic upgrade head first")


def _connection_parameters(dialect, connection_record, cargs, cparams) -> None:
    if dialect.driver == "psycopg":
        # Supavisor transaction mode does not support prepared statements.
        cparams["prepare_threshold"] = None


def configure_schema(engine: AsyncEngine) -> None:
    """Configure an engine before its first use; safe to call more than once."""
    schema = database_schema(engine.dialect.name)
    if schema is None:
        return
    target = engine.sync_engine
    target.update_execution_options(app_db_schema=schema)
    if not event.contains(target, "begin", _set_schema_path):
        event.listen(target, "begin", _set_schema_path)
        event.listen(target, "do_connect", _connection_parameters)


def prepare_migration_schema(connection: Connection) -> str | None:
    """Create the namespace before Alembic attempts to create its version table."""
    schema = database_schema(connection.dialect.name)
    if schema is not None:
        connection.execute(CreateSchema(schema, if_not_exists=True))
        connection.commit()
        connection.execution_options(app_db_schema=schema)
        event.listen(connection, "begin", _set_schema_path)
        # Alembic's unqualified models/reflection must agree on the selected schema.
        connection.dialect.default_schema_name = schema
    return schema


def offline_schema_sql(schema: str) -> tuple[str, str]:
    """Emit within the offline migration transaction, before version-table DDL."""
    return (
        f'CREATE SCHEMA IF NOT EXISTS "{schema}"',
        f'SET LOCAL search_path TO "{schema}", extensions',
    )


def include_schema_object(obj, name, type_, reflected, compare_to) -> bool:
    """The version table reflects as unqualified under the selected search_path."""
    return not (reflected and type_ == "table" and name == "alembic_version")
