"""Replace per-test and managed per-catalog polling with one installation schedule."""

import json

from alembic import op
from sqlalchemy import text

revision = "f4d5e6f7a8b9"
down_revision = "e3c4d5e6f7a8"
branch_labels = None
depends_on = None

SYSTEM_ID = "cd9c8a5570df4b91a9882b3e756c0110"


def upgrade() -> None:
    # These configs carry no domain state. Jobs and sessions retain history via SET NULL.
    # Delete only hub-owned entries; an operator-created sync remains operator-owned.
    owned = """
        SELECT id FROM schedule_configs
        WHERE (task_func = 'pipeline.connection_test' AND id IN (SELECT id FROM connection_tests))
           OR (task_func = 'jules.sync_sessions' AND EXISTS (
                SELECT 1 FROM ai_catalogs
                WHERE schedule_configs.name = 'Agent sync: ' || ai_catalogs.key
                  AND schedule_configs.payload ->> 'catalog_key' = ai_catalogs.key
           ))
    """
    # Explicitly detach history as well as relying on SET NULL, including SQLite
    # installations whose foreign-key enforcement has not been enabled.
    # Domain work is rediscovered by maintenance; detached jobs cannot be retried without a config.
    op.execute(f"""
        UPDATE schedule_jobs SET schedule_config_id = NULL, retry_need = false
        WHERE schedule_config_id IN ({owned})
    """)
    op.execute(f"UPDATE ai_catalog_sessions SET schedule_config_id = NULL WHERE schedule_config_id IN ({owned})")
    op.execute(f"DELETE FROM schedule_configs WHERE id IN ({owned})")
    op.execute(f"""
        INSERT INTO schedule_configs
            (id, name, description, task_func, interval_seconds, payload, enabled)
        VALUES ('{SYSTEM_ID}', 'System maintenance',
            'Progresses connection tests, cleans up test resources, and collects Jules session results',
            'system.maintain', 60, '{{}}', true)
        ON CONFLICT (id) DO NOTHING
    """)
    op.execute("""
        CREATE UNIQUE INDEX uq_schedule_configs_system_maintenance ON schedule_configs (task_func)
        WHERE task_func = 'system.maintain'
    """)


def downgrade() -> None:
    op.drop_index("uq_schedule_configs_system_maintenance", table_name="schedule_configs")
    removed = f"SELECT id FROM schedule_configs WHERE id = '{SYSTEM_ID}' AND task_func = 'system.maintain'"
    op.execute(f"""
        UPDATE schedule_jobs SET schedule_config_id = NULL, retry_need = false
        WHERE schedule_config_id IN ({removed})
    """)
    op.execute(f"UPDATE ai_catalog_sessions SET schedule_config_id = NULL WHERE schedule_config_id IN ({removed})")
    op.execute(f"DELETE FROM schedule_configs WHERE id = '{SYSTEM_ID}' AND task_func = 'system.maintain'")
    # Bind JSON as text on SQLite and cast on PostgreSQL; SQLite CAST(... AS JSON)
    # would coerce the document to a number instead of storing a JSON object.
    bind = op.get_bind()
    value = "CAST(:payload AS JSON)" if bind.dialect.name == "postgresql" else ":payload"
    statement = text(f"""
        INSERT INTO schedule_configs (id, name, task_func, interval_seconds, payload, enabled)
        VALUES (:id, :name, :task, :interval, {value}, true)
        ON CONFLICT (id) DO NOTHING
    """)
    for row in bind.execute(
        text("""
        SELECT id FROM connection_tests WHERE status = 'running' OR cleanup_status != 'completed'
    """)
    ).mappings():
        bind.execute(
            statement,
            {
                "id": str(row["id"]),
                "name": "Connection test " + str(row["id"]),
                "task": "pipeline.connection_test",
                "interval": 60,
                "payload": json.dumps({"test_id": str(row["id"])}),
            },
        )
    for row in bind.execute(
        text("""
        SELECT c.id, c.key FROM ai_catalogs c
        WHERE c.kind = 'jules' AND (
            EXISTS (SELECT 1 FROM project_agent_schedules a WHERE a.ai_catalog_id = c.id)
            OR EXISTS (SELECT 1 FROM ai_catalog_sessions s WHERE s.ai_catalog_id = c.id)
        ) AND NOT EXISTS (
            SELECT 1 FROM schedule_configs s WHERE s.task_func = 'jules.sync_sessions'
            AND s.name = 'Agent sync: ' || c.key AND s.payload ->> 'catalog_key' = c.key
        )
    """)
    ).mappings():
        bind.execute(
            statement,
            {
                "id": str(row["id"]),
                "name": "Agent sync: " + row["key"],
                "task": "jules.sync_sessions",
                "interval": 300,
                "payload": json.dumps({"catalog_key": row["key"]}),
            },
        )
