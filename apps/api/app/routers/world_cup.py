from __future__ import annotations

import logging

from fastapi import APIRouter, Header, HTTPException, status
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.services.api_football import (
    APIFootballRateLimitError,
    compact_match_context,
    get_api_football_usage,
    get_cached_world_cup_matches,
    refresh_world_cup_fixtures_if_needed,
)

router = APIRouter(prefix="/world-cup", tags=["world-cup"])
logger = logging.getLogger(__name__)


@router.get("/fixtures")
async def world_cup_fixtures() -> JSONResponse:
    try:
        matches = await get_cached_world_cup_matches()
    except Exception as exc:
        logger.exception("Unable to read cached World Cup fixtures.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Unable to read cached World Cup fixtures from Supabase: {exc}",
        ) from exc

    return JSONResponse(
        content={
            "matches": [compact_match_context(match) for match in matches],
            "count": len(matches),
            "api_football_usage": get_api_football_usage(),
        }
    )


@router.post("/refresh")
async def refresh_world_cup_fixtures(x_internal_token: str | None = Header(default=None)) -> JSONResponse:
    settings = get_settings()
    if not settings.internal_api_token or x_internal_token != settings.internal_api_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This internal refresh endpoint requires a valid X-Internal-Token header.",
        )

    try:
        result = await refresh_world_cup_fixtures_if_needed(force=True)
    except APIFootballRateLimitError as exc:
        logger.warning("API-Football rate limit hit while refreshing World Cup fixtures: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Unable to refresh World Cup fixtures: {exc}",
            headers={"Retry-After": str(exc.retry_after_seconds)},
        ) from exc
    except Exception as exc:
        logger.exception("Unable to refresh World Cup fixtures.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Unable to refresh World Cup fixtures: {exc}",
        ) from exc

    return JSONResponse(content=result)
