from __future__ import annotations

from uuid import UUID

import stripe
from fastapi import HTTPException, status

from app.config import get_settings
from app.services.referrals import get_applied_referral_for_checkout, mark_referral_conversion
from app.services.supabase import update_user_plan


TOURNAMENT_PASS_PRODUCT = "world_cup_tournament_pass"


def _require_setting(value: str | None, name: str) -> str:
    if value and value.strip():
        return value.strip()
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"{name} is not configured.",
    )


async def create_tournament_pass_checkout_session(user_id: UUID) -> str:
    settings = get_settings()
    stripe.api_key = _require_setting(settings.stripe_secret_key, "STRIPE_SECRET_KEY")
    referral = await get_applied_referral_for_checkout(user_id)
    price_id = _checkout_price_id(settings, has_referral=referral is not None)
    metadata = {
        "user_id": str(user_id),
        "product": TOURNAMENT_PASS_PRODUCT,
        "checkout_price_type": "referral" if referral else "standard",
    }
    if referral:
        metadata.update(
            {
                "referral_code": str(referral["code"]),
                "referral_attribution_id": str(referral["attribution_id"]),
                "referral_owner_type": str(referral.get("owner_type") or ""),
            }
        )
        if referral.get("partner_id"):
            metadata["referral_partner_id"] = str(referral["partner_id"])
        if referral.get("referrer_user_id"):
            metadata["referral_referrer_user_id"] = str(referral["referrer_user_id"])
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


def _checkout_price_id(settings, has_referral: bool) -> str:
    if has_referral:
        return _require_setting(
            settings.stripe_tournament_pass_referral_price_id,
            "STRIPE_TOURNAMENT_PASS_REFERRAL_PRICE_ID",
        )
    return _require_setting(settings.stripe_tournament_pass_price_id, "STRIPE_TOURNAMENT_PASS_PRICE_ID")


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
    amount_total = session.get("amount_total")
    gross_amount = round(float(amount_total) / 100, 2) if isinstance(amount_total, int | float) else None
    await mark_referral_conversion(user_id, gross_amount=gross_amount)
    return True


async def handle_webhook_event(event: dict) -> dict[str, bool]:
    if event.get("type") != "checkout.session.completed":
        return {"received": True, "processed": False}

    session = (event.get("data") or {}).get("object") or {}
    processed = await handle_checkout_session_completed(session)
    return {"received": True, "processed": processed}
