from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx

from app.config import get_settings
from app.services.bet_parser import ParsedBet, parse_bet_message
from app.services.supabase import get_supabase
from app.services.world_cup_teams import team_aliases_by_canonical
from app.services.world_cup_teams import normalize_text

logger = logging.getLogger(__name__)

POLYMARKET_MARKETS_TABLE = "polymarket_markets"
POLYMARKET_SNAPSHOTS_TABLE = "polymarket_market_snapshots"
POLYMARKET_WRITE_BATCH_SIZE = 25
POLYMARKET_RAW_PAYLOAD_KEYS = (
    "id",
    "marketId",
    "_id",
    "conditionId",
    "question",
    "title",
    "slug",
    "eventId",
    "active",
    "closed",
    "archived",
    "endDate",
    "liquidity",
    "liquidityNum",
    "volume",
    "volumeNum",
    "outcomes",
    "shortOutcomes",
    "outcomePrices",
    "prices",
    "clobTokenIds",
    "bestBid",
    "bestAsk",
    "spread",
)
POLYMARKET_EVENT_PAYLOAD_KEYS = (
    "id",
    "eventId",
    "_id",
    "title",
    "name",
    "question",
    "slug",
    "active",
    "closed",
    "endDate",
    "end_date",
    "endDateIso",
    "liquidity",
    "liquidityNum",
    "volume",
    "volumeNum",
)

SEARCH_TERMS = (
    "World Cup",
    "2026 World Cup",
    "FIFA World Cup",
    "World Cup winner",
    "World Cup champion",
    "Spain World Cup",
    "Argentina World Cup",
    "Brazil World Cup",
    "France World Cup",
    "England World Cup",
    "Mexico World Cup",
    "USA World Cup",
)

WORLD_CUP_HINTS = (
    "world cup",
    "wc 2026",
    "worldcup",
    "mundial",
)

NOISE_HINTS = (
    "club world cup",
    "cricket",
    "rugby",
    "women",
    "women's",
    "basketball",
    "hockey",
    "fortnite",
    "league of legends",
)

SUPPORTED_MARKET_TYPES = {
    "tournament_outright",
    "group_winner",
    "advance_to_knockout",
    "reach_stage",
    "continent_winner",
    "top_goalscorer",
    "squad_inclusion",
}

SIGNAL_TYPE_PRIORITY = (
    "group_winner",
    "advance_to_knockout",
    "reach_stage",
    "top_goalscorer",
    "continent_winner",
    "tournament_outright",
    "squad_inclusion",
)

DEFAULT_SIGNAL_TYPE_CAPS = {
    "group_winner": 4,
    "advance_to_knockout": 3,
    "reach_stage": 3,
    "top_goalscorer": 3,
    "continent_winner": 2,
    "tournament_outright": 2,
    "squad_inclusion": 0,
}

CONTINENT_MARKET_HINTS = (
    "africa",
    "asia",
    "europe",
    "north america",
    "oceania",
    "south america",
)

UNSUPPORTED_CHAT_MARKET_TYPES = {
    "Match winner",
    "Over goals",
    "Under goals",
    "Handicap",
}


@dataclass
class PolymarketCache:
    markets: list[dict[str, Any]] | None = None
    generated_at: str | None = None
    expires_at: datetime | None = None
    source: str | None = None


_polymarket_cache = PolymarketCache()


def clear_polymarket_memory_cache() -> None:
    _polymarket_cache.markets = None
    _polymarket_cache.generated_at = None
    _polymarket_cache.expires_at = None
    _polymarket_cache.source = None


async def build_polymarket_context_for_chat(message: str) -> dict[str, Any] | None:
    parsed_bet = parse_bet_message(message)
    intent = detect_polymarket_intent(message, parsed_bet)
    if not intent:
        return None

    markets = await get_cached_polymarket_markets()
    match = find_best_polymarket_market(parsed_bet, intent, markets)
    if not match:
        return {
            "matched": False,
            "supported_intent": intent,
            "teams": parsed_bet.teams,
            "note": "No usable active Polymarket World Cup 2026 market matched this request.",
            "last_fetched_at": _polymarket_cache.generated_at,
        }

    return compact_polymarket_context(match, intent)


async def get_market_signals(limit: int = 16, market_type: str | None = None) -> list[dict[str, Any]]:
    markets = await get_cached_polymarket_markets()
    usable = [
        market
        for market in markets
        if market.get("is_usable")
        and (market_type is None or market.get("market_type") == market_type)
    ]
    ranked = rank_market_signals(usable, diversified=market_type is None)
    return [compact_polymarket_context(market, market.get("market_type")) for market in ranked[:limit]]


def rank_market_signals(markets: list[dict[str, Any]], diversified: bool = True) -> list[dict[str, Any]]:
    ranked = sorted(markets, key=market_signal_sort_key, reverse=True)
    if not diversified:
        return ranked

    by_type: dict[str, list[dict[str, Any]]] = {market_type: [] for market_type in SIGNAL_TYPE_PRIORITY}
    for market in ranked:
        by_type.setdefault(str(market.get("market_type") or "unsupported"), []).append(market)

    selected: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    caps = DEFAULT_SIGNAL_TYPE_CAPS.copy()

    while True:
        added = False
        for market_type in SIGNAL_TYPE_PRIORITY:
            if caps.get(market_type, 0) <= 0:
                continue
            bucket = by_type.get(market_type) or []
            while bucket:
                candidate = bucket.pop(0)
                market_id = str(candidate.get("polymarket_market_id") or candidate.get("question") or "")
                if market_id in seen_ids:
                    continue
                selected.append(candidate)
                seen_ids.add(market_id)
                caps[market_type] = caps.get(market_type, 0) - 1
                added = True
                break
        if not added:
            break

    selected_ids = {str(market.get("polymarket_market_id") or market.get("question") or "") for market in selected}
    selected.extend(
        market
        for market in ranked
        if str(market.get("polymarket_market_id") or market.get("question") or "") not in selected_ids
    )
    return selected


