from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from app.config import get_settings
from app.services.supabase import get_supabase

logger = logging.getLogger(__name__)

WORLD_CUP_MATCHES_TABLE = "world_cup_matches"

DEFAULT_TEAM_ALIASES: dict[str, tuple[str, ...]] = {
    "Argentina": ("Argentina",),
    "Australia": ("Australia",),
    "Belgium": ("Belgium", "Bélgica", "Belgica"),
    "Brazil": ("Brazil", "Brasil"),
    "Canada": ("Canada", "Canadá"),
    "Colombia": ("Colombia",),
    "Croatia": ("Croatia", "Croacia"),
    "Denmark": ("Denmark", "Dinamarca"),
    "England": ("England", "Inglaterra"),
    "France": ("France", "Francia"),
    "Germany": ("Germany", "Alemania"),
    "Italy": ("Italy", "Italia"),
    "Japan": ("Japan", "Japón", "Japon"),
    "Mexico": ("Mexico", "México", "Mejico", "Méjico"),
    "Morocco": ("Morocco", "Marruecos"),
    "Netherlands": ("Netherlands", "Países Bajos", "Paises Bajos", "Holanda", "Holland"),
    "Portugal": ("Portugal",),
    "Senegal": ("Senegal",),
    "South Korea": ("South Korea", "Korea Republic", "Corea del Sur", "Corea"),
    "Spain": ("Spain", "España", "Espana"),
    "Switzerland": ("Switzerland", "Suiza"),
    "Uruguay": ("Uruguay",),
    "USA": ("USA", "US", "United States", "United States of America", "Estados Unidos", "EEUU", "EE.UU."),
}


@dataclass
class WorldCupCache:
    matches: list[dict[str, Any]] | None = None
    expires_at: datetime | None = None


@dataclass
class APIFootballUsage:
    fixture_requests: int = 0
    last_request_at: datetime | None = None
    last_error: str | None = None


_world_cup_cache = WorldCupCache()
_api_usage = APIFootballUsage()


def get_api_football_usage() -> dict[str, Any]:
    return {
        "fixture_requests": _api_usage.fixture_requests,
        "last_request_at": _api_usage.last_request_at.isoformat() if _api_usage.last_request_at else None,
        "last_error": _api_usage.last_error,
    }


async def fetch_world_cup_fixtures() -> list[dict[str, Any]]:
    settings = get_settings()
    if not settings.api_football_key:
        raise RuntimeError("API_FOOTBALL_KEY is not configured.")

    _api_usage.fixture_requests += 1
    _api_usage.last_request_at = datetime.now(timezone.utc)
    url = f"{settings.api_football_base_url.rstrip('/')}/fixtures"
    params = {"league": settings.world_cup_league_id, "season": settings.world_cup_season}
    headers = {"x-apisports-key": settings.api_football_key}

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(url, params=params, headers=headers)
            response.raise_for_status()
        payload = response.json()
        api_errors = payload.get("errors")
        if api_errors:
            raise RuntimeError(f"API-Football returned errors: {api_errors}")
        _api_usage.last_error = None
        return list(payload.get("response") or [])
    except Exception as exc:
        _api_usage.last_error = str(exc)
        logger.warning("API-Football fixture fetch failed: %s", exc)
        raise


async def upsert_world_cup_fixtures_to_supabase(fixtures: list[dict[str, Any]]) -> int:
    if not fixtures:
        return 0

    now = datetime.now(timezone.utc).isoformat()
    rows = [_fixture_to_row(fixture, now) for fixture in fixtures]
    client = await get_supabase()
    response = await client.table(WORLD_CUP_MATCHES_TABLE).upsert(rows, on_conflict="api_football_fixture_id").execute()
    _clear_world_cup_memory_cache()
    return len(response.data or rows)


async def get_world_cup_matches_from_supabase() -> list[dict[str, Any]]:
    client = await get_supabase()
    response = (
        await client.table(WORLD_CUP_MATCHES_TABLE)
        .select("*")
        .order("kickoff_time", desc=False)
        .execute()
    )
    return list(response.data or [])


async def get_cached_world_cup_matches() -> list[dict[str, Any]]:
    now = datetime.now(timezone.utc)
    if _world_cup_cache.matches is not None and _world_cup_cache.expires_at and _world_cup_cache.expires_at > now:
        return _world_cup_cache.matches

    matches = await get_world_cup_matches_from_supabase()
    settings = get_settings()
    _world_cup_cache.matches = matches
    _world_cup_cache.expires_at = now + timedelta(seconds=settings.world_cup_cache_ttl_seconds)
    return matches


