"""Add device_id column to users table for anonymous session linking.

Revision ID: add_device_id_to_users
Revises: 
Create Date: 2026-06-09 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_device_id_to_users'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add device_id column to users table
    op.add_column(
        'users',
        sa.Column('device_id', sa.String(255), nullable=True),
    )
    # Create index on device_id for faster lookups
    op.create_index(
        'ix_users_device_id',
        'users',
        ['device_id'],
    )


def downgrade() -> None:
    # Remove index
    op.drop_index('ix_users_device_id', table_name='users')
    # Remove column
    op.drop_column('users', 'device_id')
