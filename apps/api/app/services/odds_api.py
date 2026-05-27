from __future__ import annotations

import json
import logging
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import mean, median
from typing import Any

import httpx

from app.config import get_settings
from app.services.bet_parser import ParsedBet, parse_bet_message
from app.services.supabase import get_supabase
from app.services.world_cup_teams import canonical_team_name, normalize_text

logger = logging.getLogger(__name__)

BOOKMAKER_EVENTS_TABLE = "bookmaker_events"
BOOKMAKER_ODDS_TABLE = "bookmaker_odds"
BOOKMAKER_ODDS_SNAPSHOTS_TABLE = "bookmaker_odds_snapshots"
BOOKMAKER_CONSENSUS_TABLE = "bookmaker_market_consensus"

WORLD_CUP_SPORT_KEY = "soccer_fifa_world_cup"
WORLD_CUP_WINNER_SPORT_KEY = "soccer_fifa_world_cup_winner"
SUPPORTED_FEATURED_MARKETS = {"h2h", "spreads", "totals", "outrights"}


@dataclass
class OddsCache:
    events: list[dict[str, Any]] | None = None
    consensus: list[dict[str, Any]] | None = None
    expires_at: datetime | None = None
    source: str | None = None


@dataclass
class OddsAPIUsage:
    requests: int = 0
    last_request_at: datetime | None = None
    last_usage_headers: dict[str, str | None] | None = None
    last_error: str | None = None


_odds_cache = OddsCache()
_odds_usage = OddsAPIUsage()


def clear_odds_memory_cache() -> None:
    _odds_cache.events = None
    _odds_cache.consensus = None
    _odds_cache.expires_at = None
    _odds_cache.source = None


def get_odds_api_usage() -> dict[str, Any]:
    return {
        "requests": _odds_usage.requests,
        "last_request_at": _odds_usage.last_request_at.isoformat() if _odds_usage.last_request_at else None,
        "last_usage_headers": _odds_usage.last_usage_headers,
        "last_error": _odds_usage.last_error,
    }


async def refresh_bookmaker_events_from_api() -> dict[str, Any]:
    payload = await _api_get(f"/v4/sports/{WORLD_CUP_SPORT_KEY}/events", {"dateFormat": "iso"})
    events = [normalize_event(event) for event in collection(payload)]
    upserted = await persist_bookmaker_events(events)
    return {
        "refreshed": True,
        "events": upserted,
        "last_fetched_at": datetime.now(timezone.utc).isoformat(),
        "usage": get_odds_api_usage(),
    }


async def refresh_featured_bookmaker_odds_from_api() -> dict[str, Any]:
    settings = get_settings()
    fetched_at = datetime.now(timezone.utc).isoformat()
    events_payload = await _api_get(f"/v4/sports/{WORLD_CUP_SPORT_KEY}/events", {"dateFormat": "iso"})
    match_events = [normalize_event(event) for event in collection(events_payload)]

    featured_payload = await _api_get(
        f"/v4/sports/{WORLD_CUP_SPORT_KEY}/odds",
        {
            "dateFormat": "iso",
            **_odds_source_params(),
            "markets": settings.odds_api_markets,
            "oddsFormat": settings.odds_api_odds_format,
        },
    )
    outright_payload = await _api_get(
        f"/v4/sports/{WORLD_CUP_WINNER_SPORT_KEY}/odds",
        {
            "dateFormat": "iso",
            **_odds_source_params(),
            "markets": settings.odds_api_outright_markets,
            "oddsFormat": settings.odds_api_odds_format,
        },
    )

    featured_events = collection(featured_payload)
    outright_events = collection(outright_payload)
    events = merge_event_metadata(match_events, [normalize_event(event) for event in featured_events + outright_events])
    rows = flatten_odds(featured_events + outright_events, fetched_at=fetched_at)
    consensus = build_consensus(rows, fetched_at=fetched_at)

    event_count = await persist_bookmaker_events(events)
    odds_count = await persist_bookmaker_odds(rows)
    consensus_count = await persist_bookmaker_consensus(consensus)
    clear_odds_memory_cache()

    return {
        "refreshed": True,
        "events": event_count,
        "odds_rows": odds_count,
        "consensus_rows": consensus_count,
        "last_fetched_at": fetched_at,
        "usage": get_odds_api_usage(),
    }


