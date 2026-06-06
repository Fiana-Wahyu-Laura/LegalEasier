"""add document analysis fields to documents table

Revision ID: 20260519_0003
Revises: 20260519_0002
Create Date: 2026-05-19 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = "20260519_0003"
down_revision = "20260519_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("documents")}

    if "summary" not in columns:
        op.add_column("documents", sa.Column("summary", sa.Text(), nullable=True))
    if "risk_score" not in columns:
        op.add_column("documents", sa.Column("risk_score", sa.Integer(), nullable=True))
    if "risk_clauses_json" not in columns:
        op.add_column(
            "documents",
            sa.Column("risk_clauses_json", sa.Text(), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("documents")}

    if "risk_clauses_json" in columns:
        op.drop_column("documents", "risk_clauses_json")
    if "risk_score" in columns:
        op.drop_column("documents", "risk_score")
    if "summary" in columns:
        op.drop_column("documents", "summary")

