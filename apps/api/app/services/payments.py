from __future__ import annotations

from uuid import UUID

import stripe
from fastapi import HTTPException, status

from app.config import get_settings
from app.services.supabase import update_user_plan


TOURNAMENT_PASS_PRODUCT = "world_cup_tournament_pass"


def _require_setting(value: str | None, name: str) -> str:
    if value and value.strip():
        return value.strip()
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"{name} is not configured.",
    )


def create_tournament_pass_checkout_session(user_id: UUID) -> str:
    settings = get_settings()
    stripe.api_key = _require_setting(settings.stripe_secret_key, "STRIPE_SECRET_KEY")
    price_id = _require_setting(settings.stripe_tournament_pass_price_id, "STRIPE_TOURNAMENT_PASS_PRICE_ID")
    metadata = {"user_id": str(user_id), "product": TOURNAMENT_PASS_PRODUCT}
    app_url = settings.app_url.rstrip("/")

    session = stripe.checkout.Session.create(
        mode="payment",
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=f"{app_url}/?payment=success",
        cancel_url=f"{app_url}/?payment=cancelled",
        client_reference_id=str(user_id),
        metadata=metadata,
        payment_intent_data={"metadata": metadata},
    )
    url = getattr(session, "url", None)
    if not isinstance(url, str) or not url:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Stripe did not return a checkout URL.",
        )
    return url


def construct_webhook_event(payload: bytes, signature: str | None) -> dict:
    webhook_secret = _require_setting(get_settings().stripe_webhook_secret, "STRIPE_WEBHOOK_SECRET")
    if not signature:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing Stripe signature.",
        )

    try:
        return stripe.Webhook.construct_event(payload, signature, webhook_secret)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Stripe webhook payload.",
        ) from exc
    except stripe.error.SignatureVerificationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Stripe webhook signature.",
        ) from exc


async def handle_checkout_session_completed(session: dict) -> bool:
    metadata = session.get("metadata") or {}
    user_id_raw = metadata.get("user_id")
    if not user_id_raw:
        return False

    try:
        user_id = UUID(str(user_id_raw))
    except ValueError:
        return False

    await update_user_plan(user_id, "premium")
    return True


async def handle_webhook_event(event: dict) -> dict[str, bool]:
    if event.get("type") != "checkout.session.completed":
        return {"received": True, "processed": False}

    session = (event.get("data") or {}).get("object") or {}
    processed = await handle_checkout_session_completed(session)
    return {"received": True, "processed": processed}
