import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Annotated, AsyncGenerator

import sentry_sdk
import uvicorn
from fastapi import APIRouter, Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import and_, func, or_, select, text
from sqlalchemy.orm import Session, contains_eager
from sqlalchemy.orm.exc import StaleDataError

from mesadigital.api.db.models import (
    Category,
    Diner,
    MenuItem,
    Order,
    OrderEvent,
    OrderItem,
    Restaurant,
    RestaurantTable,
    RestaurantUser,
)
from mesadigital.api.db.session import get_db
from mesadigital.api.db.store import validate_transition
from mesadigital.api.dependencies import TokenClaims, require_any_auth, require_auth, require_diner_auth, require_role
from mesadigital.api.middleware import RequestLoggingMiddleware
from mesadigital.api.schemas import CategoryRead, CategoryUpdate, DinerRead, MenuItemRead, MenuItemUpdate, OrderRead, RestaurantRead, RestaurantUserRead, TableRead
from mesadigital.api.security import create_token, hash_password, verify_password
from mesadigital.api.settings import Settings, settings as default_settings
from shared.contracts import LEGAL_TRANSITIONS, OrderEventActorType, OrderStatus, RestaurantUserRole

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
    items: list[OrderItemRequest]


class OrderItemInResponse(BaseModel):
    id: str
    menu_item_id: str
    quantity: int
    unit_price_cents: int
    item_snapshot_name: str


class OrderReadWithItems(BaseModel):
    id: str
    restaurant_id: str
    table_id: str
    diner_id: str | None
    status: str
    created_at: datetime
    items: list[OrderItemInResponse]
    total_cents: int
    item_count: int


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


class TableCreateBody(BaseModel):
    number: int
    label: str | None = None


class TableUpdateBody(BaseModel):
    label: str | None = None
    is_active: bool | None = None


class RestaurantPatchBody(BaseModel):
    name: str | None = None
    slug: str | None = None


class TableQRResponse(BaseModel):
    table_id: str
    qr_url: str


class CreateRestaurantUserRequest(BaseModel):
    email: str
    password: str
    role: RestaurantUserRole


class PatchRestaurantUserRequest(BaseModel):
    role: RestaurantUserRole | None = None
    is_active: bool | None = None



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


@api_router.get("/public/restaurants/{slug}/tables/{number}", response_model=TableRead)
def get_public_table(slug: str, number: int, db: DbDep) -> TableRead:
    restaurant = db.scalar(
        select(Restaurant).where(
            Restaurant.slug == slug,
            Restaurant.is_active == True,  # noqa: E712
        )
    )
    if restaurant is None:
        raise HTTPException(status_code=404, detail="Restaurant not found")

    table = db.scalar(
        select(RestaurantTable).where(
            RestaurantTable.restaurant_id == restaurant.id,
            RestaurantTable.number == number,
            RestaurantTable.is_active == True,  # noqa: E712
        )
    )
    if table is None:
        raise HTTPException(status_code=404, detail="Table not found")

    return TableRead(
        id=table.id,
        restaurant_id=table.restaurant_id,
        number=table.number,
        label=table.label,
        is_active=table.is_active,
        qr_url=f"/qr/{slug}/{table.number}",
    )


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