async def seed_bookmaker_odds_from_discovery_file() -> dict[str, Any]:
    payload = load_discovery_payload()
    fetched_at = payload.get("generated_at") or datetime.now(timezone.utc).isoformat()
    events = merge_event_metadata(
        [normalize_event(event.get("raw") or event) for event in payload.get("events", [])],
        [normalize_event(event) for event in payload.get("featured_odds_raw", []) + payload.get("outright_odds_raw", [])],
    )
    odds_rows = normalize_discovery_rows(payload.get("featured_odds_rows", []) + payload.get("outright_odds_rows", []), fetched_at)
    consensus = normalize_discovery_consensus(
        payload.get("featured_consensus", []) + payload.get("outright_consensus", []),
        fetched_at,
    )

    event_count = await persist_bookmaker_events(events)
    odds_count = await persist_bookmaker_odds(odds_rows)
    consensus_count = await persist_bookmaker_consensus(consensus)
    clear_odds_memory_cache()

    return {
        "seeded": True,
        "source": "discovery_json",
        "events": event_count,
        "odds_rows": odds_count,
        "consensus_rows": consensus_count,
        "generated_at": fetched_at,
    }


async def get_compact_odds_matches(limit: int = 50) -> list[dict[str, Any]]:
    events, consensus = await get_cached_bookmaker_data()
    by_event: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in consensus:
        by_event[str(row.get("odds_api_event_id") or row.get("event_id") or "")].append(row)

    matches = []
    for event in sorted(events, key=lambda item: item.get("commence_time") or ""):
        event_id = str(event.get("odds_api_event_id") or event.get("event_id") or event.get("id") or "")
        if not event_id:
            continue
        markets = by_event.get(event_id, [])
        if not markets:
            continue
        h2h = sorted(
            [row for row in markets if row.get("market_key") == "h2h"],
            key=lambda row: row.get("no_vig_probability") or row.get("median_no_vig_probability") or 0,
            reverse=True,
        )
        matches.append(
            {
                "odds_api_event_id": event_id,
                "sport_key": event.get("sport_key"),
                "home_team": event.get("home_team"),
                "away_team": event.get("away_team"),
                "match": _event_name(event),
                "commence_time": event.get("commence_time"),
                "last_fetched_at": newest_fetched_at(markets),
                "h2h": [compact_consensus_row(row) for row in h2h],
                "featured_markets": compact_featured_markets(markets),
            }
        )
        if len(matches) >= limit:
            break
    return matches


async def analyze_user_odds(message: str, odds: float | None = None) -> dict[str, Any]:
    parsed_bet = parse_bet_message(message)
    if odds is not None:
        parsed_bet = parsed_bet.model_copy(update={"odds": odds, "implied_probability": round(1 / odds, 4)})
    context = await build_bookmaker_context_for_chat(message, parsed_bet=parsed_bet)
    return {
        "parsed_bet": parsed_bet.model_dump(),
        "bookmaker_context": context,
        "analysis": summarize_value(parsed_bet, context),
    }


