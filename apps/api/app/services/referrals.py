from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status

from app.models.referrals import BarPartnerCreate
from app.services.supabase import get_supabase


DEFAULT_DISCOUNT_AMOUNT = 1.0
DEFAULT_COMMISSION_AMOUNT = 2.0
USER_REFERRAL_COMMISSION_AMOUNT = 0.0
STANDARD_TOURNAMENT_PASS_PRICE = 9.99
USER_REFERRAL_PERK_TIERS = [
    {
        "key": "scout",
        "required_registered_referrals": 1,
        "required_paid_referrals": 0,
        "pass_price": 8.99,
        "discount_percent": 10,
        "beta_priority": False,
    },
    {
        "key": "insider",
        "required_registered_referrals": 0,
        "required_paid_referrals": 2,
        "pass_price": 4.99,
        "discount_percent": 50,
        "beta_priority": False,
    },
    {
        "key": "captain",
        "required_registered_referrals": 0,
        "required_paid_referrals": 5,
        "pass_price": 2.49,
        "discount_percent": 75,
        "beta_priority": False,
    },
    {
        "key": "legend",
        "required_registered_referrals": 0,
        "required_paid_referrals": 7,
        "pass_price": 0.0,
        "discount_percent": 100,
        "beta_priority": False,
    },
    {
        "key": "founder_circle",
        "required_registered_referrals": 0,
        "required_paid_referrals": 10,
        "pass_price": 0.0,
        "discount_percent": 100,
        "beta_priority": True,
    },
]
LEADING_BUSINESS_WORDS = {
    "BAR",
    "CAFE",
    "CAFETERIA",
    "RESTAURANTE",
    "TABERNA",
    "PUB",
    "CERVECERIA",
    "LA",
    "EL",
    "LOS",
    "LAS",
}


def normalize_referral_code(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.strip().upper())
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^A-Z0-9]", "", ascii_value)


def base_code_from_business_name(business_name: str) -> str:
    normalized_name = unicodedata.normalize("NFKD", business_name.strip().upper())
    ascii_name = normalized_name.encode("ascii", "ignore").decode("ascii")
    words = re.findall(r"[A-Z0-9]+", ascii_name)
    while len(words) > 1 and words[0] in LEADING_BUSINESS_WORDS:
        words.pop(0)
    base_code = normalize_referral_code("".join(words))
    return base_code or "MATCHMIND"


def base_code_from_user(user: dict[str, Any]) -> str:
    raw_name = str(user.get("name") or "").strip()
    raw_email = str(user.get("email") or "").strip()
    if raw_name:
        first_name = raw_name.split()[0]
        return normalize_referral_code(first_name) or "MATCHMIND"
    if raw_email and "@" in raw_email:
        return normalize_referral_code(raw_email.split("@", 1)[0]) or "MATCHMIND"
    return "MATCHMIND"


def public_user_referrer_name(user: dict[str, Any] | None) -> str:
    if not user:
        return "Matchmind user"
    name = " ".join(str(user.get("name") or "").strip().split())
    return name or "Matchmind user"


def discount_label(discount_amount: float) -> str:
    if float(discount_amount).is_integer():
        return f"€{int(discount_amount)} discount"
    return f"€{discount_amount:.2f} discount"


def user_referral_perks(registered_referrals: int, paid_referrals: int) -> dict[str, Any]:
    current_tier = None
    next_tier = None
    for tier in USER_REFERRAL_PERK_TIERS:
        registered_unlocked = registered_referrals >= int(tier["required_registered_referrals"])
        paid_unlocked = paid_referrals >= int(tier["required_paid_referrals"])
        if registered_unlocked and paid_unlocked:
            current_tier = tier
        elif next_tier is None:
            next_tier = tier

    unlocked_pass_price = float(current_tier["pass_price"]) if current_tier else STANDARD_TOURNAMENT_PASS_PRICE
    discount_percent = int(current_tier["discount_percent"]) if current_tier else 0
    beta_priority = bool(current_tier["beta_priority"]) if current_tier else False
    remaining_registered = 0
    remaining_paid = 0
    if next_tier:
        remaining_registered = max(int(next_tier["required_registered_referrals"]) - registered_referrals, 0)
        remaining_paid = max(int(next_tier["required_paid_referrals"]) - paid_referrals, 0)

    return {
        "current_tier": current_tier,
        "next_tier": next_tier,
        "unlocked_pass_price": unlocked_pass_price,
        "discount_percent": discount_percent,
        "beta_priority": beta_priority,
        "remaining_registered_referrals": remaining_registered,
        "remaining_paid_referrals": remaining_paid,
    }


