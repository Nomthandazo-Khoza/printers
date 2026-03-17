"""Add notes to orders

Revision ID: add_order_notes
Revises: 9c2491706e56
Create Date: 2026-03-10

"""
from alembic import op
import sqlalchemy as sa


revision = 'add_order_notes'
down_revision = '9c2491706e56'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('orders', sa.Column('notes', sa.Text(), nullable=True))


def downgrade():
    op.drop_column('orders', 'notes')
