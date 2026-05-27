import inspect
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import UUID

from fastapi import HTTPException

from app.models.bets import BetCreateRequest, BetSummary, BetUpdateRequest
from app.models.chat import AIChatResult, ChatRequest
from app.models.users import DEFAULT_DEV_USER_ID
from app.routers import bets as bets_router
from app.routers import chat as chat_router
from app.routers import conversations as conversations_router
from app.routers import users as users_router
from app.services import auth as auth_service
from app.services.auth import AuthenticatedUser


AUTH_USER_ID = UUID("00000000-0000-0000-0000-000000000001")
OTHER_USER_ID = UUID("00000000-0000-0000-0000-000000000002")
BET_ID = UUID("00000000-0000-0000-0000-000000000003")
CONVERSATION_ID = UUID("00000000-0000-0000-0000-000000000004")


class DummyChatSessionContext:
    user = {"id": str(AUTH_USER_ID)}

    @property
    def previous_messages(self) -> list[dict]:
        return []

    async def save_assistant_turn(
        self,
        response: str,
        confidence_score: float,
        verdict: str | None = None,
        implied_probability: float | None = None,
        stake_posture: str | None = None,
    ) -> dict:
        return {
            "conversation_id": "conversation-1",
            "response": response,
            "confidence_score": confidence_score,
            "daily_chats_remaining": 4,
            "chat_count": 1,
            "chat_count_limit": 5,
            "chat_limit_period": "day",
            "chats_remaining": 4,
        }


class AuthHelperSecurityTest(unittest.IsolatedAsyncioTestCase):
    async def test_require_authenticated_user_rejects_missing_token_by_default(self) -> None:
        with (
            patch.object(auth_service, "get_authenticated_user", AsyncMock(return_value=None)),
            patch.object(auth_service, "get_settings", return_value=SimpleNamespace(allow_dev_auth_fallback=False)),
            patch.object(auth_service, "ensure_user_profile", AsyncMock()) as ensure_user_profile,
        ):
            with self.assertRaises(HTTPException) as raised:
                await auth_service.require_authenticated_user(None)

        self.assertEqual(raised.exception.status_code, 401)
        ensure_user_profile.assert_not_awaited()

    async def test_require_authenticated_user_uses_dev_fallback_only_when_enabled(self) -> None:
        with (
            patch.object(auth_service, "get_authenticated_user", AsyncMock(return_value=None)),
            patch.object(auth_service, "get_settings", return_value=SimpleNamespace(allow_dev_auth_fallback=True)),
            patch.object(auth_service, "ensure_user_profile", AsyncMock()) as ensure_user_profile,
        ):
            user = await auth_service.require_authenticated_user(None)

        self.assertEqual(user.id, DEFAULT_DEV_USER_ID)
        ensure_user_profile.assert_awaited_once_with(DEFAULT_DEV_USER_ID, email=None)

    async def test_require_authenticated_user_prefers_valid_bearer_user(self) -> None:
        bearer_user = AuthenticatedUser(id=AUTH_USER_ID, email="alex@example.com")

        with (
            patch.object(auth_service, "get_authenticated_user", AsyncMock(return_value=bearer_user)),
            patch.object(auth_service, "get_settings") as get_settings,
            patch.object(auth_service, "ensure_user_profile", AsyncMock()) as ensure_user_profile,
        ):
            user = await auth_service.require_authenticated_user("Bearer token")

        self.assertEqual(user, bearer_user)
        get_settings.assert_not_called()
        ensure_user_profile.assert_not_awaited()


