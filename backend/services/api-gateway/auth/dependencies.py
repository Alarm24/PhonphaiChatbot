from dataclasses import dataclass

import jwt
from auth.jwt_utils import decode_token
from config import get_settings
from fastapi import Header, HTTPException


@dataclass
class CurrentUser:
    user_id: str
    username: str
    role: str  # "admin" | "user"
    staff_id: int | None


def _parse_authorization(header_value: str | None) -> str | None:
    if not header_value:
        return None
    parts = header_value.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    return parts[1]


def get_optional_user(authorization: str | None = Header(default=None)) -> CurrentUser | None:
    """Returns the user if a valid JWT is provided, otherwise None. Never raises on missing token."""
    token = _parse_authorization(authorization)
    if not token:
        return None

    settings = get_settings()
    try:
        payload = decode_token(token, settings.JWT_SECRET, settings.JWT_ALGORITHM)
    except jwt.PyJWTError:
        return None

    return CurrentUser(
        user_id=str(payload.get("sub", "")),
        username=str(payload.get("username", "")),
        role=str(payload.get("role", "user")),
        staff_id=payload.get("staff_id"),
    )


def require_user(authorization: str | None = Header(default=None)) -> CurrentUser:
    user = get_optional_user(authorization)
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


def require_admin(authorization: str | None = Header(default=None)) -> CurrentUser:
    user = require_user(authorization)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")
    return user
