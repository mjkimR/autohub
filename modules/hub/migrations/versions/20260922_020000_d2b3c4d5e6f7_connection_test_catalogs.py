"""Bind connection tests to the selected AI catalog without relabeling legacy tests."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "d2b3c4d5e6f7"
down_revision = "c1a2b3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("connection_tests", sa.Column("ai_catalog_id", sa.UUID(), nullable=True))
    op.add_column("connection_tests", sa.Column("catalog_snapshot", sa.JSON().with_variant(
        postgresql.JSONB(astext_type=sa.Text()), "postgresql"), nullable=True))
    op.create_foreign_key("fk_connection_tests_catalog", "connection_tests", "ai_catalogs",
        ["ai_catalog_id"], ["id"], ondelete="RESTRICT")
    op.create_index("ix_connection_tests_ai_catalog_id", "connection_tests", ["ai_catalog_id"])


def downgrade() -> None:
    op.drop_index("ix_connection_tests_ai_catalog_id", table_name="connection_tests")
    op.drop_constraint("fk_connection_tests_catalog", "connection_tests", type_="foreignkey")
    op.drop_column("connection_tests", "catalog_snapshot")
    op.drop_column("connection_tests", "ai_catalog_id")