async def build_bookmaker_context_for_chat(
    message: str,
    parsed_bet: ParsedBet | None = None,
    match_context: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    parsed = parsed_bet or parse_bet_message(message)
    if not parsed.teams and is_odds_discovery_request(message):
        matches = await get_compact_odds_matches(limit=6)
        if not matches:
            return {
                "matched": False,
                "mode": "discovery_shortlist",
                "note": "No cached bookmaker matches are available for a guided shortlist yet.",
            }
        return {
            "matched": True,
            "mode": "discovery_shortlist",
            "note": "Use these cached in-app bookmaker markets to guide the user without asking them to leave the app.",
            "matches": [compact_discovery_match(match) for match in matches],
        }

    if parsed.market_type == "Tournament outright":
        market_key = "outrights"
    elif parsed.market_type in {"Match winner", None}:
        market_key = "h2h"
    elif parsed.market_type == "Over goals":
        market_key = "totals"
    elif parsed.market_type == "Under goals":
        market_key = "totals"
    elif parsed.market_type == "Handicap":
        market_key = "spreads"
    else:
        return None

    events, consensus = await get_cached_bookmaker_data()
    event = find_relevant_event(parsed, events, match_context, market_key)
    if not event:
        return {
            "matched": False,
            "market_key": market_key,
            "teams": parsed.teams,
            "note": "No cached bookmaker event matched this request.",
        }

    event_id = str(event.get("odds_api_event_id") or event.get("event_id") or event.get("id") or "")
    candidate_rows = [
        row
        for row in consensus
        if str(row.get("odds_api_event_id") or row.get("event_id") or "") == event_id
        and row.get("market_key") == market_key
    ]
    row = select_consensus_row(parsed, candidate_rows, market_key)
    if not row:
        return {
            "matched": False,
            "market_key": market_key,
            "event": _event_name(event),
            "teams": parsed.teams,
            "note": "Cached bookmaker odds exist for the event, but not for the requested market/selection.",
            "last_fetched_at": newest_fetched_at(candidate_rows),
        }

    return {
        "matched": True,
        "event": _event_name(event),
        "odds_api_event_id": event_id,
        "market_key": row.get("market_key"),
        "outcome_name": row.get("outcome_name"),
        "point": row.get("point"),
        "user_odds": parsed.odds,
        "user_implied_probability": parsed.implied_probability,
        "best_price": as_float(row.get("best_price")),
        "best_bookmaker_title": row.get("best_bookmaker_title"),
        "median_price": as_float(row.get("median_price")),
        "min_price": as_float(row.get("min_price")),
        "max_price": as_float(row.get("max_price")),
        "consensus_probability": as_float(row.get("no_vig_probability") or row.get("median_no_vig_probability")),
        "bookmaker_count": int(row.get("bookmaker_count") or 0),
        "last_fetched_at": row.get("fetched_at"),
        "value_edge": value_edge(parsed.odds, row),
        "price_quality": price_quality(parsed.odds, row),
    }


def format_bookmaker_context_block(context: dict[str, Any] | None) -> str | None:
    if not context:
        return None
    if context.get("mode") == "discovery_shortlist":
        lines = [
            "BOOKMAKER DISCOVERY CONTEXT:",
            f"- Matched: {str(bool(context.get('matched'))).lower()}",
            f"- Note: {context.get('note') or 'Cached in-app bookmaker discovery context.'}",
        ]
        for index, match in enumerate(context.get("matches") or [], start=1):
            lines.extend(
                [
                    f"- Option {index}: {match.get('match')}",
                    f"  Kickoff: {match.get('commence_time') or 'unknown'}",
                    f"  Favorite: {match.get('favorite') or 'unknown'}",
                    f"  H2H prices: {match.get('h2h_summary') or 'unknown'}",
                ]
            )
            if match.get("totals_summary"):
                lines.append(f"  Totals: {match['totals_summary']}")
            if match.get("spreads_summary"):
                lines.append(f"  Handicaps: {match['spreads_summary']}")
        return "\n".join(lines)

    if not context.get("matched"):
        return "\n".join(
            [
                "BOOKMAKER CONTEXT:",
                "- Matched: false",
                f"- Market: {context.get('market_key') or 'unknown'}",
                f"- Note: {context.get('note') or 'No useful cached bookmaker odds were found.'}",
            ]
        )

    lines = [
        "BOOKMAKER CONTEXT:",
        "- Matched: true",
        f"- Event: {context.get('event')}",
        f"- Market: {context.get('market_key')}",
        f"- Selection: {context.get('outcome_name')}",
    ]
    if context.get("point") is not None:
        lines.append(f"- Line: {context.get('point')}")
    if context.get("user_odds"):
        lines.append(f"- User odds: {context['user_odds']:.2f}")
    if context.get("user_implied_probability") is not None:
        lines.append(f"- User implied probability: {context['user_implied_probability'] * 100:.1f}%")
    if context.get("consensus_probability") is not None:
        lines.append(f"- Bookmaker no-vig consensus probability: {context['consensus_probability'] * 100:.1f}%")
    if context.get("median_price") is not None:
        lines.append(f"- Median bookmaker price: {context['median_price']:.2f}")
    if context.get("best_price") is not None:
        lines.append(
            f"- Best cached price: {context['best_price']:.2f}"
            + (f" at {context['best_bookmaker_title']}" if context.get("best_bookmaker_title") else "")
        )
    if context.get("price_quality"):
        lines.append(f"- Price quality vs best cached price: {context['price_quality']}")
    if context.get("value_edge") is not None:
        lines.append(f"- User price edge vs consensus: {context['value_edge'] * 100:.1f} percentage points")
    lines.append(f"- Bookmakers in consensus: {context.get('bookmaker_count') or 0}")
    lines.append(f"- Last fetched: {context.get('last_fetched_at') or 'unknown'}")
    return "\n".join(lines)


def is_odds_discovery_request(message: str) -> bool:
    lowered = message.lower()
    patterns = [
        r"\brecommend(?:ation|ations)?\b",
        r"\bsuggest(?:ion|ions)?\b",
        r"\bwhat\s+should\s+i\s+bet\b",
        r"\bgive\s+me\s+(?:some\s+)?(?:bets?|picks?|plays?)\b",
        r"\bshortlist\b",
        r"\bbuild\s+me\s+(?:a\s+)?(?:slip|ticket|shortlist)\b",
        r"\bi\s+have\s+(?:€|\$|£)?\s*\d+",
        r"\btengo\s+(?:€|\$|£)?\s*\d+",
        r"\brecomienda\b|\brecomendaciones\b",
        r"\bsugerencias\b|\bsugi[eé]reme\b",
        r"\bqu[eé]\s+apuesto\b",
        r"\bdame\s+(?:algunas\s+)?(?:apuestas|picks|jugadas)\b",
    ]
    return any(re.search(pattern, lowered, re.IGNORECASE) for pattern in patterns)


def compact_discovery_match(match: dict[str, Any]) -> dict[str, Any]:
    h2h = match.get("h2h") or []
    favorite = max(
        h2h,
        key=lambda row: as_float(row.get("no_vig_probability")) or 0,
        default=None,
    )
    return {
        "match": match.get("match"),
        "commence_time": match.get("commence_time"),
        "favorite": _format_compact_row(favorite),
        "h2h_summary": "; ".join(_format_compact_row(row) for row in h2h[:3] if row),
        "totals_summary": "; ".join(
            _format_compact_row(row)
            for row in (match.get("featured_markets") or {}).get("totals", [])[:4]
            if row
        ),
        "spreads_summary": "; ".join(
            _format_compact_row(row)
            for row in (match.get("featured_markets") or {}).get("spreads", [])[:4]
            if row
        ),
    }


def _format_compact_row(row: dict[str, Any] | None) -> str:
    if not row:
        return ""
    outcome = row.get("outcome_name") or "unknown"
    point = row.get("point")
    price = as_float(row.get("best_price"))
    probability = as_float(row.get("no_vig_probability"))
    label = str(outcome)
    if point is not None:
        label = f"{label} {point:g}"
    if price is not None:
        label = f"{label} @ {price:.2f}"
    if probability is not None:
        label = f"{label} ({probability * 100:.1f}% fair)"
    return label


async def get_cached_bookmaker_data() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    now = datetime.now(timezone.utc)
    if _odds_cache.events is not None and _odds_cache.consensus is not None and _odds_cache.expires_at and _odds_cache.expires_at > now:
        return _odds_cache.events, _odds_cache.consensus

    settings = get_settings()
    try:
        events, consensus = await get_bookmaker_data_from_supabase()
        source = "supabase"
        if not events or not consensus:
            raise RuntimeError("Bookmaker odds cache is empty.")
    except Exception as exc:
        logger.info("Bookmaker odds Supabase cache unavailable, falling back to discovery JSON: %s", exc)
        events, consensus = get_bookmaker_data_from_discovery_file()
        source = "discovery_json"

    _odds_cache.events = events
    _odds_cache.consensus = consensus
    _odds_cache.expires_at = now + timedelta(seconds=settings.odds_api_cache_ttl_seconds)
    _odds_cache.source = source
    return events, consensus


async def get_bookmaker_data_from_supabase() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    client = await get_supabase()
    events_response = await client.table(BOOKMAKER_EVENTS_TABLE).select("*").order("commence_time", desc=False).execute()
    consensus_response = await client.table(BOOKMAKER_CONSENSUS_TABLE).select("*").execute()
    return list(events_response.data or []), list(consensus_response.data or [])


def get_bookmaker_data_from_discovery_file() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    payload = load_discovery_payload()
    generated_at = payload.get("generated_at") or datetime.now(timezone.utc).isoformat()
    events = [normalize_event(event.get("raw") or event) for event in payload.get("events", [])]
    featured_events = [normalize_event(event) for event in payload.get("featured_odds_raw", [])]
    outright_events = [normalize_event(event) for event in payload.get("outright_odds_raw", [])]
    consensus = normalize_discovery_consensus(
        payload.get("featured_consensus", []) + payload.get("outright_consensus", []),
        generated_at,
    )
    return merge_event_metadata(events, featured_events + outright_events), consensus


def load_discovery_payload() -> dict[str, Any]:
    path = _resolve_discovery_path(get_settings().odds_api_discovery_path)
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_event(event: dict[str, Any]) -> dict[str, Any]:
    event_id = event.get("odds_api_event_id") or event.get("event_id") or event.get("id")
    return {
        "odds_api_event_id": event_id,
        "sport_key": event.get("sport_key"),
        "sport_title": event.get("sport_title"),
        "home_team": event.get("home_team"),
        "away_team": event.get("away_team"),
        "commence_time": event.get("commence_time"),
        "matchmind_match_key": build_match_key(event.get("home_team"), event.get("away_team"), event.get("commence_time")),
        "raw_payload": event.get("raw") or event,
        "last_fetched_at": datetime.now(timezone.utc).isoformat(),
    }


def merge_event_metadata(primary: list[dict[str, Any]], secondary: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for event in [*primary, *secondary]:
        event_id = str(event.get("odds_api_event_id") or event.get("event_id") or event.get("id") or "")
        if event_id and event_id not in merged:
            merged[event_id] = normalize_event(event)
        elif event_id:
            merged[event_id] = {**merged[event_id], **{key: value for key, value in normalize_event(event).items() if value is not None}}
    return list(merged.values())


def flatten_odds(events: list[dict[str, Any]], fetched_at: str | None = None) -> list[dict[str, Any]]:
    fetched_at = fetched_at or datetime.now(timezone.utc).isoformat()
    rows: list[dict[str, Any]] = []
    for event in events:
        event_id = event.get("id") or event.get("odds_api_event_id")
        for bookmaker in event.get("bookmakers") or []:
            if not isinstance(bookmaker, dict):
                continue
            for market in bookmaker.get("markets") or []:
                if not isinstance(market, dict):
                    continue
                for outcome in market.get("outcomes") or []:
                    if not isinstance(outcome, dict):
                        continue
                    price = as_float(outcome.get("price"))
                    if price is None or price <= 1:
                        continue
                    rows.append(
                        {
                            "odds_api_event_id": event_id,
                            "sport_key": event.get("sport_key"),
                            "commence_time": event.get("commence_time"),
                            "home_team": event.get("home_team"),
                            "away_team": event.get("away_team"),
                            "bookmaker_key": bookmaker.get("key"),
                            "bookmaker_title": bookmaker.get("title"),
                            "bookmaker_last_update": bookmaker.get("last_update"),
                            "market_key": market.get("key"),
                            "line_key": market_line_key(str(market.get("key") or ""), outcome),
                            "market_last_update": market.get("last_update"),
                            "outcome_name": outcome.get("name"),
                            "outcome_team": canonical_team_name(outcome.get("name") or "") if outcome.get("name") not in {"Draw", "Over", "Under"} else None,
                            "price": price,
                            "point": as_float(outcome.get("point")),
                            "odds_format": "decimal",
                            "raw_payload": outcome,
                            "fetched_at": fetched_at,
                        }
                    )
    return rows


def normalize_discovery_rows(rows: list[dict[str, Any]], fetched_at: str) -> list[dict[str, Any]]:
    normalized = []
    for row in rows:
        normalized.append(
            {
                "odds_api_event_id": row.get("odds_api_event_id") or row.get("event_id"),
                "sport_key": row.get("sport_key"),
                "commence_time": row.get("commence_time"),
                "home_team": row.get("home_team"),
                "away_team": row.get("away_team"),
                "bookmaker_key": row.get("bookmaker_key"),
                "bookmaker_title": row.get("bookmaker_title"),
                "bookmaker_last_update": row.get("bookmaker_last_update"),
                "market_key": row.get("market_key"),
                "line_key": row.get("line_key") or market_line_key(str(row.get("market_key") or ""), row),
                "market_last_update": row.get("market_last_update"),
                "outcome_name": row.get("outcome_name"),
                "outcome_team": canonical_team_name(row.get("outcome_name") or "") if row.get("outcome_name") not in {"Draw", "Over", "Under"} else None,
                "price": as_float(row.get("price")),
                "point": as_float(row.get("point")),
                "odds_format": "decimal",
                "raw_payload": row,
                "fetched_at": fetched_at,
            }
        )
    return [row for row in normalized if row.get("odds_api_event_id") and row.get("price")]


def build_consensus(rows: list[dict[str, Any]], fetched_at: str | None = None) -> list[dict[str, Any]]:
    fetched_at = fetched_at or datetime.now(timezone.utc).isoformat()
    by_bookmaker_line: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_bookmaker_line[
            (
                row.get("odds_api_event_id"),
                row.get("bookmaker_key"),
                row.get("market_key"),
                pricing_line_key(row),
            )
        ].append(row)

    no_vig_by_identity: dict[tuple[Any, ...], float] = {}
    for items in by_bookmaker_line.values():
        raw_probabilities = [1 / item["price"] for item in items if item.get("price")]
        overround = sum(raw_probabilities)
        if overround <= 0:
            continue
        for item in items:
            no_vig_by_identity[row_identity(item)] = round((1 / item["price"]) / overround, 6)

    grouped: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(row.get("odds_api_event_id"), row.get("market_key"), row.get("outcome_name"), row.get("point"))].append(row)

    consensus = []
    for (event_id, market_key, outcome_name, point), items in grouped.items():
        prices = [item["price"] for item in items if item.get("price")]
        no_vig_values = [no_vig_by_identity[key] for item in items if (key := row_identity(item)) in no_vig_by_identity]
        if not prices:
            continue
        best = max(items, key=lambda item: item.get("price") or 0)
        consensus.append(
            {
                "odds_api_event_id": event_id,
                "market_key": market_key,
                "line_key": market_line_key(str(market_key or ""), {"point": point}),
                "outcome_name": outcome_name,
                "outcome_team": canonical_team_name(outcome_name or "") if outcome_name not in {"Draw", "Over", "Under"} else None,
                "point": point,
                "best_price": best.get("price"),
                "best_bookmaker_key": best.get("bookmaker_key"),
                "best_bookmaker_title": best.get("bookmaker_title"),
                "median_price": round(median(prices), 4),
                "mean_price": round(mean(prices), 4),
                "min_price": min(prices),
                "max_price": max(prices),
                "no_vig_probability": round(median(no_vig_values), 6) if no_vig_values else None,
                "bookmaker_count": len({item.get("bookmaker_key") for item in items if item.get("bookmaker_key")}),
                "stale_bookmaker_count": 0,
                "fetched_at": fetched_at,
            }
        )
    return consensus


def normalize_discovery_consensus(rows: list[dict[str, Any]], fetched_at: str) -> list[dict[str, Any]]:
    normalized = []
    for row in rows:
        outcome_name = row.get("outcome_name")
        normalized.append(
            {
                "odds_api_event_id": row.get("odds_api_event_id") or row.get("event_id"),
                "market_key": row.get("market_key"),
                "line_key": row.get("line_key") or market_line_key(str(row.get("market_key") or ""), row),
                "outcome_name": outcome_name,
                "outcome_team": canonical_team_name(outcome_name or "") if outcome_name not in {"Draw", "Over", "Under"} else None,
                "point": as_float(row.get("point")),
                "best_price": as_float(row.get("best_price")),
                "best_bookmaker_key": row.get("best_bookmaker_key"),
                "best_bookmaker_title": row.get("best_bookmaker_title"),
                "median_price": as_float(row.get("median_price")),
                "mean_price": as_float(row.get("mean_price")),
                "min_price": as_float(row.get("min_price")),
                "max_price": as_float(row.get("max_price")),
                "no_vig_probability": as_float(row.get("no_vig_probability") or row.get("median_no_vig_probability")),
                "bookmaker_count": int(row.get("bookmaker_count") or 0),
                "stale_bookmaker_count": int(row.get("stale_bookmaker_count") or 0),
                "fetched_at": row.get("fetched_at") or fetched_at,
            }
        )
    return [row for row in normalized if row.get("odds_api_event_id") and row.get("market_key")]


async def persist_bookmaker_events(events: list[dict[str, Any]]) -> int:
    rows = [bookmaker_event_to_row(event) for event in events if event.get("odds_api_event_id")]
    if not rows:
        return 0
    client = await get_supabase()
    response = await client.table(BOOKMAKER_EVENTS_TABLE).upsert(rows, on_conflict="odds_api_event_id").execute()
    return len(response.data or rows)


async def persist_bookmaker_odds(rows: list[dict[str, Any]]) -> int:
    odds_rows = [bookmaker_odds_to_row(row) for row in rows if row.get("odds_api_event_id") and row.get("price")]
    if not odds_rows:
        return 0
    client = await get_supabase()
    await client.table(BOOKMAKER_ODDS_TABLE).upsert(
        odds_rows,
        on_conflict="odds_api_event_id,bookmaker_key,market_key,outcome_name,line_key",
    ).execute()
    await client.table(BOOKMAKER_ODDS_SNAPSHOTS_TABLE).insert(odds_rows).execute()
    await prune_old_bookmaker_odds_snapshots(client)
    return len(odds_rows)


async def prune_old_bookmaker_odds_snapshots(client: Any | None = None) -> None:
    settings = get_settings()
    if settings.odds_snapshot_retention_days <= 0:
        return

    client = client or await get_supabase()
    cutoff = bookmaker_snapshot_retention_cutoff(settings.odds_snapshot_retention_days)
    await client.table(BOOKMAKER_ODDS_SNAPSHOTS_TABLE).delete().lt("fetched_at", cutoff).execute()


def bookmaker_snapshot_retention_cutoff(retention_days: int, now: datetime | None = None) -> str:
    reference_time = now or datetime.now(timezone.utc)
    return (reference_time - timedelta(days=retention_days)).isoformat()


async def persist_bookmaker_consensus(rows: list[dict[str, Any]]) -> int:
    consensus_rows = [bookmaker_consensus_to_row(row) for row in rows if row.get("odds_api_event_id") and row.get("market_key")]
    if not consensus_rows:
        return 0
    client = await get_supabase()
    await client.table(BOOKMAKER_CONSENSUS_TABLE).upsert(
        consensus_rows,
        on_conflict="odds_api_event_id,market_key,outcome_name,line_key",
    ).execute()
    return len(consensus_rows)


def bookmaker_event_to_row(event: dict[str, Any]) -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    return {
        "odds_api_event_id": event.get("odds_api_event_id"),
        "api_football_fixture_id": event.get("api_football_fixture_id"),
        "sport_key": event.get("sport_key"),
        "sport_title": event.get("sport_title"),
        "home_team": event.get("home_team"),
        "away_team": event.get("away_team"),
        "commence_time": event.get("commence_time"),
        "matchmind_match_key": event.get("matchmind_match_key") or build_match_key(event.get("home_team"), event.get("away_team"), event.get("commence_time")),
        "raw_payload": event.get("raw_payload") or event,
        "last_fetched_at": event.get("last_fetched_at") or now,
    }


def bookmaker_odds_to_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "odds_api_event_id": row.get("odds_api_event_id"),
        "bookmaker_key": row.get("bookmaker_key"),
        "bookmaker_title": row.get("bookmaker_title"),
        "market_key": row.get("market_key"),
        "line_key": row.get("line_key") or market_line_key(str(row.get("market_key") or ""), row),
        "outcome_name": row.get("outcome_name"),
        "outcome_team": row.get("outcome_team"),
        "price": row.get("price"),
        "point": row.get("point"),
        "odds_format": row.get("odds_format") or "decimal",
        "bookmaker_last_update": row.get("bookmaker_last_update"),
        "fetched_at": row.get("fetched_at"),
        "raw_payload": row.get("raw_payload") or row,
    }


