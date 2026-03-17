"""Add order_files table

Revision ID: add_order_files
Revises: add_order_notes
Create Date: 2026-03-10

"""
from alembic import op
import sqlalchemy as sa


revision = 'add_order_files'
down_revision = 'add_order_notes'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('order_files',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('order_id', sa.Integer(), nullable=False),
        sa.Column('original_filename', sa.String(length=255), nullable=False),
        sa.Column('stored_filename', sa.String(length=255), nullable=False),
        sa.Column('file_path', sa.String(length=512), nullable=False),
        sa.Column('uploaded_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('order_files')
