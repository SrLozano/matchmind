from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

import httpx
from fastapi import HTTPException, status

from app.config import get_settings
from app.models.users import DEFAULT_DEV_USER_ID
from app.services.supabase import ensure_user_profile


@dataclass(frozen=True)
class AuthenticatedUser:
    id: UUID
    email: str | None = None


def bearer_token(authorization: str | None) -> str | None:
    if not authorization or not isinstance(authorization, str):
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header.",
        )
    return token.strip()


async def get_authenticated_user(authorization: str | None) -> AuthenticatedUser | None:
    token = bearer_token(authorization)
    if token is None:
        return None

    settings = get_settings()
    url = f"{settings.supabase_url.rstrip('/')}/auth/v1/user"
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "apikey": settings.supabase_key,
            },
        )

    if response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session.",
        )

    payload = response.json()
    user_id = UUID(str(payload["id"]))
    email = payload.get("email")
    await ensure_user_profile(user_id, email=email)
    return AuthenticatedUser(id=user_id, email=email)


async def require_authenticated_user(authorization: str | None) -> AuthenticatedUser:
    authenticated_user = await get_authenticated_user(authorization)
    if authenticated_user is not None:
        return authenticated_user

    settings = get_settings()
    if settings.allow_dev_auth_fallback:
        await ensure_user_profile(DEFAULT_DEV_USER_ID, email=None)
        return AuthenticatedUser(id=DEFAULT_DEV_USER_ID, email=None)

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication is required.",
    )
