import asyncio
import unittest

from app.services.bet_parser import parse_bet_message
from app.services.odds_api import (
    build_bookmaker_context_for_chat,
    build_consensus,
    flatten_odds,
    format_bookmaker_context_block,
    get_compact_odds_matches,
    get_bookmaker_data_from_discovery_file,
    normalize_discovery_consensus,
    value_edge,
)


class OddsAPIServiceTest(unittest.TestCase):
    def test_flatten_and_consensus_compute_no_vig_probability(self) -> None:
        events = [
            {
                "id": "event-1",
                "sport_key": "soccer_fifa_world_cup",
                "commence_time": "2026-06-11T19:00:00Z",
                "home_team": "Spain",
                "away_team": "Germany",
                "bookmakers": [
                    {
                        "key": "book-a",
                        "title": "Book A",
                        "last_update": "2026-05-10T10:00:00Z",
                        "markets": [
                            {
                                "key": "h2h",
                                "last_update": "2026-05-10T10:00:00Z",
                                "outcomes": [
                                    {"name": "Spain", "price": 2.4},
                                    {"name": "Draw", "price": 3.2},
                                    {"name": "Germany", "price": 3.1},
                                ],
                            }
                        ],
                    },
                    {
                        "key": "book-b",
                        "title": "Book B",
                        "last_update": "2026-05-10T10:00:00Z",
                        "markets": [
                            {
                                "key": "h2h",
                                "last_update": "2026-05-10T10:00:00Z",
                                "outcomes": [
                                    {"name": "Spain", "price": 2.5},
                                    {"name": "Draw", "price": 3.1},
                                    {"name": "Germany", "price": 3.0},
                                ],
                            }
                        ],
                    },
                ],
            }
        ]

        rows = flatten_odds(events, fetched_at="2026-05-10T10:00:00+00:00")
        consensus = build_consensus(rows, fetched_at="2026-05-10T10:00:00+00:00")
        spain = next(row for row in consensus if row["outcome_name"] == "Spain")

        self.assertEqual(len(rows), 6)
        self.assertEqual(spain["bookmaker_count"], 2)
        self.assertEqual(spain["best_price"], 2.5)
        self.assertAlmostEqual(spain["median_price"], 2.45)
        self.assertGreater(spain["no_vig_probability"], 0.37)
        self.assertLess(spain["no_vig_probability"], 0.39)

    def test_discovery_consensus_normalizes_event_id_and_probability(self) -> None:
        rows = normalize_discovery_consensus(
            [
                {
                    "event_id": "event-1",
                    "market_key": "h2h",
                    "outcome_name": "Spain",
                    "best_price": 2.5,
                    "median_no_vig_probability": 0.38,
                    "bookmaker_count": 12,
                }
            ],
            "2026-05-10T10:00:00+00:00",
        )

        self.assertEqual(rows[0]["odds_api_event_id"], "event-1")
        self.assertEqual(rows[0]["outcome_team"], "Spain")
        self.assertEqual(rows[0]["no_vig_probability"], 0.38)

    def test_spread_consensus_keeps_signed_handicap_identity(self) -> None:
        rows = flatten_odds(
            [
                {
                    "id": "event-1",
                    "sport_key": "soccer_fifa_world_cup",
                    "commence_time": "2026-06-11T19:00:00Z",
                    "home_team": "Spain",
                    "away_team": "Germany",
                    "bookmakers": [
                        {
                            "key": "book-a",
                            "title": "Book A",
                            "last_update": "2026-05-10T10:00:00Z",
                            "markets": [
                                {
                                    "key": "spreads",
                                    "last_update": "2026-05-10T10:00:00Z",
                                    "outcomes": [
                                        {"name": "Spain", "price": 1.91, "point": -1.5},
                                        {"name": "Germany", "price": 1.91, "point": 1.5},
                                        {"name": "Spain", "price": 2.1, "point": 1.5},
                                        {"name": "Germany", "price": 1.75, "point": -1.5},
                                    ],
                                }
                            ],
                        }
                    ],
                }
            ],
            fetched_at="2026-05-10T10:00:00+00:00",
        )
        consensus = build_consensus(rows, fetched_at="2026-05-10T10:00:00+00:00")

        conflict_keys = [
            (row["odds_api_event_id"], row["market_key"], row["outcome_name"], row["line_key"])
            for row in consensus
        ]

        self.assertEqual(len(conflict_keys), len(set(conflict_keys)))
        self.assertIn(("event-1", "spreads", "Spain", "spreads:-1.5"), conflict_keys)
        self.assertIn(("event-1", "spreads", "Spain", "spreads:1.5"), conflict_keys)

    def test_value_edge_compares_user_price_to_consensus(self) -> None:
        edge = value_edge(2.80, {"no_vig_probability": 0.40})

        self.assertEqual(edge, 0.0429)

    def test_context_from_discovery_file_matches_world_cup_fixture(self) -> None:
        parsed = parse_bet_message("Mexico to beat South Africa at 1.95")
        context = asyncio.run(
            build_bookmaker_context_for_chat(
                parsed.original_message,
                parsed_bet=parsed,
                match_context={
                    "home_team": "Mexico",
                    "away_team": "South Africa",
                    "kickoff_time": "2026-06-11T19:00:00Z",
                },
            )
        )

        self.assertIsNotNone(context)
        self.assertTrue(context["matched"])
        self.assertEqual(context["market_key"], "h2h")
        self.assertEqual(context["outcome_name"], "Mexico")
        self.assertGreater(context["bookmaker_count"], 1)

    def test_context_block_contains_bookmaker_language(self) -> None:
        block = format_bookmaker_context_block(
            {
                "matched": True,
                "event": "Mexico vs South Africa",
                "market_key": "h2h",
                "outcome_name": "Mexico",
                "user_odds": 1.95,
                "user_implied_probability": 0.5128,
                "consensus_probability": 0.49,
                "best_price": 2.05,
                "best_bookmaker_title": "Pinnacle",
                "median_price": 1.98,
                "bookmaker_count": 12,
                "last_fetched_at": "2026-05-10T10:00:00+00:00",
                "value_edge": 0.0228,
            }
        )

        self.assertIn("BOOKMAKER CONTEXT:", block)
        self.assertIn("Bookmaker no-vig consensus probability", block)
        self.assertIn("Best cached price", block)

    def test_broad_recommendation_uses_discovery_context(self) -> None:
        parsed = parse_bet_message("I have 100€ and want World Cup recommendations")
        context = asyncio.run(build_bookmaker_context_for_chat(parsed.original_message, parsed_bet=parsed))

        self.assertIsNotNone(context)
        self.assertTrue(context["matched"])
        self.assertEqual(context["mode"], "discovery_shortlist")
        self.assertGreaterEqual(len(context["matches"]), 1)

        block = format_bookmaker_context_block(context)
        self.assertIn("BOOKMAKER DISCOVERY CONTEXT:", block)
        self.assertIn("Option 1:", block)

    def test_compact_odds_matches_from_discovery_file(self) -> None:
        matches = asyncio.run(get_compact_odds_matches(limit=3))

        self.assertGreaterEqual(len(matches), 1)
        self.assertIn("h2h", matches[0])
        self.assertIn("featured_markets", matches[0])

    def test_discovery_file_includes_outright_event_metadata(self) -> None:
        events, consensus = get_bookmaker_data_from_discovery_file()
        event_ids = {event["odds_api_event_id"] for event in events}
        outright_event_ids = {
            row["odds_api_event_id"]
            for row in consensus
            if row["market_key"] == "outrights"
        }

        self.assertTrue(outright_event_ids)
        self.assertTrue(outright_event_ids.issubset(event_ids))


if __name__ == "__main__":
    unittest.main()
