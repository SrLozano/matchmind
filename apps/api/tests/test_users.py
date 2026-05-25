import unittest

from app.config import get_settings
from app.models.users import DEFAULT_AVATAR_EMOJI, UserResponse
from app.services.supabase import _normalize_avatar_emoji


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


if __name__ == "__main__":
    unittest.main()
