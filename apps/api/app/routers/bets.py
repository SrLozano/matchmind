from uuid import UUID

from fastapi import APIRouter, Header, Query, Response, status

from app.models.bets import BetCreateRequest, BetListResponse, BetResponse, BetUpdateRequest
from app.models.users import DEFAULT_DEV_USER_ID
from app.services.auth import get_authenticated_user
from app.services.bets import create_bet, delete_bet, list_bets, update_bet

router = APIRouter(prefix="/bets", tags=["bets"])


@router.post("", response_model=BetResponse, status_code=status.HTTP_201_CREATED)
async def create_bet_endpoint(payload: BetCreateRequest, authorization: str | None = Header(default=None)) -> dict:
    authenticated_user = await get_authenticated_user(authorization)
    if authenticated_user:
        payload = payload.model_copy(update={"user_id": authenticated_user.id})
    return await create_bet(payload)


@router.get("", response_model=BetListResponse)
async def list_bets_endpoint(
    user_id: UUID = Query(DEFAULT_DEV_USER_ID),
    authorization: str | None = Header(default=None),
) -> BetListResponse:
    authenticated_user = await get_authenticated_user(authorization)
    bets, summary = await list_bets(authenticated_user.id if authenticated_user else user_id)
    return BetListResponse(bets=bets, summary=summary)


@router.patch("/{bet_id}", response_model=BetResponse)
async def update_bet_endpoint(
    bet_id: UUID,
    payload: BetUpdateRequest,
    authorization: str | None = Header(default=None),
) -> dict:
    authenticated_user = await get_authenticated_user(authorization)
    if authenticated_user:
        payload = payload.model_copy(update={"user_id": authenticated_user.id})
    return await update_bet(bet_id, payload)


@router.delete("/{bet_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bet_endpoint(
    bet_id: UUID,
    user_id: UUID = Query(DEFAULT_DEV_USER_ID),
    authorization: str | None = Header(default=None),
) -> Response:
    authenticated_user = await get_authenticated_user(authorization)
    await delete_bet(bet_id, authenticated_user.id if authenticated_user else user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