async def refresh_world_cup_fixtures_if_needed(force: bool = False) -> dict[str, Any]:
    matches = await get_world_cup_matches_from_supabase()
    settings = get_settings()
    stale_before = datetime.now(timezone.utc) - timedelta(hours=settings.world_cup_fixture_refresh_hours)
    newest_fetch = _newest_fetch_time(matches)

    if not force and newest_fetch and newest_fetch > stale_before:
        return {
            "refreshed": False,
            "reason": "cached fixtures are still fresh",
            "matches": len(matches),
            "last_fetched_at": newest_fetch.isoformat(),
            "usage": get_api_football_usage(),
        }

    fixtures = await fetch_world_cup_fixtures()
    upserted = await upsert_world_cup_fixtures_to_supabase(fixtures)
    return {
        "refreshed": True,
        "matches": upserted,
        "last_fetched_at": datetime.now(timezone.utc).isoformat(),
        "usage": get_api_football_usage(),
    }


async def find_match_from_message(message: str) -> dict[str, Any] | None:
    try:
        matches = await get_cached_world_cup_matches()
    except Exception as exc:
        logger.info("World Cup match cache unavailable for chat context: %s", exc)
        return None
    return find_match_in_matches(message, matches)


async def build_match_context_for_chat(message: str) -> dict[str, Any] | None:
    match = await find_match_from_message(message)
    if not match:
        return None
    return compact_match_context(match)


def find_match_in_matches(message: str, matches: list[dict[str, Any]]) -> dict[str, Any] | None:
    mentioned = _mentioned_teams(message, matches)
    if len(mentioned) >= 2:
        pair = set(mentioned[:2])
        pair_matches = [
            match
            for match in matches
            if {match.get("home_team"), match.get("away_team")} == pair
        ]
        return _best_match(pair_matches)

    if len(mentioned) == 1 and not _looks_like_outright(message):
        team = mentioned[0]
        team_matches = [
            match
            for match in matches
            if team in {match.get("home_team"), match.get("away_team")}
        ]
        return _best_match(team_matches)

    return None


def compact_match_context(match: dict[str, Any]) -> dict[str, Any]:
    fetched_at = _parse_datetime(match.get("last_fetched_at"))
    return {
        "match": f"{match.get('home_team')} vs {match.get('away_team')}",
        "kickoff_time": match.get("kickoff_time"),
        "stage": match.get("stage"),
        "status": match.get("status"),
        "score": _format_score(match),
        "venue": match.get("venue"),
        "last_fetched_at": fetched_at.isoformat() if fetched_at else match.get("last_fetched_at"),
        "freshness_minutes": _minutes_since(fetched_at),
    }


def format_match_context_block(context: dict[str, Any] | None) -> str | None:
    if not context:
        return None

    freshness = "unknown"
    if context.get("freshness_minutes") is not None:
        freshness = f"{context['freshness_minutes']} minutes ago"

    lines = [
        "MATCH CONTEXT:",
        f"- Match: {context.get('match')}",
        f"- Date: {context.get('kickoff_time') or 'unknown'}",
        f"- Stage: {context.get('stage') or 'unknown'}",
        f"- Status: {context.get('status') or 'unknown'}",
    ]
    if context.get("score"):
        lines.append(f"- Score: {context['score']}")
    if context.get("venue"):
        lines.append(f"- Venue: {context['venue']}")
    lines.append(f"- Data freshness: fixtures updated {freshness}")
    return "\n".join(lines)


def _fixture_to_row(fixture: dict[str, Any], fetched_at: str) -> dict[str, Any]:
    fixture_meta = fixture.get("fixture") or {}
    teams = fixture.get("teams") or {}
    goals = fixture.get("goals") or {}
    league = fixture.get("league") or {}
    home_team = ((teams.get("home") or {}).get("name") or "").strip()
    away_team = ((teams.get("away") or {}).get("name") or "").strip()

    return {
        "api_football_fixture_id": fixture_meta.get("id"),
        "home_team": home_team,
        "away_team": away_team,
        "home_team_aliases": list(_aliases_for_team(home_team)),
        "away_team_aliases": list(_aliases_for_team(away_team)),
        "kickoff_time": fixture_meta.get("date"),
        "venue": (fixture_meta.get("venue") or {}).get("name"),
        "stage": league.get("round"),
        "status": (fixture_meta.get("status") or {}).get("long"),
        "home_score": goals.get("home"),
        "away_score": goals.get("away"),
        "raw_payload": fixture,
        "last_fetched_at": fetched_at,
        "updated_at": fetched_at,
    }


