from uuid import UUID

from pydantic import BaseModel, Field

from app.models.users import DEFAULT_DEV_USER_ID


class ChatRequest(BaseModel):
    user_id: UUID = DEFAULT_DEV_USER_ID
    message: str = Field(..., min_length=1, max_length=4000)
    preferred_language: str | None = Field(default=None, pattern="^(en|es)$")
    conversation_id: UUID | None = None


class ChatMarketSignal(BaseModel):
    matched: bool
    market_type: str | None = None
    team: str | None = None
    teams: list[str] = Field(default_factory=list)
    group: str | None = None
    question: str | None = None
    implied_probability: float | None = Field(default=None, ge=0, le=1)
    liquidity: float | None = None
    liquidity_label: str | None = None
    volume: float | None = None
    spread: float | None = None
    signal_quality_score: int | None = Field(default=None, ge=0, le=100)
    match_confidence: float | None = Field(default=None, ge=0, le=1)
    last_fetched_at: str | None = None
    note: str | None = None


class ChatResponse(BaseModel):
    conversation_id: str | None = None
    response: str
    confidence_score: float = Field(..., ge=1, le=10)
    verdict: str | None = None
    implied_probability: float | None = Field(default=None, ge=0, le=1)
    stake_posture: str | None = None
    market_signal: ChatMarketSignal | None = None
    daily_chats_remaining: int | None


class AIChatResult(BaseModel):
    response: str
    confidence_score: float = Field(..., ge=1, le=10)
    verdict: str | None = None
    implied_probability: float | None = Field(default=None, ge=0, le=1)
    stake_posture: str | None = None
