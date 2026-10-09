"""Claim existing PR runs for SDK flow observation and replay-safe resume."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "e70a873d6576"
down_revision = "d69f762c5465"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "sdk_flow_pr_links",
        sa.Column("pipeline_run_id", sa.Uuid(), sa.ForeignKey("pipeline_runs.id"), primary_key=True),
        sa.Column("flow_run_id", sa.Uuid(), sa.ForeignKey("sdk_flow_runs.id"), nullable=False, unique=True),
        sa.Column("evidence", sa.JSON().with_variant(JSONB, "postgresql"), nullable=False),
        sa.Column("delivery_attempt_id", sa.Uuid()),
        sa.Column("canceled", sa.Boolean(), nullable=False),
        sa.Column("approved_revision", sa.Integer()),
        sa.Column("approved_digest", sa.String(64)),
        sa.Column("approved_actor", sa.String(128)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade():
    op.drop_table("sdk_flow_pr_links")
