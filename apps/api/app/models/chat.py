from uuid import UUID

from pydantic import BaseModel, Field

DEFAULT_DEV_USER_ID = UUID("a87d09e8-7e10-46b8-9927-c9500c9559cf")


class ChatRequest(BaseModel):
    user_id: UUID = DEFAULT_DEV_USER_ID
    message: str = Field(..., min_length=1, max_length=4000)


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
