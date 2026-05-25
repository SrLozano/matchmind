from uuid import UUID

from pydantic import BaseModel, Field
from typing import Literal


DEFAULT_DEV_USER_ID = UUID("a87d09e8-7e10-46b8-9927-c9500c9559cf")


class UserResponse(BaseModel):
    id: UUID
    email: str | None = None
    name: str | None = None
    plan: str = Field(pattern="^(free|premium)$")
    daily_chat_count: int
    daily_chat_count_limit: int | None
    daily_chats_remaining: int | None
    chat_count_limit: int | None
    chat_limit_period: Literal["day", "week"] | None
    chats_remaining: int | None
    last_reset_date: str | None = None
    created_at: str | None = None


class UserUpdateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)
