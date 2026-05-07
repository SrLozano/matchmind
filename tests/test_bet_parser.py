import unittest

from app.services.bet_parser import parse_bet_message


class BetParserTest(unittest.TestCase):
    def test_message_with_teams_odds_and_stake(self) -> None:
        parsed = parse_bet_message("Thinking of betting €20 on Spain to beat Germany at 2.10")

        self.assertEqual(parsed.teams, ["Spain", "Germany"])
        self.assertEqual(parsed.market_type, "Match winner")
        self.assertEqual(parsed.odds, 2.10)
        self.assertEqual(parsed.implied_probability, 0.4762)
        self.assertEqual(parsed.stake_amount, 20)
        self.assertEqual(parsed.stake_currency, "EUR")

    def test_message_with_odds_but_no_stake(self) -> None:
        parsed = parse_bet_message("Argentina to win the World Cup at 6.50?")

        self.assertEqual(parsed.teams, ["Argentina"])
        self.assertEqual(parsed.market_type, "Tournament outright")
        self.assertEqual(parsed.odds, 6.50)
        self.assertEqual(parsed.implied_probability, 0.1538)
        self.assertIsNone(parsed.stake_amount)

    def test_message_with_teams_but_no_odds(self) -> None:
        parsed = parse_bet_message("I like England to win, thoughts?")

        self.assertEqual(parsed.teams, ["England"])
        self.assertEqual(parsed.market_type, "Match winner")
        self.assertIsNone(parsed.odds)
        self.assertIn("odds", parsed.missing_fields)

    def test_vague_message_with_insufficient_info(self) -> None:
        parsed = parse_bet_message("Should I take it?")

        self.assertTrue(parsed.needs_clarification)
        self.assertIn("teams", parsed.missing_fields)
        self.assertIn("odds", parsed.missing_fields)

    def test_high_probability_odds(self) -> None:
        parsed = parse_bet_message("Brazil to beat Japan at 1.30")

        self.assertEqual(parsed.odds, 1.30)
        self.assertEqual(parsed.implied_probability, 0.7692)

    def test_low_probability_odds(self) -> None:
        parsed = parse_bet_message("Portugal to win the World Cup at 7.50")

        self.assertEqual(parsed.odds, 7.50)
        self.assertEqual(parsed.implied_probability, 0.1333)

    def test_spanish_message_with_teams_odds_and_stake(self) -> None:
        parsed = parse_bet_message("Estoy pensando en apostar 20€ a España gana a Alemania a 2,10")

        self.assertEqual(parsed.detected_language, "es")
        self.assertEqual(parsed.teams, ["Spain", "Germany"])
        self.assertEqual(parsed.raw_match_text, "España vs Alemania")
        self.assertEqual(parsed.market_type, "Match winner")
        self.assertEqual(parsed.odds, 2.10)
        self.assertEqual(parsed.implied_probability, 0.4762)
        self.assertEqual(parsed.stake_amount, 20)
        self.assertEqual(parsed.stake_currency, "EUR")

    def test_spanish_over_goals_market(self) -> None:
        parsed = parse_bet_message("Más de 2,5 goles en Brasil vs Portugal a cuota 1,85")

        self.assertEqual(parsed.detected_language, "es")
        self.assertEqual(parsed.teams, ["Brazil", "Portugal"])
        self.assertEqual(parsed.market_type, "Over goals")
        self.assertEqual(parsed.odds, 1.85)
        self.assertEqual(parsed.implied_probability, 0.5405)

    def test_spanish_outright_market_and_team_alias(self) -> None:
        parsed = parse_bet_message("Argentina campeona del Mundial a 6,50?")

        self.assertEqual(parsed.detected_language, "es")
        self.assertEqual(parsed.teams, ["Argentina"])
        self.assertEqual(parsed.market_type, "Tournament outright")
        self.assertEqual(parsed.odds, 6.50)


if __name__ == "__main__":
    unittest.main()
