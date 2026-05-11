from fastapi import APIRouter, Header, HTTPException, Request, status

from app.services.auth import get_authenticated_user
from app.services.payments import (
    construct_webhook_event,
    create_tournament_pass_checkout_session,
    handle_webhook_event,
)

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("/create-checkout-session")
async def create_checkout_session(authorization: str | None = Header(default=None)) -> dict[str, str]:
    authenticated_user = await get_authenticated_user(authorization)
    if authenticated_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication is required to start checkout.",
        )

    return {"url": create_tournament_pass_checkout_session(authenticated_user.id)}


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str | None = Header(default=None, alias="Stripe-Signature"),
) -> dict[str, bool]:
    payload = await request.body()
    event = construct_webhook_event(payload, stripe_signature)
    return await handle_webhook_event(event)
