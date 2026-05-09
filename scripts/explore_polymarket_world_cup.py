#!/usr/bin/env python3
"""Explore public Polymarket World Cup 2026 data for Matchmind.

This script is intentionally standalone. It does not import routers, services
with network side effects, database code, or modify any production state.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
import unicodedata
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx


GAMMA_BASE_URL = "https://gamma-api.polymarket.com"
CLOB_BASE_URL = "https://clob.polymarket.com"
REPORT_PATH = Path("tmp/polymarket_world_cup_discovery.json")

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

FALLBACK_TEAM_ALIASES: dict[str, tuple[str, ...]] = {
    "Argentina": ("Argentina",),
    "Brazil": ("Brazil", "Brasil"),
    "England": ("England", "Inglaterra"),
    "France": ("France", "Francia"),
    "Germany": ("Germany", "Alemania", "Deutschland"),
    "Mexico": ("Mexico", "México", "Mejico"),
    "Portugal": ("Portugal",),
    "Spain": ("Spain", "España", "Espana", "La Roja"),
    "United States": ("United States", "USA", "US", "Estados Unidos", "EEUU"),
}


def load_team_aliases() -> dict[str, tuple[str, ...]]:
    """Reuse Matchmind aliases when available, otherwise keep exploration local."""
    repo_root = Path(__file__).resolve().parents[1]
    api_root = repo_root / "apps" / "api"
    for import_root in (api_root, repo_root):
        import_root_str = str(import_root)
        if import_root_str not in sys.path:
            sys.path.insert(0, import_root_str)

    try:
        from app.services.world_cup_teams import team_aliases_by_canonical

        return team_aliases_by_canonical()
    except Exception as exc:  # pragma: no cover - intentionally defensive.
        print(f"Alias import failed, using fallback aliases: {exc}")
        return FALLBACK_TEAM_ALIASES


def normalize_text(value: Any) -> str:
    text = "" if value is None else str(value)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = text.lower().replace(".", " ")
    return " ".join(re.sub(r"[^a-z0-9]+", " ", text).split())


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


def as_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def pick_first(payload: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        if key in payload and payload[key] not in (None, ""):
            return payload[key]
    return None


def collection_from_response(payload: Any) -> list[dict[str, Any]]:
    """Gamma sometimes returns a list, sometimes an object with data/results."""
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        return []
    for key in ("data", "results", "events", "markets"):
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    return []


def event_identity(event: dict[str, Any]) -> str:
    return str(pick_first(event, ("id", "eventId", "_id", "slug")) or "")


def market_identity(market: dict[str, Any]) -> str:
    return str(pick_first(market, ("id", "marketId", "_id", "conditionId", "slug")) or "")


def extract_tags(payload: dict[str, Any]) -> list[str]:
    raw_tags = parse_jsonish(pick_first(payload, ("tags", "categories", "category")), [])
    if isinstance(raw_tags, str):
        return [raw_tags]
    if not isinstance(raw_tags, list):
        return []

    tags: list[str] = []
    for item in raw_tags:
        if isinstance(item, str):
            tags.append(item)
        elif isinstance(item, dict):
            value = pick_first(item, ("label", "name", "slug", "title"))
            if value:
                tags.append(str(value))
    return list(dict.fromkeys(tags))


def extract_outcomes_and_prices(market: dict[str, Any]) -> tuple[list[str], list[float | None]]:
    outcomes_raw = parse_jsonish(pick_first(market, ("outcomes", "shortOutcomes")), [])
    prices_raw = parse_jsonish(
        pick_first(market, ("outcomePrices", "outcome_prices", "prices")),
        [],
    )

    outcomes = [str(item) for item in outcomes_raw] if isinstance(outcomes_raw, list) else []
    prices = [as_float(item) for item in prices_raw] if isinstance(prices_raw, list) else []

    if prices and len(prices) < len(outcomes):
        prices.extend([None] * (len(outcomes) - len(prices)))
    return outcomes, prices


def extract_clob_token_ids(market: dict[str, Any]) -> list[str]:
    token_ids_raw = parse_jsonish(
        pick_first(
            market,
            (
                "clobTokenIds",
                "clob_token_ids",
                "clobTokenIDs",
                "tokenIds",
                "token_ids",
            ),
        ),
        [],
    )
    if isinstance(token_ids_raw, list):
        return [str(token_id) for token_id in token_ids_raw if token_id]
    if isinstance(token_ids_raw, str) and token_ids_raw:
        return [token_ids_raw]
    return []


def detect_teams(text: str, aliases_by_team: dict[str, tuple[str, ...]]) -> list[str]:
    normalized = f" {normalize_text(text)} "
    matched: list[str] = []
    for canonical, aliases in aliases_by_team.items():
        alias_values = (canonical, *aliases)
        for alias in alias_values:
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
        return "tournament/other"
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


def result_matches_term(payload: dict[str, Any], term: str) -> bool:
    """Guard against endpoints that ignore unknown search parameters."""
    normalized_term = normalize_text(term)
    searchable = " ".join(
        str(pick_first(payload, keys) or "")
        for keys in (
            ("title", "name", "question"),
            ("slug",),
            ("description",),
            ("ticker",),
        )
    )
    normalized_searchable = normalize_text(searchable)
    term_tokens = [token for token in normalized_term.split() if len(token) > 2]
    return bool(term_tokens) and all(token in normalized_searchable for token in term_tokens)


async def gamma_get(
    client: httpx.AsyncClient,
    endpoint: str,
    params: dict[str, Any],
    attempts: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    url = f"{GAMMA_BASE_URL}{endpoint}"
    try:
        response = await client.get(url, params=params)
        attempts.append(
            {
                "url": str(response.url),
                "status_code": response.status_code,
                "ok": response.is_success,
            }
        )
        response.raise_for_status()
        return collection_from_response(response.json())
    except Exception as exc:
        attempts.append({"url": url, "params": params, "ok": False, "error": str(exc)})
        return []


async def gamma_get_json(
    client: httpx.AsyncClient,
    endpoint: str,
    params: dict[str, Any],
    attempts: list[dict[str, Any]],
) -> Any:
    url = f"{GAMMA_BASE_URL}{endpoint}"
    try:
        response = await client.get(url, params=params)
        content_type = response.headers.get("content-type", "")
        attempt = {
            "url": str(response.url),
            "status_code": response.status_code,
            "content_type": content_type,
            "ok": response.is_success,
        }
        if not response.is_success or "json" not in content_type:
            attempt["body_preview"] = response.text[:300]
        attempts.append(attempt)
        response.raise_for_status()
        return response.json()
    except Exception as exc:
        attempts.append({"url": url, "params": params, "ok": False, "error": str(exc)})
        return None


async def search_gamma(
    client: httpx.AsyncClient,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    attempts: list[dict[str, Any]] = []
    events_by_key: dict[str, dict[str, Any]] = {}
    markets_by_key: dict[str, dict[str, Any]] = {}

    for term in SEARCH_TERMS:
        events: list[dict[str, Any]] = []
        markets: list[dict[str, Any]] = []

        for params in (
            {"q": term, "limit_per_type": 25},
            {"q": term, "limit_per_type": 25, "keep_closed_markets": 1},
        ):
            search_payload = await gamma_get_json(client, "/public-search", params, attempts)
            if isinstance(search_payload, dict):
                events.extend(item for item in search_payload.get("events", []) if isinstance(item, dict))
                markets.extend(item for item in search_payload.get("markets", []) if isinstance(item, dict))

        if not events and not markets:
            for endpoint, params in (
                ("/events", {"search": term, "limit": 25}),
                ("/markets", {"search": term, "limit": 25}),
            ):
                items = [
                    item
                    for item in await gamma_get(client, endpoint, params, attempts)
                    if result_matches_term(item, term)
                ]
                if endpoint == "/events":
                    events.extend(items)
                else:
                    markets.extend(items)

        for event in events:
            key = event_identity(event)
            if key:
                events_by_key[key] = event
            for market in event.get("markets") or []:
                if isinstance(market, dict):
                    market_key = market_identity(market)
                    if market_key:
                        market.setdefault("_parent_event_id", key)
                        market.setdefault("_parent_event_title", pick_first(event, ("title", "name", "question")))
                        market.setdefault("_parent_event_slug", pick_first(event, ("slug",)))
                        markets_by_key[market_key] = market

        for market in markets:
            key = market_identity(market)
            if key:
                markets_by_key[key] = market

    return list(events_by_key.values()), list(markets_by_key.values()), attempts


async def fetch_clob_data(
    client: httpx.AsyncClient,
    token_ids: list[str],
    max_tokens: int,
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    clob_data: dict[str, dict[str, Any]] = {}
    attempts: list[dict[str, Any]] = []
    for token_id in list(dict.fromkeys(token_ids))[:max_tokens]:
        token_data: dict[str, Any] = {}
        for endpoint, key in (("/midpoint", "midpoint"), ("/spread", "spread"), ("/book", "book")):
            try:
                response = await client.get(f"{CLOB_BASE_URL}{endpoint}", params={"token_id": token_id})
                attempts.append(
                    {
                        "url": str(response.url),
                        "status_code": response.status_code,
                        "ok": response.is_success,
                    }
                )
                token_data[f"{key}_status_code"] = response.status_code
                if response.is_success:
                    token_data[key] = response.json()
            except Exception as exc:
                attempts.append(
                    {
                        "url": f"{CLOB_BASE_URL}{endpoint}",
                        "params": {"token_id": token_id},
                        "ok": False,
                        "error": str(exc),
                    }
                )
                token_data[f"{key}_error"] = str(exc)
        clob_data[token_id] = token_data
    return clob_data, attempts


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
        "tags": extract_tags(event),
        "raw": event,
    }


def normalize_market(
    market: dict[str, Any],
    events_by_id: dict[str, dict[str, Any]],
    aliases_by_team: dict[str, tuple[str, ...]],
    clob_data: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    outcomes, prices = extract_outcomes_and_prices(market)
    token_ids = extract_clob_token_ids(market)
    event_id = str(pick_first(market, ("eventId", "event_id", "_parent_event_id")) or "")
    event = events_by_id.get(event_id, {})
    event_title = pick_first(market, ("_parent_event_title",)) or pick_first(event, ("event_title",))
    event_slug = pick_first(market, ("_parent_event_slug",)) or pick_first(event, ("event_slug",))
    question = pick_first(market, ("question", "title", "name", "description")) or ""
    market_slug = pick_first(market, ("slug",))
    combined_text = " ".join(str(part or "") for part in (event_title, event_slug, question, market_slug))
    classification = classify_market(combined_text)

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
        "tags": extract_tags(market),
        "clob_token_ids": token_ids,
        "clob": token_clob,
        "market_type_guess": classification,
        "matched_teams": detect_teams(combined_text, aliases_by_team),
        "likely_world_cup_2026": is_likely_world_cup(combined_text),
        "has_usable_prices": has_gamma_prices or has_clob_prices,
        "raw": market,
    }


def score_market(market: dict[str, Any]) -> float:
    return max(market.get("liquidity") or 0.0, market.get("volume") or 0.0)


def build_recommendation(markets: list[dict[str, Any]]) -> dict[str, Any]:
    wc_markets = [market for market in markets if market["likely_world_cup_2026"]]
    open_markets = [market for market in wc_markets if market.get("active") and not market.get("closed")]
    outright = [market for market in open_markets if market["market_type_guess"] == "tournament outright"]
    match_level = [market for market in open_markets if market["market_type_guess"] == "match winner"]
    priced = [market for market in open_markets if market["has_usable_prices"]]
    liquid = [market for market in open_markets if score_market(market) >= 1_000]

    if outright and priced and liquid and not match_level:
        verdict = "only use for outrights"
    elif wc_markets and priced and liquid:
        verdict = "integrate later"
    elif wc_markets and priced:
        verdict = "integrate later"
    else:
        verdict = "do not use for v1"

    return {
        "verdict": verdict,
        "answers": {
            "active_world_cup_2026_markets": any(market.get("active") and not market.get("closed") for market in wc_markets),
            "outright_winner_markets_with_prices": bool(outright and priced),
            "market_level_observation": "active match-level markets found" if match_level else "mostly long-term tournament markets; no active match-level markets found",
            "titles_structured_for_mapping": bool(any(market["matched_teams"] for market in wc_markets)),
            "prices_source": "Gamma prices and CLOB where token ids are present" if priced else "No usable prices found in this run",
            "liquidity_signal": "some markets exceed lightweight liquidity threshold" if liquid else "liquidity appears thin or unavailable in this run",
            "future_fields_to_store": (
                "polymarket_event_id, polymarket_market_id, market_type, matched_team, "
                "matched_fixture_id, question, slug, outcomes, prices, liquidity, volume, "
                "clob_token_ids, active, closed, end_date, raw_payload, last_fetched_at"
            ),
            "refresh_cadence": "Every 10-30 minutes for active priced markets; daily for discovery/search metadata until tournament week.",
            "biggest_risks": [
                "market matching ambiguity",
                "low or uneven liquidity",
                "missing match-level markets",
                "noisy search results",
                "API shape changes",
                "legal/compliance review for using prediction-market probabilities in betting analysis",
            ],
        },
    }


def api_reachability(attempts: list[dict[str, Any]]) -> dict[str, Any]:
    successes = [attempt for attempt in attempts if attempt.get("ok")]
    tls_failures = [
        attempt
        for attempt in attempts
        if "handshake failure" in str(attempt).lower()
        or "sslv3_alert_handshake_failure" in str(attempt).lower()
    ]
    blocked = [
        attempt
        for attempt in attempts
        if "opendns" in str(attempt).lower()
        or "cisco umbrella" in str(attempt).lower()
        or "block.opendns.com" in str(attempt).lower()
    ]
    return {
        "successful_requests": len(successes),
        "failed_requests": len(attempts) - len(successes),
        "appears_network_blocked": bool(blocked),
        "appears_tls_blocked_or_intercepted": bool(tls_failures),
        "blocked_examples": blocked[:3],
        "tls_failure_examples": tls_failures[:3],
    }


def print_summary(report: dict[str, Any]) -> None:
    summary = report["summary"]
    reachability = report.get("api_reachability", {})
    print("\nPolymarket World Cup discovery summary")
    print("--------------------------------------")
    if reachability.get("appears_network_blocked"):
        print("API reachability: blocked by local network filtering")
    elif reachability.get("appears_tls_blocked_or_intercepted"):
        print("API reachability: TLS handshake failed, likely local filtering/interception")
    else:
        print(f"API reachability: {reachability.get('successful_requests', 0)} successful requests")
    print(f"Events found: {summary['events_found']}")
    print(f"Markets found: {summary['markets_found']}")
    print(f"Likely World Cup-related markets: {summary['likely_world_cup_markets']}")
    print(f"Likely outright markets: {summary['likely_outright_markets']}")
    print(f"Likely match-level markets: {summary['likely_match_level_markets']}")
    print(f"Markets with usable prices: {summary['markets_with_usable_prices']}")
    print(f"Active/open World Cup markets: {summary['active_world_cup_markets']}")
    print(f"Active/open match-level markets: {summary['active_match_level_markets']}")

    print("\nTop 10 candidate markets by liquidity/volume:")
    for index, market in enumerate(report["top_candidate_markets"], start=1):
        title = market.get("market_question") or market.get("event_title") or "(untitled)"
        print(
            f"{index}. {title} | type={market['market_type_guess']} | "
            f"liq={market.get('liquidity')} | vol={market.get('volume')} | "
            f"teams={', '.join(market['matched_teams']) or '-'}"
        )

    print("\nUseful examples:")
    for market in report["useful_examples"]:
        print(f"- {market.get('market_question') or market.get('event_title')} ({market['market_type_guess']})")

    print("\nFalse positives/noise examples:")
    for market in report["noise_examples"]:
        print(f"- {market.get('market_question') or market.get('event_title')}")

    print(f"\nRecommendation: {report['recommendation']['verdict']}")
    print(f"JSON report: {report['report_path']}")


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report-path", default=str(REPORT_PATH))
    parser.add_argument("--max-clob-tokens", type=int, default=30)
    args = parser.parse_args()

    aliases_by_team = load_team_aliases()
    timeout = httpx.Timeout(12.0, connect=5.0)
    headers = {"User-Agent": "matchmind-polymarket-explorer/0.1"}

    async with httpx.AsyncClient(timeout=timeout, headers=headers) as client:
        events_raw, markets_raw, gamma_attempts = await search_gamma(client)
        token_ids: list[str] = []
        for market in markets_raw:
            token_ids.extend(extract_clob_token_ids(market))
        clob_data, clob_attempts = await fetch_clob_data(client, token_ids, max_tokens=args.max_clob_tokens)

    events = [normalize_event(event) for event in events_raw]
    events_by_id = {str(event["event_id"]): event for event in events if event.get("event_id")}
    markets = [normalize_market(market, events_by_id, aliases_by_team, clob_data) for market in markets_raw]

    likely_wc = [market for market in markets if market["likely_world_cup_2026"]]
    active_wc = [market for market in likely_wc if market.get("active") and not market.get("closed")]
    top_candidates = sorted(likely_wc, key=score_market, reverse=True)[:10]
    useful_examples = [market for market in top_candidates if market["market_type_guess"] != "unrelated/noise"][:5]
    noise_examples = [
        market
        for market in markets
        if not market["likely_world_cup_2026"] or market["market_type_guess"] == "unrelated/noise"
    ][:5]
    type_counts = Counter(market["market_type_guess"] for market in markets)

    report_path = Path(args.report_path)
    attempts = gamma_attempts + clob_attempts
    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "gamma_base_url": GAMMA_BASE_URL,
        "clob_base_url": CLOB_BASE_URL,
        "search_terms": list(SEARCH_TERMS),
        "request_attempts": attempts,
        "api_reachability": api_reachability(attempts),
        "summary": {
            "events_found": len(events),
            "markets_found": len(markets),
            "likely_world_cup_markets": len(likely_wc),
            "likely_outright_markets": sum(1 for market in likely_wc if market["market_type_guess"] == "tournament outright"),
            "likely_match_level_markets": sum(1 for market in likely_wc if market["market_type_guess"] == "match winner"),
            "markets_with_usable_prices": sum(1 for market in likely_wc if market["has_usable_prices"]),
            "active_world_cup_markets": len(active_wc),
            "active_outright_markets": sum(1 for market in active_wc if market["market_type_guess"] == "tournament outright"),
            "active_match_level_markets": sum(1 for market in active_wc if market["market_type_guess"] == "match winner"),
            "active_group_winner_markets": sum(1 for market in active_wc if market["market_type_guess"] == "group winner"),
            "active_progress_markets": sum(1 for market in active_wc if market["market_type_guess"] == "team to qualify/progress"),
            "market_type_counts": dict(type_counts),
            "clob_tokens_checked": len(clob_data),
        },
        "top_candidate_markets": top_candidates,
        "useful_examples": useful_examples,
        "noise_examples": noise_examples,
        "events": events,
        "markets": markets,
        "recommendation": build_recommendation(markets),
        "report_path": str(report_path),
    }

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print_summary(report)


if __name__ == "__main__":
    asyncio.run(main())
