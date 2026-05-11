from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Query, status

from app.models.conversations import ConversationDetailResponse, ConversationListResponse
from app.models.users import DEFAULT_DEV_USER_ID
from app.services.auth import get_authenticated_user
from app.services.supabase import get_user_conversation, list_user_conversations

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("", response_model=ConversationListResponse)
async def conversations(
    user_id: UUID = DEFAULT_DEV_USER_ID,
    limit: int = Query(default=20, ge=1, le=50),
    authorization: str | None = Header(default=None),
) -> ConversationListResponse:
    authenticated_user = await get_authenticated_user(authorization)
    rows = await list_user_conversations(authenticated_user.id if authenticated_user else user_id, limit=limit)
    return ConversationListResponse(conversations=rows, count=len(rows))


@router.get("/{conversation_id}", response_model=ConversationDetailResponse)
async def conversation_detail(
    conversation_id: UUID,
    user_id: UUID = DEFAULT_DEV_USER_ID,
    authorization: str | None = Header(default=None),
) -> ConversationDetailResponse:
    try:
        authenticated_user = await get_authenticated_user(authorization)
        row = await get_user_conversation(authenticated_user.id if authenticated_user else user_id, conversation_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    return ConversationDetailResponse(**row)
