from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from mesadigital.api.db.models import OrderStatus, RestaurantUserRole


# ── Restaurant ────────────────────────────────────────────────────────────────


class RestaurantCreate(BaseModel):
    slug: str
    name: str


class RestaurantUpdate(BaseModel):
    slug: str | None = None
    name: str | None = None


class RestaurantRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    name: str


# ── RestaurantUser ────────────────────────────────────────────────────────────


class RestaurantUserCreate(BaseModel):
    restaurant_id: int
    email: str
    password: str
    role: RestaurantUserRole


class RestaurantUserUpdate(BaseModel):
    email: str | None = None
    password: str | None = None
    role: RestaurantUserRole | None = None


class RestaurantUserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    restaurant_id: str
    email: str
    role: RestaurantUserRole
    # hashed_password intentionally absent (structural field-level security)


# ── Diner ─────────────────────────────────────────────────────────────────────


class DinerCreate(BaseModel):
    email: str
    name: str
    password: str


class DinerUpdate(BaseModel):
    email: str | None = None
    name: str | None = None
    password: str | None = None


class DinerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    restaurant_id: str
    phone: str
    name: str


# ── Category ──────────────────────────────────────────────────────────────────


class CategoryCreate(BaseModel):
    restaurant_id: int
    name: str
    is_visible: bool = True
    display_order: int = 0


class CategoryUpdate(BaseModel):
    name: str | None = None
    is_visible: bool | None = None
    display_order: int | None = None


class CategoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    restaurant_id: int
    name: str
    is_visible: bool
    display_order: int


# ── MenuItem ──────────────────────────────────────────────────────────────────


class MenuItemCreate(BaseModel):
    restaurant_id: int
    category_id: int
    name: str
    description: str | None = None
    price_cents: Annotated[int, Field(gt=0)]
    is_available: bool = True
    display_order: int = 0


class MenuItemUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    price_cents: Annotated[int, Field(gt=0)] | None = None
    is_available: bool | None = None
    display_order: int | None = None


class MenuItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    restaurant_id: int
    category_id: int
    name: str
    description: str | None
    price_cents: int
    is_available: bool
    display_order: int


# ── Table ─────────────────────────────────────────────────────────────────────


class TableCreate(BaseModel):
    restaurant_id: int
    number: int
    label: str | None = None


class TableUpdate(BaseModel):
    number: int | None = None
    label: str | None = None


class TableRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    restaurant_id: int
    number: int
    label: str | None
    qr_url: str

    @model_validator(mode="before")
    @classmethod
    def _compute_qr_url(cls, data: Any) -> Any:
        if isinstance(data, dict):
            return data
        restaurant = getattr(data, "restaurant", None)
        slug = restaurant.slug if restaurant is not None else ""
        return {
            "id": data.id,
            "restaurant_id": data.restaurant_id,
            "number": data.number,
            "label": data.label,
            "qr_url": f"/qr/{slug}/{data.number}",
        }


# ── Order ─────────────────────────────────────────────────────────────────────


class OrderItemInput(BaseModel):
    menu_item_id: str
    quantity: Annotated[int, Field(ge=1)]


class OrderCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    restaurant_slug: str
    table_id: int
    diner_id: int | None = None
    items: list[OrderItemInput]
    # status intentionally absent (structural field-level security)


class OrderUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    table_id: int | None = None
    diner_id: int | None = None
    # status intentionally absent (structural field-level security)


class OrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    restaurant_id: int
    table_id: int
    diner_id: int | None
    status: OrderStatus
    created_at: datetime


# ── OrderItem ─────────────────────────────────────────────────────────────────


class OrderItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_id: int
    menu_item_id: int
    quantity: int
    unit_price_cents: int
