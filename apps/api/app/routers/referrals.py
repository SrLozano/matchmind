from fastapi import APIRouter, Header, status

from app.models.referrals import (
    ApplyReferralCodeRequest,
    ApplyReferralCodeResponse,
    BarPartnerCreate,
    BarPartnerCreateResponse,
    ReferralDashboardResponse,
    ValidateReferralCodeResponse,
)
from app.services.auth import require_authenticated_user
from app.services.referrals import (
    apply_referral_code,
    create_bar_partner,
    get_referral_dashboard,
    validate_referral_code,
)

router = APIRouter(prefix="/referrals", tags=["referrals"])


@router.post("/bar-partner", response_model=BarPartnerCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_bar_partner_endpoint(
    payload: BarPartnerCreate,
    authorization: str | None = Header(default=None),
) -> dict:
    authenticated_user = await require_authenticated_user(authorization)
    return await create_bar_partner(authenticated_user.id, payload)


@router.get("/me", response_model=ReferralDashboardResponse)
async def referral_dashboard_endpoint(
    authorization: str | None = Header(default=None),
) -> dict:
    authenticated_user = await require_authenticated_user(authorization)
    return await get_referral_dashboard(authenticated_user.id)


@router.get("/validate/{code}", response_model=ValidateReferralCodeResponse)
async def validate_referral_code_endpoint(code: str) -> dict:
    return await validate_referral_code(code)


@router.post("/apply", response_model=ApplyReferralCodeResponse)
async def apply_referral_code_endpoint(
    payload: ApplyReferralCodeRequest,
    authorization: str | None = Header(default=None),
) -> dict:
    authenticated_user = await require_authenticated_user(authorization)
    return await apply_referral_code(authenticated_user.id, payload.code)
