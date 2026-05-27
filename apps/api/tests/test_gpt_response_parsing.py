import json
import unittest

from app.services.bet_parser import parse_bet_message
from app.models.chat import AIChatResult
from app.services.gpt import (
    _build_user_context,
    _chat_response_format,
    _classify_chat_intent,
    _compact_conversation_memory,
    _extract_json,
    _fallback_result,
    _finalize_result,
    _localize_visible_response_es,
    _strip_visible_metadata_lines,
)


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

        self.assertIn("Short version:", result.response)
        self.assertIn("Confidence:", result.response)
        self.assertEqual(result.implied_probability, 0.7692)
        self.assertIn(result.stake_posture, {"avoid", "very small", "small", "medium"})

    def test_broad_bankroll_question_gets_coaching_fallback(self) -> None:
        parsed = parse_bet_message("I have 100€ and I want to bet, give me some recommendations")
        result = _fallback_result(parsed)

        self.assertEqual(_classify_chat_intent(parsed.original_message, parsed), "discovery_or_bankroll_request")
        self.assertIn("shortlist", result.response)
        self.assertIn("risk style", result.response)
        self.assertEqual(result.verdict, "NOT ENOUGH INFO")
        self.assertEqual(result.stake_posture, "avoid")

    def test_spanish_bankroll_question_gets_coaching_fallback(self) -> None:
        parsed = parse_bet_message("Tengo 100€ y quiero recomendaciones para apostar")
        result = _fallback_result(parsed)

        self.assertEqual(_classify_chat_intent(parsed.original_message, parsed), "discovery_or_bankroll_request")
        self.assertIn("shortlist", result.response)
        self.assertIn("perfil de riesgo", result.response)
        self.assertEqual(result.verdict, "NOT ENOUGH INFO")
        self.assertEqual(result.stake_posture, "avoid")

    def test_spanish_fallback_uses_spanish_response_but_english_metadata(self) -> None:
        parsed = parse_bet_message("Brasil gana a Japón a 1,30")
        result = _fallback_result(parsed)

        self.assertIn("Resumen rápido:", result.response)
        self.assertIn("Confianza:", result.response)
        self.assertEqual(result.verdict, "FAIR")
        self.assertEqual(result.stake_posture, "very small")
        self.assertEqual(result.implied_probability, 0.7692)

    def test_spanish_plain_text_fallback_normalizes_metadata(self) -> None:
        result = _extract_json("Veredicto: ARRIESGADA\n\nPostura de stake:\nmuy pequeño\n\nConfianza:\n5.5/10")

        self.assertEqual(result.confidence_score, 5.5)
        self.assertEqual(result.verdict, "RISKY")
        self.assertEqual(result.stake_posture, "very small")

    def test_spanish_visible_response_cleanup_translates_labels_and_enums(self) -> None:
        response = _localize_visible_response_es(
            "Verdict: FAIR\n\nMy take:\nUSA vs South Korea is useful. The crowd signal is useful.\n\nStake posture:\nsmall — keep it controlled.\n\nConfidence:\n6/10"
        )

        self.assertIn("Veredicto: JUSTA / NEUTRAL", response)
        self.assertIn("Mi lectura:", response)
        self.assertIn("Estados Unidos vs Corea del Sur", response)
        self.assertIn("señal de mercado", response)
        self.assertIn("Postura de stake:\npequeño", response)
        self.assertIn("Confianza:", response)

    def test_visible_metadata_lines_are_stripped_for_structured_ui(self) -> None:
        response = _strip_visible_metadata_lines(
            "Me gusta como plan pequeño.\n\n**Veredicto:** NO HAY INFO SUFICIENTE.\n**Confianza:** 4/10.\nPostura de stake: evitar"
        )

        self.assertEqual(response, "Me gusta como plan pequeño.")

    def test_finalize_spanish_response_localizes_teams_and_removes_duplicate_metadata(self) -> None:
        parsed = parse_bet_message("Tengo 100€ y quiero recomendaciones")
        result = _finalize_result(
            AIChatResult(
                response="USA vs South Korea is only a candidate.\n\nVerdict: NOT ENOUGH INFO\nConfidence: 4/10",
                confidence_score=4,
                verdict="NOT ENOUGH INFO",
                stake_posture="avoid",
            ),
            parsed,
        )

        self.assertIn("Estados Unidos vs Corea del Sur", result.response)
        self.assertNotIn("Veredicto:", result.response)
        self.assertNotIn("Confianza:", result.response)

    def test_chat_response_format_uses_strict_json_schema(self) -> None:
        response_format = _chat_response_format()
        schema = response_format["json_schema"]["schema"]

        self.assertEqual(response_format["type"], "json_schema")
        self.assertTrue(response_format["json_schema"]["strict"])
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(
            schema["required"],
            ["response", "confidence_score", "verdict", "implied_probability", "stake_posture"],
        )

    def test_finalize_result_fills_missing_metadata(self) -> None:
        parsed = parse_bet_message("Brazil to beat Japan at 1.80")
        result = _finalize_result(
            AIChatResult(response="I lean fair at that number.", confidence_score=6),
            parsed,
        )

        self.assertEqual(result.implied_probability, 0.5556)
        self.assertEqual(result.verdict, "FAIR")
        self.assertEqual(result.stake_posture, "small")

    def test_conversation_memory_is_compacted_for_prompt_context(self) -> None:
        memory = _compact_conversation_memory(
            [
                {"role": "system", "content": "ignore"},
                {"role": "user", "content": "Spain to win Group A at 1.80"},
                {"role": "assistant", "content": "I would pass at that number."},
                {"role": "user", "content": "x" * 1300},
            ],
            max_turns=4,
        )

        self.assertEqual([message["role"] for message in memory], ["user", "assistant", "user"])
        self.assertEqual(len(memory[-1]["content"]), 1200)

    def test_user_context_includes_conversation_memory(self) -> None:
        parsed = parse_bet_message("What if I can get 2.10?")
        context = json.loads(
            _build_user_context(
                "What if I can get 2.10?",
                parsed,
                conversation_memory=[
                    {"role": "user", "content": "Brazil to beat Japan at 1.80"},
                    {"role": "assistant", "content": "I lean fair, but not exciting."},
                ],
            )
        )

        self.assertEqual(context["conversation_memory"][0]["content"], "Brazil to beat Japan at 1.80")
        self.assertEqual(context["user_message"], "What if I can get 2.10?")

    def test_user_context_includes_chat_intent(self) -> None:
        parsed = parse_bet_message("Build me a balanced shortlist for today")
        context = json.loads(_build_user_context("Build me a balanced shortlist for today", parsed))

        self.assertEqual(context["chat_intent"], "discovery_or_bankroll_request")


if __name__ == "__main__":
    unittest.main()