def referral_attribution_is_verified_conversion(attribution: dict[str, Any]) -> bool:
    return (
        bool(attribution.get("converted_at"))
        and attribution.get("conversion_source") == "stripe_checkout_completed"
        and bool(attribution.get("stripe_checkout_session_id"))
        and attribution.get("payout_status") != "cancelled"
    )


async def _ensure_user_exists(user_id: UUID) -> None:
    await _get_user(user_id)


async def _get_user(user_id: UUID) -> dict[str, Any]:
    client = await get_supabase()
    response = await client.table("users").select("id, email, name").eq("id", str(user_id)).limit(1).execute()
    if not response.data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User not found.")
    return response.data[0]


async def generate_unique_code_from_base(base_code: str) -> str:
    client = await get_supabase()
    base_code = normalize_referral_code(base_code) or "MATCHMIND"
    for suffix in range(1, 1000):
        candidate = base_code if suffix == 1 else f"{base_code}{suffix}"
        existing = await client.table("referral_codes").select("id").eq("code", candidate).limit(1).execute()
        if not existing.data:
            return candidate

    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="Unable to generate a unique referral code.",
    )


async def generate_unique_code(business_name: str) -> str:
    return await generate_unique_code_from_base(base_code_from_business_name(business_name))


async def create_bar_partner(user_id: UUID, payload: BarPartnerCreate) -> dict[str, Any]:
    if not payload.terms_accepted:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Terms must be accepted.")

    await _ensure_user_exists(user_id)
    client = await get_supabase()
    existing = (
        await client.table("referral_partners")
        .select("id")
        .eq("user_id", str(user_id))
        .eq("partner_type", "bar")
        .limit(1)
        .execute()
    )
    if existing.data:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This user already has a bar partner code.")

    now = datetime.now(timezone.utc).isoformat()
    partner_response = (
        await client.table("referral_partners")
        .insert(
            {
                "user_id": str(user_id),
                "partner_type": "bar",
                "business_name": payload.business_name,
                "location": payload.location,
                "responsible_name": payload.responsible_name,
                "phone": payload.phone,
                "status": "active",
                "terms_accepted_at": now,
                "updated_at": now,
            }
        )
        .execute()
    )
    if not partner_response.data:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create partner.")

    partner = partner_response.data[0]
    code = await generate_unique_code(payload.business_name)
    code_response = (
        await client.table("referral_codes")
        .insert(
            {
                "code": code,
                "owner_type": "bar_partner",
                "partner_id": partner["id"],
                "discount_type": "fixed_amount",
                "discount_amount": DEFAULT_DISCOUNT_AMOUNT,
                "commission_amount": DEFAULT_COMMISSION_AMOUNT,
                "active": True,
            }
        )
        .execute()
    )
    if not code_response.data:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create referral code.")

    return {
        "partner_id": partner["id"],
        "code": code_response.data[0]["code"],
        "business_name": partner["business_name"],
        "status": partner["status"],
    }


async def create_user_referral_code(user_id: UUID) -> dict[str, Any]:
    user = await _get_user(user_id)
    client = await get_supabase()
    existing = (
        await client.table("referral_codes")
        .select("*")
        .eq("owner_type", "user")
        .eq("owner_user_id", str(user_id))
        .limit(1)
        .execute()
    )
    if existing.data:
        summary = await get_user_referral_summary(user_id)
        return {
            "code": existing.data[0]["code"],
            "registered_referrals": summary["registered_referrals"],
            "paid_referrals": summary["paid_referrals"],
            "status_label": "Tracked",
            "perks": summary["perks"],
        }

    code = await generate_unique_code_from_base(base_code_from_user(user))
    code_response = (
        await client.table("referral_codes")
        .insert(
            {
                "code": code,
                "owner_type": "user",
                "owner_user_id": str(user_id),
                "partner_id": None,
                "discount_type": "fixed_amount",
                "discount_amount": DEFAULT_DISCOUNT_AMOUNT,
                "commission_amount": USER_REFERRAL_COMMISSION_AMOUNT,
                "active": True,
            }
        )
        .execute()
    )
    if not code_response.data:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create referral code.")

    return {
        "code": code_response.data[0]["code"],
        "registered_referrals": 0,
        "paid_referrals": 0,
        "status_label": "Tracked",
        "perks": user_referral_perks(0, 0),
    }


