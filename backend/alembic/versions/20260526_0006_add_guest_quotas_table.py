"""add guest_quotas table

Revision ID: 20260526_0006
Revises: 20260526_0005
Create Date: 2026-05-26 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = "20260526_0006"
down_revision = "20260526_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "guest_quotas",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("remaining_quota", sa.Integer(), nullable=False, server_default=sa.text("5")),
        sa.Column("last_reset", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
    )


def downgrade() -> None:
    op.drop_table("guest_quotas")
