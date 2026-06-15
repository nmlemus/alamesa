from shared.contracts import OrderStatus, RestaurantUserRole


def test_order_status_values() -> None:
    assert {s.value for s in OrderStatus} == {"pending", "confirmed", "ready", "closed"}


def test_restaurant_user_role_values() -> None:
    assert {r.value for r in RestaurantUserRole} == {"admin", "staff"}


def test_order_status_is_str_enum() -> None:
    assert isinstance(OrderStatus.PENDING, str)
    assert OrderStatus.PENDING == "pending"
    assert OrderStatus.CONFIRMED == "confirmed"
    assert OrderStatus.READY == "ready"
    assert OrderStatus.CLOSED == "closed"


def test_restaurant_user_role_is_str_enum() -> None:
    assert isinstance(RestaurantUserRole.ADMIN, str)
    assert RestaurantUserRole.ADMIN == "admin"
    assert RestaurantUserRole.STAFF == "staff"