async def get_user_referral_summary(user_id: UUID) -> dict[str, Any]:
    client = await get_supabase()
    code_response = (
        await client.table("referral_codes")
        .select("*")
        .eq("owner_type", "user")
        .eq("owner_user_id", str(user_id))
        .limit(1)
        .execute()
    )
    if not code_response.data:
        return {
            "has_code": False,
            "code": None,
            "registered_referrals": 0,
            "paid_referrals": 0,
            "status_label": "Coming soon",
            "perks": user_referral_perks(0, 0),
        }

    referral_code = code_response.data[0]
    attributions_response = (
        await client.table("referral_attributions")
        .select("*")
        .eq("referrer_user_id", str(user_id))
        .execute()
    )
    attributions = attributions_response.data or []
    registered_referrals = len(attributions)
    paid_referrals = sum(1 for attribution in attributions if referral_attribution_is_verified_conversion(attribution))
    perks = user_referral_perks(registered_referrals, paid_referrals)
    return {
        "has_code": True,
        "code": referral_code["code"],
        "registered_referrals": registered_referrals,
        "paid_referrals": paid_referrals,
        "status_label": (perks["current_tier"] or {}).get("key", "tracking"),
        "perks": perks,
    }


async def _get_active_code(normalized_code: str) -> dict[str, Any] | None:
    client = await get_supabase()
    code_response = (
        await client.table("referral_codes")
        .select("*")
        .eq("code", normalized_code)
        .eq("active", True)
        .limit(1)
        .execute()
    )
    if not code_response.data:
        return None

    code = code_response.data[0]
    if code.get("owner_type") == "bar_partner":
        partner_id = code.get("partner_id")
        if not partner_id:
            return None
        partner_response = (
            await client.table("referral_partners")
            .select("*")
            .eq("id", partner_id)
            .eq("status", "active")
            .limit(1)
            .execute()
        )
        if not partner_response.data:
            return None
        partner = partner_response.data[0]
        return {
            "code": code,
            "owner_type": "bar_partner",
            "partner": partner,
            "partner_id": partner["id"],
            "referrer_user_id": None,
            "owner_name": partner["business_name"],
            "owner_user_id": partner["user_id"],
        }

    if code.get("owner_type") == "user":
        owner_user_id = code.get("owner_user_id")
        if not owner_user_id:
            return None
        user_response = (
            await client.table("users")
            .select("id, email, name")
            .eq("id", owner_user_id)
            .limit(1)
            .execute()
        )
        if not user_response.data:
            return None
        user = user_response.data[0]
        return {
            "code": code,
            "owner_type": "user",
            "partner": None,
            "partner_id": None,
            "referrer_user_id": user["id"],
            "owner_name": public_user_referrer_name(user),
            "owner_user_id": user["id"],
        }

    return None


async def validate_referral_code(code: str) -> dict[str, Any]:
    normalized_code = normalize_referral_code(code)
    if not normalized_code:
        return {"valid": False}

    context = await _get_active_code(normalized_code)
    if context is None:
        return {"valid": False}

    referral_code = context["code"]
    discount_amount = float(referral_code["discount_amount"])
    return {
        "valid": True,
        "code": referral_code["code"],
        "partner_name": context["owner_name"],
        "discount_amount": discount_amount,
        "discount_label": discount_label(discount_amount),
        "owner_type": context["owner_type"],
    }


