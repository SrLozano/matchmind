import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.routers.bets import router as bets_router
from app.routers.chat import router as chat_router
from app.routers.polymarket import router as polymarket_router
from app.routers.users import router as users_router
from app.routers.world_cup import router as world_cup_router
from app.services.supabase import close_supabase, get_supabase, supabase_healthcheck

logger = logging.getLogger(__name__)


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
)

settings = get_settings()
allowed_origins = [
    origin.strip()
    for origin in settings.cors_allowed_origins.split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)
app.include_router(world_cup_router)
app.include_router(polymarket_router)
app.include_router(bets_router)
app.include_router(users_router)


@app.get("/")
async def root() -> JSONResponse:
    return JSONResponse(content={"name": "Matchmind API", "docs": "/docs", "health": "/health"})


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
