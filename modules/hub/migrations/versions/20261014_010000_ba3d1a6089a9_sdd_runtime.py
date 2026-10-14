"""Name the SDD capability independently of its implementation; retain legacy evidence."""

import sqlalchemy as sa
from alembic import op

revision = "ba3d1a6089a9"
down_revision = "a92c095f8798"
branch_labels = None
depends_on = None


def _settle(column):
    # An immutable legacy snapshot must never resume against a different engine.
    op.execute(sa.text(f"""
        UPDATE execution_attempts SET state = 'failed', failure_code = 'SDD_RUNTIME_CHANGED',
            failure_detail = 'Register a new execution with the devkit-spec runtime',
            finished_at = CURRENT_TIMESTAMP
        WHERE state NOT IN ('completed', 'failed') AND pipeline_run_id IN
            (SELECT id FROM pipeline_runs WHERE {column} IS NOT NULL
             AND state NOT IN ('completed', 'failed', 'canceled'))
    """))
    op.execute(sa.text(f"""
        UPDATE pipeline_runs SET state = 'canceled',
            pause_reason = 'SDD runtime changed; retained as history. Register a new execution.',
            revision = revision + 1, lease_owner = NULL, lease_token = NULL,
            lease_expires_at = NULL, next_action_at = NULL
        WHERE {column} IS NOT NULL AND state NOT IN ('completed', 'failed', 'canceled')
    """))


def upgrade():
    _settle("specrig_snapshot")
    with op.batch_alter_table("pipeline_runs") as batch:
        batch.alter_column("specrig_snapshot", new_column_name="sdd_snapshot")
        batch.alter_column("specrig_progress", new_column_name="sdd_progress")
    op.execute(sa.text("UPDATE projects SET project_type = 'sdd' WHERE project_type = 'specrig'"))


def downgrade():
    _settle("sdd_snapshot")
    with op.batch_alter_table("pipeline_runs") as batch:
        batch.alter_column("sdd_snapshot", new_column_name="specrig_snapshot")
        batch.alter_column("sdd_progress", new_column_name="specrig_progress")
    op.execute(sa.text("UPDATE projects SET project_type = 'specrig' WHERE project_type = 'sdd'"))
