from enum import StrEnum


class OrderStatus(StrEnum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PREPARING = "preparing"
    READY = "ready"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class RestaurantUserRole(StrEnum):
    ADMIN = "admin"
    STAFF = "staff"


class OrderEventActorType(StrEnum):
    DINER = "diner"
    STAFF = "staff"
    SYSTEM = "system"


LEGAL_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.PENDING: {OrderStatus.CONFIRMED, OrderStatus.CANCELLED},
    OrderStatus.CONFIRMED: {OrderStatus.PREPARING, OrderStatus.CANCELLED},
    OrderStatus.PREPARING: {OrderStatus.READY, OrderStatus.CANCELLED},
    OrderStatus.READY: {OrderStatus.CLOSED},
    OrderStatus.CLOSED: set(),
    OrderStatus.CANCELLED: set(),
}

ACTOR_PERMISSIONS: dict[tuple[OrderStatus, OrderStatus], set[OrderEventActorType]] = {
    (OrderStatus.PENDING, OrderStatus.CONFIRMED): {OrderEventActorType.STAFF},
    (OrderStatus.PENDING, OrderStatus.CANCELLED): {
        OrderEventActorType.DINER,
        OrderEventActorType.STAFF,
        OrderEventActorType.SYSTEM,
    },
    (OrderStatus.CONFIRMED, OrderStatus.PREPARING): {
        OrderEventActorType.STAFF,
        OrderEventActorType.SYSTEM,
    },
    (OrderStatus.CONFIRMED, OrderStatus.CANCELLED): {
        OrderEventActorType.STAFF,
        OrderEventActorType.SYSTEM,
    },
    (OrderStatus.PREPARING, OrderStatus.READY): {
        OrderEventActorType.STAFF,
        OrderEventActorType.SYSTEM,
    },
    (OrderStatus.PREPARING, OrderStatus.CANCELLED): {OrderEventActorType.STAFF},
    (OrderStatus.READY, OrderStatus.CLOSED): {
        OrderEventActorType.STAFF,
        OrderEventActorType.SYSTEM,
    },
}
