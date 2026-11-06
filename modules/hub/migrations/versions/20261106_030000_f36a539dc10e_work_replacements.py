"""Retain explicit Work Item replacement and exact edge acceptance evidence."""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision='f36a539dc10e'
down_revision='e25f428cba0f'
branch_labels=None
depends_on=None


def identity():
    return (sa.Column('id',sa.Uuid(),primary_key=True),
            sa.Column('created_at',sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False),
            sa.Column('updated_at',sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False))


def upgrade():
    json_type=sa.JSON().with_variant(postgresql.JSONB(),'postgresql')
    op.create_table('work_replacement_evidence',
        sa.Column('item_id',sa.Uuid(),sa.ForeignKey('work_items.id',ondelete='RESTRICT'),primary_key=True),
        sa.Column('revision',sa.Integer(),nullable=False))
    op.create_table('work_replacement_links',*identity(),
        sa.Column('project_id',sa.Uuid(),nullable=False),
        sa.Column('original_plan_id',sa.Uuid(),nullable=False),
        sa.Column('original_item_id',sa.Uuid(),nullable=False),
        sa.Column('replacement_plan_id',sa.Uuid(),nullable=False),
        sa.Column('replacement_item_id',sa.Uuid(),nullable=False),
        sa.Column('active',sa.Boolean(),nullable=False),
        sa.Column('snapshot',json_type,nullable=False),
        sa.Column('actor',sa.String(255),nullable=False),sa.Column('reason',sa.String(500),nullable=False),
        sa.ForeignKeyConstraint(['project_id','original_plan_id'],['work_plans.project_id','work_plans.id']),
        sa.ForeignKeyConstraint(['project_id','replacement_plan_id'],['work_plans.project_id','work_plans.id']),
        sa.ForeignKeyConstraint(['original_plan_id','original_item_id'],['work_items.plan_id','work_items.id']),
        sa.ForeignKeyConstraint(['replacement_plan_id','replacement_item_id'],['work_items.plan_id','work_items.id']),
        sa.UniqueConstraint('replacement_item_id',name='uq_replacement_lifetime_endpoint'))
    op.create_index('ix_work_replacement_links_original_item_id','work_replacement_links',['original_item_id'])
    op.create_index('uq_replacement_active_original','work_replacement_links',['original_item_id'],unique=True,
                    postgresql_where=sa.text('active = true'),sqlite_where=sa.text('active = 1'))
    op.create_table('work_replacement_acceptances',*identity(),
        sa.Column('link_id',sa.Uuid(),sa.ForeignKey('work_replacement_links.id',ondelete='RESTRICT'),nullable=False),
        sa.Column('plan_id',sa.Uuid(),nullable=False),
        sa.Column('dependent_item_id',sa.Uuid(),nullable=False),sa.Column('original_item_id',sa.Uuid(),nullable=False),
        sa.Column('active',sa.Boolean(),nullable=False),sa.Column('consumed',sa.Boolean(),nullable=False),
        sa.Column('snapshot',json_type,nullable=False),
        sa.Column('actor',sa.String(255),nullable=False),sa.Column('reason',sa.String(500),nullable=False),
        sa.ForeignKeyConstraint(['plan_id','dependent_item_id'],['work_items.plan_id','work_items.id']),
        sa.ForeignKeyConstraint(['plan_id','original_item_id'],['work_items.plan_id','work_items.id']))
    op.create_index('ix_work_replacement_acceptances_link_id','work_replacement_acceptances',['link_id'])
    op.create_index('uq_replacement_live_edge','work_replacement_acceptances',['dependent_item_id','original_item_id'],unique=True,
                    postgresql_where=sa.text('active = true'),sqlite_where=sa.text('active = 1'))
    op.create_table('work_replacement_events',*identity(),
        sa.Column('link_id',sa.Uuid(),sa.ForeignKey('work_replacement_links.id',ondelete='RESTRICT'),nullable=False),
        sa.Column('acceptance_id',sa.Uuid(),sa.ForeignKey('work_replacement_acceptances.id',ondelete='RESTRICT')),
        sa.Column('kind',sa.String(30),nullable=False),sa.Column('actor',sa.String(255),nullable=False),
        sa.Column('reason',sa.String(500),nullable=False),sa.Column('revision',sa.Integer(),nullable=False),
        sa.Column('evidence',json_type,nullable=False))
    op.create_index('ix_work_replacement_events_link_id','work_replacement_events',['link_id'])
    op.create_table('work_replacement_receipts',*identity(),
        sa.Column('project_id',sa.Uuid(),sa.ForeignKey('projects.id',ondelete='RESTRICT'),nullable=False),
        sa.Column('original_item_id',sa.Uuid(),sa.ForeignKey('work_items.id',ondelete='RESTRICT'),nullable=False),
        sa.Column('operation',sa.String(30),nullable=False),sa.Column('request_id',sa.Uuid(),nullable=False),
        sa.Column('digest',sa.String(64),nullable=False),sa.Column('result',json_type,nullable=False),
        sa.UniqueConstraint('project_id','operation','request_id',name='uq_replacement_request'))


def downgrade():
    for name in ('work_replacement_receipts','work_replacement_events','work_replacement_acceptances','work_replacement_links','work_replacement_evidence'):
        op.drop_table(name)