def market_signal_sort_key(market: dict[str, Any]) -> tuple[float, float, float, float]:
    market_type = str(market.get("market_type") or "")
    probability = as_float(market.get("yes_price")) or 0.0
    quality = float(market.get("signal_quality_score") or 0)
    type_bonus = {
        "group_winner": 24,
        "advance_to_knockout": 22,
        "reach_stage": 20,
        "top_goalscorer": 18,
        "continent_winner": 16,
        "squad_inclusion": 8,
        "tournament_outright": 0,
    }.get(market_type, 0)
    probability_bonus = probability_signal_bonus(market_type, probability)
    liquidity = min(float(market.get("liquidity") or 0), 100_000) / 10_000
    volume = min(float(market.get("volume") or 0), 100_000) / 20_000
    return (quality + type_bonus + probability_bonus, probability, liquidity, volume)


def probability_signal_bonus(market_type: str, probability: float) -> float:
    if probability <= 0:
        return 0
    if market_type == "tournament_outright":
        if probability < 0.02:
            return -45
        if probability < 0.05:
            return -15
        return min(probability * 100, 18)
    if market_type == "reach_stage":
        if probability < 0.03:
            return -25
        if probability < 0.06:
            return -8
        return 18 - abs(probability - 0.5) * 20
    if market_type in {"group_winner", "advance_to_knockout"}:
        return 18 - abs(probability - 0.5) * 20
    if market_type in {"top_goalscorer", "continent_winner"}:
        return min(probability * 100, 20)
    return min(probability * 50, 10)


async def get_cached_polymarket_markets() -> list[dict[str, Any]]:
    now = datetime.now(timezone.utc)
    if _polymarket_cache.markets is not None and _polymarket_cache.expires_at and _polymarket_cache.expires_at > now:
        return _polymarket_cache.markets

    settings = get_settings()
    try:
        normalized = await get_polymarket_markets_from_supabase()
        if normalized:
            _polymarket_cache.markets = normalized
            _polymarket_cache.generated_at = newest_fetch_time(normalized)
            _polymarket_cache.expires_at = now + timedelta(seconds=settings.polymarket_cache_ttl_seconds)
            _polymarket_cache.source = "supabase"
            return normalized
    except Exception as exc:
        logger.info("Polymarket Supabase cache unavailable, falling back to discovery JSON: %s", exc)

    payload = _load_discovery_payload()
    generated_at = payload.get("generated_at")
    normalized = [normalize_polymarket_market(market, generated_at) for market in payload.get("markets", [])]
    _polymarket_cache.markets = normalized
    _polymarket_cache.generated_at = generated_at
    _polymarket_cache.expires_at = now + timedelta(seconds=settings.polymarket_cache_ttl_seconds)
    _polymarket_cache.source = "discovery_json"
    return normalized


async def get_polymarket_markets_from_supabase() -> list[dict[str, Any]]:
    client = await get_supabase()
    response = (
        await client.table(POLYMARKET_MARKETS_TABLE)
        .select("*")
        .order("signal_quality_score", desc=True)
        .execute()
    )
    return [normalize_polymarket_row(row) for row in response.data or []]


async def seed_polymarket_markets_from_discovery_file() -> dict[str, Any]:
    payload = _load_discovery_payload()
    generated_at = payload.get("generated_at") or datetime.now(timezone.utc).isoformat()
    normalized = [normalize_polymarket_market(market, generated_at) for market in payload.get("markets", [])]
    return await persist_polymarket_markets(normalized, source="discovery_json")


async def refresh_polymarket_markets_from_api() -> dict[str, Any]:
    payload = await fetch_polymarket_world_cup_payload()
    generated_at = payload.get("generated_at") or datetime.now(timezone.utc).isoformat()
    normalized = [normalize_polymarket_market(market, generated_at) for market in payload.get("markets", [])]
    return await persist_polymarket_markets(normalized, source="polymarket_api")


async def persist_polymarket_markets(markets: list[dict[str, Any]], source: str) -> dict[str, Any]:
    rows = [polymarket_market_to_row(market) for market in markets if market.get("polymarket_market_id")]
    if not rows:
        clear_polymarket_memory_cache()
        return {
            "source": source,
            "markets_seen": len(markets),
            "markets_upserted": 0,
            "snapshots_inserted": 0,
            "usable_markets": 0,
        }

    client = await get_supabase()
    for batch in batched(rows, POLYMARKET_WRITE_BATCH_SIZE):
        await client.table(POLYMARKET_MARKETS_TABLE).upsert(batch, on_conflict="polymarket_market_id").execute()

    snapshots = [polymarket_market_to_snapshot_row(market) for market in markets if market.get("polymarket_market_id") and market.get("yes_price") is not None]
    if snapshots:
        for batch in batched(snapshots, POLYMARKET_WRITE_BATCH_SIZE):
            await client.table(POLYMARKET_SNAPSHOTS_TABLE).insert(batch).execute()

    clear_polymarket_memory_cache()
    return {
        "source": source,
        "markets_seen": len(markets),
        "markets_upserted": len(rows),
        "snapshots_inserted": len(snapshots),
        "usable_markets": sum(1 for market in markets if market.get("is_usable")),
        "market_type_counts": count_by_key(markets, "market_type"),
        "last_fetched_at": newest_fetch_time(markets),
    }


