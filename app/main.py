from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.routers.chat import router as chat_router
from app.services.supabase import close_supabase, get_supabase, supabase_healthcheck


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

app.include_router(chat_router)


@app.get("/health")
async def health_check() -> JSONResponse:
    await get_supabase()
    is_healthy = await supabase_healthcheck()
    status_code = 200 if is_healthy else 503
    return JSONResponse(
        status_code=status_code,
        content={"status": "ok" if is_healthy else "error", "database": is_healthy},
    )
