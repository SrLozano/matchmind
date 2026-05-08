import unittest

from app.services.bet_parser import parse_bet_message
from app.services.gpt import _extract_json, _fallback_result


class GPTResponseParsingTest(unittest.TestCase):
    def test_structured_json_fields_are_normalized(self) -> None:
        result = _extract_json(
            """
            {
              "response": "Verdict: RISKY\\n\\nConfidence:\\n5.5/10",
              "confidence_score": 5.5,
              "verdict": "risky",
              "implied_probability": 47.62,
              "stake_posture": "Very Small"
            }
            """
        )

        self.assertEqual(result.confidence_score, 5.5)
        self.assertEqual(result.verdict, "RISKY")
        self.assertEqual(result.implied_probability, 0.4762)
        self.assertEqual(result.stake_posture, "very small")

    def test_plain_text_fallback_extracts_score_and_verdict(self) -> None:
        result = _extract_json("Verdict: AVOID\n\nStake posture:\navoid\n\nConfidence:\n4/10")

        self.assertEqual(result.confidence_score, 4)
        self.assertEqual(result.verdict, "AVOID")
        self.assertEqual(result.stake_posture, "avoid")

    def test_deterministic_fallback_contains_required_structure(self) -> None:
        parsed = parse_bet_message("Brazil to beat Japan at 1.30")
        result = _fallback_result(parsed)

        self.assertIn("Verdict:", result.response)
        self.assertIn("Odds check:", result.response)
        self.assertIn("Stake posture:", result.response)
        self.assertEqual(result.implied_probability, 0.7692)
        self.assertIn(result.stake_posture, {"avoid", "very small", "small", "medium"})

    def test_spanish_fallback_uses_spanish_response_but_english_metadata(self) -> None:
        parsed = parse_bet_message("Brasil gana a Japón a 1,30")
        result = _fallback_result(parsed)

        self.assertIn("Veredicto:", result.response)
        self.assertIn("Chequeo de cuota:", result.response)
        self.assertEqual(result.verdict, "RISKY")
        self.assertEqual(result.stake_posture, "very small")
        self.assertEqual(result.implied_probability, 0.7692)

    def test_spanish_plain_text_fallback_normalizes_metadata(self) -> None:
        result = _extract_json("Veredicto: ARRIESGADA\n\nPostura de stake:\nmuy pequeño\n\nConfianza:\n5.5/10")

        self.assertEqual(result.confidence_score, 5.5)
        self.assertEqual(result.verdict, "RISKY")
        self.assertEqual(result.stake_posture, "very small")


if __name__ == "__main__":
    unittest.main()
