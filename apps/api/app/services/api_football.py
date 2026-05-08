from __future__ import annotations

import logging
import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from typing import Any

import httpx
from openai import AsyncOpenAI

from app.config import get_settings
from app.services.supabase import get_supabase
from app.services.world_cup_teams import aliases_for_team_name, canonical_team_name, normalize_text

logger = logging.getLogger(__name__)

WORLD_CUP_MATCHES_TABLE = "world_cup_matches"
FUZZY_MATCH_THRESHOLD = 0.86


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

    match = find_match_in_matches(message, matches)
    if match:
        return match

    settings = get_settings()
    if not settings.match_detection_fallback_enabled or not _message_seems_match_specific(message):
        return None

    try:
        candidates = await extract_match_candidates_with_llm(message, matches)
    except Exception as exc:
        logger.info("LLM match detection fallback failed: %s", exc)
        return None
    return find_match_from_candidate_teams(candidates, matches)


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


async def extract_match_candidates_with_llm(message: str, matches: list[dict[str, Any]]) -> list[str]:
    settings = get_settings()
    model = settings.match_detection_model or settings.openai_model
    available_teams = sorted({canonical_team_name(team) for match in matches for team in (match.get("home_team"), match.get("away_team")) if team})
    if not available_teams:
        return []

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    completion = await client.chat.completions.create(
        model=model,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": (
                    "Extract World Cup football teams from the user message. "
                    "Return JSON only with keys is_match_specific and teams. "
                    "teams must be an array of 0 to 2 team names chosen from available_teams. "
                    "If the message is vague or about a tournament outright, return is_match_specific=false."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "message": message,
                        "available_teams": available_teams,
                    },
                    ensure_ascii=False,
                ),
            },
        ],
        temperature=0,
    )
    payload = json.loads(completion.choices[0].message.content or "{}")
    if not payload.get("is_match_specific"):
        return []
    teams = payload.get("teams") or []
    if not isinstance(teams, list):
        return []
    valid_teams = set(available_teams)
    return [team for team in (canonical_team_name(str(team)) for team in teams[:2]) if team in valid_teams]


def find_match_from_candidate_teams(candidate_teams: list[str], matches: list[dict[str, Any]]) -> dict[str, Any] | None:
    if len(candidate_teams) < 2:
        return None
    pair = set(candidate_teams[:2])
    pair_matches = [
        match
        for match in matches
        if {canonical_team_name(match.get("home_team") or ""), canonical_team_name(match.get("away_team") or "")} == pair
    ]
    return _best_match(pair_matches)


def compact_match_context(match: dict[str, Any]) -> dict[str, Any]:
    fetched_at = _parse_datetime(match.get("last_fetched_at"))
    return {
        "id": match.get("api_football_fixture_id"),
        "home_team": match.get("home_team"),
        "away_team": match.get("away_team"),
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
    aliases = aliases_for_team_name(team_name)
    return tuple(dict.fromkeys(alias for alias in aliases if alias))


def _mentioned_teams(message: str, matches: list[dict[str, Any]]) -> list[str]:
    normalized_message = normalize_text(message)
    found: list[tuple[int, str]] = []
    seen: set[str] = set()
    aliases_by_team = _aliases_by_team(matches)

    for team, aliases in aliases_by_team.items():
        positions = [_alias_position(normalized_message, alias) for alias in aliases]
        positions = [position for position in positions if position is not None]
        if positions and team not in seen:
            found.append((min(positions), team))
            seen.add(team)

    if len(found) < 2:
        for position, team in _fuzzy_team_matches(normalized_message, aliases_by_team):
            if team not in seen:
                found.append((position, team))
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
            aliases_by_team[team] = tuple(dict.fromkeys((team, *aliases_for_team_name(team), *raw_aliases)))

    return aliases_by_team


def _alias_position(normalized_message: str, alias: str) -> int | None:
    normalized_alias = normalize_text(alias)
    if not normalized_alias:
        return None
    match = re.search(rf"(?<![a-z0-9]){re.escape(normalized_alias)}(?![a-z0-9])", normalized_message)
    return match.start() if match else None


def _fuzzy_team_matches(normalized_message: str, aliases_by_team: dict[str, tuple[str, ...]]) -> list[tuple[int, str]]:
    matches: list[tuple[int, str, float]] = []
    for team, aliases in aliases_by_team.items():
        best: tuple[int, float] | None = None
        for alias in aliases:
            normalized_alias = normalize_text(alias)
            if len(normalized_alias) < 4:
                continue
            candidate = _best_fuzzy_span(normalized_message, normalized_alias)
            if candidate is None:
                continue
            if best is None or candidate[1] > best[1]:
                best = candidate
        if best and best[1] >= FUZZY_MATCH_THRESHOLD:
            matches.append((best[0], team, best[1]))
    return [(position, team) for position, team, _ in sorted(matches, key=lambda item: (-item[2], item[0]))]


def _best_fuzzy_span(normalized_message: str, normalized_alias: str) -> tuple[int, float] | None:
    message_tokens = normalized_message.split()
    alias_tokens = normalized_alias.split()
    if not message_tokens or not alias_tokens:
        return None

    best: tuple[int, float] | None = None
    min_len = max(len(alias_tokens) - 1, 1)
    max_len = min(len(alias_tokens) + 1, len(message_tokens))
    for start in range(len(message_tokens)):
        for size in range(min_len, max_len + 1):
            end = start + size
            if end > len(message_tokens):
                continue
            span = " ".join(message_tokens[start:end])
            ratio = SequenceMatcher(None, span, normalized_alias).ratio()
            if best is None or ratio > best[1]:
                char_position = len(" ".join(message_tokens[:start]))
                best = (char_position, ratio)
    return best


def _looks_like_outright(message: str) -> bool:
    return bool(
        re.search(
            r"\b(?:world cup|mundial|campe[oó]n|campeona|campeon|winner|outright|ganar\s+(?:el\s+)?mundial)\b",
            message,
            re.IGNORECASE,
        )
    )


def _message_seems_match_specific(message: str) -> bool:
    if _looks_like_outright(message):
        return False
    return bool(
        re.search(
            r"\b(?:vs|v|versus|against|contra|partido|match|beat|beats|ganar|gana|vence|vencer|derrota)\b",
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
