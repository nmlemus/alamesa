from __future__ import annotations

from collections.abc import Callable
from typing import Annotated, Any

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from mesadigital.api.db.models import Diner, RestaurantUser
from mesadigital.api.db.session import get_db
from mesadigital.api.schemas import DinerRead, RestaurantUserRead
from mesadigital.api.security import decode_token

_bearer = HTTPBearer()


def _extract_token(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
) -> dict[str, Any]:
    return decode_token(credentials.credentials)


TokenDep = Annotated[dict[str, Any], Depends(_extract_token)]


def require_auth(
    token: TokenDep,
    db: Annotated[Session, Depends(get_db)],
) -> RestaurantUserRead:
    if token.get("type") != "staff":
        raise HTTPException(status_code=401, detail="Invalid token type")
    user = db.scalar(
        select(RestaurantUser).where(RestaurantUser.id == token.get("sub"))
    )
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return RestaurantUserRead.model_validate(user)


def require_diner_auth(
    token: TokenDep,
    db: Annotated[Session, Depends(get_db)],
) -> DinerRead:
    if token.get("type") != "diner":
        raise HTTPException(status_code=401, detail="Invalid token type")
    diner = db.scalar(
        select(Diner).where(Diner.id == token.get("sub"))
    )
    if diner is None:
        raise HTTPException(status_code=401, detail="Diner not found")
    return DinerRead.model_validate(diner)


def require_role(roles: list[str]) -> Callable[[dict[str, Any]], None]:
    """Returns a dependency that raises 403 if the JWT role is not in `roles`."""

    def _guard(token: TokenDep) -> None:
        if token.get("role") not in roles:
            raise HTTPException(status_code=403, detail="Insufficient role")

    return _guard


def require_restaurant_scope(restaurant_id: str) -> Callable[[dict[str, Any]], None]:
    """Returns a dependency that raises 403 if the JWT restaurant_id differs from `restaurant_id`."""

    def _guard(token: TokenDep) -> None:
        if token.get("restaurant_id") != restaurant_id:
            raise HTTPException(status_code=403, detail="Insufficient restaurant scope")

    return _guard
