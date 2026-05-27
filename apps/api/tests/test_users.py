import unittest
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

from fastapi import HTTPException

from app.config import get_settings
from app.models.users import DEFAULT_AVATAR_EMOJI, UserResponse
from app.services.supabase import _normalize_avatar_emoji, ensure_user_profile


class FakeQuery:
    def __init__(self, client, table_name: str):
        self.client = client
        self.table_name = table_name
        self.action = "select"
        self.payload = None
        self.filters = []
        self.limit_count = None

    def select(self, *_args):
        self.action = "select"
        return self

    def insert(self, payload):
        self.action = "insert"
        self.payload = payload
        return self

    def update(self, payload):
        self.action = "update"
        self.payload = payload
        return self

    def eq(self, key, value):
        self.filters.append((key, str(value)))
        return self

    def limit(self, count):
        self.limit_count = count
        return self

    async def execute(self):
        rows = self.client.tables.setdefault(self.table_name, [])
        if self.action == "insert":
            payload = deepcopy(self.payload)
            payload.setdefault("id", str(uuid4()))
            rows.append(payload)
            return SimpleNamespace(data=[payload])

        matches = [row for row in rows if all(str(row.get(key)) == value for key, value in self.filters)]
        if self.limit_count is not None:
            matches = matches[: self.limit_count]

        if self.action == "update":
            for row in matches:
                row.update(deepcopy(self.payload))
            return SimpleNamespace(data=deepcopy(matches))

        return SimpleNamespace(data=deepcopy(matches))


class FakeSupabase:
    def __init__(self, tables=None):
        self.tables = tables or {}

    def table(self, table_name: str):
        return FakeQuery(self, table_name)


class UsersModelTest(unittest.TestCase):
    def test_user_response_accepts_free_plan_with_remaining_chats(self) -> None:
        payload = UserResponse(
            id="a87d09e8-7e10-46b8-9927-c9500c9559cf",
            email="alex@example.com",
            name="Alex",
            plan="free",
            daily_chat_count=2,
            daily_chat_count_limit=get_settings().free_daily_chat_limit,
            daily_chats_remaining=3,
            chat_count_limit=get_settings().free_daily_chat_limit,
            chat_limit_period="day",
            chats_remaining=3,
        )

        self.assertEqual(payload.plan, "free")
        self.assertEqual(payload.name, "Alex")
        self.assertEqual(payload.avatar_emoji, DEFAULT_AVATAR_EMOJI)
        self.assertEqual(payload.daily_chats_remaining, 3)

    def test_user_response_accepts_premium_plan_with_hidden_usage_quota(self) -> None:
        payload = UserResponse(
            id="a87d09e8-7e10-46b8-9927-c9500c9559cf",
            email=None,
            plan="premium",
            daily_chat_count=25,
            daily_chat_count_limit=None,
            daily_chats_remaining=None,
            chat_count_limit=None,
            chat_limit_period=None,
            chats_remaining=None,
        )

        self.assertEqual(payload.plan, "premium")
        self.assertIsNone(payload.daily_chats_remaining)
        self.assertIsNone(payload.chat_count_limit)
        self.assertIsNone(payload.chat_limit_period)
        self.assertIsNone(payload.chats_remaining)

    def test_avatar_accepts_one_character_or_one_emoji(self) -> None:
        self.assertEqual(_normalize_avatar_emoji("M"), "M")
        self.assertEqual(_normalize_avatar_emoji("⚽"), "⚽")
        self.assertEqual(_normalize_avatar_emoji("👍🏽"), "👍🏽")
        self.assertEqual(_normalize_avatar_emoji("🇪🇸"), "🇪🇸")
        self.assertEqual(_normalize_avatar_emoji("👨‍👩‍👧"), "👨‍👩‍👧")

    def test_avatar_rejects_text_and_multiple_emoji(self) -> None:
        self.assertIsNone(_normalize_avatar_emoji("MM"))
        self.assertIsNone(_normalize_avatar_emoji("Alex"))
        self.assertIsNone(_normalize_avatar_emoji("⚽⚽"))
        self.assertIsNone(_normalize_avatar_emoji("M ⚽"))


class UserProfileSecurityTest(unittest.IsolatedAsyncioTestCase):
    async def test_ensure_user_profile_normalizes_email_for_new_profile(self) -> None:
        user_id = UUID("11111111-1111-4111-8111-111111111111")
        client = FakeSupabase({"users": []})

        with patch("app.services.supabase.get_supabase", new_callable=AsyncMock, return_value=client):
            user = await ensure_user_profile(user_id, email=" Alex@Example.COM ")

        self.assertEqual(user["id"], str(user_id))
        self.assertEqual(user["email"], "alex@example.com")
        self.assertEqual(user["name"], "Alex")

    async def test_ensure_user_profile_rejects_email_owned_by_different_user(self) -> None:
        existing_user_id = UUID("11111111-1111-4111-8111-111111111111")
        new_auth_user_id = UUID("22222222-2222-4222-8222-222222222222")
        client = FakeSupabase(
            {
                "users": [
                    {
                        "id": str(existing_user_id),
                        "email": "alex@example.com",
                        "name": "Alex",
                    }
                ]
            }
        )

        with patch("app.services.supabase.get_supabase", new_callable=AsyncMock, return_value=client):
            with self.assertRaises(HTTPException) as raised:
                await ensure_user_profile(new_auth_user_id, email="alex@example.com")

        self.assertEqual(raised.exception.status_code, 409)
        self.assertEqual(len(client.tables["users"]), 1)


if __name__ == "__main__":
    unittest.main()
