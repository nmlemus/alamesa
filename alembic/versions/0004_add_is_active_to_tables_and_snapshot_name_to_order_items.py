"""add is_active to tables and item_snapshot_name to order_items

Revision ID: 0004
Revises: 0003
Create Date: 2026-06-16

"""
import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("tables") as batch_op:
        batch_op.add_column(
            sa.Column(
                "is_active",
                sa.Boolean(),
                nullable=False,
                server_default=sa.true(),
            )
        )
    with op.batch_alter_table("order_items") as batch_op:
        batch_op.add_column(
            sa.Column(
                "item_snapshot_name",
                sa.String(200),
                nullable=False,
                server_default="",
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("order_items") as batch_op:
        batch_op.drop_column("item_snapshot_name")
    with op.batch_alter_table("tables") as batch_op:
        batch_op.drop_column("is_active")
