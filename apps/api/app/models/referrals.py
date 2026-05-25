from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

ReferralOwnerType = Literal["bar_partner", "user"]
UserReferralTierKey = Literal["scout", "insider", "captain", "legend", "founder_circle"]


class BarPartnerCreate(BaseModel):
    user_id: UUID | None = None
    business_name: str = Field(..., min_length=1, max_length=160)
    location: str = Field(..., min_length=1, max_length=160)
    responsible_name: str = Field(..., min_length=1, max_length=120)
    phone: str = Field(..., min_length=6, max_length=40)
    terms_accepted: bool

    @field_validator("business_name", "location", "responsible_name", "phone")
    @classmethod
    def clean_required_text(cls, value: str) -> str:
        cleaned = " ".join(value.strip().split())
        if not cleaned:
            raise ValueError("This field is required.")
        return cleaned


class ReferralPartnerResponse(BaseModel):
    id: UUID
    user_id: UUID
    partner_type: Literal["bar"]
    business_name: str
    location: str
    responsible_name: str
    status: str
    terms_accepted_at: datetime
    created_at: datetime
    updated_at: datetime | None = None


class ReferralCodeResponse(BaseModel):
    id: UUID
    code: str
    owner_type: ReferralOwnerType
    partner_id: UUID | None = None
    owner_user_id: UUID | None = None
    discount_type: Literal["fixed_amount"]
    discount_amount: float
    commission_amount: float
    active: bool
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    created_at: datetime


class BarPartnerCreateResponse(BaseModel):
    partner_id: UUID
    code: str
    business_name: str
    status: str


class UserReferralTier(BaseModel):
    key: UserReferralTierKey
    required_registered_referrals: int
    required_paid_referrals: int
    pass_price: float
    discount_percent: int
    beta_priority: bool = False


class UserReferralPerks(BaseModel):
    current_tier: UserReferralTier | None = None
    next_tier: UserReferralTier | None = None
    unlocked_pass_price: float = 9.99
    discount_percent: int = 0
    beta_priority: bool = False
    remaining_registered_referrals: int = 1
    remaining_paid_referrals: int = 0


class UserReferralSummary(BaseModel):
    has_code: bool
    code: str | None = None
    registered_referrals: int = 0
    paid_referrals: int = 0
    status_label: str = "Coming soon"
    perks: UserReferralPerks = Field(default_factory=UserReferralPerks)


class UserReferralCodeCreateResponse(BaseModel):
    code: str
    registered_referrals: int = 0
    paid_referrals: int = 0
    status_label: str = "Tracked"
    perks: UserReferralPerks = Field(default_factory=UserReferralPerks)


class ApplyReferralCodeRequest(BaseModel):
    user_id: UUID | None = None
    code: str = Field(..., min_length=1, max_length=80)


class ApplyReferralCodeResponse(BaseModel):
    applied: bool
    code: str
    partner_name: str
    discount_amount: float
    owner_type: ReferralOwnerType | None = None


class ValidateReferralCodeResponse(BaseModel):
    valid: bool
    code: str | None = None
    partner_name: str | None = None
    discount_amount: float | None = None
    discount_label: str | None = None
    owner_type: ReferralOwnerType | None = None


class AppliedReferralResponse(BaseModel):
    code: str
    partner_name: str
    discount_amount: float
    applied_at: datetime | None = None
    owner_type: ReferralOwnerType | None = None


class ReferralDashboardResponse(BaseModel):
    has_bar_partner: bool
    partner: ReferralPartnerResponse | None = None
    code: str | None = None
    registered_referrals: int = 0
    paid_referrals: int = 0
    estimated_payout: float = 0.0
    commission_amount: float = 2.0
    discount_amount: float = 1.0
    applied_referral: AppliedReferralResponse | None = None
    user_referral: UserReferralSummary = Field(default_factory=UserReferralSummary)