@api_router.post("/orders", response_model=OrderReadWithItems, status_code=201)
def create_order(
    body: CreateOrderRequest,
    db: DbDep,
    diner: Annotated[DinerRead, Depends(require_diner_auth)],
) -> OrderReadWithItems:
    restaurant = db.scalar(
        select(Restaurant).where(
            Restaurant.slug == body.restaurant_slug,
            Restaurant.is_active == True,  # noqa: E712
        )
    )
    if restaurant is None:
        raise HTTPException(status_code=404, detail="Restaurant not found")

    if diner.restaurant_id != restaurant.id:
        raise HTTPException(status_code=403, detail="Diner does not belong to this restaurant")

    table = db.scalar(
        select(RestaurantTable).where(
            RestaurantTable.id == body.table_id,
            RestaurantTable.restaurant_id == restaurant.id,
            RestaurantTable.is_active == True,  # noqa: E712
        )
    )
    if table is None:
        raise HTTPException(status_code=422, detail="Table not found or inactive")

    # Validate all items upfront; collect failing IDs
    failing_item_ids: list[str] = []
    resolved_items: dict[str, MenuItem] = {}
    for req in body.items:
        item = db.scalar(
            select(MenuItem).where(
                MenuItem.id == req.menu_item_id,
                MenuItem.restaurant_id == restaurant.id,
            )
        )
        if item is None or not item.is_available:
            failing_item_ids.append(req.menu_item_id)
        else:
            resolved_items[req.menu_item_id] = item

    if failing_item_ids:
        raise HTTPException(
            status_code=422,
            detail={"unavailable_item_ids": failing_item_ids},
        )

    # Single transaction: order + items (with snapshots) + creation event
    order = Order(
        restaurant_id=restaurant.id,
        table_id=table.id,
        diner_id=diner.id,
        status=OrderStatus.PENDING,
    )
    db.add(order)
    db.flush()

    for req in body.items:
        mi = resolved_items[req.menu_item_id]
        db.add(
            OrderItem(
                order_id=order.id,
                menu_item_id=mi.id,
                quantity=req.quantity,
                unit_price_cents=mi.price_cents,
                item_snapshot_name=mi.name,
            )
        )

    db.add(
        OrderEvent(
            order_id=order.id,
            actor_type=OrderEventActorType.DINER,
            actor_id=diner.id,
            from_status=OrderStatus.PENDING,
            to_status=OrderStatus.PENDING,
        )
    )

    db.commit()
    db.refresh(order)

    items_out = [
        OrderItemInResponse(
            id=oi.id,
            menu_item_id=oi.menu_item_id,
            quantity=oi.quantity,
            unit_price_cents=oi.unit_price_cents,
            item_snapshot_name=oi.item_snapshot_name,
        )
        for oi in order.items
    ]
    total_cents = sum(oi.unit_price_cents * oi.quantity for oi in order.items)
    item_count = sum(oi.quantity for oi in order.items)

    return OrderReadWithItems(
        id=order.id,
        restaurant_id=order.restaurant_id,
        table_id=order.table_id,
        diner_id=order.diner_id,
        status=str(order.status),
        created_at=order.created_at,
        items=items_out,
        total_cents=total_cents,
        item_count=item_count,
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


@api_router.post("/orders/{order_id}/confirm", response_model=OrderRead)
def confirm_order(
    order_id: str,
    db: DbDep,
    staff: Annotated[RestaurantUserRead, Depends(require_auth)],
) -> OrderRead:
    order = db.scalar(select(Order).where(Order.id == order_id).with_for_update())
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.restaurant_id != staff.restaurant_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    validate_transition(order, OrderStatus.CONFIRMED, OrderEventActorType.STAFF)

    now = datetime.now(timezone.utc)
    order.status = OrderStatus.CONFIRMED
    order.confirmed_at = now
    order.updated_at = now

    db.add(
        OrderEvent(
            order_id=order.id,
            actor_type=OrderEventActorType.STAFF,
            actor_id=staff.id,
            from_status=OrderStatus.PENDING,
            to_status=OrderStatus.CONFIRMED,
        )
    )

    try:
        db.commit()
    except StaleDataError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Order was modified concurrently")
    db.refresh(order)
    return OrderRead.model_validate(order)


@api_router.post("/orders/{order_id}/cancel", response_model=OrderRead)
def cancel_order(
    order_id: str,
    db: DbDep,
    auth: Annotated[TokenClaims, Depends(require_any_auth)],
) -> OrderRead:
    order = db.scalar(select(Order).where(Order.id == order_id).with_for_update())
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.restaurant_id != auth.restaurant_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    actor_type = (
        OrderEventActorType.DINER if auth.token_type == "diner" else OrderEventActorType.STAFF
    )

    if actor_type == OrderEventActorType.DINER:
        if order.diner_id != auth.sub:
            raise HTTPException(status_code=403, detail="Forbidden")
        if order.status != OrderStatus.PENDING:
            raise HTTPException(status_code=403, detail="Forbidden")

    from_status = OrderStatus(order.status)
    validate_transition(order, OrderStatus.CANCELLED, actor_type)

    now = datetime.now(timezone.utc)
    order.status = OrderStatus.CANCELLED
    order.cancelled_at = now
    order.updated_at = now

    db.add(
        OrderEvent(
            order_id=order.id,
            actor_type=actor_type,
            actor_id=auth.sub,
            from_status=from_status,
            to_status=OrderStatus.CANCELLED,
        )
    )

    try:
        db.commit()
    except StaleDataError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Order was modified concurrently")
    db.refresh(order)
    return OrderRead.model_validate(order)


@api_router.post("/orders/{order_id}/start-preparing", response_model=OrderRead)
def start_preparing_order(
    order_id: str,
    db: DbDep,
    staff: Annotated[RestaurantUserRead, Depends(require_auth)],
) -> OrderRead:
    order = db.scalar(select(Order).where(Order.id == order_id).with_for_update())
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.restaurant_id != staff.restaurant_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    validate_transition(order, OrderStatus.PREPARING, OrderEventActorType.STAFF)

    now = datetime.now(timezone.utc)
    order.status = OrderStatus.PREPARING
    order.preparing_at = now
    order.updated_at = now

    db.add(
        OrderEvent(
            order_id=order.id,
            actor_type=OrderEventActorType.STAFF,
            actor_id=staff.id,
            from_status=OrderStatus.CONFIRMED,
            to_status=OrderStatus.PREPARING,
        )
    )

    try:
        db.commit()
    except StaleDataError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Order was modified concurrently")
    db.refresh(order)
    return OrderRead.model_validate(order)


@api_router.post("/orders/{order_id}/mark-ready", response_model=OrderRead)
def mark_ready_order(
    order_id: str,
    db: DbDep,
    staff: Annotated[RestaurantUserRead, Depends(require_auth)],
) -> OrderRead:
    order = db.scalar(select(Order).where(Order.id == order_id).with_for_update())
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.restaurant_id != staff.restaurant_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    validate_transition(order, OrderStatus.READY, OrderEventActorType.STAFF)

    now = datetime.now(timezone.utc)
    order.status = OrderStatus.READY
    order.ready_at = now
    order.updated_at = now

    db.add(
        OrderEvent(
            order_id=order.id,
            actor_type=OrderEventActorType.STAFF,
            actor_id=staff.id,
            from_status=OrderStatus.PREPARING,
            to_status=OrderStatus.READY,
        )
    )

    try:
        db.commit()
    except StaleDataError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Order was modified concurrently")
    db.refresh(order)
    return OrderRead.model_validate(order)


@api_router.post("/orders/{order_id}/close", response_model=OrderRead)
def close_order(
    order_id: str,
    db: DbDep,
    staff: Annotated[RestaurantUserRead, Depends(require_auth)],
) -> OrderRead:
    order = db.scalar(select(Order).where(Order.id == order_id).with_for_update())
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.restaurant_id != staff.restaurant_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    validate_transition(order, OrderStatus.CLOSED, OrderEventActorType.STAFF)

    now = datetime.now(timezone.utc)
    order.status = OrderStatus.CLOSED
    order.closed_at = now
    order.updated_at = now

    db.add(
        OrderEvent(
            order_id=order.id,
            actor_type=OrderEventActorType.STAFF,
            actor_id=staff.id,
            from_status=OrderStatus.READY,
            to_status=OrderStatus.CLOSED,
        )
    )

    try:
        db.commit()
    except StaleDataError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Order was modified concurrently")
    db.refresh(order)
    return OrderRead.model_validate(order)


@api_router.get("/orders/{order_id}", response_model=OrderReadWithItems)
def get_order(
    order_id: str,
    db: DbDep,
    auth: Annotated[TokenClaims, Depends(require_any_auth)],
) -> OrderReadWithItems:
    order = db.scalar(select(Order).where(Order.id == order_id))
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")

    if auth.token_type == "diner":
        if order.diner_id != auth.sub or order.restaurant_id != auth.restaurant_id:
            raise HTTPException(status_code=403, detail="Forbidden")
    else:
        if order.restaurant_id != auth.restaurant_id:
            raise HTTPException(status_code=403, detail="Forbidden")

    items_out = [
        OrderItemInResponse(
            id=oi.id,
            menu_item_id=oi.menu_item_id,
            quantity=oi.quantity,
            unit_price_cents=oi.unit_price_cents,
            item_snapshot_name=oi.item_snapshot_name,
        )
        for oi in order.items
    ]
    total_cents = sum(oi.unit_price_cents * oi.quantity for oi in order.items)
    item_count = sum(oi.quantity for oi in order.items)

    return OrderReadWithItems(
        id=order.id,
        restaurant_id=order.restaurant_id,
        table_id=order.table_id,
        diner_id=order.diner_id,
        status=str(order.status),
        created_at=order.created_at,
        items=items_out,
        total_cents=total_cents,
        item_count=item_count,
    )


_SSE_POLL_INTERVAL = 2.0
_SSE_MAX_ITERATIONS: int | None = None  # None = infinite; set to finite in tests


@api_router.get("/restaurants/{rid}/orders/stream")
async def stream_restaurant_orders(
    rid: str,
    db: DbDep,
    staff: Annotated[RestaurantUserRead, Depends(require_auth)],
) -> StreamingResponse:
    if staff.restaurant_id != rid:
        raise HTTPException(status_code=403, detail="Forbidden")

    async def generate() -> AsyncGenerator[str, None]:
        yield "retry: 3000\n\n"
        seen: dict[str, str] = {}
        iteration = 0

        while _SSE_MAX_ITERATIONS is None or iteration < _SSE_MAX_ITERATIONS:
            iteration += 1
            orders = db.scalars(
                select(Order)
                .where(Order.restaurant_id == rid)
                .order_by(Order.created_at.desc())
                .limit(200)
            ).all()

            for order in orders:
                status_str = str(order.status)
                if seen.get(order.id) != status_str:
                    seen[order.id] = status_str
                    payload = OrderRead.model_validate(order).model_dump_json()
                    yield f"event: order_updated\ndata: {payload}\n\n"

            await asyncio.sleep(_SSE_POLL_INTERVAL)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@api_router.get("/restaurants/{rid}/orders", response_model=list[OrderRead])
def list_restaurant_orders(
    rid: str,
    db: DbDep,
    staff: Annotated[RestaurantUserRead, Depends(require_auth)],
    status: str | None = None,
    before: str | None = None,
    limit: int = 100,
) -> list[OrderRead]:
    if staff.restaurant_id != rid:
        raise HTTPException(status_code=403, detail="Forbidden")

    stmt = (
        select(Order)
        .where(Order.restaurant_id == rid)
        .order_by(Order.created_at.desc(), Order.id.desc())
        .limit(limit)
    )

    if status is not None:
        raw_statuses = [s.strip() for s in status.split(",") if s.strip()]
        try:
            statuses = [OrderStatus(s) for s in raw_statuses]
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=f"Invalid status value: {exc}")
        if statuses:
            stmt = stmt.where(Order.status.in_(statuses))

    if before is not None:
        pivot_exists = db.scalar(
            select(func.count()).where(Order.id == before, Order.restaurant_id == rid)
        )
        if not pivot_exists:
            raise HTTPException(status_code=422, detail="Invalid cursor: order not found")
        # Use a scalar subquery so both sides of the comparison use the same
        # SQLite string format, avoiding Python datetime serialisation mismatches.
        pivot_ca = select(Order.created_at).where(Order.id == before).scalar_subquery()
        stmt = stmt.where(
            or_(
                Order.created_at < pivot_ca,
                and_(Order.created_at == pivot_ca, Order.id < before),
            )
        )

    orders = db.scalars(stmt).all()
    return [OrderRead.model_validate(o) for o in orders]


