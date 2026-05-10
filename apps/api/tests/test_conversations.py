import unittest

from app.services.supabase import _conversation_messages, _conversation_summary


class ConversationsTest(unittest.TestCase):
    def test_conversation_summary_uses_first_user_message_as_title(self) -> None:
        conversation = {
            "id": "conversation-1",
            "user_id": "user-1",
            "created_at": "2026-05-10T10:00:00+00:00",
            "messages": [
                {
                    "role": "user",
                    "content": "Brazil to beat Japan at 1.80",
                    "created_at": "2026-05-10T10:00:00+00:00",
                },
                {
                    "role": "assistant",
                    "content": "I would keep it small.",
                    "confidence_score": 6,
                    "created_at": "2026-05-10T10:01:00+00:00",
                },
            ],
        }

        summary = _conversation_summary(conversation)

        self.assertEqual(summary["title"], "Brazil to beat Japan at 1.80")
        self.assertEqual(summary["last_message_preview"], "I would keep it small.")
        self.assertEqual(summary["message_count"], 2)
        self.assertEqual(summary["updated_at"], "2026-05-10T10:01:00+00:00")

    def test_conversation_messages_filters_invalid_rows(self) -> None:
        messages = _conversation_messages(
            {
                "messages": [
                    {"role": "system", "content": "ignore"},
                    {"role": "user", "content": "  "},
                    {"role": "user", "content": "Spain at 2.20"},
                    {"role": "assistant", "content": "Interesting price.", "confidence_score": 6.5},
                    "bad row",
                ]
            }
        )

        self.assertEqual([message["role"] for message in messages], ["user", "assistant"])
        self.assertEqual(messages[1]["confidence_score"], 6.5)


if __name__ == "__main__":
    unittest.main()
