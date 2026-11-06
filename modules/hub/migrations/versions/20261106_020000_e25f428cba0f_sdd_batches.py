"""Retain selected native SDD batches and exact admission checkpoints."""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "e25f428cba0f"
down_revision = "d14e317ba9be"
branch_labels = None
depends_on = None


def identity_columns():
    return (
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def upgrade():
    # Freeze the migration schema; later model changes must not alter historical replay.
    json_type = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")
    op.create_table("sdd_batches", *identity_columns(),
        sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("request_digest", sa.String(64), nullable=False),
        sa.Column("actor", sa.String(255), nullable=False),
        sa.Column("state", sa.String(30), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("exclusion", sa.Boolean(), nullable=False),
        sa.Column("basis", json_type, nullable=False),
        sa.Column("evaluation", json_type, nullable=False),
        sa.Column("detail", sa.String(2048)),
        sa.UniqueConstraint("project_id", "request_id"),
    )
    op.create_index("uq_sdd_batch_exclusion", "sdd_batches", ["project_id"], unique=True,
        postgresql_where=sa.text("exclusion = true"), sqlite_where=sa.text("exclusion = true"))
    op.create_table("sdd_batch_members", *identity_columns(),
        sa.Column("batch_id", sa.Uuid(), sa.ForeignKey("sdd_batches.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("anchor_id", sa.String(255), nullable=False),
        sa.Column("path", sa.String(1024), nullable=False),
        sa.Column("initial", json_type, nullable=False),
        sa.Column("phase", sa.String(30), nullable=False),
        sa.Column("state", sa.String(30), nullable=False),
        sa.Column("spec_anchor", json_type),
        sa.Column("outcome", json_type),
        sa.UniqueConstraint("batch_id", "position"),
        sa.UniqueConstraint("batch_id", "anchor_id"),
    )
    op.create_table("sdd_activity_claims", *identity_columns(),
        sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("member_id", sa.Uuid(), sa.ForeignKey("sdd_batch_members.id", ondelete="RESTRICT")),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("actor", sa.String(255), nullable=False),
        sa.Column("request_digest", sa.String(64), nullable=False),
        sa.Column("unit", sa.String(255), nullable=False),
        sa.Column("activity", sa.String(10), nullable=False),
        sa.Column("settled", sa.Boolean(), nullable=False),
        sa.Column("checkpoint", json_type, nullable=False),
        sa.Column("run_id", sa.Uuid(), sa.ForeignKey("pipeline_runs.id", ondelete="RESTRICT")),
        sa.UniqueConstraint("project_id", "request_id"),
    )
    op.create_index("uq_sdd_activity_claim_live", "sdd_activity_claims", ["project_id", "unit", "activity"], unique=True,
        postgresql_where=sa.text("settled = false"), sqlite_where=sa.text("settled = false"))
    op.create_table("sdd_batch_controls", *identity_columns(),
        sa.Column("batch_id", sa.Uuid(), sa.ForeignKey("sdd_batches.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("actor", sa.String(255), nullable=False),
        sa.Column("request_digest", sa.String(64), nullable=False),
        sa.Column("action", sa.String(10), nullable=False),
        sa.UniqueConstraint("batch_id", "request_id"),
    )


def downgrade():
    for name in ("sdd_batch_controls", "sdd_activity_claims", "sdd_batch_members", "sdd_batches"):
        op.drop_table(name)