@api_router.get("/restaurants/{rid}/tables", response_model=list[TableRead])
def list_tables(
    rid: str,
    db: DbDep,
    admin: Annotated[RestaurantUserRead, Depends(require_role(["admin"]))],
) -> list[TableRead]:
    if admin.restaurant_id != rid:
        raise HTTPException(status_code=403, detail="Forbidden")
    tables = db.scalars(
        select(RestaurantTable)
        .where(RestaurantTable.restaurant_id == rid)
        .order_by(RestaurantTable.number)
    ).all()
    return [TableRead.model_validate(t) for t in tables]


@api_router.post("/restaurants/{rid}/tables", response_model=TableRead, status_code=201)
def create_table(
    rid: str,
    body: TableCreateBody,
    db: DbDep,
    admin: Annotated[RestaurantUserRead, Depends(require_role(["admin"]))],
) -> TableRead:
    if admin.restaurant_id != rid:
        raise HTTPException(status_code=403, detail="Forbidden")
    restaurant = db.scalar(select(Restaurant).where(Restaurant.id == rid))
    if restaurant is None:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    existing = db.scalar(
        select(RestaurantTable).where(
            RestaurantTable.restaurant_id == rid,
            RestaurantTable.number == body.number,
        )
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="Table number already exists in this restaurant")
    table = RestaurantTable(restaurant_id=rid, number=body.number, label=body.label)
    db.add(table)
    db.flush()
    if restaurant.first_qr_generated_at is None:
        restaurant.first_qr_generated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(table)
    return TableRead.model_validate(table)


