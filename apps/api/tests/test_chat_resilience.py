import unittest
from unittest.mock import AsyncMock, patch

from app.models.chat import AIChatResult, ChatRequest
from app.routers import chat as chat_router


class DummyChatSessionContext:
    user = {
        "id": "00000000-0000-0000-0000-000000000001",
        "plan": "free",
        "daily_chat_count": 1,
        "daily_chat_count_limit": 5,
    }
    conversation = {"id": "conversation-1", "messages": []}

    async def save_assistant_turn(self, response: str, confidence_score: float) -> dict:
        return {
            "response": response,
            "confidence_score": confidence_score,
            "daily_chats_remaining": 4,
            "conversation": self.conversation,
        }


class ChatResilienceTest(unittest.IsolatedAsyncioTestCase):
    async def test_safe_context_call_returns_none_when_source_fails(self) -> None:
        async def failing_builder() -> dict:
            raise RuntimeError("provider unavailable")

        with self.assertLogs(chat_router.logger, level="WARNING"):
            result = await chat_router._safe_context_call("test_source", failing_builder)

        self.assertIsNone(result)

    async def test_chat_continues_when_all_data_sources_fail(self) -> None:
        ai_result = AIChatResult(
            response="I can still give you a cautious read without live data.",
            confidence_score=4.5,
            verdict="NOT ENOUGH INFO",
            implied_probability=None,
            stake_posture="avoid",
        )

        with (
            patch.object(
                chat_router,
                "enforce_daily_limit_and_store",
                AsyncMock(return_value=DummyChatSessionContext()),
            ),
            patch.object(
                chat_router,
                "build_match_context_for_chat",
                AsyncMock(side_effect=RuntimeError("fixtures down")),
            ),
            patch.object(
                chat_router,
                "build_polymarket_context_for_chat",
                AsyncMock(side_effect=RuntimeError("market down")),
            ),
            patch.object(
                chat_router,
                "build_bookmaker_context_for_chat",
                AsyncMock(side_effect=RuntimeError("odds down")),
            ),
            patch.object(chat_router, "generate_chat_reply", AsyncMock(return_value=ai_result)) as generate_reply,
        ):
            with self.assertLogs(chat_router.logger, level="WARNING"):
                response = await chat_router.chat(ChatRequest(message="Brazil to beat Japan at 1.80"))

        self.assertEqual(response.response, ai_result.response)
        self.assertEqual(response.confidence_score, 4.5)
        self.assertEqual(response.verdict, "NOT ENOUGH INFO")
        self.assertEqual(response.stake_posture, "avoid")
        self.assertIsNone(response.market_signal)
        self.assertEqual(response.daily_chats_remaining, 4)
        generate_reply.assert_awaited_once()
        self.assertEqual(generate_reply.await_args.args[1], None)
        self.assertEqual(generate_reply.await_args.args[2], None)
        self.assertEqual(generate_reply.await_args.args[3], None)


if __name__ == "__main__":
    unittest.main()
