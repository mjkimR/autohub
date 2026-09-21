"""operator notices

Revision ID: a1b2c3d4e5f6
Revises: 061a3a930c1e
Create Date: 2026-09-21 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '061a3a930c1e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('notification_channels',
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('kind', sa.String(length=30), nullable=False),
    sa.Column('enabled', sa.Boolean(), nullable=False),
    sa.Column('config', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('credentials_ciphertext', sa.LargeBinary(), nullable=False),
    sa.Column('credentials_nonce', sa.LargeBinary(), nullable=False),
    sa.Column('credential_key_version', sa.String(length=255), nullable=False),
    sa.Column('last_sent_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('last_error', sa.Text(), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name')
    )
    op.add_column('github_webhook_deliveries', sa.Column('pull_number', sa.Integer(), nullable=True))
    op.add_column('github_webhook_deliveries', sa.Column('auto_run', sa.Boolean(), server_default='0', nullable=False))
    op.add_column('github_webhook_deliveries', sa.Column('requested_catalog', sa.String(length=255), nullable=True))
    op.add_column('github_webhook_deliveries', sa.Column('attempts', sa.Integer(), server_default='0', nullable=False))
    op.add_column('pipeline_runs', sa.Column('notified_revision', sa.Integer(), nullable=True))
    # Runs that stopped before notices existed are history; only later stops are announced.
    op.execute('UPDATE pipeline_runs SET notified_revision = revision')
    # Deliveries received before replay facts were kept cannot be replayed.
    op.execute("UPDATE github_webhook_deliveries SET attempts = 2")


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('pipeline_runs', 'notified_revision')
    op.drop_column('github_webhook_deliveries', 'attempts')
    op.drop_column('github_webhook_deliveries', 'requested_catalog')
    op.drop_column('github_webhook_deliveries', 'auto_run')
    op.drop_column('github_webhook_deliveries', 'pull_number')
    op.drop_table('notification_channels')
