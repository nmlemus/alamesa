"""initial migration

Revision ID: 0001
Revises:
Create Date: 2026-06-15

"""
import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "restaurants",
        sa.Column("id", sa.String(32), nullable=False),
        sa.Column("slug", sa.String(50), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )

    op.create_table(
        "diners",
        sa.Column("id", sa.String(32), nullable=False),
        sa.Column("restaurant_id", sa.String(32), nullable=False),
        sa.Column("phone", sa.String(30), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("hashed_password", sa.String(200), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["restaurant_id"], ["restaurants.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "restaurant_id", "phone", name="uq_diners_restaurant_id_phone"
        ),
    )

    op.create_table(
        "restaurant_users",
        sa.Column("id", sa.String(32), nullable=False),
        sa.Column("restaurant_id", sa.String(32), nullable=False),
        sa.Column("email", sa.String(200), nullable=False),
        sa.Column("hashed_password", sa.String(200), nullable=False),
        sa.Column(
            "role",
            sa.Enum("admin", "staff", name="restaurantuserrole", native_enum=False),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["restaurant_id"], ["restaurants.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "restaurant_id",
            "email",
            name="uq_restaurant_users_restaurant_id_email",
        ),
    )

    op.create_table(
        "categories",
        sa.Column("id", sa.String(32), nullable=False),
        sa.Column("restaurant_id", sa.String(32), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("is_visible", sa.Boolean(), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["restaurant_id"], ["restaurants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_categories_restaurant_visible_order",
        "categories",
        ["restaurant_id", "is_visible", "display_order"],
    )

    op.create_table(
        "tables",
        sa.Column("id", sa.String(32), nullable=False),
        sa.Column("restaurant_id", sa.String(32), nullable=False),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(50), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["restaurant_id"], ["restaurants.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "restaurant_id", "number", name="uq_tables_restaurant_id_number"
        ),
    )

    op.create_table(
        "menu_items",
        sa.Column("id", sa.String(32), nullable=False),
        sa.Column("restaurant_id", sa.String(32), nullable=False),
        sa.Column("category_id", sa.String(32), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("price_cents", sa.Integer(), nullable=False),
        sa.Column("is_available", sa.Boolean(), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"]),
        sa.ForeignKeyConstraint(["restaurant_id"], ["restaurants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_menu_items_restaurant_available_cat_order",
        "menu_items",
        ["restaurant_id", "is_available", "category_id", "display_order"],
    )

    op.create_table(
        "orders",
        sa.Column("id", sa.String(32), nullable=False),
        sa.Column("restaurant_id", sa.String(32), nullable=False),
        sa.Column("table_id", sa.String(32), nullable=False),
        sa.Column("diner_id", sa.String(32), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'confirmed', 'preparing', 'ready', 'closed', 'cancelled')",
            name="ck_orders_status",
        ),
        sa.ForeignKeyConstraint(["diner_id"], ["diners.id"]),
        sa.ForeignKeyConstraint(["restaurant_id"], ["restaurants.id"]),
        sa.ForeignKeyConstraint(["table_id"], ["tables.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_orders_restaurant_status_created",
        "orders",
        ["restaurant_id", "status", "created_at"],
    )
    op.create_index(
        "ix_orders_restaurant_updated",
        "orders",
        ["restaurant_id", "updated_at"],
    )

    op.create_table(
        "order_items",
        sa.Column("id", sa.String(32), nullable=False),
        sa.Column("order_id", sa.String(32), nullable=False),
        sa.Column("menu_item_id", sa.String(32), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price_cents", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["menu_item_id"], ["menu_items.id"]),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "order_events",
        sa.Column("id", sa.String(32), nullable=False),
        sa.Column("order_id", sa.String(32), nullable=False),
        sa.Column(
            "actor_type",
            sa.Enum(
                "diner",
                "staff",
                "system",
                name="ordereventactortype",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("actor_id", sa.String(32), nullable=True),
        sa.Column("from_status", sa.String(20), nullable=False),
        sa.Column("to_status", sa.String(20), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_order_events_order_created",
        "order_events",
        ["order_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_order_events_order_created", table_name="order_events")
    op.drop_table("order_events")
    op.drop_table("order_items")
    op.drop_index("ix_orders_restaurant_updated", table_name="orders")
    op.drop_index("ix_orders_restaurant_status_created", table_name="orders")
    op.drop_table("orders")
    op.drop_index(
        "ix_menu_items_restaurant_available_cat_order", table_name="menu_items"
    )
    op.drop_table("menu_items")
    op.drop_table("tables")
    op.drop_index(
        "ix_categories_restaurant_visible_order", table_name="categories"
    )
    op.drop_table("categories")
    op.drop_table("restaurant_users")
    op.drop_table("diners")
    op.drop_table("restaurants")
