"""Add rebuildable decision discovery and bootstrap persisted owners in bounded batches."""

import sqlalchemy as sa
from alembic import op

revision = "d14e317ba9be"
down_revision = "c03d206a98ad"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("run_decision_entries",
        sa.Column("key", sa.String(255), primary_key=True),
        sa.Column("run_id", sa.Uuid(), sa.ForeignKey("pipeline_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", sa.String(40), nullable=False),
        sa.Column("subject_id", sa.String(255), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("question_state", sa.String(30)),
        sa.Column("actionable", sa.Boolean(), nullable=False),
        sa.Column("waiting_since", sa.DateTime(timezone=True), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("head_sha", sa.String(64)),
    )
    op.create_index("ix_run_decision_entries_run_id", "run_decision_entries", ["run_id"])
    op.create_index("ix_run_decisions_waiting", "run_decision_entries", ["waiting_since", "key"])
    op.create_index("ix_run_decisions_project_waiting", "run_decision_entries", ["project_id", "waiting_since", "key"])
    op.create_index("ix_run_decisions_kind_waiting", "run_decision_entries", ["kind", "waiting_since", "key"])
    # Discovery is rebuildable, with no authoritative records synthesized.
    from app.features.project_management.pipeline_runs.discovery_projection import sync_run
    from app.features.project_management.pipeline_runs.models import PipelineRun
    from app_layer_base.utils.time_util import get_current_utc_time

    connection = op.get_bind()
    now, after = get_current_utc_time(), None
    while True:
        statement = sa.select(PipelineRun.id).order_by(PipelineRun.id).limit(100)
        if after is not None:
            statement = statement.where(PipelineRun.id > after)
        ids = list(connection.scalars(statement))
        if not ids:
            break
        for run_id in ids:
            sync_run(connection, run_id, now)
        after = ids[-1]


def downgrade():
    op.drop_table("run_decision_entries")