def bookmaker_consensus_to_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "odds_api_event_id": row.get("odds_api_event_id"),
        "market_key": row.get("market_key"),
        "line_key": row.get("line_key") or market_line_key(str(row.get("market_key") or ""), row),
        "outcome_name": row.get("outcome_name"),
        "outcome_team": row.get("outcome_team"),
        "point": row.get("point"),
        "best_price": row.get("best_price"),
        "best_bookmaker_key": row.get("best_bookmaker_key"),
        "best_bookmaker_title": row.get("best_bookmaker_title"),
        "median_price": row.get("median_price"),
        "mean_price": row.get("mean_price"),
        "min_price": row.get("min_price"),
        "max_price": row.get("max_price"),
        "no_vig_probability": row.get("no_vig_probability"),
        "bookmaker_count": row.get("bookmaker_count") or 0,
        "stale_bookmaker_count": row.get("stale_bookmaker_count") or 0,
        "fetched_at": row.get("fetched_at"),
    }


def find_relevant_event(
    parsed_bet: ParsedBet,
    events: list[dict[str, Any]],
    match_context: dict[str, Any] | None,
    market_key: str,
) -> dict[str, Any] | None:
    if market_key == "outrights":
        return next((event for event in events if event.get("sport_key") == WORLD_CUP_WINNER_SPORT_KEY), None)

    if match_context:
        context_key = build_match_key(match_context.get("home_team"), match_context.get("away_team"), match_context.get("kickoff_time"))
        for event in events:
            if event.get("matchmind_match_key") == context_key:
                return event

    if len(parsed_bet.teams) >= 2:
        pair = {canonical_team_name(team) for team in parsed_bet.teams[:2]}
        return next(
            (
                event
                for event in events
                if {canonical_team_name(event.get("home_team") or ""), canonical_team_name(event.get("away_team") or "")} == pair
            ),
            None,
        )
    return None


