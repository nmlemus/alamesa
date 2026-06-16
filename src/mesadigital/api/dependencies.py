from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from mesadigital.api.db.models import Diner, RestaurantUser
from mesadigital.api.db.session import get_db
from mesadigital.api.schemas import DinerRead, RestaurantUserRead
from mesadigital.api.security import decode_token

_bearer = HTTPBearer()

_DbDep = Annotated[Session, Depends(get_db)]
_CredsDep = Annotated[HTTPAuthorizationCredentials, Depends(_bearer)]


class TokenClaims(BaseModel):
    token_type: str  # "staff" or "diner"
    sub: str
    restaurant_id: str
    role: str | None = None


def require_auth(credentials: _CredsDep, db: _DbDep) -> RestaurantUserRead:
    claims = decode_token(credentials.credentials)
    if claims.get("type") != "staff":
        raise HTTPException(status_code=401, detail="Invalid token type")
    user_id: str = claims.get("sub", "")
    user = db.scalar(select(RestaurantUser).where(RestaurantUser.id == user_id))
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return RestaurantUserRead.model_validate(user)


def require_diner_auth(credentials: _CredsDep, db: _DbDep) -> DinerRead:
    claims = decode_token(credentials.credentials)
    if claims.get("type") != "diner":
        raise HTTPException(status_code=401, detail="Invalid token type")
    diner_id: str = claims.get("sub", "")
    diner = db.scalar(select(Diner).where(Diner.id == diner_id))
    if diner is None:
        raise HTTPException(status_code=401, detail="Diner not found")
    return DinerRead.model_validate(diner)


def require_any_auth(credentials: _CredsDep) -> TokenClaims:
    claims = decode_token(credentials.credentials)
    token_type = claims.get("type")
    if token_type not in ("staff", "diner"):
        raise HTTPException(status_code=401, detail="Invalid token type")
    return TokenClaims(
        token_type=token_type,
        sub=claims.get("sub", ""),
        restaurant_id=claims.get("restaurant_id", ""),
        role=claims.get("role"),
    )


def require_role(roles: list[str]) -> Callable[..., RestaurantUserRead]:
    def _check(
        user: Annotated[RestaurantUserRead, Depends(require_auth)],
    ) -> RestaurantUserRead:
        if str(user.role) not in roles:
            raise HTTPException(status_code=403, detail="Insufficient role")
        return user

    return _check


def require_restaurant_scope(
    restaurant_id: str,
    user: Annotated[RestaurantUserRead, Depends(require_auth)],
) -> RestaurantUserRead:
    if user.restaurant_id != restaurant_id:
        raise HTTPException(status_code=403, detail="Restaurant scope mismatch")
    return user
