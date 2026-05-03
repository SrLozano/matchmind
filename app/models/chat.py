from uuid import UUID

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    user_id: UUID
    message: str = Field(..., min_length=1, max_length=4000)


class ChatResponse(BaseModel):
    response: str
    confidence_score: int = Field(..., ge=1, le=10)
    daily_chats_remaining: int | None


class AIChatResult(BaseModel):
    response: str
    confidence_score: int = Field(..., ge=1, le=10)
