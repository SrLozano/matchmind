import unittest

from app.services.bet_parser import parse_bet_message
from app.services.gpt import _extract_json, _fallback_result, _localize_visible_response_es


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

    def test_nested_json_response_text_is_unwrapped(self) -> None:
        result = _extract_json(
            """
            {
              "response": "{\\"response\\":\\"Verdict: FAIR\\\\n\\\\nMy take:\\\\nNested text is unwrapped.\\",\\"confidence_score\\":6}",
              "confidence_score": 6,
              "verdict": "fair",
              "stake_posture": "small"
            }
            """
        )

        self.assertEqual(result.response, "Verdict: FAIR\n\nMy take:\nNested text is unwrapped.")
        self.assertEqual(result.confidence_score, 6)

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

    def test_spanish_visible_response_cleanup_translates_labels_and_enums(self) -> None:
        response = _localize_visible_response_es(
            "Verdict: FAIR\n\nMy take:\nThe crowd signal is useful.\n\nStake posture:\nsmall — keep it controlled.\n\nConfidence:\n6/10"
        )

        self.assertIn("Veredicto: JUSTA / NEUTRAL", response)
        self.assertIn("Mi lectura:", response)
        self.assertIn("señal de mercado", response)
        self.assertIn("Postura de stake:\npequeño", response)
        self.assertIn("Confianza:", response)


if __name__ == "__main__":
    unittest.main()
