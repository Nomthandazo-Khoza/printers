"""Order workflow: payment_status, updated_at, paid_at, collected_at, order_notifications

Revision ID: order_workflow
Revises: add_order_files
Create Date: 2026-03-10

"""
from alembic import op
import sqlalchemy as sa


revision = 'order_workflow'
down_revision = 'add_order_files'
branch_labels = None
depends_on = None


def _column_exists(conn, table, column):
    if conn.dialect.name == 'sqlite':
        r = conn.execute(sa.text(f"PRAGMA table_info({table})"))
        return any(row[1] == column for row in r)
    return False


def upgrade():
    conn = op.get_bind()
    # Add new columns to orders (skip if already present from partial run)
    for col_spec in [
        ('payment_status', sa.Column('payment_status', sa.String(32), server_default='unpaid', nullable=False)),
        ('updated_at', sa.Column('updated_at', sa.DateTime(), nullable=True)),
        ('paid_at', sa.Column('paid_at', sa.DateTime(), nullable=True)),
        ('collected_at', sa.Column('collected_at', sa.DateTime(), nullable=True)),
    ]:
        col_name, col = col_spec
        if not _column_exists(conn, 'orders', col_name):
            op.add_column('orders', col)

    # Migrate existing order_status and payment_status (run UPDATEs)
    conn = op.get_bind()
    if conn.dialect.name == 'sqlite':
        conn.execute(sa.text("UPDATE orders SET order_status = 'submitted' WHERE order_status = 'Pending'"))
        conn.execute(sa.text("UPDATE orders SET order_status = 'in_progress' WHERE order_status = 'In Progress'"))
        conn.execute(sa.text("UPDATE orders SET order_status = 'ready_for_collection' WHERE order_status = 'Completed'"))
        conn.execute(sa.text("UPDATE orders SET order_status = 'completed' WHERE order_status = 'Collected'"))
        conn.execute(sa.text("UPDATE orders SET payment_status = 'paid' WHERE id IN (SELECT order_id FROM payments)"))
        conn.execute(sa.text("UPDATE orders SET updated_at = created_at WHERE updated_at IS NULL"))
        conn.execute(sa.text("UPDATE orders SET paid_at = (SELECT payment_date FROM payments p WHERE p.order_id = orders.id LIMIT 1) WHERE payment_status = 'paid'"))
    else:
        conn.execute(sa.text("""
            UPDATE orders SET
                order_status = CASE
                    WHEN order_status = 'Pending' THEN 'submitted'
                    WHEN order_status = 'In Progress' THEN 'in_progress'
                    WHEN order_status = 'Completed' THEN 'ready_for_collection'
                    WHEN order_status = 'Collected' THEN 'completed'
                    ELSE order_status
                END,
                payment_status = CASE WHEN EXISTS (SELECT 1 FROM payments WHERE payments.order_id = orders.id) THEN 'paid' ELSE 'unpaid' END,
                updated_at = COALESCE(updated_at, created_at)
        """))
        conn.execute(sa.text("UPDATE orders o SET paid_at = (SELECT payment_date FROM payments p WHERE p.order_id = o.id LIMIT 1) WHERE o.payment_status = 'paid'"))

    # Note: order_status stays String(20) in DB; SQLite does not support ALTER COLUMN type. Values like ready_for_collection still fit.

    # Create order_notifications table (skip if exists)
    from sqlalchemy import inspect
    insp = inspect(conn)
    if 'order_notifications' not in insp.get_table_names():
        op.create_table('order_notifications',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('order_id', sa.Integer(), nullable=False),
            sa.Column('message', sa.String(length=512), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ),
            sa.PrimaryKeyConstraint('id')
        )


def downgrade():
    op.drop_table('order_notifications')
    op.drop_column('orders', 'collected_at')
    op.drop_column('orders', 'paid_at')
    op.drop_column('orders', 'updated_at')
    op.drop_column('orders', 'payment_status')