async def fetch_polymarket_world_cup_payload() -> dict[str, Any]:
    attempts: list[dict[str, Any]] = []
    settings = get_settings()
    async with httpx.AsyncClient(timeout=20) as client:
        events, markets = await search_gamma(client, attempts)
        events_by_id = {str(event_identity(event)): normalize_event(event) for event in events if event_identity(event)}
        token_ids = [
            token_id
            for market in markets
            for token_id in extract_clob_token_ids(market)
        ]
        clob_data = await fetch_clob_data(client, token_ids, settings.polymarket_refresh_clob_token_limit, attempts)

    aliases_by_team = team_aliases_by_canonical()
    normalized_markets = [
        normalize_api_market(market, events_by_id, aliases_by_team, clob_data)
        for market in markets
    ]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "request_attempts": attempts,
        "events": list(events_by_id.values()),
        "markets": normalized_markets,
        "summary": {
            "events_found": len(events),
            "markets_found": len(markets),
            "likely_world_cup_markets": sum(1 for market in normalized_markets if market.get("likely_world_cup_2026")),
            "markets_with_usable_prices": sum(1 for market in normalized_markets if market.get("has_usable_prices")),
            "active_world_cup_markets": sum(1 for market in normalized_markets if market.get("likely_world_cup_2026") and market.get("active") and not market.get("closed")),
        },
    }


def detect_polymarket_intent(message: str, parsed_bet: ParsedBet | None = None) -> str | None:
    parsed_bet = parsed_bet or parse_bet_message(message)
    normalized = normalize_text(message)

    if re.search(r"\b(?:over|under|goals?|goles|corners?|cards?|tarjetas|handicap|h[áa]ndicap)\b", message, re.IGNORECASE):
        return None
    if re.search(r"\b(?:quarterfinal|quarter-final|semifinal|semi-final|final|cuartos|semifinal|final)\b", normalized):
        return "reach_stage"
    if re.search(r"\b(?:advance|qualify|progress|knockout|knockouts|clasificar|clasifica|octavos)\b", normalized):
        return "advance_to_knockout"
    if "group" in normalized and re.search(r"\b(?:winner|win|top|ganar|gana|grupo)\b", normalized):
        return "group_winner"
    if parsed_bet.market_type == "Tournament outright" or re.search(
        r"\b(?:world cup|mundial|copa)\b.*\b(?:winner|champion|campeon|campeona|ganar|gana|win)\b|\b(?:winner|champion|campeon|campeona|ganar|gana|win)\b.*\b(?:world cup|mundial|copa)\b",
        normalized,
    ):
        return "tournament_outright"
    if parsed_bet.market_type in UNSUPPORTED_CHAT_MARKET_TYPES:
        return None
    if re.search(r"\b(?:top goalscorer|golden boot|pichichi|goleador)\b", normalized):
        return "top_goalscorer"
    if re.search(r"\b(?:squad|roster|convocatoria|convocado|lista)\b", normalized):
        return "squad_inclusion"
    return None


def find_best_polymarket_market(
    parsed_bet: ParsedBet,
    intent: str,
    markets: list[dict[str, Any]],
) -> dict[str, Any] | None:
    settings = get_settings()
    teams = set(parsed_bet.teams)
    candidates = [
        market
        for market in markets
        if market.get("is_usable")
        and market.get("market_type") == intent
        and market.get("match_confidence", 0) >= settings.polymarket_min_match_confidence
        and market.get("signal_quality_score", 0) >= settings.polymarket_min_signal_quality
        and (not teams or bool(teams & set(market.get("matched_teams") or [])))
    ]
    if not candidates:
        return None

    if not teams:
        return max(
            candidates,
            key=lambda market: (
                market.get("yes_price") or 0,
                market.get("signal_quality_score") or 0,
                market.get("liquidity") or 0,
            ),
        )

    return max(
        candidates,
        key=lambda market: (
            len(teams & set(market.get("matched_teams") or [])),
            market.get("signal_quality_score") or 0,
            market.get("liquidity") or 0,
            market.get("volume") or 0,
        ),
    )


