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


def discount_label(discount_amount: float) -> str:
    if float(discount_amount).is_integer():
        return f"€{int(discount_amount)} discount"
    return f"€{discount_amount:.2f} discount"


async def _ensure_user_exists(user_id: UUID) -> None:
    client = await get_supabase()
    response = await client.table("users").select("id").eq("id", str(user_id)).limit(1).execute()
    if not response.data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User not found.")


async def generate_unique_code(business_name: str) -> str:
    client = await get_supabase()
    base_code = base_code_from_business_name(business_name)
    for suffix in range(1, 1000):
        candidate = base_code if suffix == 1 else f"{base_code}{suffix}"
        existing = await client.table("referral_codes").select("id").eq("code", candidate).limit(1).execute()
        if not existing.data:
            return candidate

    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="Unable to generate a unique referral code.",
    )


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


async def _get_active_code(normalized_code: str) -> tuple[dict[str, Any], dict[str, Any]] | None:
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
    partner_response = (
        await client.table("referral_partners")
        .select("*")
        .eq("id", code["partner_id"])
        .eq("status", "active")
        .limit(1)
        .execute()
    )
    if not partner_response.data:
        return None
    return code, partner_response.data[0]


async def validate_referral_code(code: str) -> dict[str, Any]:
    normalized_code = normalize_referral_code(code)
    if not normalized_code:
        return {"valid": False}

    match = await _get_active_code(normalized_code)
    if match is None:
        return {"valid": False}

    referral_code, partner = match
    discount_amount = float(referral_code["discount_amount"])
    return {
        "valid": True,
        "code": referral_code["code"],
        "partner_name": partner["business_name"],
        "discount_amount": discount_amount,
        "discount_label": discount_label(discount_amount),
    }


async def apply_referral_code(user_id: UUID, code: str) -> dict[str, Any]:
    await _ensure_user_exists(user_id)
    normalized_code = normalize_referral_code(code)
    match = await _get_active_code(normalized_code)
    if match is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="This code does not exist.")

    referral_code, partner = match
    if str(partner["user_id"]) == str(user_id):
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
                "partner_id": partner["id"],
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
        "partner_name": partner["business_name"],
        "discount_amount": float(referral_code["discount_amount"]),
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
    paid_referrals = sum(1 for attribution in attributions if attribution.get("converted_at"))
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
    partner_response = (
        await client.table("referral_partners")
        .select("business_name")
        .eq("id", attribution["partner_id"])
        .limit(1)
        .execute()
    )
    if not code_response.data or not partner_response.data:
        return None

    return {
        "code": code_response.data[0]["code"],
        "partner_name": partner_response.data[0]["business_name"],
        "discount_amount": float(attribution.get("discount_amount") or code_response.data[0]["discount_amount"]),
        "applied_at": attribution.get("applied_at"),
    }


async def mark_referral_conversion(user_id: UUID, gross_amount: float | None = None) -> bool:
    client = await get_supabase()
    existing = (
        await client.table("referral_attributions")
        .select("id, converted_at, commission_amount")
        .eq("referred_user_id", str(user_id))
        .limit(1)
        .execute()
    )
    if not existing.data or existing.data[0].get("converted_at"):
        return False

    updates: dict[str, Any] = {"converted_at": datetime.now(timezone.utc).isoformat()}
    if gross_amount is not None:
        updates["gross_amount"] = round(gross_amount, 2)

    response = (
        await client.table("referral_attributions")
        .update(updates)
        .eq("id", existing.data[0]["id"])
        .execute()
    )
    return bool(response.data)
