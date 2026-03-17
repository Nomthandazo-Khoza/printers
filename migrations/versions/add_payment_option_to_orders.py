"""Add payment_option to orders

Revision ID: add_payment_option
Revises: add_notifications
Create Date: 2026-03-10

"""
from alembic import op
import sqlalchemy as sa


revision = 'add_payment_option'
down_revision = 'add_notifications'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'orders',
        sa.Column('payment_option', sa.String(length=32), nullable=False, server_default='pay_later'),
    )


def downgrade():
    op.drop_column('orders', 'payment_option')
