"""Add payment method and migrate payment option

Revision ID: 6d709be70cf0
Revises: add_payment_option
Create Date: 2026-03-17 11:34:34.003186

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6d709be70cf0'
down_revision = 'add_payment_option'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('orders', sa.Column('payment_method', sa.String(length=32), nullable=True))
    op.execute(sa.text("UPDATE orders SET payment_option = 'pay_now_online' WHERE payment_option = 'pay_now'"))
    op.execute(sa.text("UPDATE orders SET payment_option = 'pay_later_counter' WHERE payment_option = 'pay_later'"))


def downgrade():
    op.drop_column('orders', 'payment_method')
