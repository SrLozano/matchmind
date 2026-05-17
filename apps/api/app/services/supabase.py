from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
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

    @property
    def previous_messages(self) -> list[dict[str, Any]]:
        messages = list(self.conversation.get("messages", []))
        if messages and messages[-1].get("role") == "user":
            return messages[:-1]
        return messages

    async def save_assistant_turn(self, response: str, confidence_score: float) -> dict[str, Any]:
        messages = list(self.conversation.get("messages", []))
        messages.append(
            {
                "role": "assistant",
                "content": response,
                "confidence_score": confidence_score,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        )

        client = await get_supabase()
        updated_conversation = await (
            client.table("conversations")
            .update({"messages": messages})
            .eq("id", self.conversation["id"])
            .execute()
        )

        chat_count = int(self.user.get("daily_chat_count", 0))
        chat_limit = _chat_limit_for_plan(self.user.get("plan", "free"))
        plan = self.user.get("plan", "free")
        chat_usage = _public_chat_usage(plan, chat_count, chat_limit)

        return {
            "conversation_id": self.conversation["id"],
            "response": response,
            "confidence_score": confidence_score,
            "daily_chats_remaining": chat_usage["daily_chats_remaining"],
            "chat_count": chat_count,
            "chat_count_limit": chat_usage["chat_count_limit"],
            "chat_limit_period": chat_usage["chat_limit_period"],
            "chats_remaining": chat_usage["chats_remaining"],
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


async def supabase_healthcheck() -> tuple[bool, str]:
    client = await get_supabase()
    try:
        await client.table("users").select("id").limit(1).execute()
        return True, "Supabase connection is healthy."
    except Exception as exc:
        return False, str(exc)


async def _get_user(user_id: UUID) -> dict[str, Any]:
    client = await get_supabase()
    response = await client.table("users").select("*").eq("id", str(user_id)).limit(1).execute()
    if not response.data:
        raise ValueError("User not found.")
    return response.data[0]


async def ensure_user_profile(user_id: UUID, email: str | None = None) -> dict[str, Any]:
    client = await get_supabase()
    existing = await client.table("users").select("*").eq("id", str(user_id)).limit(1).execute()
    if existing.data:
        user = existing.data[0]
        if email and user.get("email") != email:
            updated = await client.table("users").update({"email": email}).eq("id", str(user_id)).execute()
            return updated.data[0] if updated.data else user
        return user

    response = (
        await client.table("users")
        .insert(
            {
                "id": str(user_id),
                "email": email,
                "plan": "free",
                "daily_chat_count": 0,
                "last_reset_date": date.today().isoformat(),
            }
        )
        .execute()
    )
    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user profile.",
        )
    return response.data[0]


async def get_user_profile(user_id: UUID) -> dict[str, Any]:
    user = await _reset_chat_count_if_needed(await _get_user(user_id))
    plan = user.get("plan", "free")
    chat_limit = _chat_limit_for_plan(plan)
    chat_count = int(user.get("daily_chat_count", 0))
    chat_usage = _public_chat_usage(plan, chat_count, chat_limit)

    return {
        "id": user["id"],
        "email": user.get("email"),
        "plan": plan,
        "daily_chat_count": chat_count,
        "daily_chat_count_limit": chat_usage["chat_count_limit"],
        "daily_chats_remaining": chat_usage["daily_chats_remaining"],
        "chat_count_limit": chat_usage["chat_count_limit"],
        "chat_limit_period": chat_usage["chat_limit_period"],
        "chats_remaining": chat_usage["chats_remaining"],
        "last_reset_date": user.get("last_reset_date"),
        "created_at": user.get("created_at"),
    }


async def update_user_plan(user_id: UUID, plan: str) -> dict[str, Any]:
    client = await get_supabase()
    response = (
        await client.table("users")
        .update({"plan": plan, "daily_chat_count": 0, "last_reset_date": date.today().isoformat()})
        .eq("id", str(user_id))
        .execute()
    )
    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User profile not found.",
        )
    return response.data[0]


