import logging
import asyncio
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from fastapi import APIRouter, HTTPException, status

from app.models.chat import ChatMarketSignal, ChatRequest, ChatResponse
from app.services.api_football import build_match_context_for_chat
from app.services.gpt import generate_chat_reply
from app.services.odds_api import build_bookmaker_context_for_chat
from app.services.polymarket import build_polymarket_context_for_chat
from app.services.supabase import enforce_daily_limit_and_store, release_reserved_chat

router = APIRouter(tags=["chat"])
logger = logging.getLogger(__name__)
T = TypeVar("T")


@router.post("/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest) -> ChatResponse:
    user_context = None
    try:
        user_context = await enforce_daily_limit_and_store(payload.user_id, payload.message)
        match_context, polymarket_context = await asyncio.gather(
            _safe_context_call("api_football", build_match_context_for_chat, payload.message),
            _safe_context_call("polymarket", build_polymarket_context_for_chat, payload.message),
        )
        bookmaker_context = await _safe_context_call(
            "bookmaker_odds",
            build_bookmaker_context_for_chat,
            payload.message,
            match_context=match_context,
        )
        ai_result = await generate_chat_reply(
            payload.message,
            match_context,
            polymarket_context,
            bookmaker_context,
            preferred_language=payload.preferred_language,
        )
        saved_turn = await user_context.save_assistant_turn(
            ai_result.response,
            ai_result.confidence_score,
        )
        return ChatResponse(
            response=saved_turn["response"],
            confidence_score=saved_turn["confidence_score"],
            verdict=ai_result.verdict,
            implied_probability=ai_result.implied_probability,
            stake_posture=ai_result.stake_posture,
            market_signal=_build_chat_market_signal(polymarket_context),
            daily_chats_remaining=saved_turn["daily_chats_remaining"],
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(exc),
        ) from exc
    except HTTPException:
        raise
    except Exception as exc:
        if user_context is not None:
            await release_reserved_chat(user_context.user)
        logger.exception("Chat request failed for user_id=%s", payload.user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to process chat request.",
        ) from exc


async def _safe_context_call(
    source_name: str,
    builder: Callable[..., Awaitable[T]],
    *args: Any,
    **kwargs: Any,
) -> T | None:
    try:
        return await builder(*args, **kwargs)
    except Exception:
        logger.warning("Chat data source failed: %s", source_name, exc_info=True)
        return None


def _build_chat_market_signal(polymarket_context: dict | None) -> ChatMarketSignal | None:
    if not polymarket_context:
        return None
    if not polymarket_context.get("matched"):
        return ChatMarketSignal(
            matched=False,
            market_type=polymarket_context.get("supported_intent"),
            teams=polymarket_context.get("teams") or [],
            note=polymarket_context.get("note"),
            last_fetched_at=polymarket_context.get("last_fetched_at"),
        )
    return ChatMarketSignal(
        matched=True,
        market_type=polymarket_context.get("market_type"),
        team=polymarket_context.get("team"),
        teams=polymarket_context.get("teams") or [],
        group=polymarket_context.get("group"),
        question=polymarket_context.get("question"),
        implied_probability=polymarket_context.get("implied_probability"),
        liquidity=polymarket_context.get("liquidity"),
        liquidity_label=polymarket_context.get("liquidity_label"),
        volume=polymarket_context.get("volume"),
        spread=polymarket_context.get("spread"),
        signal_quality_score=polymarket_context.get("signal_quality_score"),
        match_confidence=polymarket_context.get("match_confidence"),
        last_fetched_at=polymarket_context.get("last_fetched_at"),
    )