def select_consensus_row(parsed_bet: ParsedBet, rows: list[dict[str, Any]], market_key: str) -> dict[str, Any] | None:
    if not rows:
        return None
    if market_key == "outrights" and parsed_bet.teams:
        team = canonical_team_name(parsed_bet.teams[0])
        return find_row_for_outcome(rows, team)
    if market_key == "h2h" and parsed_bet.teams:
        # The parser orders mentions by text position; for "Spain to beat Germany", the first team is the selection.
        return find_row_for_outcome(rows, canonical_team_name(parsed_bet.teams[0]))
    if market_key == "totals":
        target = "Over" if parsed_bet.market_type == "Over goals" else "Under"
        point = extract_line_point(parsed_bet.original_message)
        candidates = [row for row in rows if row.get("outcome_name") == target]
        if point is not None:
            exact = [row for row in candidates if as_float(row.get("point")) == point]
            if exact:
                return max(exact, key=lambda row: row.get("bookmaker_count") or 0)
        return max(candidates, key=lambda row: row.get("bookmaker_count") or 0, default=None)
    return max(rows, key=lambda row: row.get("bookmaker_count") or 0)


def find_row_for_outcome(rows: list[dict[str, Any]], outcome: str) -> dict[str, Any] | None:
    normalized_outcome = canonical_team_name(outcome)
    exact = [
        row
        for row in rows
        if canonical_team_name(str(row.get("outcome_team") or row.get("outcome_name") or "")) == normalized_outcome
    ]
    return max(exact, key=lambda row: row.get("bookmaker_count") or 0, default=None)


