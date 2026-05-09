from __future__ import annotations

import logging

from fastapi import APIRouter, Header, HTTPException, Query, status
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.services.polymarket import (
    SUPPORTED_MARKET_TYPES,
    get_market_signals,
    refresh_polymarket_markets_from_api,
    seed_polymarket_markets_from_discovery_file,
)

router = APIRouter(prefix="/polymarket", tags=["polymarket"])
logger = logging.getLogger(__name__)


@router.get("/signals")
async def polymarket_signals(
    limit: int = Query(default=16, ge=1, le=50),
    market_type: str | None = Query(default=None),
) -> JSONResponse:
    if market_type is not None and market_type not in SUPPORTED_MARKET_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported market_type. Use one of: {', '.join(sorted(SUPPORTED_MARKET_TYPES))}",
        )

    try:
        signals = await get_market_signals(limit=limit, market_type=market_type)
    except Exception as exc:
        logger.exception("Unable to read Polymarket signals.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Unable to read Polymarket signals: {exc}",
        ) from exc

    return JSONResponse(content={"signals": signals, "count": len(signals)})


@router.post("/seed-from-discovery")
async def seed_polymarket_from_discovery(x_internal_token: str | None = Header(default=None)) -> JSONResponse:
    _require_internal_token(x_internal_token)
    try:
        result = await seed_polymarket_markets_from_discovery_file()
    except Exception as exc:
        logger.exception("Unable to seed Polymarket markets from discovery JSON.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Unable to seed Polymarket markets: {exc}",
        ) from exc
    return JSONResponse(content=result)


@router.post("/refresh")
async def refresh_polymarket_markets(x_internal_token: str | None = Header(default=None)) -> JSONResponse:
    _require_internal_token(x_internal_token)
    try:
        result = await refresh_polymarket_markets_from_api()
    except Exception as exc:
        logger.exception("Unable to refresh Polymarket markets.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Unable to refresh Polymarket markets: {exc}",
        ) from exc
    return JSONResponse(content=result)


def _require_internal_token(x_internal_token: str | None) -> None:
    settings = get_settings()
    if not settings.internal_api_token or x_internal_token != settings.internal_api_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This internal Polymarket endpoint requires a valid X-Internal-Token header.",
        )
