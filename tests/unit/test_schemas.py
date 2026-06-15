import pytest
from pydantic import ValidationError

from mesadigital.api.schemas import (
    DinerRead,
    MenuItemCreate,
    MenuItemRead,
    MenuItemUpdate,
    OrderCreate,
    OrderItemInput,
    OrderItemRead,
    OrderRead,
    OrderUpdate,
    RestaurantRead,
    RestaurantUserRead,
    TableRead,
)


# ── AC #2: status absent from OrderCreate / OrderUpdate ───────────────────────


def test_order_create_rejects_status_field() -> None:
    with pytest.raises(ValidationError):
        OrderCreate(
            restaurant_slug="demo",
            table_id=1,
            items=[],
            status="pending",  # type: ignore[call-arg]
        )


def test_order_update_rejects_status_field() -> None:
    with pytest.raises(ValidationError):
        OrderUpdate(status="confirmed")  # type: ignore[call-arg]


def test_order_create_valid_without_status() -> None:
    obj = OrderCreate(
        restaurant_slug="demo",
        table_id=1,
        items=[OrderItemInput(menu_item_id="42", quantity=2)],
    )
    assert obj.restaurant_slug == "demo"
    assert not hasattr(obj, "status")


# ── AC #3: hashed_password absent from RestaurantUserRead ─────────────────────


def test_restaurant_user_read_has_no_hashed_password() -> None:
    fields = RestaurantUserRead.model_fields
    assert "hashed_password" not in fields
    assert "password_hash" not in fields


# ── AC #4: price_cents gt=0 on MenuItemCreate / MenuItemUpdate ────────────────


def test_menu_item_create_price_cents_must_be_positive() -> None:
    with pytest.raises(ValidationError):
        MenuItemCreate(
            restaurant_id=1,
            category_id=1,
            name="Tacos",
            price_cents=0,
        )


def test_menu_item_create_negative_price_rejected() -> None:
    with pytest.raises(ValidationError):
        MenuItemCreate(
            restaurant_id=1,
            category_id=1,
            name="Tacos",
            price_cents=-100,
        )


def test_menu_item_create_valid_price() -> None:
    obj = MenuItemCreate(
        restaurant_id=1, category_id=1, name="Tacos", price_cents=1200
    )
    assert obj.price_cents == 1200


def test_menu_item_update_price_cents_must_be_positive_when_set() -> None:
    with pytest.raises(ValidationError):
        MenuItemUpdate(price_cents=0)


def test_menu_item_update_none_price_is_valid() -> None:
    obj = MenuItemUpdate(price_cents=None)
    assert obj.price_cents is None


def test_menu_item_update_positive_price_is_valid() -> None:
    obj = MenuItemUpdate(price_cents=500)
    assert obj.price_cents == 500


# ── AC #5: OrderItemInput validation ──────────────────────────────────────────


def test_order_item_input_quantity_ge_1() -> None:
    with pytest.raises(ValidationError):
        OrderItemInput(menu_item_id="1", quantity=0)


def test_order_item_input_negative_quantity_rejected() -> None:
    with pytest.raises(ValidationError):
        OrderItemInput(menu_item_id="1", quantity=-1)


def test_order_item_input_menu_item_id_is_str() -> None:
    obj = OrderItemInput(menu_item_id="abc-123", quantity=3)
    assert isinstance(obj.menu_item_id, str)
    assert obj.menu_item_id == "abc-123"


def test_order_item_input_valid() -> None:
    obj = OrderItemInput(menu_item_id="42", quantity=1)
    assert obj.quantity == 1


# ── AC #6: TableRead.qr_url computed from restaurant.slug + table.number ──────


def test_table_read_qr_url_from_orm_object() -> None:
    class FakeRestaurant:
        slug = "mi-restaurante"

    class FakeTable:
        id = 7
        restaurant_id = 3
        number = 5
        label = "Terraza"
        restaurant = FakeRestaurant()

    table_read = TableRead.model_validate(FakeTable())
    assert table_read.qr_url == "/qr/mi-restaurante/5"
    assert table_read.number == 5


def test_table_read_qr_url_from_dict() -> None:
    obj = TableRead.model_validate(
        {
            "id": 1,
            "restaurant_id": 2,
            "number": 3,
            "label": None,
            "qr_url": "/qr/slug/3",
        }
    )
    assert obj.qr_url == "/qr/slug/3"


# ── AC #7: from_attributes=True on all Read schemas ──────────────────────────


@pytest.mark.parametrize(
    "schema",
    [
        RestaurantRead,
        RestaurantUserRead,
        DinerRead,
        MenuItemRead,
        TableRead,
        OrderRead,
        OrderItemRead,
    ],
)
def test_read_schema_has_from_attributes(schema: type) -> None:
    assert schema.model_config.get("from_attributes") is True
