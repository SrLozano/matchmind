#!/usr/bin/env python3
"""Explore The Odds API World Cup 2026 data for Matchmind.

This script is intentionally standalone. It does not write to Supabase or call
application routers. It fetches provider metadata and a small quota-aware sample
of World Cup odds, then writes a JSON report for parser/schema design.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from statistics import median
from typing import Any

import httpx


BASE_URL = "https://api.the-odds-api.com"
REPORT_PATH = Path("tmp/odds_api_world_cup_discovery.json")
ENV_PATHS = (Path(".env"), Path("apps/api/.env"))
WORLD_CUP_SPORT_KEY = "soccer_fifa_world_cup"
WORLD_CUP_WINNER_SPORT_KEY = "soccer_fifa_world_cup_winner"
DEFAULT_REGIONS = "eu"
DEFAULT_MARKETS = "h2h,spreads,totals"
DEFAULT_OUTRIGHT_MARKETS = "outrights"
DEFAULT_EVENT_MARKETS = "btts,draw_no_bet,double_chance,h2h_3_way,alternate_totals_corners,alternate_totals_cards"
USAGE_HEADERS = ("x-requests-remaining", "x-requests-used", "x-requests-last")


def load_dotenv(paths: tuple[Path, ...] = ENV_PATHS) -> None:
    for path in paths:
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


def load_team_aliases() -> dict[str, tuple[str, ...]]:
    repo_root = Path(__file__).resolve().parents[1]
    api_root = repo_root / "apps" / "api"
    for import_root in (api_root, repo_root):
        import_root_str = str(import_root)
        if import_root_str not in sys.path:
            sys.path.insert(0, import_root_str)

    try:
        from app.services.world_cup_teams import team_aliases_by_canonical

        return team_aliases_by_canonical()
    except Exception:
        return {
            "Argentina": ("Argentina",),
            "Brazil": ("Brazil", "Brasil"),
            "England": ("England", "Inglaterra"),
            "France": ("France", "Francia"),
            "Germany": ("Germany", "Alemania"),
            "Mexico": ("Mexico", "México", "Mejico"),
            "Portugal": ("Portugal",),
            "Spain": ("Spain", "España", "Espana"),
            "United States": ("United States", "USA", "US", "Estados Unidos", "EEUU"),
        }


def normalize_text(value: Any) -> str:
    text = "" if value is None else str(value)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = text.lower().replace(".", " ")
    return " ".join(re.sub(r"[^a-z0-9]+", " ", text).split())


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


def usage_from_headers(headers: httpx.Headers) -> dict[str, str | None]:
    return {header: headers.get(header) for header in USAGE_HEADERS}


def redact_query(url: httpx.URL) -> str:
    return str(url.copy_set_param("apiKey", "REDACTED")) if "apiKey" in dict(url.params) else str(url)


async def api_get(
    client: httpx.AsyncClient,
    path: str,
    params: dict[str, Any],
    attempts: list[dict[str, Any]],
) -> Any:
    url = f"{BASE_URL.rstrip('/')}{path}"
    try:
        response = await client.get(url, params=params)
        content_type = response.headers.get("content-type", "")
        attempt = {
            "url": redact_query(response.url),
            "status_code": response.status_code,
            "ok": response.is_success,
            "usage": usage_from_headers(response.headers),
        }
        if not response.is_success or "json" not in content_type:
            attempt["body_preview"] = response.text[:300]
        attempts.append(attempt)
        response.raise_for_status()
        return response.json()
    except Exception as exc:
        safe_params = {key: ("REDACTED" if key == "apiKey" else value) for key, value in params.items()}
        attempts.append({"url": url, "params": safe_params, "ok": False, "error": str(exc)})
        return None


def collection(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        for key in ("data", "events", "results"):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    return []


def decimal_price(value: Any) -> float | None:
    try:
        price = float(value)
    except (TypeError, ValueError):
        return None
    return price if price > 1 else None


def implied_probability(price: float | None) -> float | None:
    return round(1 / price, 6) if price else None


def market_line_key(market_key: str, outcome: dict[str, Any]) -> str:
    point = outcome.get("point")
    if point is None:
        return market_key
    return f"{market_key}:{point}"


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


def normalize_event(event: dict[str, Any], aliases_by_team: dict[str, tuple[str, ...]]) -> dict[str, Any]:
    text = " ".join(str(event.get(key) or "") for key in ("home_team", "away_team"))
    return {
        "id": event.get("id"),
        "sport_key": event.get("sport_key"),
        "sport_title": event.get("sport_title"),
        "commence_time": event.get("commence_time"),
        "home_team": event.get("home_team"),
        "away_team": event.get("away_team"),
        "matched_teams": detect_teams(text, aliases_by_team),
        "raw": event,
    }


def flatten_odds(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for event in events:
        for bookmaker in event.get("bookmakers") or []:
            if not isinstance(bookmaker, dict):
                continue
            for market in bookmaker.get("markets") or []:
                if not isinstance(market, dict):
                    continue
                for outcome in market.get("outcomes") or []:
                    if not isinstance(outcome, dict):
                        continue
                    price = decimal_price(outcome.get("price"))
                    rows.append(
                        {
                            "event_id": event.get("id"),
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
                            "price": price,
                            "point": outcome.get("point"),
                            "description": outcome.get("description"),
                            "raw_implied_probability": implied_probability(price),
                        }
                    )
    return rows


def build_consensus(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    bookmaker_lines: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if row.get("price") is None:
            continue
        bookmaker_lines[
            (
                row.get("event_id"),
                row.get("bookmaker_key"),
                row.get("market_key"),
                pricing_line_key(row),
            )
        ].append(row)

    no_vig_by_row_key: dict[tuple[Any, ...], float] = {}
    for items in bookmaker_lines.values():
        raw_probabilities = [1 / item["price"] for item in items if item.get("price")]
        overround = sum(raw_probabilities)
        if overround <= 0:
            continue
        for item in items:
            price = item.get("price")
            if price:
                no_vig_by_row_key[row_identity(item)] = round((1 / price) / overround, 6)

    grouped: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if row.get("price") is None:
            continue
        grouped[
            (
                row.get("event_id"),
                row.get("market_key"),
                row.get("outcome_name"),
                row.get("point"),
            )
        ].append(row)

    consensus: list[dict[str, Any]] = []
    for (event_id, market_key, outcome_name, point), items in grouped.items():
        prices = [item["price"] for item in items if item.get("price")]
        implied_values = [1 / price for price in prices]
        no_vig_values = [no_vig_by_row_key[key] for item in items if (key := row_identity(item)) in no_vig_by_row_key]
        best = max(items, key=lambda item: item.get("price") or 0)
        consensus.append(
            {
                "event_id": event_id,
                "market_key": market_key,
                "outcome_name": outcome_name,
                "point": point,
                "bookmaker_count": len({item.get("bookmaker_key") for item in items}),
                "best_price": best.get("price"),
                "best_bookmaker_key": best.get("bookmaker_key"),
                "best_bookmaker_title": best.get("bookmaker_title"),
                "median_price": round(median(prices), 4) if prices else None,
                "min_price": min(prices) if prices else None,
                "max_price": max(prices) if prices else None,
                "median_raw_implied_probability": round(median(implied_values), 6) if implied_values else None,
                "median_no_vig_probability": round(median(no_vig_values), 6) if no_vig_values else None,
            }
        )
    return sorted(
        consensus,
        key=lambda item: (
            str(item.get("event_id") or ""),
            str(item.get("market_key") or ""),
            str(item.get("point") or ""),
            str(item.get("outcome_name") or ""),
        ),
    )


def row_identity(row: dict[str, Any]) -> tuple[Any, ...]:
    return (
        row.get("event_id"),
        row.get("bookmaker_key"),
        row.get("market_key"),
        row.get("outcome_name"),
        row.get("point"),
        row.get("price"),
    )


def summarize_event_markets(payloads: list[dict[str, Any]]) -> dict[str, Any]:
    market_counts = Counter()
    bookmaker_counts = Counter()
    examples: list[dict[str, Any]] = []

    for payload in payloads:
        event_id = payload.get("event_id")
        for bookmaker in payload.get("bookmakers") or []:
            if not isinstance(bookmaker, dict):
                continue
            bookmaker_counts[bookmaker.get("key") or "unknown"] += 1
            for market in bookmaker.get("markets") or []:
                if not isinstance(market, dict):
                    continue
                market_key = market.get("key") or "unknown"
                market_counts[market_key] += 1
                if len(examples) < 20:
                    examples.append(
                        {
                            "event_id": event_id,
                            "bookmaker_key": bookmaker.get("key"),
                            "market_key": market_key,
                            "outcomes_sample": (market.get("outcomes") or [])[:4],
                        }
                    )

    return {
        "market_counts": dict(market_counts),
        "bookmaker_counts": dict(bookmaker_counts),
        "examples": examples,
    }


def api_reachability(attempts: list[dict[str, Any]]) -> dict[str, Any]:
    successes = [attempt for attempt in attempts if attempt.get("ok")]
    return {
        "successful_requests": len(successes),
        "failed_requests": len(attempts) - len(successes),
        "last_usage": next((attempt.get("usage") for attempt in reversed(attempts) if attempt.get("usage")), None),
        "errors": [attempt for attempt in attempts if not attempt.get("ok")][:5],
    }


def build_recommendation(report: dict[str, Any]) -> dict[str, Any]:
    summary = report["summary"]
    featured_market_counts = summary["featured_market_counts"]
    event_market_counts = summary["event_market_counts"]
    has_world_cup = summary["world_cup_sport_active"]
    has_events = summary["events_found"] > 0
    has_featured = bool(featured_market_counts)
    has_outrights = summary["outright_rows_found"] > 0

    if has_world_cup and has_events and has_featured:
        verdict = "integrate featured match odds"
    elif has_world_cup and has_outrights:
        verdict = "integrate outrights first"
    elif has_world_cup:
        verdict = "sport available; rerun closer to tournament"
    else:
        verdict = "not ready for integration"

    return {
        "verdict": verdict,
        "answers": {
            "world_cup_sport_available": has_world_cup,
            "match_events_available": has_events,
            "featured_markets_available": sorted(featured_market_counts),
            "additional_markets_seen": sorted(event_market_counts),
            "outrights_available": has_outrights,
            "best_v1_surface": "Daily Feed and Odds Analyzer" if has_featured else "Provider monitoring",
            "fields_to_store": (
                "odds_api_event_id, sport_key, commence_time, teams, bookmaker_key, "
                "market_key, outcome_name, point, price, bookmaker_last_update, "
                "raw_payload, fetched_at"
            ),
        },
    }


def print_summary(report: dict[str, Any]) -> None:
    summary = report["summary"]
    reachability = report["api_reachability"]

    print("\nThe Odds API World Cup discovery summary")
    print("----------------------------------------")
    print(f"API reachability: {reachability['successful_requests']} successful, {reachability['failed_requests']} failed")
    if reachability.get("last_usage"):
        print(f"Last usage headers: {reachability['last_usage']}")
    print(f"World Cup sport active: {summary['world_cup_sport_active']}")
    print(f"World Cup winner sport active: {summary['world_cup_winner_sport_active']}")
    print(f"Events found: {summary['events_found']}")
    print(f"Featured odds events found: {summary['featured_odds_events_found']}")
    print(f"Featured odds rows: {summary['featured_rows_found']}")
    print(f"Outright odds rows: {summary['outright_rows_found']}")
    print(f"Featured markets: {summary['featured_market_counts']}")
    print(f"Additional sampled markets: {summary['event_market_counts']}")
    print(f"Bookmakers seen: {summary['bookmaker_counts']}")
    print(f"Recommendation: {report['recommendation']['verdict']}")
    print(f"JSON report: {report['report_path']}")


async def main() -> None:
    global BASE_URL

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report-path", default=str(REPORT_PATH))
    parser.add_argument("--base-url", default=os.environ.get("ODDS_API_BASE_URL", BASE_URL))
    parser.add_argument("--regions", default=os.environ.get("ODDS_API_REGIONS", DEFAULT_REGIONS))
    parser.add_argument("--bookmakers", default=os.environ.get("ODDS_API_BOOKMAKERS", ""))
    parser.add_argument("--markets", default=os.environ.get("ODDS_API_MARKETS", DEFAULT_MARKETS))
    parser.add_argument("--outright-markets", default=DEFAULT_OUTRIGHT_MARKETS)
    parser.add_argument("--event-markets", default=DEFAULT_EVENT_MARKETS)
    parser.add_argument("--max-event-market-checks", type=int, default=3)
    parser.add_argument("--max-event-odds-checks", type=int, default=2)
    parser.add_argument("--skip-additional", action="store_true")
    args = parser.parse_args()

    BASE_URL = args.base_url

    load_dotenv()
    api_key = os.environ.get("ODDS_API_KEY")
    if not api_key:
        raise SystemExit("ODDS_API_KEY is not configured in the environment or .env")

    aliases_by_team = load_team_aliases()
    timeout = httpx.Timeout(20.0, connect=8.0)
    attempts: list[dict[str, Any]] = []
    params_base = {"apiKey": api_key, "dateFormat": "iso"}
    if args.bookmakers:
        odds_source_params = {"bookmakers": args.bookmakers}
    else:
        odds_source_params = {"regions": args.regions}

    async with httpx.AsyncClient(timeout=timeout, headers={"User-Agent": "matchmind-odds-api-explorer/0.1"}) as client:
        sports_payload = await api_get(client, "/v4/sports", {"apiKey": api_key, "all": "true"}, attempts)
        sports = collection(sports_payload)

        events_payload = await api_get(
            client,
            f"/v4/sports/{WORLD_CUP_SPORT_KEY}/events",
            params_base,
            attempts,
        )
        events_raw = collection(events_payload)
        events = [normalize_event(event, aliases_by_team) for event in events_raw]

        featured_payload = await api_get(
            client,
            f"/v4/sports/{WORLD_CUP_SPORT_KEY}/odds",
            {
                **params_base,
                **odds_source_params,
                "markets": args.markets,
                "oddsFormat": "decimal",
            },
            attempts,
        )
        featured_odds = collection(featured_payload)

        outright_payload = await api_get(
            client,
            f"/v4/sports/{WORLD_CUP_WINNER_SPORT_KEY}/odds",
            {
                **params_base,
                **odds_source_params,
                "markets": args.outright_markets,
                "oddsFormat": "decimal",
            },
            attempts,
        )
        outright_odds = collection(outright_payload)

        event_markets_payloads: list[dict[str, Any]] = []
        event_additional_odds_payloads: list[dict[str, Any]] = []
        if not args.skip_additional:
            sample_event_ids = [event.get("id") for event in events if event.get("id")]
            for event_id in sample_event_ids[: args.max_event_market_checks]:
                payload = await api_get(
                    client,
                    f"/v4/sports/{WORLD_CUP_SPORT_KEY}/events/{event_id}/markets",
                    {**params_base, **odds_source_params},
                    attempts,
                )
                if isinstance(payload, dict):
                    payload["event_id"] = event_id
                    event_markets_payloads.append(payload)
                elif isinstance(payload, list):
                    event_markets_payloads.append({"event_id": event_id, "bookmakers": payload})

            for event_id in sample_event_ids[: args.max_event_odds_checks]:
                payload = await api_get(
                    client,
                    f"/v4/sports/{WORLD_CUP_SPORT_KEY}/events/{event_id}/odds",
                    {
                        **params_base,
                        **odds_source_params,
                        "markets": args.event_markets,
                        "oddsFormat": "decimal",
                    },
                    attempts,
                )
                if isinstance(payload, dict):
                    payload["event_id"] = event_id
                    event_additional_odds_payloads.append(payload)

    featured_rows = flatten_odds(featured_odds)
    outright_rows = flatten_odds(outright_odds)
    additional_rows = flatten_odds(event_additional_odds_payloads)
    consensus = build_consensus(featured_rows)
    outright_consensus = build_consensus(outright_rows)
    additional_summary = summarize_event_markets(event_markets_payloads + event_additional_odds_payloads)
    sports_by_key = {sport.get("key"): sport for sport in sports if sport.get("key")}

    report_path = Path(args.report_path)
    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "base_url": BASE_URL,
        "sport_keys": [WORLD_CUP_SPORT_KEY, WORLD_CUP_WINNER_SPORT_KEY],
        "request_config": {
            "regions": args.regions,
            "bookmakers": args.bookmakers or None,
            "markets": args.markets,
            "outright_markets": args.outright_markets,
            "event_markets": None if args.skip_additional else args.event_markets,
            "max_event_market_checks": 0 if args.skip_additional else args.max_event_market_checks,
            "max_event_odds_checks": 0 if args.skip_additional else args.max_event_odds_checks,
        },
        "request_attempts": attempts,
        "api_reachability": api_reachability(attempts),
        "summary": {
            "sports_found": len(sports),
            "world_cup_sport_active": bool(sports_by_key.get(WORLD_CUP_SPORT_KEY, {}).get("active")),
            "world_cup_winner_sport_active": bool(sports_by_key.get(WORLD_CUP_WINNER_SPORT_KEY, {}).get("active")),
            "events_found": len(events),
            "featured_odds_events_found": len(featured_odds),
            "featured_rows_found": len(featured_rows),
            "outright_odds_events_found": len(outright_odds),
            "outright_rows_found": len(outright_rows),
            "additional_rows_found": len(additional_rows),
            "featured_market_counts": dict(Counter(row["market_key"] for row in featured_rows if row.get("market_key"))),
            "outright_market_counts": dict(Counter(row["market_key"] for row in outright_rows if row.get("market_key"))),
            "event_market_counts": additional_summary["market_counts"],
            "bookmaker_counts": dict(Counter(row["bookmaker_key"] for row in featured_rows + outright_rows + additional_rows if row.get("bookmaker_key"))),
            "event_ids_sampled_for_additional_markets": [
                payload.get("event_id") for payload in event_markets_payloads + event_additional_odds_payloads
            ],
        },
        "world_cup_sport": sports_by_key.get(WORLD_CUP_SPORT_KEY),
        "world_cup_winner_sport": sports_by_key.get(WORLD_CUP_WINNER_SPORT_KEY),
        "events": events,
        "featured_odds_raw": featured_odds,
        "featured_odds_rows": featured_rows,
        "featured_consensus": consensus,
        "outright_odds_raw": outright_odds,
        "outright_odds_rows": outright_rows,
        "outright_consensus": outright_consensus,
        "event_markets_raw": event_markets_payloads,
        "additional_event_odds_raw": event_additional_odds_payloads,
        "additional_event_odds_rows": additional_rows,
        "additional_market_summary": additional_summary,
        "recommendation": {},
        "report_path": str(report_path),
    }
    report["recommendation"] = build_recommendation(report)

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print_summary(report)


if __name__ == "__main__":
    asyncio.run(main())
