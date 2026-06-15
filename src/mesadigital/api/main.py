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
    Diner,
    MenuItem,
    Order,
    OrderItem,
    Restaurant,
    RestaurantTable,
)
from shared.contracts import LEGAL_TRANSITIONS, OrderStatus

app = FastAPI(title="Mesa Digital API")

DB_URL = os.environ.get("DATABASE_URL", "sqlite:///dev.db")
engine = create_engine(DB_URL, connect_args={"check_same_thread": False})


def get_db() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session


DbDep = Annotated[Session, Depends(get_db)]


# ── Request / response schemas ─────────────────────────────────────────────


class DinerRegisterRequest(BaseModel):
    restaurant_slug: str
    phone: str
    name: str
    password: str


class DinerResponse(BaseModel):
    id: str
    phone: str
    name: str


class MenuItemOut(BaseModel):
    id: str
    name: str
    description: str | None
    price_cents: int
    available: bool


class CategoryOut(BaseModel):
    id: str
    name: str
    items: list[MenuItemOut]


class TableOut(BaseModel):
    id: str
    number: int
    label: str | None


class RestaurantOut(BaseModel):
    id: str
    slug: str
    name: str


class MenuResponse(BaseModel):
    restaurant: RestaurantOut
    categories: list[CategoryOut]
    tables: list[TableOut]


class OrderItemRequest(BaseModel):
    menu_item_id: str
    quantity: int


class CreateOrderRequest(BaseModel):
    restaurant_slug: str
    table_id: str
    diner_id: str | None = None
    items: list[OrderItemRequest]


class OrderResponse(BaseModel):
    id: str
    status: str
    table_id: str
    restaurant_id: str


class UpdateStatusRequest(BaseModel):
    status: str


# ── Routes ────────────────────────────────────────────────────────────────


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/diners/register", response_model=DinerResponse, status_code=201)
def register_diner(body: DinerRegisterRequest, db: DbDep) -> DinerResponse:
    restaurant = db.scalar(
        select(Restaurant).where(Restaurant.slug == body.restaurant_slug)
    )
    if restaurant is None:
        raise HTTPException(status_code=404, detail="Restaurant not found")

    existing = db.scalar(
        select(Diner).where(
            Diner.restaurant_id == restaurant.id,
            Diner.phone == body.phone,
        )
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="Phone already registered")

    diner = Diner(
        restaurant_id=restaurant.id,
        phone=body.phone,
        name=body.name,
        hashed_password=hashlib.sha256(body.password.encode()).hexdigest(),
    )
    db.add(diner)
    db.commit()
    db.refresh(diner)
    return DinerResponse(id=diner.id, phone=diner.phone, name=diner.name)


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
        status=str(order.status),
        table_id=order.table_id,
        restaurant_id=order.restaurant_id,
    )


@app.patch("/api/orders/{order_id}/status", response_model=OrderResponse)
def update_order_status(
    order_id: str, body: UpdateStatusRequest, db: DbDep
) -> OrderResponse:
    try:
        new_status = OrderStatus(body.status)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid status: {body.status!r}")

    order = db.scalar(select(Order).where(Order.id == order_id))
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")

    allowed = LEGAL_TRANSITIONS.get(OrderStatus(str(order.status)), set())
    if new_status not in allowed:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Cannot transition from {str(order.status)!r} "
                f"to {new_status.value!r}"
            ),
        )

    order.status = new_status
    db.commit()
    db.refresh(order)
    return OrderResponse(
        id=order.id,
        status=str(order.status),
        table_id=order.table_id,
        restaurant_id=order.restaurant_id,
    )


def main() -> None:
    uvicorn.run("mesadigital.api.main:app", host="0.0.0.0", port=8000, reload=False)
