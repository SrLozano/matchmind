import logging
import asyncio

from fastapi import APIRouter, HTTPException, status

from app.models.chat import ChatRequest, ChatResponse
from app.services.api_football import build_match_context_for_chat
from app.services.gpt import generate_chat_reply
from app.services.polymarket import build_polymarket_context_for_chat
from app.services.supabase import enforce_daily_limit_and_store, release_reserved_chat

router = APIRouter(tags=["chat"])
logger = logging.getLogger(__name__)


@router.post("/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest) -> ChatResponse:
    user_context = None
    try:
        user_context = await enforce_daily_limit_and_store(payload.user_id, payload.message)
        match_context, polymarket_context = await asyncio.gather(
            build_match_context_for_chat(payload.message),
            build_polymarket_context_for_chat(payload.message),
        )
        ai_result = await generate_chat_reply(
            payload.message,
            match_context,
            polymarket_context,
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
