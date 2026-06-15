from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from shared.contracts import (
    ACTOR_PERMISSIONS,
    LEGAL_TRANSITIONS,
    OrderEventActorType,
    OrderStatus,
)


def require_restaurant_scope(
    resource: Any, restaurant_id: str, session: Session
) -> None:
    """Raise 403 if *resource*.restaurant_id does not match *restaurant_id*."""
    if getattr(resource, "restaurant_id", None) != restaurant_id:
        raise HTTPException(status_code=403, detail="Forbidden")


def validate_transition(
    order: Any,
    to_status: OrderStatus,
    actor_type: OrderEventActorType,
) -> None:
    """Raise 409 if the status transition or actor is not permitted."""
    from_status = OrderStatus(order.status)

    allowed_targets = LEGAL_TRANSITIONS.get(from_status, set())
    if to_status not in allowed_targets:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot transition from {from_status!r} to {to_status!r}",
        )

    permitted_actors = ACTOR_PERMISSIONS.get((from_status, to_status), set())
    if actor_type not in permitted_actors:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Actor {actor_type!r} is not permitted to transition "
                f"from {from_status!r} to {to_status!r}"
            ),
        )
