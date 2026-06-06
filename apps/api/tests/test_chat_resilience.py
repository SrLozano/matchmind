import unittest
from unittest.mock import AsyncMock, patch
from uuid import UUID

from app.models.chat import AIChatResult, ChatRequest
from app.services.auth import AuthenticatedUser
from app.routers import chat as chat_router


class DummyChatSessionContext:
    user = {
        "id": "00000000-0000-0000-0000-000000000001",
        "plan": "free",
        "daily_chat_count": 1,
        "daily_chat_count_limit": 5,
    }
    conversation = {
        "id": "conversation-1",
        "messages": [
            {"role": "user", "content": "Brazil to beat Japan at 1.80"},
            {"role": "assistant", "content": "I lean fair, but not exciting."},
            {"role": "user", "content": "What if I can get 2.10?"},
        ],
    }

    @property
    def previous_messages(self) -> list[dict]:
        return self.conversation["messages"][:-1]

    async def save_assistant_turn(
        self,
        response: str,
        confidence_score: float,
        verdict: str | None = None,
        implied_probability: float | None = None,
        stake_posture: str | None = None,
        recommended_stake: int | None = None,
    ) -> dict:
        return {
            "conversation_id": self.conversation["id"],
            "response": response,
            "confidence_score": confidence_score,
            "daily_chats_remaining": 4,
            "chat_count": 1,
            "chat_count_limit": 5,
            "chat_limit_period": "day",
            "chats_remaining": 4,
            "conversation": self.conversation,
        }


class ChatResilienceTest(unittest.IsolatedAsyncioTestCase):
    async def test_safe_context_call_returns_none_when_source_fails(self) -> None:
        async def failing_builder() -> dict:
            raise RuntimeError("provider unavailable")

        with self.assertLogs(chat_router.logger, level="WARNING"):
            result = await chat_router._safe_context_call("test_source", failing_builder)

        self.assertIsNone(result)

    async def test_follow_up_message_reuses_previous_bet_for_provider_matching(self) -> None:
        message = chat_router._message_with_current_bet_context(
            "What if I can get 2.10?",
            [
                {"role": "user", "content": "Brazil to beat Japan at 1.80"},
                {"role": "assistant", "content": "I lean fair, but not exciting."},
            ],
        )

        self.assertIn("Current user message: What if I can get 2.10?", message)
        self.assertIn("Previous bet under discussion: Brazil to beat Japan at 1.80", message)

    async def test_complete_new_bet_does_not_reuse_previous_context(self) -> None:
        message = chat_router._message_with_current_bet_context(
            "Argentina to beat Morocco at 1.90",
            [{"role": "user", "content": "Brazil to beat Japan at 1.80"}],
        )

        self.assertEqual(message, "Argentina to beat Morocco at 1.90")

    async def test_chat_continues_when_all_data_sources_fail(self) -> None:
        ai_result = AIChatResult(
            response="I can still give you a cautious read without live data.",
            confidence_score=4.5,
            verdict="NOT ENOUGH INFO",
            implied_probability=None,
            stake_posture="avoid",
            recommended_stake=1,
        )

        with (
            patch.object(
                chat_router,
                "require_authenticated_user",
                AsyncMock(return_value=AuthenticatedUser(id=UUID(DummyChatSessionContext.user["id"]))),
            ),
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
        self.assertEqual(response.recommended_stake, 1)
        self.assertIsNone(response.market_signal)
        self.assertEqual(response.conversation_id, "conversation-1")
        self.assertEqual(response.daily_chats_remaining, 4)
        self.assertEqual(response.chats_remaining, 4)
        generate_reply.assert_awaited_once()
        self.assertEqual(generate_reply.await_args.args[1], None)
        self.assertEqual(generate_reply.await_args.args[2], None)
        self.assertEqual(generate_reply.await_args.args[3], None)
        self.assertEqual(
            generate_reply.await_args.kwargs["conversation_memory"],
            DummyChatSessionContext.conversation["messages"][:-1],
        )


if __name__ == "__main__":
    unittest.main()