def summarize_value(parsed_bet: ParsedBet, context: dict[str, Any] | None) -> dict[str, Any]:
    if not context or not context.get("matched"):
        return {"verdict": "not_enough_info", "summary": "No matching cached bookmaker consensus was found."}
    edge = context.get("value_edge")
    if parsed_bet.odds is None:
        return {"verdict": "needs_odds", "summary": "Bookmaker consensus is available, but the user odds are missing."}
    if edge is None:
        return {"verdict": "fair", "summary": "Consensus exists, but edge could not be calculated."}
    if edge >= 0.04:
        verdict = "good_value"
        summary = "The entered price is meaningfully above the no-vig bookmaker consensus."
    elif edge <= -0.04:
        verdict = "poor_value"
        summary = "The entered price is meaningfully below the no-vig bookmaker consensus."
    else:
        verdict = "fair"
        summary = "The entered price is close to the no-vig bookmaker consensus."
    return {"verdict": verdict, "edge": edge, "summary": summary}


def value_edge(user_odds: float | None, row: dict[str, Any]) -> float | None:
    consensus_probability = as_float(row.get("no_vig_probability") or row.get("median_no_vig_probability"))
    if user_odds is None or not consensus_probability:
        return None
    return round((1 / user_odds) - consensus_probability, 4) * -1


