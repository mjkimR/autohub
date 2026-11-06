"""Add reusable Work Plan definitions and operation receipts."""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "b582df39e211"
down_revision = "a471ce28d100"
branch_labels = None
depends_on = None


def common():
    return [sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id", ondelete="RESTRICT"), nullable=False)]


def upgrade():
    j = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")
    op.create_table("work_plan_templates", *common(), sa.Column("name", sa.String(200), nullable=False), sa.Column("revision", sa.Integer(), nullable=False), sa.Column("deleted", sa.Boolean(), nullable=False), sa.Column("schema_version", sa.Integer(), nullable=False), sa.Column("definition", j, nullable=False), sa.Column("created_actor", sa.String(255), nullable=False), sa.Column("updated_actor", sa.String(255), nullable=False))
    op.create_index("ix_work_plan_templates_project_id", "work_plan_templates", ["project_id"])
    op.create_table("work_template_requests", *common(), sa.Column("operation", sa.String(20), nullable=False), sa.Column("request_id", sa.Uuid(), nullable=False), sa.Column("actor", sa.String(255), nullable=False), sa.Column("digest", sa.String(64), nullable=False), sa.Column("template_id", sa.Uuid(), nullable=False), sa.Column("plan_id", sa.Uuid()), sa.Column("result", j, nullable=False), sa.UniqueConstraint("project_id", "operation", "request_id", name="uq_work_template_request"))
    op.create_index("ix_work_template_requests_project_id", "work_template_requests", ["project_id"])


def downgrade():
    op.drop_table("work_template_requests")
    op.drop_table("work_plan_templates")
