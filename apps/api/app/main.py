import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.routers.bets import router as bets_router
from app.routers.chat import router as chat_router
from app.routers.conversations import router as conversations_router
from app.routers.odds import router as odds_router
from app.routers.payments import router as payments_router
from app.routers.polymarket import router as polymarket_router
from app.routers.referrals import router as referrals_router
from app.routers.users import router as users_router
from app.routers.world_cup import router as world_cup_router
from app.services.supabase import close_supabase, get_supabase, supabase_healthcheck

logger = logging.getLogger(__name__)
settings = get_settings()


def is_production_environment(environment: str) -> bool:
    return environment.strip().lower() in {"prod", "production"}


def validate_production_security() -> None:
    if not is_production_environment(settings.app_environment):
        return

    if settings.allow_dev_auth_fallback:
        raise RuntimeError("ALLOW_DEV_AUTH_FALLBACK must be false in production.")

    normalized_origins = {
        origin.strip()
        for origin in settings.cors_allowed_origins.split(",")
        if origin.strip()
    }
    if "*" in normalized_origins:
        raise RuntimeError("CORS_ALLOWED_ORIGINS must not contain '*' in production.")

    if not settings.internal_api_token or settings.internal_api_token == "change-me-for-internal-refresh":
        raise RuntimeError("INTERNAL_API_TOKEN must be set to a non-placeholder value in production.")


validate_production_security()


@asynccontextmanager
async def lifespan(_: FastAPI):
    await get_supabase()
    try:
        yield
    finally:
        await close_supabase()


app = FastAPI(
    title="Matchmind API",
    description="AI-powered betting coach backend for the 2026 FIFA World Cup.",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.api_docs_enabled else None,
    redoc_url="/redoc" if settings.api_docs_enabled else None,
    openapi_url="/openapi.json" if settings.api_docs_enabled else None,
)


def normalize_origin(origin: str | None) -> str | None:
    if not origin:
        return None
    return origin.strip().rstrip("/") or None


allowed_origins = sorted(
    {
        origin
        for origin in [
            *(normalize_origin(origin) for origin in settings.cors_allowed_origins.split(",")),
            normalize_origin(settings.app_url),
        ]
        if origin
    }
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)
app.include_router(conversations_router)
app.include_router(world_cup_router)
app.include_router(polymarket_router)
app.include_router(odds_router)
app.include_router(payments_router)
app.include_router(bets_router)
app.include_router(referrals_router)
app.include_router(users_router)


@app.get("/")
async def root() -> JSONResponse:
    content = {"name": "Matchmind API", "health": "/health"}
    if settings.api_docs_enabled:
        content["docs"] = "/docs"
    return JSONResponse(content=content)


@app.get("/health")
async def health_check() -> JSONResponse:
    await get_supabase()
    is_healthy, detail = await supabase_healthcheck()
    status_code = 200 if is_healthy else 503
    if not is_healthy:
        logger.warning("Health check failed: %s", detail)
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "ok" if is_healthy else "error",
            "database": is_healthy,
            "detail": detail,
        },
    )
