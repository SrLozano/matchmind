from uuid import UUID

from pydantic import BaseModel, Field

from app.models.users import DEFAULT_DEV_USER_ID


class ChatRequest(BaseModel):
    user_id: UUID = DEFAULT_DEV_USER_ID
    message: str = Field(..., min_length=1, max_length=4000)
    preferred_language: str | None = Field(default=None, pattern="^(en|es)$")


class ChatResponse(BaseModel):
    response: str
    confidence_score: float = Field(..., ge=1, le=10)
    verdict: str | None = None
    implied_probability: float | None = Field(default=None, ge=0, le=1)
    stake_posture: str | None = None
    daily_chats_remaining: int | None


class AIChatResult(BaseModel):
    response: str
    confidence_score: float = Field(..., ge=1, le=10)
    verdict: str | None = None
    implied_probability: float | None = Field(default=None, ge=0, le=1)
    stake_posture: str | None = None
