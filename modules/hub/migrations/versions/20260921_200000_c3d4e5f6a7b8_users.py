"""users

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-09-21 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """The account table of app-prebuilt-user. The operator's account is created at startup, not here."""
    op.create_table('users',
    sa.Column('lastname', sa.String(length=255), nullable=True, comment="The user's last name."),
    sa.Column('firstname', sa.String(length=255), nullable=False, comment="The user's first name."),
    sa.Column('email', sa.String(length=320), nullable=False, comment="The user's email address (unique)."),
    sa.Column('hashed_password', sa.String(length=255), nullable=True, comment='Hashed password for traditional login (optional for social logins).'),
    sa.Column('extra', sa.JSON(), nullable=True, comment='Additional user metadata in JSON format.'),
    sa.Column('is_active', sa.Boolean(), nullable=False, comment='Whether the user account is active.'),
    sa.Column('is_verified', sa.Boolean(), nullable=False, comment="Whether the user's email address has been verified."),
    sa.Column('is_superadmin', sa.Boolean(), nullable=False, comment='Whether the user has superadmin privileges (can skip RBAC checks).'),
    sa.Column('last_login_at', sa.DateTime(), nullable=True, comment="Timestamp of the user's last successful login."),
    sa.Column('profile_image_url', sa.String(length=2048), nullable=True, comment="URL to the user's profile image."),
    sa.Column('phone_number', sa.String(length=50), nullable=True, comment="The user's phone number."),
    sa.Column('locale', sa.String(length=20), nullable=True, comment="The user's preferred locale (e.g., 'en_US', 'ko_KR')."),
    sa.Column('timezone', sa.String(length=100), nullable=True, comment="The user's preferred timezone (e.g., 'Asia/Seoul')."),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('email')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('users')
