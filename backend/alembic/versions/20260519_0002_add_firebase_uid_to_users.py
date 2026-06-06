"""add firebase_uid to users table

Revision ID: 20260519_0002
Revises: 20260511_0001
Create Date: 2026-05-19 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = "20260519_0002"
down_revision = "20260511_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    columns = {column["name"] for column in inspector.get_columns("users")}
    if "firebase_uid" not in columns:
        op.add_column(
            "users",
            sa.Column("firebase_uid", sa.String(length=255), nullable=True),
        )
        inspector = sa.inspect(bind)

    indexes = {index["name"] for index in inspector.get_indexes("users")}
    if "ix_users_firebase_uid" not in indexes:
        op.create_index("ix_users_firebase_uid", "users", ["firebase_uid"], unique=True)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    indexes = {index["name"] for index in inspector.get_indexes("users")}
    if "ix_users_firebase_uid" in indexes:
        op.drop_index("ix_users_firebase_uid", table_name="users")

    columns = {column["name"] for column in inspector.get_columns("users")}
    if "firebase_uid" in columns:
        op.drop_column("users", "firebase_uid")