def normalize_polymarket_market(market: dict[str, Any], last_fetched_at: str | None) -> dict[str, Any]:
    raw_payload = market.get("raw") or market
    market_type = infer_market_type_from_text(
        normalize_market_type(market.get("market_type_guess")),
        market.get("market_question"),
        market.get("event_title"),
        market.get("event_slug"),
        market.get("market_slug"),
    )
    yes_price = extract_yes_price(market)
    liquidity = as_float(market.get("liquidity"))
    volume = as_float(market.get("volume"))
    spread = as_float((market.get("raw") or {}).get("spread")) or extract_clob_number(market, "spread", "spread")
    best_bid = as_float((market.get("raw") or {}).get("bestBid"))
    best_ask = as_float((market.get("raw") or {}).get("bestAsk"))
    midpoint = extract_clob_number(market, "midpoint", "mid") or yes_price
    match_confidence = calculate_match_confidence(market, market_type)
    signal_quality_score = calculate_signal_quality_score(
        market_type=market_type,
        active=bool(market.get("active")),
        closed=bool(market.get("closed")),
        likely_world_cup=bool(market.get("likely_world_cup_2026")),
        yes_price=yes_price,
        liquidity=liquidity,
        volume=volume,
        spread=spread,
        match_confidence=match_confidence,
    )
    is_usable = (
        market_type in SUPPORTED_MARKET_TYPES
        and bool(market.get("likely_world_cup_2026"))
        and bool(market.get("active"))
        and not bool(market.get("closed"))
        and yes_price is not None
        and match_confidence >= get_settings().polymarket_min_match_confidence
    )

    return {
        "polymarket_event_id": market.get("event_id"),
        "polymarket_market_id": market.get("market_id"),
        "condition_id": raw_payload.get("conditionId"),
        "market_type": market_type,
        "matched_teams": market.get("matched_teams") or [],
        "matched_team": (market.get("matched_teams") or [None])[0],
        "matched_group": extract_group(market),
        "question": market.get("market_question"),
        "slug": market.get("market_slug"),
        "event_title": market.get("event_title"),
        "event_slug": market.get("event_slug"),
        "outcomes": market.get("outcomes") or [],
        "outcome_prices": market.get("outcome_prices") or [],
        "yes_price": yes_price,
        "implied_probability": yes_price,
        "liquidity": liquidity,
        "volume": volume,
        "active": bool(market.get("active")),
        "closed": bool(market.get("closed")),
        "archived": bool((market.get("raw") or {}).get("archived")),
        "end_date": market.get("end_date"),
        "clob_token_ids": market.get("clob_token_ids") or [],
        "best_bid": best_bid,
        "best_ask": best_ask,
        "midpoint": midpoint,
        "spread": spread,
        "match_confidence": match_confidence,
        "signal_quality_score": signal_quality_score,
        "is_usable": is_usable and signal_quality_score >= get_settings().polymarket_min_signal_quality,
        "last_fetched_at": last_fetched_at,
        "raw_payload": compact_polymarket_raw_payload(raw_payload),
    }


def compact_polymarket_context(market: dict[str, Any], intent: str | None) -> dict[str, Any]:
    return {
        "matched": True,
        "market_type": intent or market.get("market_type"),
        "team": market.get("matched_team"),
        "teams": market.get("matched_teams") or [],
        "group": market.get("matched_group"),
        "question": market.get("question") or "",
        "slug": market.get("slug"),
        "yes_price": market.get("yes_price"),
        "implied_probability": market.get("implied_probability"),
        "liquidity": market.get("liquidity"),
        "volume": market.get("volume"),
        "best_bid": market.get("best_bid"),
        "best_ask": market.get("best_ask"),
        "midpoint": market.get("midpoint"),
        "spread": market.get("spread"),
        "match_confidence": market.get("match_confidence"),
        "signal_quality_score": market.get("signal_quality_score"),
        "liquidity_label": liquidity_label(market.get("liquidity")),
        "active": market.get("active"),
        "closed": market.get("closed"),
        "end_date": market.get("end_date"),
        "last_fetched_at": market.get("last_fetched_at"),
    }


def format_polymarket_context_block(context: dict[str, Any] | None) -> str | None:
    if not context:
        return None
    if not context.get("matched"):
        return (
            "POLYMARKET CONTEXT:\n"
            f"- Supported intent: {context.get('supported_intent')}\n"
            "- Matched market: none\n"
            f"- Note: {context.get('note')}\n"
            "- Use this as absence of a crowd signal, not as evidence for or against the bet."
        )

    probability = context.get("implied_probability")
    probability_text = f"{probability * 100:.1f}%" if isinstance(probability, int | float) else "unknown"
    lines = [
        "POLYMARKET CONTEXT:",
        f"- Market type: {context.get('market_type')}",
        f"- Question: {context.get('question')}",
        f"- Crowd probability: {probability_text}",
        f"- Liquidity: {context.get('liquidity_label')} ({context.get('liquidity') or 0:g})",
        f"- Volume: {context.get('volume') or 0:g}",
        f"- Signal quality: {context.get('signal_quality_score')}/100",
        f"- Match confidence: {context.get('match_confidence')}",
    ]
    if context.get("spread") is not None:
        lines.append(f"- Bid/ask spread: {context['spread']}")
    lines.append("- Treat this as prediction-market crowd probability, not truth or betting instruction.")
    return "\n".join(lines)


def normalize_market_type(value: Any) -> str:
    normalized = normalize_text(str(value or ""))
    if normalized == "top goalscorer":
        return "top_goalscorer"
    if normalized == "continent winner":
        return "continent_winner"
    if normalized == "reach stage":
        return "reach_stage"
    if normalized == "tournament outright":
        return "tournament_outright"
    if normalized == "group winner":
        return "group_winner"
    if normalized == "team to qualify progress":
        return "advance_to_knockout"
    if normalized == "tournament other":
        return "squad_inclusion"
    return normalized.replace(" ", "_") or "unsupported"


