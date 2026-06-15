"""add is_active to restaurants and last_seen_at to diners

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-15

"""
import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("restaurants") as batch_op:
        batch_op.add_column(
            sa.Column(
                "is_active",
                sa.Boolean(),
                nullable=False,
                server_default=sa.true(),
            )
        )
    with op.batch_alter_table("diners") as batch_op:
        batch_op.add_column(
            sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table("diners") as batch_op:
        batch_op.drop_column("last_seen_at")
    with op.batch_alter_table("restaurants") as batch_op:
        batch_op.drop_column("is_active")