def _aliases_for_team(team_name: str) -> tuple[str, ...]:
    configured = _default_aliases_for_team(team_name)
    aliases = (team_name, *configured)
    return tuple(dict.fromkeys(alias for alias in aliases if alias))


def _default_aliases_for_team(team_name: str) -> tuple[str, ...]:
    if team_name in DEFAULT_TEAM_ALIASES:
        return DEFAULT_TEAM_ALIASES[team_name]

    normalized_team = _normalize_text(team_name)
    for canonical, aliases in DEFAULT_TEAM_ALIASES.items():
        if normalized_team in {_normalize_text(canonical), *(_normalize_text(alias) for alias in aliases)}:
            return (canonical, *aliases)
    return ()


def _mentioned_teams(message: str, matches: list[dict[str, Any]]) -> list[str]:
    normalized_message = _normalize_text(message)
    found: list[tuple[int, str]] = []
    seen: set[str] = set()
    aliases_by_team = _aliases_by_team(matches)

    for team, aliases in aliases_by_team.items():
        positions = [_alias_position(normalized_message, alias) for alias in aliases]
        positions = [position for position in positions if position is not None]
        if positions and team not in seen:
            found.append((min(positions), team))
            seen.add(team)

    return [team for _, team in sorted(found)]


def _aliases_by_team(matches: list[dict[str, Any]]) -> dict[str, tuple[str, ...]]:
    aliases_by_team: dict[str, tuple[str, ...]] = {}
    for match in matches:
        for team_key, aliases_key in (("home_team", "home_team_aliases"), ("away_team", "away_team_aliases")):
            team = match.get(team_key)
            if not team:
                continue
            raw_aliases = match.get(aliases_key) or []
            aliases_by_team[team] = tuple(dict.fromkeys((team, *_default_aliases_for_team(team), *raw_aliases)))

    return aliases_by_team


def _alias_position(normalized_message: str, alias: str) -> int | None:
    normalized_alias = _normalize_text(alias)
    if not normalized_alias:
        return None
    match = re.search(rf"(?<![a-z0-9]){re.escape(normalized_alias)}(?![a-z0-9])", normalized_message)
    return match.start() if match else None


def _normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)
    value = "".join(char for char in value if not unicodedata.combining(char))
    value = value.lower().replace(".", " ")
    return " ".join(re.sub(r"[^a-z0-9]+", " ", value).split())


def _looks_like_outright(message: str) -> bool:
    return bool(
        re.search(
            r"\b(?:world cup|mundial|campe[oó]n|campeona|campeon|winner|outright|ganar\s+(?:el\s+)?mundial)\b",
            message,
            re.IGNORECASE,
        )
    )


def _best_match(matches: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not matches:
        return None
    now = datetime.now(timezone.utc)

    def score(match: dict[str, Any]) -> tuple[int, float]:
        kickoff = _parse_datetime(match.get("kickoff_time"))
        if kickoff is None:
            return (2, float("inf"))
        if kickoff >= now:
            return (0, abs((kickoff - now).total_seconds()))
        return (1, abs((now - kickoff).total_seconds()))

    return min(matches, key=score)


def _newest_fetch_time(matches: list[dict[str, Any]]) -> datetime | None:
    fetched_times = [_parse_datetime(match.get("last_fetched_at")) for match in matches]
    fetched_times = [value for value in fetched_times if value is not None]
    return max(fetched_times) if fetched_times else None


def _parse_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str) and value:
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _minutes_since(value: datetime | None) -> int | None:
    if value is None:
        return None
    return max(int((datetime.now(timezone.utc) - value).total_seconds() // 60), 0)


def _format_score(match: dict[str, Any]) -> str | None:
    home_score = match.get("home_score")
    away_score = match.get("away_score")
    if home_score is None or away_score is None:
        return None
    return f"{home_score}-{away_score}"


def _clear_world_cup_memory_cache() -> None:
    _world_cup_cache.matches = None
    _world_cup_cache.expires_at = None