async def list_user_conversations(user_id: UUID, limit: int = 20) -> list[dict[str, Any]]:
    client = await get_supabase()
    response = (
        await client.table("conversations")
        .select("*")
        .eq("user_id", str(user_id))
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    conversations = response.data or []
    summaries = [_conversation_summary(conversation) for conversation in conversations]
    return sorted(
        summaries,
        key=lambda conversation: conversation.get("updated_at") or conversation.get("created_at") or "",
        reverse=True,
    )


async def get_user_conversation(user_id: UUID, conversation_id: UUID) -> dict[str, Any]:
    conversation = await _get_conversation_for_user(str(user_id), conversation_id)
    summary = _conversation_summary(conversation)
    return {
        **summary,
        "messages": _conversation_messages(conversation),
    }


def _conversation_summary(conversation: dict[str, Any]) -> dict[str, Any]:
    messages = _conversation_messages(conversation)
    first_user_message = next((message for message in messages if message["role"] == "user"), None)
    last_message = messages[-1] if messages else None
    title_source = first_user_message["content"] if first_user_message else "New conversation"
    preview_source = last_message["content"] if last_message else None

    return {
        "id": str(conversation.get("id") or ""),
        "user_id": str(conversation.get("user_id") or ""),
        "title": _compact_text(title_source, 64),
        "last_message_preview": _compact_text(preview_source, 96) if preview_source else None,
        "message_count": len(messages),
        "created_at": _string_or_none(conversation.get("created_at")),
        "updated_at": _conversation_updated_at(conversation, messages),
    }


def _conversation_messages(conversation: dict[str, Any]) -> list[dict[str, Any]]:
    raw_messages = conversation.get("messages") or []
    if not isinstance(raw_messages, list):
        return []

    messages: list[dict[str, Any]] = []
    for raw_message in raw_messages:
        if not isinstance(raw_message, dict):
            continue
        role = str(raw_message.get("role") or "").strip()
        content = str(raw_message.get("content") or "").strip()
        if role not in {"user", "assistant"} or not content:
            continue
        messages.append(
            {
                "role": role,
                "content": content,
                "confidence_score": raw_message.get("confidence_score"),
                "created_at": _string_or_none(raw_message.get("created_at")),
            }
        )
    return messages


def _conversation_updated_at(conversation: dict[str, Any], messages: list[dict[str, Any]]) -> str | None:
    for message in reversed(messages):
        if message.get("created_at"):
            return message["created_at"]
    return _string_or_none(conversation.get("created_at"))


def _compact_text(value: str, limit: int) -> str:
    text = " ".join(value.split())
    if len(text) <= limit:
        return text
    return f"{text[: max(limit - 3, 0)].rstrip()}..."


def _string_or_none(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _chat_limit_for_plan(plan: str) -> int:
    settings = get_settings()
    if plan == "premium":
        return settings.premium_weekly_chat_limit
    return settings.free_daily_chat_limit


def _chat_limit_period_for_plan(plan: str) -> str:
    return "week" if plan == "premium" else "day"


def _public_chat_usage(plan: str, chat_count: int, chat_limit: int) -> dict[str, int | str | None]:
    if plan == "premium":
        return {
            "daily_chats_remaining": None,
            "chat_count_limit": None,
            "chat_limit_period": None,
            "chats_remaining": None,
        }

    chats_remaining = max(chat_limit - chat_count, 0)
    return {
        "daily_chats_remaining": chats_remaining,
        "chat_count_limit": chat_limit,
        "chat_limit_period": _chat_limit_period_for_plan(plan),
        "chats_remaining": chats_remaining,
    }


def _current_period_start(plan: str, today: date | None = None) -> date:
    current_date = today or date.today()
    if plan == "premium":
        return current_date - timedelta(days=current_date.weekday())
    return current_date


async def _reset_chat_count_if_needed(user: dict[str, Any]) -> dict[str, Any]:
    plan = user.get("plan", "free")
    today = date.today()
    period_start = _current_period_start(plan, today)
    last_reset_raw = user.get("last_reset_date")
    if isinstance(last_reset_raw, date):
        last_reset = last_reset_raw
    elif last_reset_raw:
        last_reset = date.fromisoformat(last_reset_raw)
    else:
        last_reset = None

    if last_reset and last_reset >= period_start:
        return user

    client = await get_supabase()
    response = (
        await client.table("users")
        .update({"daily_chat_count": 0, "last_reset_date": period_start.isoformat()})
        .eq("id", user["id"])
        .execute()
    )
    return response.data[0]


async def _enforce_chat_limit(user: dict[str, Any]) -> dict[str, Any]:
    user = await _reset_chat_count_if_needed(user)
    plan = user.get("plan", "free")
    chat_limit = _chat_limit_for_plan(plan)
    user["daily_chat_count_limit"] = chat_limit

    if int(user.get("daily_chat_count", 0)) >= chat_limit:
        if plan == "premium":
            raise PermissionError("Weekly fair-use chat limit reached for premium plan.")
        raise PermissionError("Daily chat limit reached for free plan.")

    client = await get_supabase()
    response = (
        await client.table("users")
        .update(
            {
                "daily_chat_count": int(user.get("daily_chat_count", 0)) + 1,
                "last_reset_date": _current_period_start(plan).isoformat(),
            }
        )
        .eq("id", user["id"])
        .execute()
    )
    updated_user = response.data[0]
    updated_user["daily_chat_count_limit"] = chat_limit
    return updated_user


async def _get_conversation_for_user(user_id: str, conversation_id: UUID) -> dict[str, Any]:
    client = await get_supabase()
    response = (
        await client.table("conversations")
        .select("*")
        .eq("id", str(conversation_id))
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    if not response.data:
        raise ValueError("Conversation not found.")
    return response.data[0]


async def _append_user_turn(conversation: dict[str, Any], message: str) -> dict[str, Any]:
    messages = list(conversation.get("messages", []))
    messages.append(
        {
            "role": "user",
            "content": message,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    )

    client = await get_supabase()
    response = (
        await client.table("conversations")
        .update({"messages": messages})
        .eq("id", conversation["id"])
        .execute()
    )
    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update conversation.",
        )
    return response.data[0]


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


async def enforce_daily_limit_and_store(
    user_id: UUID,
    message: str,
    conversation_id: UUID | None = None,
) -> ChatSessionContext:
    user = await _get_user(user_id)
    updated_user = await _enforce_chat_limit(user)
    if conversation_id is None:
        conversation = await _create_conversation(str(user_id), message)
    else:
        existing_conversation = await _get_conversation_for_user(str(user_id), conversation_id)
        conversation = await _append_user_turn(existing_conversation, message)
    return ChatSessionContext(user=updated_user, conversation=conversation)


async def release_reserved_chat(user: dict[str, Any]) -> None:
    current_count = max(int(user.get("daily_chat_count", 0)) - 1, 0)
    client = await get_supabase()
    await client.table("users").update({"daily_chat_count": current_count}).eq("id", user["id"]).execute()
