from collections.abc import Generator
from datetime import datetime, timedelta, timezone
from typing import Annotated

import uvicorn
from fastapi import APIRouter, Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import select, text
from sqlalchemy.orm import Session, contains_eager

from mesadigital.api.db.models import (
    Category,
    Diner,
    MenuItem,
    Order,
    OrderItem,
    Restaurant,
    RestaurantTable,
    RestaurantUser,
)
from mesadigital.api.db.session import get_db
from mesadigital.api.dependencies import require_auth, require_restaurant_scope
from mesadigital.api.schemas import CategoryRead, CategoryUpdate, MenuItemRead, RestaurantRead, RestaurantUserRead
from mesadigital.api.security import create_token, hash_password, verify_password
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


class StaffLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class DinerPublicRegisterRequest(BaseModel):
    name: str = Field(min_length=2)
    phone: str = Field(min_length=1)


class DinerTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class CategoryCreateBody(BaseModel):
    name: str
    is_visible: bool = True
    display_order: int = 0


# ── API Router ────────────────────────────────────────────────────────────

api_router = APIRouter()


@api_router.get("/healthz")
def healthz(db: DbDep) -> dict[str, str]:
    try:
        db.execute(text("SELECT 1"))
        return {"db": "ok"}
    except Exception:
        raise HTTPException(status_code=503, detail={"db": "error"})


@api_router.post("/auth/login", response_model=StaffLoginResponse)
def staff_login(body: StaffLoginRequest, db: DbDep) -> StaffLoginResponse:
    user = db.scalar(select(RestaurantUser).where(RestaurantUser.email == body.email))
    password_ok = verify_password(body.password, user.hashed_password) if user is not None else False
    if user is None or not password_ok or not user.is_active:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_token(
        {
            "sub": user.id,
            "restaurant_id": user.restaurant_id,
            "role": str(user.role),
            "type": "staff",
        },
        timedelta(days=7),
    )
    return StaffLoginResponse(access_token=token)


@api_router.post("/public/restaurants/{restaurant_id}/diners/register")
def public_register_diner(
    restaurant_id: str, body: DinerPublicRegisterRequest, db: DbDep
) -> JSONResponse:
    restaurant = db.scalar(
        select(Restaurant).where(
            Restaurant.id == restaurant_id,
            Restaurant.is_active == True,  # noqa: E712
        )
    )
    if restaurant is None:
        raise HTTPException(status_code=404, detail="Restaurant not found")

    existing = db.scalar(
        select(Diner).where(
            Diner.restaurant_id == restaurant_id,
            Diner.phone == body.phone,
        )
    )

    now = datetime.now(timezone.utc)

    if existing is None:
        diner = Diner(
            restaurant_id=restaurant_id,
            phone=body.phone,
            name=body.name,
            hashed_password="",
            last_seen_at=now,
        )
        db.add(diner)
        db.commit()
        db.refresh(diner)
        http_status = 201
    else:
        existing.name = body.name
        existing.last_seen_at = now
        db.commit()
        db.refresh(existing)
        diner = existing
        http_status = 200

    token = create_token(
        {
            "sub": diner.id,
            "restaurant_id": diner.restaurant_id,
            "type": "diner",
        },
        timedelta(hours=24),
    )
    return JSONResponse(
        content={"access_token": token, "token_type": "bearer"},
        status_code=http_status,
    )


@api_router.get("/public/restaurants/{slug}", response_model=RestaurantRead)
def get_public_restaurant(slug: str, db: DbDep) -> RestaurantRead:
    restaurant = db.scalar(
        select(Restaurant).where(
            Restaurant.slug == slug,
            Restaurant.is_active == True,  # noqa: E712
        )
    )
    if restaurant is None:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    return RestaurantRead.model_validate(restaurant)