class UserSpecificRouteSecurityTest(unittest.IsolatedAsyncioTestCase):
    async def assert_unauthorized(self, route_call, patch_target: str) -> None:
        with patch(patch_target, AsyncMock(side_effect=HTTPException(status_code=401, detail="Authentication is required."))):
            with self.assertRaises(HTTPException) as raised:
                await route_call()

        self.assertEqual(raised.exception.status_code, 401)

    async def test_user_specific_routes_return_401_without_authentication(self) -> None:
        checks = [
            (
                lambda: chat_router.chat(ChatRequest(message="Brazil to win")),
                "app.routers.chat.require_authenticated_user",
            ),
            (lambda: users_router.current_user(), "app.routers.users.require_authenticated_user"),
            (
                lambda: bets_router.create_bet_endpoint(
                    BetCreateRequest(
                        match="Spain vs Germany",
                        pick="Spain win",
                        market_type="match_winner",
                        amount=20,
                        odds=2.1,
                    )
                ),
                "app.routers.bets.require_authenticated_user",
            ),
            (lambda: bets_router.list_bets_endpoint(), "app.routers.bets.require_authenticated_user"),
            (
                lambda: bets_router.update_bet_endpoint(BET_ID, BetUpdateRequest(outcome="win")),
                "app.routers.bets.require_authenticated_user",
            ),
            (lambda: bets_router.delete_bet_endpoint(BET_ID), "app.routers.bets.require_authenticated_user"),
            (lambda: conversations_router.conversations(), "app.routers.conversations.require_authenticated_user"),
            (
                lambda: conversations_router.conversation_detail(CONVERSATION_ID),
                "app.routers.conversations.require_authenticated_user",
            ),
        ]

        for route_call, patch_target in checks:
            with self.subTest(patch_target=patch_target):
                await self.assert_unauthorized(route_call, patch_target)

    async def test_chat_uses_authenticated_user_and_ignores_payload_user_id(self) -> None:
        ai_result = AIChatResult(response="No edge there.", confidence_score=6.0)

        with (
            patch.object(
                chat_router,
                "require_authenticated_user",
                AsyncMock(return_value=AuthenticatedUser(id=AUTH_USER_ID)),
            ),
            patch.object(
                chat_router,
                "enforce_daily_limit_and_store",
                AsyncMock(return_value=DummyChatSessionContext()),
            ) as enforce_limit,
            patch.object(chat_router, "build_match_context_for_chat", AsyncMock(return_value=None)),
            patch.object(chat_router, "build_polymarket_context_for_chat", AsyncMock(return_value=None)),
            patch.object(chat_router, "build_bookmaker_context_for_chat", AsyncMock(return_value=None)),
            patch.object(chat_router, "generate_chat_reply", AsyncMock(return_value=ai_result)),
        ):
            await chat_router.chat(ChatRequest(user_id=OTHER_USER_ID, message="Brazil to win"), "Bearer token")

        self.assertEqual(enforce_limit.await_args.args[0], AUTH_USER_ID)

    async def test_bet_payload_user_id_is_overwritten_by_authenticated_user(self) -> None:
        created_bet = {
            "id": BET_ID,
            "user_id": AUTH_USER_ID,
            "match": "Spain vs Germany",
            "pick": "Spain win",
            "market_type": "match_winner",
            "bookmaker": "Bet365",
            "amount": 20,
            "odds": 2.1,
            "outcome": "pending",
            "profit_loss": 0,
            "created_at": "2026-06-11T10:00:00+00:00",
        }

        with (
            patch.object(
                bets_router,
                "require_authenticated_user",
                AsyncMock(return_value=AuthenticatedUser(id=AUTH_USER_ID)),
            ),
            patch.object(bets_router, "create_bet", AsyncMock(return_value=created_bet)) as create_bet,
        ):
            await bets_router.create_bet_endpoint(
                BetCreateRequest(
                    user_id=OTHER_USER_ID,
                    match="Spain vs Germany",
                    pick="Spain win",
                    market_type="match_winner",
                    bookmaker="Bet365",
                    amount=20,
                    odds=2.1,
                ),
                "Bearer token",
            )

        self.assertEqual(create_bet.await_args.args[0].user_id, AUTH_USER_ID)

    async def test_bet_update_payload_user_id_is_overwritten_by_authenticated_user(self) -> None:
        updated_bet = {
            "id": BET_ID,
            "user_id": AUTH_USER_ID,
            "match": "Spain vs Germany",
            "pick": "Spain win",
            "market_type": "match_winner",
            "bookmaker": "Bet365",
            "amount": 20,
            "odds": 2.1,
            "outcome": "win",
            "profit_loss": 22,
            "created_at": "2026-06-11T10:00:00+00:00",
        }

        with (
            patch.object(
                bets_router,
                "require_authenticated_user",
                AsyncMock(return_value=AuthenticatedUser(id=AUTH_USER_ID)),
            ),
            patch.object(bets_router, "update_bet", AsyncMock(return_value=updated_bet)) as update_bet,
        ):
            await bets_router.update_bet_endpoint(
                BET_ID,
                BetUpdateRequest(user_id=OTHER_USER_ID, outcome="win"),
                "Bearer token",
            )

        self.assertEqual(update_bet.await_args.args[1].user_id, AUTH_USER_ID)

    async def test_reads_and_deletes_scope_to_authenticated_user(self) -> None:
        empty_summary = BetSummary(
            total_bets=0,
            pending_bets=0,
            wins=0,
            losses=0,
            win_rate=0,
            total_staked=0,
            pending_exposure=0,
            profit_loss=0,
            roi=0,
        )

        with (
            patch.object(
                bets_router,
                "require_authenticated_user",
                AsyncMock(return_value=AuthenticatedUser(id=AUTH_USER_ID)),
            ),
            patch.object(bets_router, "list_bets", AsyncMock(return_value=([], empty_summary))) as list_bets,
            patch.object(bets_router, "delete_bet", AsyncMock()) as delete_bet,
        ):
            await bets_router.list_bets_endpoint("Bearer token")
            await bets_router.delete_bet_endpoint(BET_ID, "Bearer token")

        list_bets.assert_awaited_once_with(AUTH_USER_ID)
        delete_bet.assert_awaited_once_with(BET_ID, AUTH_USER_ID)

    async def test_profile_and_conversations_do_not_accept_user_id_query_params(self) -> None:
        self.assertNotIn("user_id", inspect.signature(users_router.current_user).parameters)
        self.assertNotIn("user_id", inspect.signature(bets_router.list_bets_endpoint).parameters)
        self.assertNotIn("user_id", inspect.signature(bets_router.delete_bet_endpoint).parameters)
        self.assertNotIn("user_id", inspect.signature(conversations_router.conversations).parameters)
        self.assertNotIn("user_id", inspect.signature(conversations_router.conversation_detail).parameters)


if __name__ == "__main__":
    unittest.main()
