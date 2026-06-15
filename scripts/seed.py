#!/usr/bin/env python3
"""
Seed Mesa Digital with demo data.

Creates:
  - 1 restaurant  (slug="demo", name="Restaurante Demo")
  - 1 admin user  (admin@demo.mesadigital.io / demo1234)
  - 2 categories
  - 5 menu items with price_cents
  - 3 tables

Safe to run multiple times (idempotent via existence checks).
"""
import os
import sys
from pathlib import Path

# Allow running as `python scripts/seed.py` without installing the package.
_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_ROOT / "src"))

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from mesadigital.api.db.models import (
    Base,
    Category,
    MenuItem,
    Restaurant,
    RestaurantTable,
    RestaurantUser,
    RestaurantUserRole,
)
from mesadigital.api.security import hash_password

DB_URL = os.environ.get("DATABASE_URL", "sqlite:///dev.db")


def seed(session: Session) -> None:
    # ── Restaurant ────────────────────────────────────────────────────────────
    restaurant = session.scalar(
        select(Restaurant).where(Restaurant.slug == "demo")
    )
    if restaurant is None:
        restaurant = Restaurant(slug="demo", name="Restaurante Demo")
        session.add(restaurant)
        session.flush()
    else:
        restaurant.name = "Restaurante Demo"

    # ── Admin user ────────────────────────────────────────────────────────────
    admin_email = "admin@demo.mesadigital.io"
    admin = session.scalar(
        select(RestaurantUser).where(RestaurantUser.email == admin_email)
    )
    if admin is None:
        admin = RestaurantUser(
            restaurant_id=restaurant.id,
            email=admin_email,
            hashed_password=hash_password("demo1234"),
            role=RestaurantUserRole.ADMIN,
            is_active=True,
        )
        session.add(admin)
        session.flush()

    # ── Categories ────────────────────────────────────────────────────────────
    cat_names = ["Entrantes", "Platos Principales"]
    categories: list[Category] = []
    for i, cat_name in enumerate(cat_names):
        cat = session.scalar(
            select(Category).where(
                Category.restaurant_id == restaurant.id,
                Category.name == cat_name,
            )
        )
        if cat is None:
            cat = Category(
                restaurant_id=restaurant.id, name=cat_name, display_order=i
            )
            session.add(cat)
            session.flush()
        categories.append(cat)

    # ── Menu items ────────────────────────────────────────────────────────────
    items_data: list[tuple[Category, str, str, int]] = [
        (categories[0], "Croquetas de jamón", "Croquetas caseras de jamón ibérico", 850),
        (categories[0], "Ensalada mixta", "Ensalada con atún y aceitunas", 700),
        (categories[1], "Paella valenciana", "Paella tradicional para dos personas", 2400),
        (categories[1], "Entrecot a la brasa", "250 g de ternera gallega", 2200),
        (categories[1], "Lubina al horno", "Con verduras de temporada", 1950),
    ]
    for cat, name, desc, price_cents in items_data:
        item = session.scalar(
            select(MenuItem).where(
                MenuItem.restaurant_id == restaurant.id,
                MenuItem.name == name,
            )
        )
        if item is None:
            session.add(
                MenuItem(
                    restaurant_id=restaurant.id,
                    category_id=cat.id,
                    name=name,
                    description=desc,
                    price_cents=price_cents,
                    is_available=True,
                )
            )
        else:
            item.price_cents = price_cents
            item.description = desc

    # ── Tables ────────────────────────────────────────────────────────────────
    for number in range(1, 4):
        table = session.scalar(
            select(RestaurantTable).where(
                RestaurantTable.restaurant_id == restaurant.id,
                RestaurantTable.number == number,
            )
        )
        if table is None:
            session.add(
                RestaurantTable(
                    restaurant_id=restaurant.id,
                    number=number,
                    label=f"Mesa {number}",
                )
            )

    session.commit()

    print("Seed completed successfully.")
    print(f"  Restaurant : {restaurant.name!r} (slug={restaurant.slug!r})")
    print(f"  Admin user : {admin_email}")
    print(f"  Categories : {len(cat_names)}")
    print(f"  Menu items : {len(items_data)}")
    print("  Tables     : 3")


def main() -> None:
    db_engine = create_engine(DB_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(db_engine)
    with Session(db_engine) as session:
        seed(session)


if __name__ == "__main__":
    main()
