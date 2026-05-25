from fastapi import APIRouter, Header, HTTPException, status

from app.models.users import UserResponse, UserUpdateRequest
from app.services.auth import require_authenticated_user
from app.services.supabase import get_user_profile, update_user_profile

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
async def current_user(
    authorization: str | None = Header(default=None),
) -> dict:
    try:
        authenticated_user = await require_authenticated_user(authorization)
        return await get_user_profile(authenticated_user.id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.patch("/me", response_model=UserResponse)
async def update_current_user(
    payload: UserUpdateRequest,
    authorization: str | None = Header(default=None),
) -> dict:
    try:
        authenticated_user = await require_authenticated_user(authorization)
        return await update_user_profile(authenticated_user.id, payload.name)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
