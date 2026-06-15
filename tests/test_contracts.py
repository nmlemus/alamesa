from shared.contracts import OrderEventActorType, OrderStatus, RestaurantUserRole


def test_order_status_values() -> None:
    assert {s.value for s in OrderStatus} == {
        "pending",
        "confirmed",
        "preparing",
        "ready",
        "closed",
        "cancelled",
    }


def test_restaurant_user_role_values() -> None:
    assert {r.value for r in RestaurantUserRole} == {"admin", "staff"}


def test_order_event_actor_type_values() -> None:
    assert {a.value for a in OrderEventActorType} == {"diner", "staff", "system"}


def test_order_status_is_str_enum() -> None:
    assert isinstance(OrderStatus.PENDING, str)
    assert OrderStatus.PENDING == "pending"
    assert OrderStatus.CONFIRMED == "confirmed"
    assert OrderStatus.PREPARING == "preparing"
    assert OrderStatus.READY == "ready"
    assert OrderStatus.CLOSED == "closed"
    assert OrderStatus.CANCELLED == "cancelled"


def test_restaurant_user_role_is_str_enum() -> None:
    assert isinstance(RestaurantUserRole.ADMIN, str)
    assert RestaurantUserRole.ADMIN == "admin"
    assert RestaurantUserRole.STAFF == "staff"


def test_order_event_actor_type_is_str_enum() -> None:
    assert isinstance(OrderEventActorType.DINER, str)
    assert OrderEventActorType.DINER == "diner"
    assert OrderEventActorType.STAFF == "staff"
    assert OrderEventActorType.SYSTEM == "system"
