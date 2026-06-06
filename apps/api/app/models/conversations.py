from pydantic import BaseModel, Field


class ConversationMessage(BaseModel):
    role: str
    content: str
    confidence_score: float | None = None
    verdict: str | None = None
    implied_probability: float | None = None
    stake_posture: str | None = None
    recommended_stake: int | None = Field(default=None, ge=1, le=10)
    created_at: str | None = None


class ConversationSummary(BaseModel):
    id: str
    user_id: str
    title: str
    last_message_preview: str | None = None
    message_count: int = 0
    created_at: str | None = None
    updated_at: str | None = None


class ConversationListResponse(BaseModel):
    conversations: list[ConversationSummary]
    count: int


class ConversationDetailResponse(ConversationSummary):
    messages: list[ConversationMessage] = Field(default_factory=list)
