from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator


BetOutcome = Literal["win", "loss", "pending", "cashed_out"]


class BetCreateRequest(BaseModel):
    user_id: UUID | None = None
    match: str = Field(..., min_length=1, max_length=200)
    pick: str = Field(..., min_length=1, max_length=160)
    market_type: str = Field(..., min_length=1, max_length=80)
    bookmaker: str | None = Field(default=None, max_length=120)
    amount: float = Field(..., gt=0)
    odds: float = Field(..., gt=1)
    outcome: BetOutcome = "pending"

    @field_validator("match", "pick", "market_type")
    @classmethod
    def clean_required_text(cls, value: str) -> str:
        cleaned_value = value.strip()
        if not cleaned_value:
            raise ValueError("Field must not be empty.")
        return cleaned_value

    @field_validator("bookmaker")
    @classmethod
    def clean_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return value
        cleaned_value = value.strip()
        return cleaned_value or None


class BetUpdateRequest(BaseModel):
    user_id: UUID | None = None
    match: str | None = Field(default=None, min_length=1, max_length=200)
    pick: str | None = Field(default=None, min_length=1, max_length=160)
    market_type: str | None = Field(default=None, min_length=1, max_length=80)
    bookmaker: str | None = Field(default=None, max_length=120)
    amount: float | None = Field(default=None, gt=0)
    odds: float | None = Field(default=None, gt=1)
    outcome: BetOutcome | None = None

    @field_validator("match", "pick", "market_type")
    @classmethod
    def clean_required_text(cls, value: str | None) -> str | None:
        if value is None:
            return value

        cleaned_value = value.strip()
        if not cleaned_value:
            raise ValueError("Field must not be empty.")
        return cleaned_value

    @field_validator("bookmaker")
    @classmethod
    def clean_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return value
        cleaned_value = value.strip()
        return cleaned_value or None

    @model_validator(mode="after")
    def require_update_field(self) -> "BetUpdateRequest":
        if (
            self.match is None
            and self.pick is None
            and self.market_type is None
            and "bookmaker" not in self.model_fields_set
            and self.amount is None
            and self.odds is None
            and self.outcome is None
        ):
            raise ValueError("At least one bet field must be provided.")
        return self


class BetResponse(BaseModel):
    id: UUID
    user_id: UUID
    match: str
    pick: str
    market_type: str
    bookmaker: str | None = None
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
    pending_exposure: float
    profit_loss: float
    roi: float


class BetListResponse(BaseModel):
    bets: list[BetResponse]
    summary: BetSummary
