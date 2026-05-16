from uuid import UUID

from pydantic import BaseModel, Field
from typing import Literal


DEFAULT_DEV_USER_ID = UUID("a87d09e8-7e10-46b8-9927-c9500c9559cf")


class UserResponse(BaseModel):
    id: UUID
    email: str | None = None
    plan: str = Field(pattern="^(free|premium)$")
    daily_chat_count: int
    daily_chat_count_limit: int
    daily_chats_remaining: int | None
    chat_count_limit: int
    chat_limit_period: Literal["day", "week"]
    chats_remaining: int
    last_reset_date: str | None = None
    created_at: str | None = None