@api_router.patch("/tables/{table_id}", response_model=TableRead)
def update_table(
    table_id: str,
    body: TableUpdateBody,
    db: DbDep,
    admin: Annotated[RestaurantUserRead, Depends(require_role(["admin"]))],
) -> TableRead:
    table = db.scalar(select(RestaurantTable).where(RestaurantTable.id == table_id))
    if table is None:
        raise HTTPException(status_code=404, detail="Table not found")
    if table.restaurant_id != admin.restaurant_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    if body.label is not None:
        table.label = body.label
    if body.is_active is not None:
        table.is_active = body.is_active
    db.commit()
    db.refresh(table)
    return TableRead.model_validate(table)


@api_router.patch("/restaurants/{rid}", response_model=RestaurantRead)
def update_restaurant(
    rid: str,
    body: RestaurantPatchBody,
    db: DbDep,
    admin: Annotated[RestaurantUserRead, Depends(require_role(["admin"]))],
) -> RestaurantRead:
    if admin.restaurant_id != rid:
        raise HTTPException(status_code=403, detail="Forbidden")
    restaurant = db.scalar(select(Restaurant).where(Restaurant.id == rid))
    if restaurant is None:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    if body.slug is not None and restaurant.first_qr_generated_at is not None:
        raise HTTPException(status_code=409, detail="Slug is immutable after first QR generation.")
    if body.name is not None:
        restaurant.name = body.name
    if body.slug is not None:
        restaurant.slug = body.slug
    db.commit()
    db.refresh(restaurant)
    return RestaurantRead.model_validate(restaurant)


