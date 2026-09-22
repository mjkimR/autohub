"""Add Google identity login, approval history, and session revocation versions."""

import sqlalchemy as sa
from alembic import op

revision = "b6f7a8b9c0d1"
down_revision = "a5e6f7a8b9c0"
branch_labels = None
depends_on = None


def timestamps():
    return [sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)]


def upgrade() -> None:
    # Existing local accounts retain their access and existing version-zero tokens.
    op.add_column("users", sa.Column("approval_status", sa.String(16), nullable=False, server_default="approved"))
    op.add_column("users", sa.Column("auth_version", sa.Integer(), nullable=False, server_default="0"))
    op.create_table("user_access_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("actor_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("action", sa.String(32), nullable=False), sa.Column("reason", sa.String(500)), *timestamps())
    op.create_index("ix_user_access_events_user_id", "user_access_events", ["user_id"])
    op.create_table("user_external_identities",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("issuer", sa.String(255), nullable=False), sa.Column("subject", sa.String(255), nullable=False),
        *timestamps(), sa.UniqueConstraint("issuer", "subject", name="uq_user_external_identity"))
    op.create_index("ix_user_external_identities_user_id", "user_external_identities", ["user_id"])
    op.create_table("google_login_flows",
        sa.Column("key", sa.String(64), primary_key=True), sa.Column("browser_hash", sa.String(64), nullable=False),
        sa.Column("nonce", sa.String(128)), sa.Column("verifier", sa.String(128)),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_google_login_flows_expires_at", "google_login_flows", ["expires_at"])


def downgrade() -> None:
    # A downgraded server has no approval gate. Never silently re-enable these accounts.
    op.execute("UPDATE users SET is_active = false WHERE approval_status <> 'approved' OR auth_version > 0")
    op.drop_table("google_login_flows")
    op.drop_table("user_external_identities")
    op.drop_table("user_access_events")
    op.drop_column("users", "auth_version")
    op.drop_column("users", "approval_status")
