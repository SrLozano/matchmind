from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator


BetOutcome = Literal["win", "loss", "pending"]


class BetCreateRequest(BaseModel):
    user_id: UUID | None = None
    match: str = Field(..., min_length=1, max_length=200)
    amount: float = Field(..., gt=0)
    odds: float = Field(..., gt=1)
    outcome: BetOutcome = "pending"

    @field_validator("match")
    @classmethod
    def clean_match(cls, value: str) -> str:
        cleaned_value = value.strip()
        if not cleaned_value:
            raise ValueError("Match must not be empty.")
        return cleaned_value


class BetUpdateRequest(BaseModel):
    user_id: UUID | None = None
    match: str | None = Field(default=None, min_length=1, max_length=200)
    amount: float | None = Field(default=None, gt=0)
    odds: float | None = Field(default=None, gt=1)
    outcome: BetOutcome | None = None

    @field_validator("match")
    @classmethod
    def clean_match(cls, value: str | None) -> str | None:
        if value is None:
            return value

        cleaned_value = value.strip()
        if not cleaned_value:
            raise ValueError("Match must not be empty.")
        return cleaned_value

    @model_validator(mode="after")
    def require_update_field(self) -> "BetUpdateRequest":
        if self.match is None and self.amount is None and self.odds is None and self.outcome is None:
            raise ValueError("At least one bet field must be provided.")
        return self


class BetResponse(BaseModel):
    id: UUID
    user_id: UUID
    match: str
    amount: float
    odds: float
    outcome: BetOutcome
    profit_loss: float
    created_at: datetime


class BetSummary(BaseModel):
    total_bets: int
    pending_bets: int
    wins: int
    losses: int
    win_rate: float
    total_staked: float
    profit_loss: float
    roi: float


class BetListResponse(BaseModel):
    bets: list[BetResponse]
    summary: BetSummary