@api_router.get("/tables/{table_id}/qr", response_model=TableQRResponse)
def get_table_qr(
    table_id: str,
    db: DbDep,
    staff: Annotated[RestaurantUserRead, Depends(require_auth)],
) -> TableQRResponse:
    table = db.scalar(select(RestaurantTable).where(RestaurantTable.id == table_id))
    if table is None:
        raise HTTPException(status_code=404, detail="Table not found")
    if table.restaurant_id != staff.restaurant_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    restaurant = table.restaurant
    if restaurant.first_qr_generated_at is None:
        restaurant.first_qr_generated_at = datetime.now(timezone.utc)
        db.commit()
    return TableQRResponse(table_id=table_id, qr_url=f"/qr/{restaurant.slug}/{table.number}")


# ── Category CRUD ─────────────────────────────────────────────────────────


class CategoryCreateBody(BaseModel):
    name: str
    is_visible: bool = True
    display_order: int = 0


@api_router.get("/restaurants/{rid}/categories", response_model=list[CategoryRead])
def list_categories(
    rid: str,
    db: DbDep,
    staff: Annotated[RestaurantUserRead, Depends(require_auth)],
) -> list[CategoryRead]:
    if staff.restaurant_id != rid:
        raise HTTPException(status_code=403, detail="Forbidden")
    categories = db.scalars(
        select(Category)
        .where(Category.restaurant_id == rid)
        .order_by(Category.display_order)
    ).all()
    return [CategoryRead.model_validate(cat) for cat in categories]


