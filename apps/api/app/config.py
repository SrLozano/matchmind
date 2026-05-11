from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    supabase_url: str = Field(..., alias="SUPABASE_URL")
    supabase_key: str = Field(..., alias="SUPABASE_KEY")
    openai_api_key: str = Field(..., alias="OPENAI_API_KEY")
    stripe_secret_key: str | None = Field(default=None, alias="STRIPE_SECRET_KEY")
    stripe_webhook_secret: str | None = Field(default=None, alias="STRIPE_WEBHOOK_SECRET")
    stripe_tournament_pass_price_id: str | None = Field(default=None, alias="STRIPE_TOURNAMENT_PASS_PRICE_ID")
    app_url: str = Field(default="http://localhost:3000", alias="APP_URL")
    openai_model: str = Field(default="gpt-5.4-mini", alias="OPENAI_MODEL")
    free_daily_chat_limit: int = Field(default=5, alias="FREE_DAILY_CHAT_LIMIT")
    api_football_key: str | None = Field(default=None, alias="API_FOOTBALL_KEY")
    api_football_base_url: str = Field(default="https://v3.football.api-sports.io", alias="API_FOOTBALL_BASE_URL")
    world_cup_league_id: int = Field(default=1, alias="WORLD_CUP_LEAGUE_ID")
    world_cup_season: int = Field(default=2026, alias="WORLD_CUP_SEASON")
    world_cup_cache_ttl_seconds: int = Field(default=600, alias="WORLD_CUP_CACHE_TTL_SECONDS")
    world_cup_fixture_refresh_hours: int = Field(default=12, alias="WORLD_CUP_FIXTURE_REFRESH_HOURS")
    odds_api_key: str | None = Field(default=None, alias="ODDS_API_KEY")
    odds_api_base_url: str = Field(default="https://api.the-odds-api.com", alias="ODDS_API_BASE_URL")
    odds_api_regions: str = Field(default="eu", alias="ODDS_API_REGIONS")
    odds_api_bookmakers: str = Field(default="", alias="ODDS_API_BOOKMAKERS")
    odds_api_markets: str = Field(default="h2h,spreads,totals", alias="ODDS_API_MARKETS")
    odds_api_outright_markets: str = Field(default="outrights", alias="ODDS_API_OUTRIGHT_MARKETS")
    odds_api_odds_format: str = Field(default="decimal", alias="ODDS_API_ODDS_FORMAT")
    odds_api_cache_ttl_seconds: int = Field(default=600, alias="ODDS_API_CACHE_TTL_SECONDS")
    odds_api_discovery_path: str = Field(default="tmp/odds_api_world_cup_discovery.json", alias="ODDS_API_DISCOVERY_PATH")
    polymarket_discovery_path: str = Field(default="tmp/polymarket_world_cup_discovery.json", alias="POLYMARKET_DISCOVERY_PATH")
    polymarket_gamma_base_url: str = Field(default="https://gamma-api.polymarket.com", alias="POLYMARKET_GAMMA_BASE_URL")
    polymarket_clob_base_url: str = Field(default="https://clob.polymarket.com", alias="POLYMARKET_CLOB_BASE_URL")
    polymarket_cache_ttl_seconds: int = Field(default=600, alias="POLYMARKET_CACHE_TTL_SECONDS")
    polymarket_refresh_clob_token_limit: int = Field(default=40, alias="POLYMARKET_REFRESH_CLOB_TOKEN_LIMIT")
    polymarket_min_match_confidence: float = Field(default=0.7, alias="POLYMARKET_MIN_MATCH_CONFIDENCE")
    polymarket_min_signal_quality: int = Field(default=40, alias="POLYMARKET_MIN_SIGNAL_QUALITY")
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
