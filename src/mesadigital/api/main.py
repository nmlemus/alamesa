import hashlib
import os
from collections.abc import Generator

import uvicorn
from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from typing import Annotated

from mesadigital.api.db.models import (
    Base,
    Diner,
    MenuItem,
    Order,
    OrderItem,
    OrderStatus,
    Restaurant,
    RestaurantTable,
)

app = FastAPI(title="Mesa Digital API")

DB_URL = os.environ.get("DATABASE_URL", "sqlite:///dev.db")
engine = create_engine(DB_URL, connect_args={"check_same_thread": False})


def get_db() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session


DbDep = Annotated[Session, Depends(get_db)]

VALID_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.PENDING: {OrderStatus.CONFIRMED},
    OrderStatus.CONFIRMED: {OrderStatus.READY},
    OrderStatus.READY: {OrderStatus.CLOSED},
    OrderStatus.CLOSED: set(),
}


# ── Request / response schemas ─────────────────────────────────────────────


class DinerRegisterRequest(BaseModel):
    email: str
    name: str
    password: str


class DinerResponse(BaseModel):
    id: int
    email: str
    name: str


class MenuItemOut(BaseModel):
    id: int
    name: str
    description: str | None
    price_cents: int
    available: bool


class CategoryOut(BaseModel):
    id: int
    name: str
    items: list[MenuItemOut]


class TableOut(BaseModel):
    id: int
    number: int
    label: str | None


class RestaurantOut(BaseModel):
    id: int
    slug: str
    name: str


class MenuResponse(BaseModel):
    restaurant: RestaurantOut
    categories: list[CategoryOut]
    tables: list[TableOut]


class OrderItemRequest(BaseModel):
    menu_item_id: int
    quantity: int


class CreateOrderRequest(BaseModel):
    restaurant_slug: str
    table_id: int
    diner_id: int | None = None
    items: list[OrderItemRequest]


class OrderResponse(BaseModel):
    id: int
    status: str
    table_id: int
    restaurant_id: int


class UpdateStatusRequest(BaseModel):
    status: str


# ── Routes ────────────────────────────────────────────────────────────────


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/diners/register", response_model=DinerResponse, status_code=201)
def register_diner(body: DinerRegisterRequest, db: DbDep) -> DinerResponse:
    existing = db.scalar(select(Diner).where(Diner.email == body.email))
    if existing is not None:
        raise HTTPException(status_code=409, detail="Email already registered")
    diner = Diner(
        email=body.email,
        name=body.name,
        password_hash=hashlib.sha256(body.password.encode()).hexdigest(),
    )
    db.add(diner)
    db.commit()
    db.refresh(diner)
    return DinerResponse(id=diner.id, email=diner.email, name=diner.name)


@app.get("/api/restaurants/{slug}/menu", response_model=MenuResponse)
def get_menu(slug: str, db: DbDep) -> MenuResponse:
    restaurant = db.scalar(select(Restaurant).where(Restaurant.slug == slug))
    if restaurant is None:
        raise HTTPException(status_code=404, detail="Restaurant not found")

    categories_out: list[CategoryOut] = []
    for cat in sorted(restaurant.categories, key=lambda c: c.sort_order):
        items_out = [
            MenuItemOut(
                id=item.id,
                name=item.name,
                description=item.description,
                price_cents=item.price_cents,
                available=item.available,
            )
            for item in cat.menu_items
        ]
        categories_out.append(
            CategoryOut(id=cat.id, name=cat.name, items=items_out)
        )

    tables_out = [
        TableOut(id=t.id, number=t.number, label=t.label)
        for t in restaurant.tables
    ]

    return MenuResponse(
        restaurant=RestaurantOut(
            id=restaurant.id, slug=restaurant.slug, name=restaurant.name
        ),
        categories=categories_out,
        tables=tables_out,
    )


@app.post("/api/orders", response_model=OrderResponse, status_code=201)
def create_order(body: CreateOrderRequest, db: DbDep) -> OrderResponse:
    restaurant = db.scalar(
        select(Restaurant).where(Restaurant.slug == body.restaurant_slug)
    )
    if restaurant is None:
        raise HTTPException(status_code=404, detail="Restaurant not found")

    table = db.scalar(
        select(RestaurantTable).where(
            RestaurantTable.id == body.table_id,
            RestaurantTable.restaurant_id == restaurant.id,
        )
    )
    if table is None:
        raise HTTPException(status_code=404, detail="Table not found")

    order = Order(
        restaurant_id=restaurant.id,
        table_id=table.id,
        diner_id=body.diner_id,
        status=OrderStatus.PENDING,
    )
    db.add(order)
    db.flush()

    for req in body.items:
        menu_item = db.scalar(
            select(MenuItem).where(
                MenuItem.id == req.menu_item_id,
                MenuItem.restaurant_id == restaurant.id,
            )
        )
        if menu_item is None:
            raise HTTPException(
                status_code=404,
                detail=f"Menu item {req.menu_item_id} not found",
            )
        db.add(
            OrderItem(
                order_id=order.id,
                menu_item_id=menu_item.id,
                quantity=req.quantity,
                unit_price_cents=menu_item.price_cents,
            )
        )

    db.commit()
    db.refresh(order)
    return OrderResponse(
        id=order.id,
        status=order.status.value,
        table_id=order.table_id,
        restaurant_id=order.restaurant_id,
    )


@app.patch("/api/orders/{order_id}/status", response_model=OrderResponse)
def update_order_status(
    order_id: int, body: UpdateStatusRequest, db: DbDep
) -> OrderResponse:
    try:
        new_status = OrderStatus(body.status)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid status: {body.status!r}")

    order = db.scalar(select(Order).where(Order.id == order_id))
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")

    allowed = VALID_TRANSITIONS.get(order.status, set())
    if new_status not in allowed:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Cannot transition from {order.status.value!r} "
                f"to {new_status.value!r}"
            ),
        )

    order.status = new_status
    db.commit()
    db.refresh(order)
    return OrderResponse(
        id=order.id,
        status=order.status.value,
        table_id=order.table_id,
        restaurant_id=order.restaurant_id,
    )


def main() -> None:
    uvicorn.run("mesadigital.api.main:app", host="0.0.0.0", port=8000, reload=False)