@api_router.post("/restaurants/{rid}/categories", response_model=CategoryRead, status_code=201)
def create_category(
    rid: str,
    body: CategoryCreateBody,
    db: DbDep,
    staff: Annotated[RestaurantUserRead, Depends(require_auth)],
) -> CategoryRead:
    if staff.restaurant_id != rid:
        raise HTTPException(status_code=403, detail="Forbidden")
    category = Category(
        restaurant_id=rid,
        name=body.name,
        is_visible=body.is_visible,
        display_order=body.display_order,
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    return CategoryRead.model_validate(category)


@api_router.patch("/categories/{category_id}", response_model=CategoryRead)
def update_category(
    category_id: str,
    body: CategoryUpdate,
    db: DbDep,
    staff: Annotated[RestaurantUserRead, Depends(require_auth)],
) -> CategoryRead:
    category = db.scalar(select(Category).where(Category.id == category_id))
    if category is None:
        raise HTTPException(status_code=404, detail="Category not found")
    if category.restaurant_id != staff.restaurant_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    if body.name is not None:
        category.name = body.name
    if body.is_visible is not None:
        category.is_visible = body.is_visible
    if body.display_order is not None:
        category.display_order = body.display_order
    db.commit()
    db.refresh(category)
    return CategoryRead.model_validate(category)


@api_router.delete("/categories/{category_id}", status_code=204)
def delete_category(
    category_id: str,
    db: DbDep,
    staff: Annotated[RestaurantUserRead, Depends(require_auth)],
) -> None:
    category = db.scalar(select(Category).where(Category.id == category_id))
    if category is None:
        raise HTTPException(status_code=404, detail="Category not found")
    if category.restaurant_id != staff.restaurant_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    if category.menu_items:
        raise HTTPException(status_code=409, detail="Category has menu items")
    db.delete(category)
    db.commit()


# ── MenuItem CRUD ─────────────────────────────────────────────────────────


class MenuItemCreateBody(BaseModel):
    category_id: str
    name: str
    description: str | None = None
    price_cents: int = Field(gt=0)
    is_available: bool = True
    display_order: int = 0


@api_router.get("/restaurants/{rid}/menu-items", response_model=list[MenuItemRead])
def list_menu_items(
    rid: str,
    db: DbDep,
    staff: Annotated[RestaurantUserRead, Depends(require_auth)],
    category_id: str | None = None,
) -> list[MenuItemRead]:
    if staff.restaurant_id != rid:
        raise HTTPException(status_code=403, detail="Forbidden")
    q = select(MenuItem).where(MenuItem.restaurant_id == rid)
    if category_id is not None:
        q = q.where(MenuItem.category_id == category_id)
    q = q.order_by(MenuItem.display_order)
    items = db.scalars(q).all()
    return [MenuItemRead.model_validate(item) for item in items]


@api_router.post("/restaurants/{rid}/menu-items", response_model=MenuItemRead, status_code=201)
def create_menu_item(
    rid: str,
    body: MenuItemCreateBody,
    db: DbDep,
    staff: Annotated[RestaurantUserRead, Depends(require_auth)],
) -> MenuItemRead:
    if staff.restaurant_id != rid:
        raise HTTPException(status_code=403, detail="Forbidden")
    category = db.scalar(select(Category).where(Category.id == body.category_id))
    if category is None or category.restaurant_id != rid:
        raise HTTPException(status_code=422, detail="category_id does not belong to this restaurant")
    item = MenuItem(
        restaurant_id=rid,
        category_id=body.category_id,
        name=body.name,
        description=body.description,
        price_cents=body.price_cents,
        is_available=body.is_available,
        display_order=body.display_order,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return MenuItemRead.model_validate(item)


@api_router.patch("/menu-items/{item_id}", response_model=MenuItemRead)
def update_menu_item(
    item_id: str,
    body: MenuItemUpdate,
    db: DbDep,
    staff: Annotated[RestaurantUserRead, Depends(require_auth)],
) -> MenuItemRead:
    item = db.scalar(select(MenuItem).where(MenuItem.id == item_id))
    if item is None:
        raise HTTPException(status_code=404, detail="MenuItem not found")
    if item.restaurant_id != staff.restaurant_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    if body.category_id is not None:
        category = db.scalar(select(Category).where(Category.id == body.category_id))
        if category is None or category.restaurant_id != staff.restaurant_id:
            raise HTTPException(status_code=422, detail="category_id does not belong to this restaurant")
        item.category_id = body.category_id
    if body.name is not None:
        item.name = body.name
    if body.description is not None:
        item.description = body.description
    if body.price_cents is not None:
        item.price_cents = body.price_cents
    if body.is_available is not None:
        item.is_available = body.is_available
    if body.display_order is not None:
        item.display_order = body.display_order
    db.commit()
    db.refresh(item)
    return MenuItemRead.model_validate(item)


@api_router.delete("/menu-items/{item_id}", status_code=204)
def delete_menu_item(
    item_id: str,
    db: DbDep,
    staff: Annotated[RestaurantUserRead, Depends(require_auth)],
) -> None:
    item = db.scalar(select(MenuItem).where(MenuItem.id == item_id))
    if item is None:
        raise HTTPException(status_code=404, detail="MenuItem not found")
    if item.restaurant_id != staff.restaurant_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    db.delete(item)
    db.commit()


# ── Restaurant Users CRUD ──────────────────────────────────────────────────


@api_router.get("/restaurants/{rid}/users", response_model=list[RestaurantUserRead])
def list_restaurant_users(
    rid: str,
    db: DbDep,
    admin: Annotated[RestaurantUserRead, Depends(require_role(["admin"]))],
) -> list[RestaurantUserRead]:
    if admin.restaurant_id != rid:
        raise HTTPException(status_code=403, detail="Forbidden")
    users = db.scalars(
        select(RestaurantUser).where(RestaurantUser.restaurant_id == rid)
    ).all()
    return [RestaurantUserRead.model_validate(u) for u in users]


@api_router.post("/restaurants/{rid}/users", response_model=RestaurantUserRead, status_code=201)
def create_restaurant_user(
    rid: str,
    body: CreateRestaurantUserRequest,
    db: DbDep,
    admin: Annotated[RestaurantUserRead, Depends(require_role(["admin"]))],
) -> RestaurantUserRead:
    if admin.restaurant_id != rid:
        raise HTTPException(status_code=403, detail="Forbidden")
    existing = db.scalar(
        select(RestaurantUser).where(
            RestaurantUser.restaurant_id == rid,
            RestaurantUser.email == body.email,
        )
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="Email already registered")
    user = RestaurantUser(
        restaurant_id=rid,
        email=body.email,
        hashed_password=hash_password(body.password),
        role=body.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return RestaurantUserRead.model_validate(user)


@api_router.patch("/users/{user_id}", response_model=RestaurantUserRead)
def patch_restaurant_user(
    user_id: str,
    body: PatchRestaurantUserRequest,
    db: DbDep,
    admin: Annotated[RestaurantUserRead, Depends(require_role(["admin"]))],
) -> RestaurantUserRead:
    user = db.scalar(select(RestaurantUser).where(RestaurantUser.id == user_id))
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if user.restaurant_id != admin.restaurant_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    if body.is_active is False and user_id == admin.id:
        raise HTTPException(status_code=403, detail="Cannot deactivate your own account")
    if body.role is not None:
        user.role = body.role
    if body.is_active is not None:
        user.is_active = body.is_active
    db.commit()
    db.refresh(user)
    return RestaurantUserRead.model_validate(user)


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

    if cfg.SENTRY_DSN:
        sentry_sdk.init(dsn=cfg.SENTRY_DSN, environment=cfg.ENVIRONMENT)

    logging.getLogger("mesadigital.api.access").setLevel(logging.INFO)

    application = FastAPI(title="Mesa Digital API")

    application.add_middleware(
        CORSMiddleware,
        allow_origins=cfg.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.add_middleware(RequestLoggingMiddleware)

    application.include_router(api_router, prefix="/api")

    @application.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return application


app = create_app()


def main() -> None:
    uvicorn.run("mesadigital.api.main:app", host="0.0.0.0", port=8000, reload=False)
