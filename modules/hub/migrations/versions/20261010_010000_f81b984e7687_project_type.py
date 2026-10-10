"""Add project_type to projects."""

import sqlalchemy as sa
from alembic import op

revision = "f81b984e7687"
down_revision = "e70a873d6576"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "projects",
        sa.Column("project_type", sa.String(50), nullable=False, server_default="general"),
    )


def downgrade():
    op.drop_column("projects", "project_type")
