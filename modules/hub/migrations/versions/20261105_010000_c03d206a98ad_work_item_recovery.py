"""Add typed Work Item recovery history without synthesizing legacy attempts."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "c03d206a98ad"
down_revision = "9d0e1f2a3b4c"
branch_labels = None
depends_on = None


def upgrade():
    json_type = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")
    op.create_table(
        "work_item_recoveries",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("plan_id", sa.Uuid(), sa.ForeignKey("work_plans.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("item_id", sa.Uuid(), sa.ForeignKey("work_items.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("request_digest", sa.String(64), nullable=False),
        sa.Column("actor", sa.String(255), nullable=False),
        sa.Column("reason", sa.String(500), nullable=False),
        sa.Column("command", json_type, nullable=False),
        sa.Column("prior_outcome", json_type, nullable=False),
        sa.Column("accepted_revision", sa.Integer(), nullable=False),
        sa.Column("accepted_run_revision", sa.Integer()),
        sa.Column("state", sa.String(30), nullable=False),
        sa.Column("detail", sa.Text(), nullable=False),
        sa.Column("lease_generation", sa.Integer(), nullable=False),
        sa.UniqueConstraint("project_id", "request_id", name="uq_work_item_recovery_request"),
    )
    for column in ("plan_id", "item_id"):
        op.create_index("ix_work_item_recoveries_" + column, "work_item_recoveries", [column])
    predicate = sa.text("state IN ('accepted', 'reconciling', 'awaiting-admission')")
    op.create_index(
        "uq_work_item_pending_recovery",
        "work_item_recoveries",
        ["item_id"],
        unique=True,
        postgresql_where=predicate,
        sqlite_where=predicate,
    )
    op.create_table(
        "work_item_recovery_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "recovery_id", sa.Uuid(), sa.ForeignKey("work_item_recoveries.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.UniqueConstraint("recovery_id", "sequence", name="uq_work_item_recovery_event_sequence"),
        sa.Column("kind", sa.String(30), nullable=False),
        sa.Column("detail", sa.Text(), nullable=False),
        sa.Column("evidence", json_type, nullable=False),
    )
    op.create_index("ix_work_item_recovery_events_recovery_id", "work_item_recovery_events", ["recovery_id"])


def downgrade():
    op.drop_table("work_item_recovery_events")
    op.drop_table("work_item_recoveries")
