from uuid import UUID

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    user_id: UUID
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
