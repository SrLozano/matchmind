from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import HTTPException, status

from app.models.bets import BetCreateRequest, BetSummary, BetUpdateRequest
from app.services.supabase import get_supabase


def calculate_profit_loss(amount: float, odds: float, outcome: str) -> float:
    if outcome == "pending":
        return 0.0
    if outcome == "loss":
        return round(-amount, 2)
    return round(amount * (odds - 1), 2)


def build_bet_summary(bets: list[dict[str, Any]]) -> BetSummary:
    total_bets = len(bets)
    pending_bets = sum(1 for bet in bets if bet["outcome"] == "pending")
    wins = sum(1 for bet in bets if bet["outcome"] == "win")
    losses = sum(1 for bet in bets if bet["outcome"] == "loss")
    settled_bets = wins + losses
    total_staked = round(sum(float(bet["amount"]) for bet in bets), 2)
    profit_loss = round(sum(float(bet["profit_loss"]) for bet in bets), 2)

    return BetSummary(
        total_bets=total_bets,
        pending_bets=pending_bets,
        wins=wins,
        losses=losses,
        win_rate=round(wins / settled_bets, 4) if settled_bets else 0.0,
        total_staked=total_staked,
        profit_loss=profit_loss,
        roi=round(profit_loss / total_staked, 4) if total_staked else 0.0,
    )


async def _ensure_user_exists(user_id: UUID) -> None:
    client = await get_supabase()
    response = await client.table("users").select("id").eq("id", str(user_id)).limit(1).execute()
    if not response.data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User not found.")


async def create_bet(payload: BetCreateRequest) -> dict[str, Any]:
    await _ensure_user_exists(payload.user_id)
    client = await get_supabase()
    amount = round(payload.amount, 2)
    odds = round(payload.odds, 2)
    bet_data = {
        "user_id": str(payload.user_id),
        "match": payload.match,
        "amount": amount,
        "odds": odds,
        "outcome": payload.outcome,
        "profit_loss": calculate_profit_loss(amount, odds, payload.outcome),
    }
    response = await client.table("bet_tracker").insert(bet_data).execute()
    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create bet.",
        )
    return response.data[0]


async def list_bets(user_id: UUID) -> tuple[list[dict[str, Any]], BetSummary]:
    await _ensure_user_exists(user_id)
    client = await get_supabase()
    response = (
        await client.table("bet_tracker")
        .select("*")
        .eq("user_id", str(user_id))
        .order("created_at", desc=True)
        .execute()
    )
    bets = response.data or []
    return bets, build_bet_summary(bets)


async def update_bet(bet_id: UUID, payload: BetUpdateRequest) -> dict[str, Any]:
    client = await get_supabase()
    existing_response = (
        await client.table("bet_tracker")
        .select("*")
        .eq("id", str(bet_id))
        .eq("user_id", str(payload.user_id))
        .limit(1)
        .execute()
    )
    if not existing_response.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bet not found.")

    existing_bet = existing_response.data[0]
    amount = round(payload.amount if payload.amount is not None else float(existing_bet["amount"]), 2)
    odds = round(payload.odds if payload.odds is not None else float(existing_bet["odds"]), 2)
    outcome = payload.outcome if payload.outcome is not None else existing_bet["outcome"]

    update_data: dict[str, Any] = {
        "amount": amount,
        "odds": odds,
        "outcome": outcome,
        "profit_loss": calculate_profit_loss(amount, odds, outcome),
    }
    if payload.match is not None:
        update_data["match"] = payload.match

    response = (
        await client.table("bet_tracker")
        .update(update_data)
        .eq("id", str(bet_id))
        .eq("user_id", str(payload.user_id))
        .execute()
    )
    if not response.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bet not found.")
    return response.data[0]


async def delete_bet(bet_id: UUID, user_id: UUID) -> None:
    client = await get_supabase()
    existing_response = (
        await client.table("bet_tracker")
        .select("id")
        .eq("id", str(bet_id))
        .eq("user_id", str(user_id))
        .limit(1)
        .execute()
    )
    if not existing_response.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bet not found.")

    await client.table("bet_tracker").delete().eq("id", str(bet_id)).eq("user_id", str(user_id)).execute()
