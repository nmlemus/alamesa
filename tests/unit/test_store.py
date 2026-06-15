import pytest
from fastapi import HTTPException

from mesadigital.api.db.store import validate_transition
from shared.contracts import OrderEventActorType, OrderStatus


class _Order:
    """Minimal stub that mimics the Order model's status attribute."""

    def __init__(self, status: OrderStatus) -> None:
        self.status = status


def test_validate_transition_raises_409_on_illegal_transition() -> None:
    order = _Order(OrderStatus.CLOSED)
    with pytest.raises(HTTPException) as exc_info:
        validate_transition(order, OrderStatus.PENDING, OrderEventActorType.STAFF)
    assert exc_info.value.status_code == 409


def test_validate_transition_raises_409_when_actor_not_permitted() -> None:
    order = _Order(OrderStatus.PENDING)
    with pytest.raises(HTTPException) as exc_info:
        # DINER is not allowed to confirm an order
        validate_transition(order, OrderStatus.CONFIRMED, OrderEventActorType.DINER)
    assert exc_info.value.status_code == 409


def test_validate_transition_passes_for_legal_transition_and_actor() -> None:
    order = _Order(OrderStatus.PENDING)
    # Should not raise
    validate_transition(order, OrderStatus.CONFIRMED, OrderEventActorType.STAFF)
