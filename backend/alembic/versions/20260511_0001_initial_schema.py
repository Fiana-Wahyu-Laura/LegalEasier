"""create initial schema - users and documents tables

Revision ID: 20260511_0001
Revises: 
Create Date: 2026-05-11 00:01:00.000000
"""

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = "20260511_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if 'users' not in tables:
        op.create_table(
            'users',
            sa.Column('id', sa.UUID(), nullable=False),
            sa.Column('firebase_uid', sa.String(length=255), nullable=False),
            sa.Column('email', sa.String(length=255), nullable=False),
            sa.Column('display_name', sa.String(length=255), nullable=True),
            sa.Column('hashed_password', sa.String(length=255), nullable=True),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('firebase_uid'),
            sa.UniqueConstraint('email'),
        )
        inspector = sa.inspect(bind)

    user_columns = {column['name'] for column in inspector.get_columns('users')}
    user_indexes = {index['name'] for index in inspector.get_indexes('users')}
    if 'email' in user_columns and 'ix_users_email' not in user_indexes:
        op.create_index('ix_users_email', 'users', ['email'], unique=False)
    if 'firebase_uid' in user_columns and 'ix_users_firebase_uid' not in user_indexes:
        op.create_index('ix_users_firebase_uid', 'users', ['firebase_uid'], unique=False)

    if 'documents' not in tables:
        op.create_table(
            'documents',
            sa.Column('id', sa.UUID(), nullable=False),
            sa.Column('owner_id', sa.UUID(), nullable=True),
            sa.Column('filename', sa.String(length=1024), nullable=False),
            sa.Column('storage_path', sa.String(length=2048), nullable=False),
            sa.Column('status', sa.String(length=32), nullable=False, server_default=sa.text("'pending'")),
            sa.Column('extracted_text', sa.Text(), nullable=True),
            sa.Column('summary', sa.Text(), nullable=True),
            sa.Column('risk_score', sa.Integer(), nullable=True),
            sa.Column('risk_clauses_json', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ),
            sa.PrimaryKeyConstraint('id'),
        )
        inspector = sa.inspect(bind)

    document_columns = {column['name'] for column in inspector.get_columns('documents')}
    document_indexes = {index['name'] for index in inspector.get_indexes('documents')}
    if 'owner_id' in document_columns and 'ix_documents_owner_id' not in document_indexes:
        op.create_index('ix_documents_owner_id', 'documents', ['owner_id'], unique=False)
    if 'status' in document_columns and 'ix_documents_status' not in document_indexes:
        op.create_index('ix_documents_status', 'documents', ['status'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_documents_status', table_name='documents')
    op.drop_index('ix_documents_owner_id', table_name='documents')
    op.drop_table('documents')
    op.drop_index('ix_users_firebase_uid', table_name='users')
    op.drop_index('ix_users_email', table_name='users')
    op.drop_table('users')
