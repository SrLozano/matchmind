from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from supabase import AsyncClient, acreate_client

from app.config import get_settings

_supabase_client: AsyncClient | None = None


@dataclass
class ChatSessionContext:
    user: dict[str, Any]
    conversation: dict[str, Any]

    async def save_assistant_turn(self, response: str, confidence_score: int) -> dict[str, Any]:
        messages = list(self.conversation.get("messages", []))
        messages.append(
            {
                "role": "assistant",
                "content": response,
                "confidence_score": confidence_score,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        )

        updated_conversation = (
            await get_supabase()
        ).table("conversations").update({"messages": messages}).eq("id", self.conversation["id"]).execute()

        daily_remaining = None
        if self.user["plan"] == "free":
            daily_remaining = max(self.user["daily_chat_count_limit"] - self.user["daily_chat_count"], 0)

        return {
            "response": response,
            "confidence_score": confidence_score,
            "daily_chats_remaining": daily_remaining,
            "conversation": updated_conversation.data[0] if updated_conversation.data else None,
        }


async def get_supabase() -> AsyncClient:
    global _supabase_client
    if _supabase_client is None:
        settings = get_settings()
        _supabase_client = await acreate_client(settings.supabase_url, settings.supabase_key)
    return _supabase_client


async def close_supabase() -> None:
    global _supabase_client
    _supabase_client = None


async def supabase_healthcheck() -> bool:
    client = await get_supabase()
    try:
        response = await client.table("users").select("id").limit(1).execute()
        return response.data is not None
    except Exception:
        return False


async def _get_user(user_id: UUID) -> dict[str, Any]:
    client = await get_supabase()
    response = await client.table("users").select("*").eq("id", str(user_id)).limit(1).execute()
    if not response.data:
        raise ValueError("User not found.")
    return response.data[0]


async def _reset_daily_count_if_needed(user: dict[str, Any]) -> dict[str, Any]:
    today = date.today()
    last_reset_raw = user.get("last_reset_date")
    if isinstance(last_reset_raw, date):
        last_reset = last_reset_raw
    elif last_reset_raw:
        last_reset = date.fromisoformat(last_reset_raw)
    else:
        last_reset = None

    if last_reset == today:
        return user

    client = await get_supabase()
    response = (
        await client.table("users")
        .update({"daily_chat_count": 0, "last_reset_date": today.isoformat()})
        .eq("id", user["id"])
        .execute()
    )
    return response.data[0]


async def _enforce_daily_limit(user: dict[str, Any]) -> dict[str, Any]:
    settings = get_settings()
    user = await _reset_daily_count_if_needed(user)
    user["daily_chat_count_limit"] = settings.free_daily_chat_limit

    if user["plan"] != "free":
        return user

    if user["daily_chat_count"] >= settings.free_daily_chat_limit:
        raise PermissionError("Daily chat limit reached for free plan.")

    client = await get_supabase()
    response = (
        await client.table("users")
        .update({"daily_chat_count": user["daily_chat_count"] + 1, "last_reset_date": date.today().isoformat()})
        .eq("id", user["id"])
        .execute()
    )
    updated_user = response.data[0]
    updated_user["daily_chat_count_limit"] = settings.free_daily_chat_limit
    return updated_user


async def _create_conversation(user_id: str, message: str) -> dict[str, Any]:
    client = await get_supabase()
    response = (
        await client.table("conversations")
        .insert(
            {
                "user_id": user_id,
                "messages": [
                    {
                        "role": "user",
                        "content": message,
                        "created_at": datetime.now(timezone.utc).isoformat(),
                    }
                ],
            }
        )
        .execute()
    )
    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create conversation.",
        )
    return response.data[0]


async def enforce_daily_limit_and_store(user_id: UUID, message: str) -> ChatSessionContext:
    user = await _get_user(user_id)
    updated_user = await _enforce_daily_limit(user)
    conversation = await _create_conversation(str(user_id), message)
    return ChatSessionContext(user=updated_user, conversation=conversation)


async def release_reserved_chat(user: dict[str, Any]) -> None:
    if user.get("plan") != "free":
        return

    current_count = max(int(user.get("daily_chat_count", 0)) - 1, 0)
    client = await get_supabase()
    await client.table("users").update({"daily_chat_count": current_count}).eq("id", user["id"]).execute()
