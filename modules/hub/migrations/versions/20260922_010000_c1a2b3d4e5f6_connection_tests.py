"""Persist isolated connection tests and their cleanup lifecycle."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "c1a2b3d4e5f6"
down_revision = "574ca96e6e8e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    json_type = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")
    op.create_table(
        "connection_tests",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("project_id", sa.UUID(), sa.ForeignKey("projects.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("project_revision", sa.Integer(), nullable=False),
        sa.Column("repository", sa.String(255), nullable=False),
        sa.Column("connector_id", sa.UUID(), nullable=False),
        sa.Column("verification", json_type, nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("phase", sa.String(30), nullable=False),
        sa.Column("cleanup_status", sa.String(30), nullable=False),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("evidence", json_type, nullable=False),
        sa.Column("deadline", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lease_token", sa.UUID(), nullable=True),
        sa.Column("lease_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_requested", sa.Boolean(), nullable=False),
    )
    op.create_index("ix_connection_tests_project_created", "connection_tests", ["project_id", "created_at"])
    op.create_index("uq_connection_tests_active_project", "connection_tests", ["project_id"], unique=True,
        postgresql_where=sa.text("status = 'running'"), sqlite_where=sa.text("status = 'running'"))


def downgrade() -> None:
    op.drop_table("connection_tests")