def infer_market_type_from_text(current_type: str, *text_parts: Any) -> str:
    text = normalize_text(" ".join(str(part or "") for part in text_parts))
    if not text:
        return current_type
    if any(hint in text for hint in ("top goalscorer", "golden boot", "most goals")):
        return "top_goalscorer"
    if "world cup" in text and any(continent in text for continent in CONTINENT_MARKET_HINTS):
        if re.search(r"\b(?:win|winner|wins)\b", text):
            return "continent_winner"
    if re.search(r"\b(?:reach|make)\b.*\b(?:final|semi final|semifinal|quarter final|quarterfinal)\b", text):
        return "reach_stage"
    if "group" in text and any(hint in text for hint in ("winner", "win group", "top group")):
        return "group_winner"
    if any(hint in text for hint in ("qualify", "advance", "progress", "knockout stages", "knockout stage")):
        return "advance_to_knockout"
    return current_type


def extract_yes_price(market: dict[str, Any]) -> float | None:
    outcomes = market.get("outcomes") or []
    prices = market.get("outcome_prices") or []
    for index, outcome in enumerate(outcomes):
        if normalize_text(str(outcome)) == "yes" and index < len(prices):
            return as_float(prices[index])
    return as_float(prices[0]) if prices else None


def calculate_match_confidence(market: dict[str, Any], market_type: str) -> float:
    if not market.get("likely_world_cup_2026") or market_type not in SUPPORTED_MARKET_TYPES:
        return 0.0
    if not market.get("matched_teams") and market_type not in {"continent_winner", "top_goalscorer"}:
        return 0.4
    if market_type in {"tournament_outright", "group_winner", "advance_to_knockout", "reach_stage"}:
        return 1.0
    return 0.7


def calculate_signal_quality_score(
    *,
    market_type: str,
    active: bool,
    closed: bool,
    likely_world_cup: bool,
    yes_price: float | None,
    liquidity: float | None,
    volume: float | None,
    spread: float | None,
    match_confidence: float,
) -> int:
    if market_type not in SUPPORTED_MARKET_TYPES or not active or closed or not likely_world_cup or yes_price is None:
        return 0

    score = int(match_confidence * 35)
    score += min(int((liquidity or 0) / 500), 25)
    score += min(int((volume or 0) / 2_000), 20)
    if spread is None:
        score += 5
    elif spread <= 0.01:
        score += 20
    elif spread <= 0.03:
        score += 12
    elif spread <= 0.08:
        score += 5
    return max(0, min(score, 100))


def liquidity_label(liquidity: Any) -> str:
    value = as_float(liquidity) or 0
    if value >= 50_000:
        return "Strong"
    if value >= 5_000:
        return "Medium"
    if value >= 1_000:
        return "Light"
    return "Thin"


def extract_group(market: dict[str, Any]) -> str | None:
    text = " ".join(str(value or "") for value in (market.get("event_title"), market.get("market_question"), market.get("event_slug")))
    match = re.search(r"\bgroup\s+([a-l])\b", text, re.IGNORECASE)
    return match.group(1).upper() if match else None


def extract_clob_number(market: dict[str, Any], payload_key: str, value_key: str) -> float | None:
    for token_data in (market.get("clob") or {}).values():
        payload = token_data.get(payload_key)
        if isinstance(payload, dict):
            value = as_float(payload.get(value_key))
            if value is not None:
                return value
    return None


def compact_polymarket_raw_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    compact = {key: payload[key] for key in POLYMARKET_RAW_PAYLOAD_KEYS if key in payload}
    for key in ("_parent_event_id", "_parent_event_title", "_parent_event_slug"):
        if key in payload:
            compact[key] = payload[key]
    return compact


def compact_polymarket_event_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    return {key: payload[key] for key in POLYMARKET_EVENT_PAYLOAD_KEYS if key in payload}


def as_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def normalize_polymarket_row(row: dict[str, Any]) -> dict[str, Any]:
    yes_price = as_float(row.get("yes_price"))
    market_type = infer_market_type_from_text(
        normalize_market_type(row.get("market_type")),
        row.get("question"),
        row.get("event_title"),
        row.get("event_slug"),
        row.get("slug"),
    )
    active = bool(row.get("active"))
    closed = bool(row.get("closed"))
    match_confidence = normalized_row_match_confidence(row, market_type)
    quality_score = calculate_signal_quality_score(
        market_type=market_type,
        active=active,
        closed=closed,
        likely_world_cup=is_likely_world_cup(
            " ".join(str(row.get(key) or "") for key in ("question", "event_title", "event_slug", "slug"))
        ),
        yes_price=yes_price,
        liquidity=as_float(row.get("liquidity")),
        volume=as_float(row.get("volume")),
        spread=as_float(row.get("spread")),
        match_confidence=match_confidence,
    )
    if quality_score == 0:
        quality_score = int(row.get("signal_quality_score") or 0)
    return {
        "polymarket_event_id": row.get("polymarket_event_id"),
        "polymarket_market_id": row.get("polymarket_market_id"),
        "condition_id": row.get("condition_id"),
        "market_type": market_type,
        "matched_teams": row.get("matched_teams") or [],
        "matched_team": row.get("matched_team"),
        "matched_group": row.get("matched_group"),
        "question": row.get("question"),
        "slug": row.get("slug"),
        "event_title": row.get("event_title"),
        "event_slug": row.get("event_slug"),
        "outcomes": row.get("outcomes") or [],
        "outcome_prices": row.get("outcome_prices") or [],
        "yes_price": yes_price,
        "implied_probability": yes_price,
        "liquidity": as_float(row.get("liquidity")),
        "volume": as_float(row.get("volume")),
        "active": active,
        "closed": closed,
        "archived": bool(row.get("archived")),
        "end_date": row.get("end_date"),
        "clob_token_ids": row.get("clob_token_ids") or [],
        "best_bid": as_float(row.get("best_bid")),
        "best_ask": as_float(row.get("best_ask")),
        "midpoint": as_float(row.get("midpoint")) or yes_price,
        "spread": as_float(row.get("spread")),
        "match_confidence": match_confidence,
        "signal_quality_score": quality_score,
        "is_usable": normalized_row_is_usable(row, market_type, yes_price, match_confidence, quality_score),
        "last_fetched_at": row.get("last_fetched_at"),
        "raw_payload": row.get("raw_payload") or {},
    }


