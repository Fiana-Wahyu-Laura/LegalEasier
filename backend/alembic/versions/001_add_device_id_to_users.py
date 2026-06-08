"""Add device_id column to users table for anonymous session linking.

Revision ID: add_device_id_to_users
Revises: 20260526_0006
Create Date: 2026-06-09 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_device_id_to_users'
down_revision = '20260526_0006'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column['name'] for column in inspector.get_columns('users')}

    if 'device_id' not in columns:
        op.add_column(
            'users',
            sa.Column('device_id', sa.String(255), nullable=True),
        )
        inspector = sa.inspect(bind)

    indexes = {index['name'] for index in inspector.get_indexes('users')}
    if 'ix_users_device_id' not in indexes:
        op.create_index(
            'ix_users_device_id',
            'users',
            ['device_id'],
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    indexes = {index['name'] for index in inspector.get_indexes('users')}

    if 'ix_users_device_id' in indexes:
        op.drop_index('ix_users_device_id', table_name='users')

    columns = {column['name'] for column in inspector.get_columns('users')}
    if 'device_id' in columns:
        op.drop_column('users', 'device_id')
