import unittest
from datetime import datetime, timezone

from app.services.api_football import (
    compact_match_context,
    find_match_in_matches,
    find_match_from_candidate_teams,
    format_match_context_block,
    is_api_football_rate_limit_error,
)


NOW = datetime.now(timezone.utc).isoformat()


class APIFootballContextTest(unittest.TestCase):
    def setUp(self) -> None:
        self.matches = [
            {
                "home_team": "Spain",
                "away_team": "Germany",
                "home_team_aliases": ["Spain", "España", "Espana"],
                "away_team_aliases": ["Germany", "Alemania"],
                "kickoff_time": "2026-06-15T19:00:00+00:00",
                "stage": "Group Stage - 1",
                "status": "Not Started",
                "home_score": None,
                "away_score": None,
                "venue": "MetLife Stadium",
                "last_fetched_at": NOW,
            },
            {
                "home_team": "Argentina",
                "away_team": "Japan",
                "home_team_aliases": ["Argentina"],
                "away_team_aliases": ["Japan", "Japón", "Japon"],
                "kickoff_time": "2026-06-16T19:00:00+00:00",
                "stage": "Group Stage - 1",
                "status": "Not Started",
                "home_score": None,
                "away_score": None,
                "venue": None,
                "last_fetched_at": NOW,
            },
            {
                "home_team": "United States",
                "away_team": "Mexico",
                "home_team_aliases": ["United States"],
                "away_team_aliases": ["Mexico", "México"],
                "kickoff_time": "2026-06-17T19:00:00+00:00",
                "stage": "Group Stage - 1",
                "status": "Not Started",
                "home_score": None,
                "away_score": None,
                "venue": None,
                "last_fetched_at": NOW,
            },
            {
                "home_team": "South Africa",
                "away_team": "Korea Republic",
                "home_team_aliases": ["South Africa"],
                "away_team_aliases": ["Korea Republic"],
                "kickoff_time": "2026-06-18T19:00:00+00:00",
                "stage": "Group Stage - 1",
                "status": "Not Started",
                "home_score": None,
                "away_score": None,
                "venue": "BMO Field",
                "last_fetched_at": NOW,
            },
        ]

    def test_spanish_message_maps_to_match(self) -> None:
        match = find_match_in_matches("Estoy pensando en meter 20€ a España contra Alemania a cuota 2.10", self.matches)

        self.assertIsNotNone(match)
        self.assertEqual(match["home_team"], "Spain")
        self.assertEqual(match["away_team"], "Germany")

    def test_english_message_maps_to_match(self) -> None:
        match = find_match_in_matches("Thinking of putting €20 on Spain to beat Germany at 2.10", self.matches)

        self.assertIsNotNone(match)
        self.assertEqual(match["home_team"], "Spain")
        self.assertEqual(match["away_team"], "Germany")

    def test_mixed_message_maps_to_match(self) -> None:
        match = find_match_in_matches("Spain vs Alemania at 2.10, cómo lo ves?", self.matches)

        self.assertIsNotNone(match)
        self.assertEqual(match["home_team"], "Spain")
        self.assertEqual(match["away_team"], "Germany")

    def test_api_team_name_still_gets_default_spanish_aliases(self) -> None:
        match = find_match_in_matches("Estados Unidos contra México a 2.40", self.matches)

        self.assertIsNotNone(match)
        self.assertEqual(match["home_team"], "United States")
        self.assertEqual(match["away_team"], "Mexico")

    def test_spanglish_south_africa_south_korea_message_maps_to_fixture(self) -> None:
        match = find_match_in_matches("Quiero apostar al partido de sur africa contra sur korea, en qué estadio es?", self.matches)

        self.assertIsNotNone(match)
        self.assertEqual(match["home_team"], "South Africa")
        self.assertEqual(match["away_team"], "Korea Republic")

    def test_llm_candidate_teams_are_validated_against_fixture_names(self) -> None:
        match = find_match_from_candidate_teams(["South Africa", "South Korea"], self.matches)

        self.assertIsNotNone(match)
        self.assertEqual(match["home_team"], "South Africa")
        self.assertEqual(match["away_team"], "Korea Republic")

    def test_outright_message_with_one_team_does_not_force_match_context(self) -> None:
        match = find_match_in_matches("Argentina campeona del mundial a cuota 6.50", self.matches)

        self.assertIsNone(match)

    def test_vague_message_does_not_match(self) -> None:
        match = find_match_in_matches("¿Qué apuesta ves buena hoy?", self.matches)

        self.assertIsNone(match)

    def test_compact_context_formats_fixture_freshness(self) -> None:
        context = compact_match_context(self.matches[0])
        block = format_match_context_block(context)

        self.assertIn("MATCH CONTEXT:", block)
        self.assertIn("Spain vs Germany", block)
        self.assertIn("fixtures updated", block)

    def test_api_football_rate_limit_error_is_detected_from_provider_key(self) -> None:
        errors = {"rateLimit": "Too many requests. You have exceeded the limit of requests per minute."}

        self.assertTrue(is_api_football_rate_limit_error(errors))

    def test_api_football_non_rate_limit_error_is_not_detected_as_rate_limit(self) -> None:
        errors = {"token": "Invalid API key."}

        self.assertFalse(is_api_football_rate_limit_error(errors))


if __name__ == "__main__":
    unittest.main()
