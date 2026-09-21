"""remove linear connectors

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-09-21 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """The `linear` connector provider was removed; no feature ever read these credentials.

    A leftover row would fail validation and break the connector list. Nothing can reference one: projects accept
    only `github` connectors and AI catalogs only `jules` connectors.
    """
    op.execute("DELETE FROM connectors WHERE provider = 'linear'")


def downgrade() -> None:
    """The deleted credentials cannot be restored."""
