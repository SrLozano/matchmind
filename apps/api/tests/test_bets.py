import unittest

from pydantic import ValidationError

from app.models.bets import BetCreateRequest, BetUpdateRequest
from app.models.users import DEFAULT_DEV_USER_ID
from app.services.bets import build_bet_summary, calculate_profit_loss


class BetTrackerTest(unittest.TestCase):
    def test_profit_loss_for_pending_bet_is_zero(self) -> None:
        self.assertEqual(calculate_profit_loss(20, 2.10, "pending"), 0.0)

    def test_profit_loss_for_winning_bet_returns_net_profit(self) -> None:
        self.assertEqual(calculate_profit_loss(20, 2.10, "win"), 22.0)

    def test_profit_loss_for_losing_bet_returns_negative_stake(self) -> None:
        self.assertEqual(calculate_profit_loss(20, 2.10, "loss"), -20.0)

    def test_summary_uses_settled_bets_for_win_rate(self) -> None:
        summary = build_bet_summary(
            [
                {"amount": 20, "profit_loss": 22, "outcome": "win"},
                {"amount": 10, "profit_loss": -10, "outcome": "loss"},
                {"amount": 15, "profit_loss": 0, "outcome": "pending"},
            ]
        )

        self.assertEqual(summary.total_bets, 3)
        self.assertEqual(summary.pending_bets, 1)
        self.assertEqual(summary.wins, 1)
        self.assertEqual(summary.losses, 1)
        self.assertEqual(summary.win_rate, 0.5)
        self.assertEqual(summary.total_staked, 45)
        self.assertEqual(summary.profit_loss, 12)
        self.assertEqual(summary.roi, 0.2667)

    def test_update_payload_requires_at_least_one_editable_field(self) -> None:
        with self.assertRaises(ValidationError):
            BetUpdateRequest(user_id="a87d09e8-7e10-46b8-9927-c9500c9559cf")

    def test_create_payload_rejects_blank_match_after_trimming(self) -> None:
        with self.assertRaises(ValidationError):
            BetCreateRequest(
                match="   ",
                amount=20,
                odds=2.10,
            )

    def test_create_payload_defaults_to_dev_user(self) -> None:
        payload = BetCreateRequest(match="Spain vs Germany", amount=20, odds=2.10)

        self.assertEqual(payload.user_id, DEFAULT_DEV_USER_ID)


if __name__ == "__main__":
    unittest.main()