def normalized_row_match_confidence(row: dict[str, Any], market_type: str) -> float:
    stored = as_float(row.get("match_confidence")) or 0.0
    if market_type in {"continent_winner", "top_goalscorer"}:
        return max(stored, 0.7)
    if market_type == "reach_stage" and row.get("matched_teams"):
        return max(stored, 1.0)
    return stored


def normalized_row_is_usable(
    row: dict[str, Any],
    market_type: str,
    yes_price: float | None,
    match_confidence: float,
    quality_score: int,
) -> bool:
    if bool(row.get("is_usable")) and market_type in SUPPORTED_MARKET_TYPES:
        return True
    text = " ".join(str(row.get(key) or "") for key in ("question", "event_title", "event_slug", "slug"))
    return (
        market_type in SUPPORTED_MARKET_TYPES
        and is_likely_world_cup(text)
        and bool(row.get("active"))
        and not bool(row.get("closed"))
        and yes_price is not None
        and match_confidence >= get_settings().polymarket_min_match_confidence
        and quality_score >= get_settings().polymarket_min_signal_quality
    )


def polymarket_market_to_row(market: dict[str, Any]) -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    return {
        "polymarket_event_id": market.get("polymarket_event_id"),
        "polymarket_market_id": market.get("polymarket_market_id"),
        "condition_id": market.get("condition_id"),
        "market_type": market.get("market_type"),
        "matched_team": market.get("matched_team"),
        "matched_teams": market.get("matched_teams") or [],
        "matched_group": market.get("matched_group"),
        "matched_player": market.get("matched_player"),
        "question": market.get("question"),
        "slug": market.get("slug"),
        "event_title": market.get("event_title"),
        "event_slug": market.get("event_slug"),
        "outcomes": market.get("outcomes") or [],
        "outcome_prices": market.get("outcome_prices") or [],
        "yes_price": market.get("yes_price"),
        "no_price": extract_no_price(market),
        "liquidity": market.get("liquidity"),
        "volume": market.get("volume"),
        "active": bool(market.get("active")),
        "closed": bool(market.get("closed")),
        "archived": bool(market.get("archived")),
        "end_date": market.get("end_date"),
        "clob_token_ids": market.get("clob_token_ids") or [],
        "best_bid": market.get("best_bid"),
        "best_ask": market.get("best_ask"),
        "midpoint": market.get("midpoint"),
        "spread": market.get("spread"),
        "raw_payload": compact_polymarket_raw_payload(market.get("raw_payload") or {}),
        "match_confidence": market.get("match_confidence") or 0,
        "signal_quality_score": market.get("signal_quality_score") or 0,
        "is_usable": bool(market.get("is_usable")),
        "last_fetched_at": market.get("last_fetched_at") or now,
        "updated_at": now,
    }


def polymarket_market_to_snapshot_row(market: dict[str, Any]) -> dict[str, Any]:
    return {
        "polymarket_market_id": market.get("polymarket_market_id"),
        "yes_price": market.get("yes_price"),
        "no_price": extract_no_price(market),
        "liquidity": market.get("liquidity"),
        "volume": market.get("volume"),
        "best_bid": market.get("best_bid"),
        "best_ask": market.get("best_ask"),
        "midpoint": market.get("midpoint"),
        "spread": market.get("spread"),
        "signal_quality_score": market.get("signal_quality_score") or 0,
        "fetched_at": market.get("last_fetched_at") or datetime.now(timezone.utc).isoformat(),
    }


def extract_no_price(market: dict[str, Any]) -> float | None:
    outcomes = market.get("outcomes") or []
    prices = market.get("outcome_prices") or []
    for index, outcome in enumerate(outcomes):
        if normalize_text(str(outcome)) == "no" and index < len(prices):
            return as_float(prices[index])
    return None


def newest_fetch_time(markets: list[dict[str, Any]]) -> str | None:
    values = [market.get("last_fetched_at") for market in markets if market.get("last_fetched_at")]
    return max(values) if values else None


