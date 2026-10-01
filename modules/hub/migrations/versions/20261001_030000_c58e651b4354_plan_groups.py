"""Add optional Work Plan classification without execution isolation."""

import sqlalchemy as sa
from alembic import op

revision = "c58e651b4354"
down_revision = "b47d540a3243"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("work_plans", sa.Column("group_key", sa.String(100), nullable=True))
    op.create_index("ix_work_plans_project_group", "work_plans", ["project_id", "group_key"])


def downgrade():
    op.drop_index("ix_work_plans_project_group", table_name="work_plans")
    op.drop_column("work_plans", "group_key")