async def apply_referral_code(user_id: UUID, code: str) -> dict[str, Any]:
    await _ensure_user_exists(user_id)
    normalized_code = normalize_referral_code(code)
    context = await _get_active_code(normalized_code)
    if context is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="This code does not exist.")

    referral_code = context["code"]
    if str(context["owner_user_id"]) == str(user_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot apply your own referral code.")

    client = await get_supabase()
    existing = (
        await client.table("referral_attributions")
        .select("id")
        .eq("referred_user_id", str(user_id))
        .limit(1)
        .execute()
    )
    if existing.data:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="You have already applied a code.")

    attribution_response = (
        await client.table("referral_attributions")
        .insert(
            {
                "referred_user_id": str(user_id),
                "referral_code_id": referral_code["id"],
                "partner_id": context["partner_id"],
                "referrer_user_id": context["referrer_user_id"],
                "discount_amount": float(referral_code["discount_amount"]),
                "commission_amount": float(referral_code["commission_amount"]),
                "payout_status": "pending",
            }
        )
        .execute()
    )
    if not attribution_response.data:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to apply referral code.")

    return {
        "applied": True,
        "code": referral_code["code"],
        "partner_name": context["owner_name"],
        "discount_amount": float(referral_code["discount_amount"]),
        "owner_type": context["owner_type"],
    }


async def get_referral_dashboard(user_id: UUID) -> dict[str, Any]:
    await _ensure_user_exists(user_id)
    client = await get_supabase()
    partners_response = (
        await client.table("referral_partners")
        .select("*")
        .eq("user_id", str(user_id))
        .eq("partner_type", "bar")
        .limit(1)
        .execute()
    )

    applied_referral = await _get_applied_referral(user_id)
    user_referral = await get_user_referral_summary(user_id)
    if not partners_response.data:
        return {
            "has_bar_partner": False,
            "partner": None,
            "code": None,
            "registered_referrals": 0,
            "paid_referrals": 0,
            "estimated_payout": 0.0,
            "commission_amount": DEFAULT_COMMISSION_AMOUNT,
            "discount_amount": DEFAULT_DISCOUNT_AMOUNT,
            "applied_referral": applied_referral,
            "user_referral": user_referral,
        }

    partner = partners_response.data[0]
    code_response = (
        await client.table("referral_codes")
        .select("*")
        .eq("partner_id", partner["id"])
        .eq("owner_type", "bar_partner")
        .limit(1)
        .execute()
    )
    referral_code = code_response.data[0] if code_response.data else None
    attributions_response = (
        await client.table("referral_attributions")
        .select("*")
        .eq("partner_id", partner["id"])
        .execute()
    )
    attributions = attributions_response.data or []
    paid_referrals = sum(1 for attribution in attributions if referral_attribution_is_verified_conversion(attribution))
    commission_amount = float(referral_code["commission_amount"]) if referral_code else DEFAULT_COMMISSION_AMOUNT
    discount_amount = float(referral_code["discount_amount"]) if referral_code else DEFAULT_DISCOUNT_AMOUNT

    return {
        "has_bar_partner": True,
        "partner": partner,
        "code": referral_code["code"] if referral_code else None,
        "registered_referrals": len(attributions),
        "paid_referrals": paid_referrals,
        "estimated_payout": round(paid_referrals * commission_amount, 2),
        "commission_amount": commission_amount,
        "discount_amount": discount_amount,
        "applied_referral": applied_referral,
        "user_referral": user_referral,
    }


async def _get_applied_referral(user_id: UUID) -> dict[str, Any] | None:
    client = await get_supabase()
    attribution_response = (
        await client.table("referral_attributions")
        .select("*")
        .eq("referred_user_id", str(user_id))
        .limit(1)
        .execute()
    )
    if not attribution_response.data:
        return None

    attribution = attribution_response.data[0]
    code_response = (
        await client.table("referral_codes")
        .select("*")
        .eq("id", attribution["referral_code_id"])
        .limit(1)
        .execute()
    )
    if not code_response.data:
        return None

    referral_code = code_response.data[0]
    owner_name = "Matchmind"
    owner_type = referral_code.get("owner_type")
    if owner_type == "bar_partner" and attribution.get("partner_id"):
        partner_response = (
            await client.table("referral_partners")
            .select("business_name")
            .eq("id", attribution["partner_id"])
            .limit(1)
            .execute()
        )
        if not partner_response.data:
            return None
        owner_name = partner_response.data[0]["business_name"]
    elif owner_type == "user" and attribution.get("referrer_user_id"):
        user_response = (
            await client.table("users")
            .select("id, email, name")
            .eq("id", attribution["referrer_user_id"])
            .limit(1)
            .execute()
        )
        owner_name = public_user_referrer_name(user_response.data[0] if user_response.data else None)

    return {
        "code": referral_code["code"],
        "partner_name": owner_name,
        "discount_amount": float(attribution.get("discount_amount") or referral_code["discount_amount"]),
        "applied_at": attribution.get("applied_at"),
        "owner_type": owner_type,
    }


