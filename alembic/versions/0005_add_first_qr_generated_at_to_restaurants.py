"""add first_qr_generated_at to restaurants

Revision ID: 0005
Revises: 0004
Create Date: 2026-06-16

"""
import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("restaurants") as batch_op:
        batch_op.add_column(
            sa.Column(
                "first_qr_generated_at",
                sa.DateTime(timezone=True),
                nullable=True,
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("restaurants") as batch_op:
        batch_op.drop_column("first_qr_generated_at")
