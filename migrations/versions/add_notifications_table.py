"""Add notifications table (customer navbar notifications)

Revision ID: add_notifications
Revises: order_workflow
Create Date: 2026-03-10

"""
from alembic import op
import sqlalchemy as sa


revision = 'add_notifications'
down_revision = 'order_workflow'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('notifications',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('customer_id', sa.Integer(), nullable=False),
        sa.Column('order_id', sa.Integer(), nullable=True),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('message', sa.String(length=512), nullable=False),
        sa.Column('type', sa.String(length=20), nullable=False),
        sa.Column('is_read', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_notifications_customer_id'), 'notifications', ['customer_id'], unique=False)
    op.create_index(op.f('ix_notifications_created_at'), 'notifications', ['created_at'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_notifications_created_at'), table_name='notifications')
    op.drop_index(op.f('ix_notifications_customer_id'), table_name='notifications')
    op.drop_table('notifications')
