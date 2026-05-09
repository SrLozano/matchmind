from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.models.users import DEFAULT_DEV_USER_ID, UserResponse
from app.services.supabase import get_user_profile

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
async def current_user(user_id: UUID = Query(DEFAULT_DEV_USER_ID)) -> dict:
    try:
        return await get_user_profile(user_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
