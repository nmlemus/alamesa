"""add is_active to restaurant_users

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-15

"""
import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "restaurant_users",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )


def downgrade() -> None:
    with op.batch_alter_table("restaurant_users") as batch_op:
        batch_op.drop_column("is_active")
