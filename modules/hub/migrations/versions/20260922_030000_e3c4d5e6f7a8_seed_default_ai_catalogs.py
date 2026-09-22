"""Restore the default AI catalogs omitted from the consolidated initial schema."""

from alembic import op

revision = "e3c4d5e6f7a8"
down_revision = "d2b3c4d5e6f7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Keys identify operator-owned accounts. Never replace their IDs, credentials,
    # policy, enabled state, or quota history when repairing an existing database.
    # Hex UUID literals work with both PostgreSQL UUID and SQLite's UUID storage.
    op.execute("""
        INSERT INTO ai_catalogs (
            id, key, name, kind, adapter, connector_id, enabled,
            availability_state, configured_concurrency, refresh_jitter_minutes,
            policy_config, policy_state, revision
        ) VALUES (
            '19d3207380944df78eb38c9ba910538b',
            'personal-codex', 'Personal Codex', 'codex', 'codex-github-mention',
            NULL, true, 'normal', 1, 10, '{}', '{}', 1
        ), (
            'da55dcf60b484f38bd6035a4d8746257',
            'personal-jules', 'Personal Jules', 'jules', 'jules-api',
            NULL, true, 'normal', 15, 10,
            '{"daily_task_limit": 100, "window": "rolling", "timezone": "UTC"}', '{}', 1
        )
        ON CONFLICT (key) DO NOTHING
    """)


def downgrade() -> None:
    # Catalogs may now own projects, sessions, credentials, and quota history.
    # A data backfill cannot distinguish these from pre-existing operator data.
    pass
