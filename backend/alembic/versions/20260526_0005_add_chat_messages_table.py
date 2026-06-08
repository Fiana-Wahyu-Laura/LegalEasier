"""add chat_messages table

Revision ID: 20260526_0005
Revises: 20260519_0004
Create Date: 2026-05-26 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = "20260526_0005"
down_revision = "20260519_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "chat_messages" not in tables:
        op.create_table(
            "chat_messages",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("user_id", sa.UUID(), nullable=True),
            sa.Column("document_id", sa.UUID(), nullable=False),
            sa.Column("question", sa.Text(), nullable=True),
            sa.Column("answer", sa.Text(), nullable=True),
            sa.Column("sources_json", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        inspector = sa.inspect(bind)

    columns = {column["name"] for column in inspector.get_columns("chat_messages")}
    indexes = {index["name"] for index in inspector.get_indexes("chat_messages")}
    if "document_id" in columns and "ix_chat_messages_document_id" not in indexes:
        op.create_index("ix_chat_messages_document_id", "chat_messages", ["document_id"], unique=False)
    if "user_id" in columns and "ix_chat_messages_user_id" not in indexes:
        op.create_index("ix_chat_messages_user_id", "chat_messages", ["user_id"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "chat_messages" in tables:
        indexes = {index["name"] for index in inspector.get_indexes("chat_messages")}
        if "ix_chat_messages_user_id" in indexes:
            op.drop_index("ix_chat_messages_user_id", table_name="chat_messages")
        if "ix_chat_messages_document_id" in indexes:
            op.drop_index("ix_chat_messages_document_id", table_name="chat_messages")
        op.drop_table("chat_messages")
