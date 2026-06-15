import hashlib
from collections.abc import Generator
from datetime import timedelta
from typing import Annotated

import uvicorn
from fastapi import APIRouter, Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from mesadigital.api.db.models import (
    Diner,
    MenuItem,
    Order,
    OrderItem,
    Restaurant,
    RestaurantTable,
    RestaurantUser,
)
from mesadigital.api.db.session import get_db
from mesadigital.api.security import create_token, verify_password
from mesadigital.api.settings import Settings, settings as default_settings
from shared.contracts import LEGAL_TRANSITIONS, OrderStatus

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


class StaffLoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ── API Router ────────────────────────────────────────────────────────────

api_router = APIRouter()


@api_router.post("/auth/login", response_model=TokenResponse)
def staff_login(body: StaffLoginRequest, db: DbDep) -> TokenResponse:
    _invalid = HTTPException(status_code=401, detail="Invalid credentials")
    user = db.scalar(select(RestaurantUser).where(RestaurantUser.email == body.email))
    if user is None or not verify_password(body.password, user.hashed_password):
        raise _invalid
    if not user.is_active:
        raise _invalid
    token = create_token(
        {
            "sub": user.id,
            "restaurant_id": user.restaurant_id,
            "role": str(user.role),
            "type": "staff",
        },
        timedelta(days=7),
    )
    return TokenResponse(access_token=token)


@api_router.get("/healthz")
def healthz(db: DbDep) -> dict[str, str]:
    try:
        db.execute(text("SELECT 1"))
        return {"db": "ok"}
    except Exception:
        raise HTTPException(status_code=503, detail={"db": "error"})


@api_router.post("/diners/register", response_model=DinerResponse, status_code=201)
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


@api_router.get("/restaurants/{slug}/menu", response_model=MenuResponse)
def get_menu(slug: str, db: DbDep) -> MenuResponse:
    restaurant = db.scalar(select(Restaurant).where(Restaurant.slug == slug))
    if restaurant is None:
        raise HTTPException(status_code=404, detail="Restaurant not found")

    categories_out: list[CategoryOut] = []
    for cat in sorted(restaurant.categories, key=lambda c: c.display_order):
        items_out = [
            MenuItemOut(
                id=item.id,
                name=item.name,
                description=item.description,
                price_cents=item.price_cents,
                available=item.is_available,
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


@api_router.post("/orders", response_model=OrderResponse, status_code=201)
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


@api_router.patch("/orders/{order_id}/status", response_model=OrderResponse)
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


# ── App factory ────────────────────────────────────────────────────────────


def create_app(cfg: Settings | None = None) -> FastAPI:
    if cfg is None:
        cfg = default_settings

    if "postgresql" in cfg.DATABASE_URL and cfg.SECRET_KEY == "dev-secret-change-in-prod":
        raise RuntimeError(
            "SECRET_KEY must be changed from the default value before using PostgreSQL"
        )

    if cfg.ENVIRONMENT == "prod" and "*" in cfg.CORS_ORIGINS:
        raise ValueError("Wildcard CORS origin '*' is not allowed in production")

    application = FastAPI(title="Mesa Digital API")

    application.add_middleware(
        CORSMiddleware,
        allow_origins=cfg.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.include_router(api_router, prefix="/api")

    @application.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return application


app = create_app()


def main() -> None:
    uvicorn.run("mesadigital.api.main:app", host="0.0.0.0", port=8000, reload=False)
