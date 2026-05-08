from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    supabase_url: str = Field(..., alias="SUPABASE_URL")
    supabase_key: str = Field(..., alias="SUPABASE_KEY")
    openai_api_key: str = Field(..., alias="OPENAI_API_KEY")
    stripe_secret_key: str = Field(..., alias="STRIPE_SECRET_KEY")
    openai_model: str = Field(default="gpt-5.4-mini", alias="OPENAI_MODEL")
    free_daily_chat_limit: int = Field(default=5, alias="FREE_DAILY_CHAT_LIMIT")
    api_football_key: str | None = Field(default=None, alias="API_FOOTBALL_KEY")
    api_football_base_url: str = Field(default="https://v3.football.api-sports.io", alias="API_FOOTBALL_BASE_URL")
    world_cup_league_id: int = Field(default=1, alias="WORLD_CUP_LEAGUE_ID")
    world_cup_season: int = Field(default=2026, alias="WORLD_CUP_SEASON")
    world_cup_cache_ttl_seconds: int = Field(default=600, alias="WORLD_CUP_CACHE_TTL_SECONDS")
    world_cup_fixture_refresh_hours: int = Field(default=12, alias="WORLD_CUP_FIXTURE_REFRESH_HOURS")
    match_detection_fallback_enabled: bool = Field(default=True, alias="MATCH_DETECTION_FALLBACK_ENABLED")
    match_detection_model: str | None = Field(default=None, alias="MATCH_DETECTION_MODEL")
    internal_api_token: str | None = Field(default=None, alias="INTERNAL_API_TOKEN")
    cors_allowed_origins: str = Field(
        default="http://localhost:3000,http://127.0.0.1:3000",
        alias="CORS_ALLOWED_ORIGINS",
    )

    model_config = SettingsConfigDict(
        env_file=("../../.env", ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
