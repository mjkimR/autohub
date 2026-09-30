"""Make work plan registration replayable within a project."""

import sqlalchemy as sa
from alembic import op

revision = "f25b328e1021"
down_revision = "e14a217d0910"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("work_plans") as batch:
        batch.add_column(sa.Column("registration_request_id", sa.Uuid(), nullable=True))
        batch.add_column(sa.Column("registration_digest", sa.String(64), nullable=True))
        batch.create_unique_constraint("uq_work_plan_registration", ["project_id", "registration_request_id"])


def downgrade():
    with op.batch_alter_table("work_plans") as batch:
        batch.drop_constraint("uq_work_plan_registration", type_="unique")
        batch.drop_column("registration_digest")
        batch.drop_column("registration_request_id")