def price_quality(user_odds: float | None, row: dict[str, Any]) -> str | None:
    best_price = as_float(row.get("best_price"))
    if user_odds is None or not best_price:
        return None

    ratio = user_odds / best_price
    if ratio >= 0.995:
        return "best available or effectively equal to the best cached price"
    if ratio >= 0.97:
        return "strong; close to the best cached price"
    if ratio >= 0.94:
        return "acceptable; below the best cached price but still in range"
    return "weak; meaningfully below the best cached price"


def compact_consensus_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "market_key": row.get("market_key"),
        "outcome_name": row.get("outcome_name"),
        "point": row.get("point"),
        "best_price": as_float(row.get("best_price")),
        "best_bookmaker_title": row.get("best_bookmaker_title"),
        "median_price": as_float(row.get("median_price")),
        "no_vig_probability": as_float(row.get("no_vig_probability") or row.get("median_no_vig_probability")),
        "bookmaker_count": int(row.get("bookmaker_count") or 0),
    }


def compact_featured_markets(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {}
    for market_key in ("spreads", "totals"):
        market_rows = [row for row in rows if row.get("market_key") == market_key]
        result[market_key] = [compact_consensus_row(row) for row in sorted(market_rows, key=lambda item: (str(item.get("point")), str(item.get("outcome_name"))))[:6]]
    return result


def collection(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        for key in ("data", "events", "results"):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    return []


async def _api_get(path: str, params: dict[str, Any]) -> Any:
    settings = get_settings()
    if not settings.odds_api_key:
        raise RuntimeError("ODDS_API_KEY is not configured.")
    url = f"{settings.odds_api_base_url.rstrip('/')}{path}"
    request_params = {"apiKey": settings.odds_api_key, **params}
    _odds_usage.requests += 1
    _odds_usage.last_request_at = datetime.now(timezone.utc)
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(20.0, connect=8.0)) as client:
            response = await client.get(url, params=request_params)
            _odds_usage.last_usage_headers = {
                "x-requests-remaining": response.headers.get("x-requests-remaining"),
                "x-requests-used": response.headers.get("x-requests-used"),
                "x-requests-last": response.headers.get("x-requests-last"),
            }
            response.raise_for_status()
            _odds_usage.last_error = None
            return response.json()
    except Exception as exc:
        _odds_usage.last_error = str(exc)
        logger.warning("The Odds API request failed: %s", exc)
        raise


def _odds_source_params() -> dict[str, str]:
    settings = get_settings()
    if settings.odds_api_bookmakers.strip():
        return {"bookmakers": settings.odds_api_bookmakers.strip()}
    return {"regions": settings.odds_api_regions}


def _resolve_discovery_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    repo_root = Path(__file__).resolve().parents[4]
    return repo_root / path


def build_match_key(home_team: Any, away_team: Any, kickoff_time: Any) -> str | None:
    if not home_team or not away_team:
        return None
    date_part = str(kickoff_time or "")[:10]
    teams = sorted([normalize_text(str(home_team)), normalize_text(str(away_team))])
    return "|".join([*teams, date_part])


def _event_name(event: dict[str, Any]) -> str:
    home = event.get("home_team")
    away = event.get("away_team")
    if home and away:
        return f"{home} vs {away}"
    return event.get("sport_title") or "World Cup outright"


def line_key(row: dict[str, Any]) -> str:
    if row.get("line_key"):
        return str(row["line_key"])
    point = row.get("point")
    if point is None:
        return str(row.get("market_key") or "")
    return f"{row.get('market_key')}:{point}"


def pricing_line_key(row: dict[str, Any]) -> str:
    market_key = str(row.get("market_key") or "")
    point = row.get("point")
    if point is None:
        return market_key
    if market_key == "spreads":
        try:
            return f"{market_key}:{abs(float(point))}"
        except (TypeError, ValueError):
            return f"{market_key}:{point}"
    return str(row.get("line_key") or f"{market_key}:{point}")


def market_line_key(market_key: str, outcome: dict[str, Any]) -> str:
    point = outcome.get("point")
    if point is None:
        return market_key
    return f"{market_key}:{point}"


def row_identity(row: dict[str, Any]) -> tuple[Any, ...]:
    return (
        row.get("odds_api_event_id"),
        row.get("bookmaker_key"),
        row.get("market_key"),
        row.get("outcome_name"),
        row.get("point"),
        row.get("price"),
    )


def extract_line_point(message: str) -> float | None:
    match = re.search(r"\b(?:over|under|más\s+de|mas\s+de|menos\s+de)\s+(\d+(?:[.,]\d+)?)", message, re.IGNORECASE)
    if not match:
        return None
    return as_float(match.group(1).replace(",", "."))


def newest_fetched_at(rows: list[dict[str, Any]]) -> str | None:
    values = [str(row.get("fetched_at") or row.get("last_fetched_at") or "") for row in rows if row.get("fetched_at") or row.get("last_fetched_at")]
    return max(values) if values else None


def as_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
