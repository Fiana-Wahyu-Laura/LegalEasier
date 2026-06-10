"""add deleted_at to documents and CASCADE to foreign keys

Revision ID: 20260609_0007
Revises: 20260526_0006
Create Date: 2026-06-09 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = "20260609_0007"
down_revision = "20260526_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # 1. Add deleted_at column to documents
    columns = {column["name"] for column in inspector.get_columns("documents")}
    if "deleted_at" not in columns:
        op.add_column(
            "documents",
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index("ix_documents_deleted_at", "documents", ["deleted_at"])

    # 2. Recreate FK constraints with ON DELETE CASCADE
    #    documents.owner_id → users.id
    _recreate_fk_if_exists(
        "documents",
        "documents_owner_id_fkey",
        "owner_id",
        "users",
        "id",
    )
    #    chat_messages.user_id → users.id
    _recreate_fk_if_exists(
        "chat_messages",
        "chat_messages_user_id_fkey",
        "user_id",
        "users",
        "id",
    )
    #    chat_messages.document_id → documents.id
    _recreate_fk_if_exists(
        "chat_messages",
        "chat_messages_document_id_fkey",
        "document_id",
        "documents",
        "id",
    )


def _recreate_fk_if_exists(
    table_name: str,
    constraint_name: str,
    column: str,
    ref_table: str,
    ref_column: str,
) -> None:
    """Drop and recreate a foreign key constraint with ON DELETE CASCADE."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    fks = inspector.get_foreign_keys(table_name)
    for fk in fks:
        if fk.get("name") == constraint_name:
            op.drop_constraint(constraint_name, table_name, type_="foreignkey")
            op.create_foreign_key(
                constraint_name, table_name, ref_table,
                [column], [ref_column],
                ondelete="CASCADE",
            )
            return

    # If constraint name doesn't match, try to find it by column
    for fk in fks:
        if column in fk.get("constrained_columns", []):
            actual_name = fk["name"]
            op.drop_constraint(actual_name, table_name, type_="foreignkey")
            op.create_foreign_key(
                constraint_name, table_name, ref_table,
                [column], [ref_column],
                ondelete="CASCADE",
            )
            return


def downgrade() -> None:
    # 1. Remove CASCADE from FKs (restore to NO ACTION / default)
    _recreate_fk_no_cascade(
        "documents",
        "documents_owner_id_fkey",
        "owner_id",
        "users",
        "id",
    )
    _recreate_fk_no_cascade(
        "chat_messages",
        "chat_messages_user_id_fkey",
        "user_id",
        "users",
        "id",
    )
    _recreate_fk_no_cascade(
        "chat_messages",
        "chat_messages_document_id_fkey",
        "document_id",
        "documents",
        "id",
    )

    # 2. Remove deleted_at column and index
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("documents")}
    if "deleted_at" in columns:
        op.drop_index("ix_documents_deleted_at", table_name="documents")
        op.drop_column("documents", "deleted_at")


def _recreate_fk_no_cascade(
    table_name: str,
    constraint_name: str,
    column: str,
    ref_table: str,
    ref_column: str,
) -> None:
    """Drop and recreate a foreign key constraint without CASCADE."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    fks = inspector.get_foreign_keys(table_name)
    for fk in fks:
        if column in fk.get("constrained_columns", []):
            actual_name = fk["name"]
            op.drop_constraint(actual_name, table_name, type_="foreignkey")
            op.create_foreign_key(
                constraint_name, table_name, ref_table,
                [column], [ref_column],
            )
            return
