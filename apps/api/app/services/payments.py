from __future__ import annotations

from uuid import UUID

import stripe
from fastapi import HTTPException, status

from app.config import get_settings
from app.services.referrals import (
    STANDARD_TOURNAMENT_PASS_PRICE,
    get_applied_referral_for_checkout,
    get_user_referral_summary,
    mark_referral_conversion,
)
from app.services.supabase import update_user_plan


TOURNAMENT_PASS_PRODUCT = "world_cup_tournament_pass"
SCOUT_PASS_PRICE = 8.99
INSIDER_PASS_PRICE = 4.99
CAPTAIN_PASS_PRICE = 2.49
FREE_PASS_PRICE = 0.0


def _require_setting(value: str | None, name: str) -> str:
    if value and value.strip():
        return value.strip()
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"{name} is not configured.",
    )


async def create_tournament_pass_checkout_session(user_id: UUID) -> str:
    settings = get_settings()
    offer = await _checkout_offer(user_id)
    referral = offer["applied_referral"]
    metadata: dict[str, str] = {
        "user_id": str(user_id),
        "product": TOURNAMENT_PASS_PRODUCT,
        "checkout_price_type": offer["price_type"],
        "checkout_price_amount": f"{offer['price']:.2f}",
    }
    if offer.get("tier_key"):
        metadata["referral_tier_key"] = str(offer["tier_key"])
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
    if offer["price"] <= FREE_PASS_PRICE:
        await update_user_plan(user_id, "premium")
        return f"{app_url}/?payment=success"

    stripe.api_key = _require_setting(settings.stripe_secret_key, "STRIPE_SECRET_KEY")
    price_id = _checkout_price_id(settings, offer["price"])
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


async def _checkout_offer(user_id: UUID) -> dict:
    applied_referral = await get_applied_referral_for_checkout(user_id)
    applied_referral_price = (
        max(STANDARD_TOURNAMENT_PASS_PRICE - float(applied_referral["discount_amount"]), FREE_PASS_PRICE)
        if applied_referral
        else None
    )
    user_referral = await get_user_referral_summary(user_id)
    user_perks = user_referral.get("perks") or {}
    user_tier = user_perks.get("current_tier") or None
    user_referral_price = (
        float(user_perks["unlocked_pass_price"])
        if user_referral.get("has_code") and user_perks.get("unlocked_pass_price") is not None
        else None
    )

    candidates = [
        {
            "price": STANDARD_TOURNAMENT_PASS_PRICE,
            "price_type": "standard",
            "tier_key": None,
            "applied_referral": None,
        }
    ]
    if applied_referral_price is not None:
        candidates.append(
            {
                "price": applied_referral_price,
                "price_type": "referral",
                "tier_key": None,
                "applied_referral": applied_referral,
            }
        )
    if user_referral_price is not None:
        tier_key = user_tier.get("key") if isinstance(user_tier, dict) else None
        candidates.append(
            {
                "price": max(user_referral_price, FREE_PASS_PRICE),
                "price_type": f"user_referral_{tier_key}" if tier_key else "user_referral",
                "tier_key": tier_key,
                "applied_referral": applied_referral,
            }
        )

    return min(candidates, key=lambda candidate: float(candidate["price"]))


def _checkout_price_id(settings, price: float) -> str:
    if _prices_match(price, SCOUT_PASS_PRICE):
        return _require_setting(
            settings.stripe_tournament_pass_referral_price_id,
            "STRIPE_TOURNAMENT_PASS_REFERRAL_PRICE_ID",
        )
    if _prices_match(price, INSIDER_PASS_PRICE):
        return _require_setting(
            settings.stripe_tournament_pass_insider_price_id,
            "STRIPE_TOURNAMENT_PASS_INSIDER_PRICE_ID",
        )
    if _prices_match(price, CAPTAIN_PASS_PRICE):
        return _require_setting(
            settings.stripe_tournament_pass_captain_price_id,
            "STRIPE_TOURNAMENT_PASS_CAPTAIN_PRICE_ID",
        )
    if not _prices_match(price, STANDARD_TOURNAMENT_PASS_PRICE):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"No Stripe price is configured for a €{price:.2f} tournament pass.",
        )
    return _require_setting(settings.stripe_tournament_pass_price_id, "STRIPE_TOURNAMENT_PASS_PRICE_ID")


def _prices_match(left: float, right: float) -> bool:
    return abs(float(left) - float(right)) < 0.005


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
