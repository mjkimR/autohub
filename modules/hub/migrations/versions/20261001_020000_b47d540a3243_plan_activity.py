"""Persist Work Plan discussion and change history."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "b47d540a3243"
down_revision = "a36c439f2132"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "work_plan_activities",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("plan_id", sa.Uuid(), sa.ForeignKey("work_plans.id", ondelete="CASCADE"), nullable=False),
        sa.Column("request_id", sa.Uuid()),
        sa.Column("kind", sa.String(30), nullable=False),
        sa.Column("actor", sa.String(255), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("changes", sa.JSON().with_variant(postgresql.JSONB(), "postgresql"), nullable=False),
        sa.UniqueConstraint("plan_id", "request_id", name="uq_work_plan_comment_request"),
    )
    op.create_index("ix_work_plan_activities_plan_id", "work_plan_activities", ["plan_id"])


def downgrade():
    # Old clients do not understand draft/proposed or incomplete/empty plans.
    # Refuse rollback until these plans have been made ready or withdrawn.
    bind = op.get_bind()
    if bind.scalar(sa.text("SELECT count(*) FROM work_plans WHERE state IN ('draft', 'proposed')")):
        raise RuntimeError("Make draft/proposed plans ready or revoke them before downgrading")
    op.drop_table("work_plan_activities")