def count_by_key(items: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        value = str(item.get(key) or "unknown")
        counts[value] = counts.get(value, 0) + 1
    return counts


def batched(items: list[dict[str, Any]], size: int) -> list[list[dict[str, Any]]]:
    return [items[index : index + size] for index in range(0, len(items), size)]


async def search_gamma(client: httpx.AsyncClient, attempts: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    events_by_key: dict[str, dict[str, Any]] = {}
    markets_by_key: dict[str, dict[str, Any]] = {}

    for term in SEARCH_TERMS:
        payloads = [
            await gamma_get_json(client, "/public-search", {"q": term, "limit_per_type": 25}, attempts),
            await gamma_get_json(
                client,
                "/public-search",
                {"q": term, "limit_per_type": 25, "keep_closed_markets": 1},
                attempts,
            ),
        ]
        for payload in payloads:
            if not isinstance(payload, dict):
                continue
            for event in payload.get("events") or []:
                if not isinstance(event, dict):
                    continue
                key = event_identity(event)
                if key:
                    events_by_key[key] = compact_polymarket_event_payload(event)
                for market in event.get("markets") or []:
                    if isinstance(market, dict):
                        market.setdefault("_parent_event_title", pick_first(event, ("title", "name", "question")))
                        market.setdefault("_parent_event_slug", pick_first(event, ("slug",)))
                        if not should_keep_polymarket_search_market(market):
                            continue
                        market_key = market_identity(market)
                        if market_key:
                            market.setdefault("_parent_event_id", key)
                            markets_by_key[market_key] = market
            for market in payload.get("markets") or []:
                if isinstance(market, dict):
                    if not should_keep_polymarket_search_market(market):
                        continue
                    key = market_identity(market)
                    if key:
                        markets_by_key[key] = market

        if not any(isinstance(payload, dict) for payload in payloads):
            for endpoint in ("/events", "/markets"):
                items = await gamma_get(client, endpoint, {"search": term, "limit": 25}, attempts)
                for item in items:
                    if endpoint == "/events":
                        key = event_identity(item)
                        if key:
                            events_by_key[key] = compact_polymarket_event_payload(item)
                    else:
                        key = market_identity(item)
                        if key and should_keep_polymarket_search_market(item):
                            markets_by_key[key] = item

    return list(events_by_key.values()), list(markets_by_key.values())


async def gamma_get(client: httpx.AsyncClient, endpoint: str, params: dict[str, Any], attempts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    payload = await gamma_get_json(client, endpoint, params, attempts)
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        for key in ("data", "results", "events", "markets"):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    return []


async def gamma_get_json(client: httpx.AsyncClient, endpoint: str, params: dict[str, Any], attempts: list[dict[str, Any]]) -> Any:
    url = f"{get_settings().polymarket_gamma_base_url.rstrip('/')}{endpoint}"
    try:
        response = await client.get(url, params=params)
        attempts.append({"url": str(response.url), "status_code": response.status_code, "ok": response.is_success})
        response.raise_for_status()
        return response.json()
    except Exception as exc:
        attempts.append({"url": url, "params": params, "ok": False, "error": str(exc)})
        return None


async def fetch_clob_data(
    client: httpx.AsyncClient,
    token_ids: list[str],
    max_tokens: int,
    attempts: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    clob_data: dict[str, dict[str, Any]] = {}
    base_url = get_settings().polymarket_clob_base_url.rstrip("/")
    for token_id in list(dict.fromkeys(token_ids))[:max_tokens]:
        token_data: dict[str, Any] = {}
        for endpoint, key in (("/midpoint", "midpoint"), ("/spread", "spread"), ("/book", "book")):
            try:
                response = await client.get(f"{base_url}{endpoint}", params={"token_id": token_id})
                attempts.append({"url": str(response.url), "status_code": response.status_code, "ok": response.is_success})
                token_data[f"{key}_status_code"] = response.status_code
                if response.is_success:
                    token_data[key] = response.json()
            except Exception as exc:
                attempts.append({"url": f"{base_url}{endpoint}", "params": {"token_id": token_id}, "ok": False, "error": str(exc)})
                token_data[f"{key}_error"] = str(exc)
        clob_data[token_id] = token_data
    return clob_data


def normalize_event(event: dict[str, Any]) -> dict[str, Any]:
    return {
        "event_id": pick_first(event, ("id", "eventId", "_id")),
        "event_title": pick_first(event, ("title", "name", "question")),
        "event_slug": pick_first(event, ("slug",)),
        "active": pick_first(event, ("active",)),
        "closed": pick_first(event, ("closed",)),
        "end_date": pick_first(event, ("endDate", "end_date", "endDateIso")),
        "liquidity": as_float(pick_first(event, ("liquidity", "liquidityNum"))),
        "volume": as_float(pick_first(event, ("volume", "volumeNum"))),
        "raw": event,
    }


def normalize_api_market(
    market: dict[str, Any],
    events_by_id: dict[str, dict[str, Any]],
    aliases_by_team: dict[str, tuple[str, ...]],
    clob_data: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    outcomes, prices = extract_outcomes_and_prices(market)
    token_ids = extract_clob_token_ids(market)
    event_id = str(pick_first(market, ("eventId", "event_id", "_parent_event_id")) or "")
    event = events_by_id.get(event_id, {})
    event_title = pick_first(market, ("_parent_event_title",)) or event.get("event_title")
    event_slug = pick_first(market, ("_parent_event_slug",)) or event.get("event_slug")
    question = pick_first(market, ("question", "title", "name", "description")) or ""
    market_slug = pick_first(market, ("slug",))
    combined_text = " ".join(str(part or "") for part in (event_title, event_slug, question, market_slug))
    token_clob = {token_id: clob_data[token_id] for token_id in token_ids if token_id in clob_data}
    has_gamma_prices = any(price is not None for price in prices)
    has_clob_prices = any(data.get("midpoint") or data.get("book") for data in token_clob.values())

    return {
        "event_id": event_id or None,
        "event_title": event_title,
        "event_slug": event_slug,
        "market_id": pick_first(market, ("id", "marketId", "_id", "conditionId")),
        "market_question": question,
        "market_slug": market_slug,
        "outcomes": outcomes,
        "outcome_prices": prices,
        "liquidity": as_float(pick_first(market, ("liquidity", "liquidityNum"))),
        "volume": as_float(pick_first(market, ("volume", "volumeNum"))),
        "active": pick_first(market, ("active",)),
        "closed": pick_first(market, ("closed",)),
        "end_date": pick_first(market, ("endDate", "end_date", "endDateIso")),
        "clob_token_ids": token_ids,
        "clob": token_clob,
        "market_type_guess": classify_market(combined_text),
        "matched_teams": detect_teams(combined_text, aliases_by_team),
        "likely_world_cup_2026": is_likely_world_cup(combined_text),
        "has_usable_prices": has_gamma_prices or has_clob_prices,
        "raw": market,
    }


def event_identity(event: dict[str, Any]) -> str:
    return str(pick_first(event, ("id", "eventId", "_id", "slug")) or "")


def market_identity(market: dict[str, Any]) -> str:
    return str(pick_first(market, ("id", "marketId", "_id", "conditionId", "slug")) or "")


def should_keep_polymarket_search_market(market: dict[str, Any]) -> bool:
    text = " ".join(
        str(part or "")
        for part in (
            pick_first(market, ("_parent_event_title",)),
            pick_first(market, ("_parent_event_slug",)),
            pick_first(market, ("question", "title", "name", "description")),
            pick_first(market, ("slug",)),
        )
    )
    return is_likely_world_cup(text)


def pick_first(payload: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        if key in payload and payload[key] not in (None, ""):
            return payload[key]
    return None


def parse_jsonish(value: Any, default: Any = None) -> Any:
    if value is None:
        return default
    if isinstance(value, (list, dict, int, float, bool)):
        return value
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return default
        try:
            return json.loads(stripped)
        except json.JSONDecodeError:
            return value
    return value


def extract_outcomes_and_prices(market: dict[str, Any]) -> tuple[list[str], list[float | None]]:
    outcomes_raw = parse_jsonish(pick_first(market, ("outcomes", "shortOutcomes")), [])
    prices_raw = parse_jsonish(pick_first(market, ("outcomePrices", "outcome_prices", "prices")), [])
    outcomes = [str(item) for item in outcomes_raw] if isinstance(outcomes_raw, list) else []
    prices = [as_float(item) for item in prices_raw] if isinstance(prices_raw, list) else []
    if prices and len(prices) < len(outcomes):
        prices.extend([None] * (len(outcomes) - len(prices)))
    return outcomes, prices


def extract_clob_token_ids(market: dict[str, Any]) -> list[str]:
    raw = parse_jsonish(
        pick_first(market, ("clobTokenIds", "clob_token_ids", "clobTokenIDs", "tokenIds", "token_ids")),
        [],
    )
    if isinstance(raw, list):
        return [str(token_id) for token_id in raw if token_id]
    if isinstance(raw, str) and raw:
        return [raw]
    return []


def detect_teams(text: str, aliases_by_team: dict[str, tuple[str, ...]]) -> list[str]:
    normalized = f" {normalize_text(text)} "
    matched: list[str] = []
    for canonical, aliases in aliases_by_team.items():
        for alias in (canonical, *aliases):
            normalized_alias = normalize_text(alias)
            if normalized_alias and f" {normalized_alias} " in normalized:
                matched.append(canonical)
                break
    return sorted(set(matched))


def classify_market(text: str) -> str:
    normalized = normalize_text(text)
    if any(hint in normalized for hint in ("club world cup", "women s world cup")):
        return "unrelated/noise"
    if any(hint in normalized for hint in ("top goalscorer", "golden boot", "most goals")):
        return "top goalscorer"
    if "world cup" in normalized and any(continent in normalized for continent in CONTINENT_MARKET_HINTS):
        if re.search(r"\b(?:win|winner|wins)\b", normalized):
            return "continent winner"
    if re.search(r"\b(?:reach|make)\b.*\b(?:final|semi final|semifinal|quarter final|quarterfinal)\b", normalized):
        return "reach stage"
    if "group" in normalized and any(hint in normalized for hint in ("winner", "win group", "top group")):
        return "group winner"
    if any(hint in normalized for hint in ("winner", "champion", "win the world cup", "lift the world cup")):
        return "tournament outright"
    if any(hint in normalized for hint in ("qualify", "advance", "progress", "make the round", "make round", "reach")):
        return "team to qualify/progress"
    if re.search(r"\b(vs|v|versus)\b", normalized) or "draw" in normalized:
        return "match winner"
    if "world cup" in normalized or "fifa" in normalized:
        return "tournament/other"
    return "unrelated/noise"


def is_likely_world_cup(text: str) -> bool:
    normalized = normalize_text(text)
    has_world_cup = any(hint in normalized for hint in WORLD_CUP_HINTS)
    has_2026 = "2026" in normalized
    is_noise = any(hint in normalized for hint in NOISE_HINTS)
    return has_world_cup and has_2026 and not is_noise


def _load_discovery_payload() -> dict[str, Any]:
    path = _resolve_discovery_path(get_settings().polymarket_discovery_path)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        logger.info("Polymarket discovery file not found: %s", path)
        return {"markets": [], "generated_at": None}
    except json.JSONDecodeError as exc:
        logger.warning("Polymarket discovery file is not valid JSON: %s", exc)
        return {"markets": [], "generated_at": None}


def _resolve_discovery_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    candidates = [
        Path.cwd() / path,
        Path(__file__).resolve().parents[4] / path,
        Path(__file__).resolve().parents[2] / path,
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]
