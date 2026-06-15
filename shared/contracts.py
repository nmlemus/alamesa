from enum import Enum


class OrderStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    READY = "ready"
    CLOSED = "closed"


class RestaurantUserRole(str, Enum):
    ADMIN = "admin"
    STAFF = "staff"
