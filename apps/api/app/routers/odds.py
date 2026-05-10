from __future__ import annotations

import logging

from fastapi import APIRouter, Header, HTTPException, Query, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.config import get_settings
from app.services.odds_api import (
    analyze_user_odds,
    get_compact_odds_matches,
    refresh_bookmaker_events_from_api,
    refresh_featured_bookmaker_odds_from_api,
    seed_bookmaker_odds_from_discovery_file,
)

router = APIRouter(prefix="/odds", tags=["odds"])
logger = logging.getLogger(__name__)


class OddsAnalyzeRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    odds: float | None = Field(default=None, gt=1)


@router.get("/matches")
async def odds_matches(limit: int = Query(default=50, ge=1, le=100)) -> JSONResponse:
    try:
        matches = await get_compact_odds_matches(limit=limit)
    except Exception as exc:
        logger.exception("Unable to read cached bookmaker odds.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Unable to read cached bookmaker odds: {exc}",
        ) from exc

    return JSONResponse(content={"matches": matches, "count": len(matches)})


@router.post("/analyze")
async def odds_analyze(payload: OddsAnalyzeRequest) -> JSONResponse:
    try:
        result = await analyze_user_odds(payload.message, payload.odds)
    except Exception as exc:
        logger.exception("Unable to analyze odds.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Unable to analyze odds: {exc}",
        ) from exc
    return JSONResponse(content=result)


@router.post("/seed-from-discovery")
async def seed_odds_from_discovery(x_internal_token: str | None = Header(default=None)) -> JSONResponse:
    _require_internal_token(x_internal_token)
    try:
        result = await seed_bookmaker_odds_from_discovery_file()
    except Exception as exc:
        logger.exception("Unable to seed bookmaker odds from discovery JSON.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Unable to seed bookmaker odds: {exc}",
        ) from exc
    return JSONResponse(content=result)


@router.post("/refresh/events")
async def refresh_odds_events(x_internal_token: str | None = Header(default=None)) -> JSONResponse:
    _require_internal_token(x_internal_token)
    try:
        result = await refresh_bookmaker_events_from_api()
    except Exception as exc:
        logger.exception("Unable to refresh bookmaker events.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Unable to refresh bookmaker events: {exc}",
        ) from exc
    return JSONResponse(content=result)


@router.post("/refresh")
async def refresh_odds(x_internal_token: str | None = Header(default=None)) -> JSONResponse:
    _require_internal_token(x_internal_token)
    try:
        result = await refresh_featured_bookmaker_odds_from_api()
    except Exception as exc:
        logger.exception("Unable to refresh bookmaker odds.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Unable to refresh bookmaker odds: {exc}",
        ) from exc
    return JSONResponse(content=result)


def _require_internal_token(x_internal_token: str | None) -> None:
    settings = get_settings()
    if not settings.internal_api_token or x_internal_token != settings.internal_api_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This internal odds endpoint requires a valid X-Internal-Token header.",
        )