async def get_applied_referral_for_checkout(user_id: UUID) -> dict[str, Any] | None:
    client = await get_supabase()
    attribution_response = (
        await client.table("referral_attributions")
        .select("id, referral_code_id, partner_id, referrer_user_id, discount_amount")
        .eq("referred_user_id", str(user_id))
        .limit(1)
        .execute()
    )
    if not attribution_response.data:
        return None

    attribution = attribution_response.data[0]
    code_response = (
        await client.table("referral_codes")
        .select("code, discount_amount, active, owner_type, partner_id, owner_user_id")
        .eq("id", attribution["referral_code_id"])
        .limit(1)
        .execute()
    )
    if not code_response.data or not code_response.data[0].get("active"):
        return None

    referral_code = code_response.data[0]
    return {
        "attribution_id": attribution["id"],
        "code": referral_code["code"],
        "owner_type": referral_code.get("owner_type"),
        "partner_id": attribution.get("partner_id"),
        "referrer_user_id": attribution.get("referrer_user_id"),
        "discount_amount": float(attribution.get("discount_amount") or referral_code["discount_amount"]),
    }


async def mark_referral_conversion(
    user_id: UUID,
    *,
    gross_amount: float | None = None,
    stripe_checkout_session_id: str,
    stripe_payment_intent_id: str | None = None,
    converted_price_type: str | None = None,
    conversion_source: str = "stripe_checkout_completed",
) -> bool:
    client = await get_supabase()
    existing = (
        await client.table("referral_attributions")
        .select("id, converted_at, commission_amount, stripe_checkout_session_id")
        .eq("referred_user_id", str(user_id))
        .limit(1)
        .execute()
    )
    if not existing.data or existing.data[0].get("converted_at"):
        return False

    updates: dict[str, Any] = {
        "converted_at": datetime.now(timezone.utc).isoformat(),
        "conversion_source": conversion_source,
        "stripe_checkout_session_id": stripe_checkout_session_id,
    }
    if stripe_payment_intent_id:
        updates["stripe_payment_intent_id"] = stripe_payment_intent_id
    if converted_price_type:
        updates["converted_price_type"] = converted_price_type
    if gross_amount is not None:
        updates["gross_amount"] = round(gross_amount, 2)

    response = (
        await client.table("referral_attributions")
        .update(updates)
        .eq("id", existing.data[0]["id"])
        .execute()
    )
    return bool(response.data)


async def cancel_referral_payout_for_payment_intent(
    stripe_payment_intent_id: str | None,
    *,
    cancellation_reason: str,
    stripe_dispute_id: str | None = None,
) -> bool:
    if not stripe_payment_intent_id:
        return False

    client = await get_supabase()
    existing = (
        await client.table("referral_attributions")
        .select("id, payout_status")
        .eq("stripe_payment_intent_id", stripe_payment_intent_id)
        .limit(1)
        .execute()
    )
    if not existing.data or existing.data[0].get("payout_status") == "paid":
        return False

    updates: dict[str, Any] = {
        "payout_status": "cancelled",
        "payout_cancelled_at": datetime.now(timezone.utc).isoformat(),
        "payout_cancellation_reason": cancellation_reason,
    }
    if stripe_dispute_id:
        updates["stripe_dispute_id"] = stripe_dispute_id

    response = (
        await client.table("referral_attributions")
        .update(updates)
        .eq("id", existing.data[0]["id"])
        .execute()
    )
    return bool(response.data)
