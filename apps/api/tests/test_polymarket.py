import asyncio
import unittest

from app.services.bet_parser import parse_bet_message
from app.services.polymarket import (
    build_polymarket_context_for_chat,
    detect_polymarket_intent,
    find_best_polymarket_market,
    format_polymarket_context_block,
    get_market_signals,
    normalize_polymarket_market,
    polymarket_market_to_row,
    polymarket_market_to_snapshot_row,
)


class PolymarketContextTest(unittest.TestCase):
    def test_detects_tournament_outright_intent(self) -> None:
        parsed = parse_bet_message("Should I bet Spain to win the World Cup at 9.00?")

        self.assertEqual(detect_polymarket_intent(parsed.original_message, parsed), "tournament_outright")

    def test_does_not_use_polymarket_for_match_winner(self) -> None:
        parsed = parse_bet_message("Should I bet Spain to beat Germany at 2.10?")

        self.assertIsNone(detect_polymarket_intent(parsed.original_message, parsed))

    def test_finds_spain_outright_market_from_discovery_file(self) -> None:
        context = asyncio.run(build_polymarket_context_for_chat("Should I bet Spain to win the World Cup at 9.00?"))

        self.assertIsNotNone(context)
        self.assertTrue(context["matched"])
        self.assertEqual(context["market_type"], "tournament_outright")
        self.assertEqual(context["team"], "Spain")
        self.assertGreater(context["implied_probability"], 0)
        self.assertGreaterEqual(context["signal_quality_score"], 40)

    def test_group_winner_context_includes_group(self) -> None:
        context = asyncio.run(build_polymarket_context_for_chat("Spain to win Group H, is that good value?"))

        self.assertIsNotNone(context)
        self.assertTrue(context["matched"])
        self.assertEqual(context["market_type"], "group_winner")
        self.assertEqual(context["group"], "H")

    def test_general_outright_question_uses_crowd_favorite_not_liquidity_longshot(self) -> None:
        context = asyncio.run(build_polymarket_context_for_chat("Who does the market think will win the World Cup?"))

        self.assertIsNotNone(context)
        self.assertTrue(context["matched"])
        self.assertEqual(context["market_type"], "tournament_outright")
        self.assertEqual(context["team"], "France")

    def test_supported_but_unmatched_context_is_explicit(self) -> None:
        parsed = parse_bet_message("Spain to win the World Cup")
        market = find_best_polymarket_market(parsed, "advance_to_knockout", [])

        self.assertIsNone(market)

    def test_context_block_uses_crowd_probability_language(self) -> None:
        context = asyncio.run(build_polymarket_context_for_chat("Should I bet Spain to win the World Cup at 9.00?"))
        block = format_polymarket_context_block(context)

        self.assertIn("POLYMARKET CONTEXT:", block)
        self.assertIn("Crowd probability", block)
        self.assertIn("prediction-market crowd probability", block)

    def test_market_signals_returns_compact_ranked_signals(self) -> None:
        signals = asyncio.run(get_market_signals(limit=3, market_type="tournament_outright"))

        self.assertEqual(len(signals), 3)
        self.assertTrue(all(signal["matched"] for signal in signals))
        self.assertTrue(all(signal["market_type"] == "tournament_outright" for signal in signals))

    def test_market_row_contains_database_cache_fields(self) -> None:
        market = normalize_polymarket_market(
            {
                "event_id": "event-1",
                "event_title": "FIFA World Cup Group H Winner",
                "event_slug": "fifa-world-cup-group-h-winner",
                "market_id": "market-1",
                "market_question": "Will Spain win Group H in the 2026 FIFA World Cup?",
                "market_slug": "will-spain-win-group-h-in-the-2026-fifa-world-cup",
                "outcomes": ["Yes", "No"],
                "outcome_prices": [0.8, 0.2],
                "liquidity": 10_000,
                "volume": 20_000,
                "active": True,
                "closed": False,
                "end_date": "2026-06-27T00:00:00Z",
                "clob_token_ids": ["yes-token", "no-token"],
                "market_type_guess": "group winner",
                "matched_teams": ["Spain"],
                "likely_world_cup_2026": True,
                "raw": {"conditionId": "condition-1", "bestBid": 0.79, "bestAsk": 0.81, "spread": 0.02},
            },
            "2026-05-09T10:00:00+00:00",
        )
        row = polymarket_market_to_row(market)
        snapshot = polymarket_market_to_snapshot_row(market)

        self.assertEqual(row["polymarket_market_id"], "market-1")
        self.assertEqual(row["condition_id"], "condition-1")
        self.assertEqual(row["market_type"], "group_winner")
        self.assertEqual(row["matched_team"], "Spain")
        self.assertEqual(row["matched_group"], "H")
        self.assertEqual(row["yes_price"], 0.8)
        self.assertEqual(row["no_price"], 0.2)
        self.assertTrue(row["is_usable"])
        self.assertEqual(snapshot["polymarket_market_id"], "market-1")
        self.assertEqual(snapshot["yes_price"], 0.8)


if __name__ == "__main__":
    unittest.main()
