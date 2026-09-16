"""Add project agent schedules.

``project_agent_schedules`` is a project's recurring agent session (catalog, work type, prompt, trigger). Each row
owns one ``schedule_configs`` row, which the hub derives from it and the project on every save.

Revision ID: d6e7f8a9b0c1
Revises: c5d6e7f8a9b0
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d6e7f8a9b0c1"
down_revision: str | None = "c5d6e7f8a9b0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "project_agent_schedules",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("schedule_config_id", sa.Uuid(), nullable=False),
        sa.Column("ai_catalog_id", sa.Uuid(), nullable=False),
        sa.Column("work_type", sa.String(20), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("starting_branch", sa.String(255), nullable=False, server_default="main"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("cron_expression", sa.String(100), nullable=True),
        sa.Column("interval_seconds", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["schedule_config_id"], ["schedule_configs.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["ai_catalog_id"], ["ai_catalogs.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("schedule_config_id"),
    )
    op.create_index("ix_project_agent_schedules_project_id", "project_agent_schedules", ["project_id"], unique=False)
    op.create_index(
        "ix_project_agent_schedules_ai_catalog_id", "project_agent_schedules", ["ai_catalog_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_project_agent_schedules_ai_catalog_id", table_name="project_agent_schedules")
    op.drop_index("ix_project_agent_schedules_project_id", table_name="project_agent_schedules")
    op.drop_table("project_agent_schedules")