@api_router.get("/public/restaurants/{slug}/menu", response_model=list[CategoryRead])
def get_public_menu(slug: str, db: DbDep) -> list[CategoryRead]:
    restaurant = db.scalar(
        select(Restaurant).where(
            Restaurant.slug == slug,
            Restaurant.is_active == True,  # noqa: E712
        )
    )
    if restaurant is None:
        raise HTTPException(status_code=404, detail="Restaurant not found")

    stmt = (
        select(Category)
        .outerjoin(
            MenuItem,
            (MenuItem.category_id == Category.id) & (MenuItem.is_available == True),  # noqa: E712
        )
        .where(
            Category.restaurant_id == restaurant.id,
            Category.is_visible == True,  # noqa: E712
        )
        .order_by(Category.display_order, MenuItem.display_order)
        .options(contains_eager(Category.menu_items))
    )
    categories = db.scalars(stmt).unique().all()

    return [
        CategoryRead(
            id=cat.id,
            restaurant_id=cat.restaurant_id,
            name=cat.name,
            is_visible=cat.is_visible,
            display_order=cat.display_order,
            items=[
                MenuItemRead(
                    id=item.id,
                    restaurant_id=item.restaurant_id,
                    category_id=item.category_id,
                    name=item.name,
                    description=item.description,
                    price_cents=item.price_cents,
                    is_available=item.is_available,
                    display_order=item.display_order,
                )
                for item in sorted(cat.menu_items, key=lambda i: i.display_order)
            ],
        )
        for cat in categories
    ]


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
        hashed_password=hash_password(body.password),
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
        if not cat.is_visible:
            continue
        items_out = [
            MenuItemOut(
                id=item.id,
                name=item.name,
                description=item.description,
                price_cents=item.price_cents,
                available=item.is_available,
            )
            for item in sorted(cat.menu_items, key=lambda i: i.display_order)
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


# ── Category CRUD ─────────────────────────────────────────────────────────

_AdminScopeDep = Annotated[RestaurantUserRead, Depends(require_restaurant_scope)]
_AuthDep = Annotated[RestaurantUserRead, Depends(require_auth)]


@api_router.get("/restaurants/{restaurant_id}/categories", response_model=list[CategoryRead])
def list_categories(
    restaurant_id: str,
    db: DbDep,
    user: _AdminScopeDep,
) -> list[CategoryRead]:
    if str(user.role) != "admin":
        raise HTTPException(status_code=403, detail="Insufficient role")
    categories = db.scalars(
        select(Category)
        .where(Category.restaurant_id == restaurant_id)
        .order_by(Category.display_order)
    ).all()
    return [CategoryRead.model_validate(cat) for cat in categories]


@api_router.post(
    "/restaurants/{restaurant_id}/categories",
    response_model=CategoryRead,
    status_code=201,
)
def create_category(
    restaurant_id: str,
    body: CategoryCreateBody,
    db: DbDep,
    user: _AdminScopeDep,
) -> CategoryRead:
    if str(user.role) != "admin":
        raise HTTPException(status_code=403, detail="Insufficient role")
    cat = Category(
        restaurant_id=restaurant_id,
        name=body.name,
        is_visible=body.is_visible,
        display_order=body.display_order,
    )
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return CategoryRead.model_validate(cat)


@api_router.patch("/categories/{category_id}", response_model=CategoryRead)
def update_category(
    category_id: str,
    body: CategoryUpdate,
    db: DbDep,
    user: _AuthDep,
) -> CategoryRead:
    if str(user.role) != "admin":
        raise HTTPException(status_code=403, detail="Insufficient role")
    cat = db.scalar(select(Category).where(Category.id == category_id))
    if cat is None:
        raise HTTPException(status_code=404, detail="Category not found")
    if cat.restaurant_id != user.restaurant_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    if body.name is not None:
        cat.name = body.name
    if body.display_order is not None:
        cat.display_order = body.display_order
    if body.is_visible is not None:
        cat.is_visible = body.is_visible
    db.commit()
    db.refresh(cat)
    return CategoryRead.model_validate(cat)


@api_router.delete("/categories/{category_id}", status_code=204)
def delete_category(
    category_id: str,
    db: DbDep,
    user: _AuthDep,
) -> None:
    if str(user.role) != "admin":
        raise HTTPException(status_code=403, detail="Insufficient role")
    cat = db.scalar(select(Category).where(Category.id == category_id))
    if cat is None:
        raise HTTPException(status_code=404, detail="Category not found")
    if cat.restaurant_id != user.restaurant_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    if cat.menu_items:
        raise HTTPException(status_code=409, detail="Category has menu items")
    db.delete(cat)
    db.commit()


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
