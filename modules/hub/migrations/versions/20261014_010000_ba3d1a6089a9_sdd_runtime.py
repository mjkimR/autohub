"""Name the SDD capability independently of its implementation."""

import sqlalchemy as sa
from alembic import op

revision = "ba3d1a6089a9"
down_revision = "a92c095f8798"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("pipeline_runs") as batch:
        batch.alter_column("specrig_snapshot", new_column_name="sdd_snapshot")
        batch.alter_column("specrig_progress", new_column_name="sdd_progress")
    op.execute(sa.text("UPDATE projects SET project_type = 'sdd' WHERE project_type = 'specrig'"))


def downgrade():
    with op.batch_alter_table("pipeline_runs") as batch:
        batch.alter_column("sdd_snapshot", new_column_name="specrig_snapshot")
        batch.alter_column("sdd_progress", new_column_name="specrig_progress")
    op.execute(sa.text("UPDATE projects SET project_type = 'specrig' WHERE project_type = 'sdd'"))
