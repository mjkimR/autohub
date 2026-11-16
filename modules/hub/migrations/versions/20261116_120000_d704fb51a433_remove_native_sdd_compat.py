"""Remove unused native batch and built-in bridge storage."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "d704fb51a433"
down_revision = "c693ea40f322"
branch_labels = None
depends_on = None


def upgrade():
    convention = {"fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s"}
    member_fk = next(
        fk
        for fk in sa.inspect(op.get_bind()).get_foreign_keys("sdd_activity_claims")
        if fk["constrained_columns"] == ["member_id"]
    )
    constraint_name = member_fk["name"] or "fk_sdd_activity_claims_member_id_sdd_batch_members"
    with op.batch_alter_table("sdd_activity_claims", naming_convention=convention) as batch:
        batch.drop_constraint(constraint_name, type_="foreignkey")
        batch.drop_column("member_id")
    op.drop_table("sdd_batch_controls")
    op.drop_table("sdd_batch_members")
    op.drop_table("sdd_batches")
    op.drop_table("sdk_flow_pr_links")
    with op.batch_alter_table("pipeline_runs") as batch:
        batch.drop_column("sdd_progress")
    with op.batch_alter_table("run_resume_receipts") as batch:
        batch.drop_column("decision_evidence")


def identity_columns():
    return (
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade():
    # Freeze the migration schema; later model changes must not alter historical replay.
    json_type = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")
    op.add_column("pipeline_runs", sa.Column("sdd_progress", json_type, nullable=True))
    op.add_column("run_resume_receipts", sa.Column("decision_evidence", json_type, nullable=True))
    op.create_table(
        "sdd_batches",
        *identity_columns(),
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
    op.create_index(
        "uq_sdd_batch_exclusion",
        "sdd_batches",
        ["project_id"],
        unique=True,
        postgresql_where=sa.text("exclusion = true"),
        sqlite_where=sa.text("exclusion = true"),
    )
    op.create_table(
        "sdd_batch_members",
        *identity_columns(),
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
    op.create_table(
        "sdd_batch_controls",
        *identity_columns(),
        sa.Column("batch_id", sa.Uuid(), sa.ForeignKey("sdd_batches.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("actor", sa.String(255), nullable=False),
        sa.Column("request_digest", sa.String(64), nullable=False),
        sa.Column("action", sa.String(10), nullable=False),
        sa.UniqueConstraint("batch_id", "request_id"),
    )

    with op.batch_alter_table("sdd_activity_claims") as batch:
        batch.add_column(sa.Column("member_id", sa.Uuid(), nullable=True))
        batch.create_foreign_key(
            "fk_sdd_activity_claims_member_id_sdd_batch_members",
            "sdd_batch_members",
            ["member_id"],
            ["id"],
            ondelete="RESTRICT",
        )
    op.create_table(
        "sdk_flow_pr_links",
        sa.Column("pipeline_run_id", sa.Uuid(), sa.ForeignKey("pipeline_runs.id"), primary_key=True),
        sa.Column("flow_run_id", sa.Uuid(), sa.ForeignKey("sdk_flow_runs.id"), nullable=False, unique=True),
        sa.Column("evidence", json_type, nullable=False),
        sa.Column("delivery_attempt_id", sa.Uuid()),
        sa.Column("canceled", sa.Boolean(), nullable=False),
        sa.Column("approved_revision", sa.Integer()),
        sa.Column("approved_digest", sa.String(64)),
        sa.Column("approved_actor", sa.String(128)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
