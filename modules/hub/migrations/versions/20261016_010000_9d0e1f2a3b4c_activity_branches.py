"""Record an explicitly attached activity branch on work items (strategy layer 01 section 4.7)."""

import sqlalchemy as sa
from alembic import op

revision = "9d0e1f2a3b4c"
down_revision = "ba3d1a6089a9"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("work_items") as batch:
        batch.add_column(sa.Column("attach_branch", sa.String(length=64), nullable=True))


def downgrade():
    with op.batch_alter_table("work_items") as batch:
        batch.drop_column("attach_branch")
