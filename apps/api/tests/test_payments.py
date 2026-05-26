import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import UUID

import stripe
from fastapi import HTTPException

from app.routers.payments import create_checkout_session
from app.services.auth import AuthenticatedUser
from app.services.payments import (
    construct_webhook_event,
    create_tournament_pass_checkout_session,
    handle_webhook_event,
)


USER_ID = UUID("a87d09e8-7e10-46b8-9927-c9500c9559cf")


def payment_settings() -> SimpleNamespace:
    return SimpleNamespace(
        stripe_secret_key="sk_test_matchmind",
        stripe_webhook_secret="whsec_matchmind",
        stripe_tournament_pass_price_id="price_tournament_pass",
        stripe_tournament_pass_referral_price_id="price_tournament_pass_referral",
        stripe_tournament_pass_insider_price_id="price_tournament_pass_insider",
        stripe_tournament_pass_captain_price_id="price_tournament_pass_captain",
        app_url="http://localhost:3000",
    )


def user_referral_summary(
    *,
    has_code: bool = False,
    tier_key: str | None = None,
    unlocked_pass_price: float = 9.99,
) -> dict:
    return {
        "has_code": has_code,
        "code": "MARIO" if has_code else None,
        "registered_referrals": 0,
        "paid_referrals": 0,
        "status_label": tier_key or "tracking",
        "perks": {
            "current_tier": {"key": tier_key} if tier_key else None,
            "next_tier": None,
            "unlocked_pass_price": unlocked_pass_price,
            "discount_percent": 0,
            "beta_priority": False,
            "remaining_registered_referrals": 0,
            "remaining_paid_referrals": 0,
        },
    }


class PaymentsTest(unittest.TestCase):
    def test_invalid_webhook_signature_is_rejected(self) -> None:
        signature_error = stripe.error.SignatureVerificationError("bad signature", "t=1,v1=bad")

        with patch("app.services.payments.get_settings", return_value=payment_settings()):
            with patch("app.services.payments.stripe.Webhook.construct_event", side_effect=signature_error):
                with self.assertRaises(HTTPException) as raised:
                    construct_webhook_event(b"{}", "t=1,v1=bad")

        self.assertEqual(raised.exception.status_code, 400)
        self.assertEqual(raised.exception.detail, "Invalid Stripe webhook signature.")


class PaymentsAsyncTest(unittest.IsolatedAsyncioTestCase):
    async def test_checkout_session_creation_uses_standard_price_without_referral(self) -> None:
        created_kwargs = {}

        def fake_create(**kwargs):
            created_kwargs.update(kwargs)
            return SimpleNamespace(url="https://checkout.stripe.com/c/test")

        with patch("app.services.payments.get_settings", return_value=payment_settings()):
            with patch("app.services.payments.get_applied_referral_for_checkout", new_callable=AsyncMock, return_value=None):
                with patch("app.services.payments.get_user_referral_summary", new_callable=AsyncMock, return_value=user_referral_summary()):
                    with patch("app.services.payments.stripe.checkout.Session.create", side_effect=fake_create):
                        checkout_url = await create_tournament_pass_checkout_session(USER_ID)

        self.assertEqual(checkout_url, "https://checkout.stripe.com/c/test")
        self.assertEqual(created_kwargs["mode"], "payment")
        self.assertEqual(created_kwargs["line_items"], [{"price": "price_tournament_pass", "quantity": 1}])
        self.assertEqual(created_kwargs["client_reference_id"], str(USER_ID))
        self.assertEqual(created_kwargs["metadata"]["user_id"], str(USER_ID))
        self.assertEqual(created_kwargs["metadata"]["checkout_price_type"], "standard")
        self.assertEqual(created_kwargs["metadata"]["checkout_price_amount"], "9.99")
        self.assertEqual(created_kwargs["payment_intent_data"]["metadata"]["user_id"], str(USER_ID))
        self.assertEqual(created_kwargs["success_url"], "http://localhost:3000/?payment=success")
        self.assertEqual(created_kwargs["cancel_url"], "http://localhost:3000/?payment=cancelled")

    async def test_checkout_session_uses_referral_price_when_user_has_applied_code(self) -> None:
        created_kwargs = {}

        def fake_create(**kwargs):
            created_kwargs.update(kwargs)
            return SimpleNamespace(url="https://checkout.stripe.com/c/test")

        referral = {
            "attribution_id": "attr_123",
            "code": "CERVANTES",
            "owner_type": "bar_partner",
            "partner_id": "partner_123",
            "referrer_user_id": None,
            "discount_amount": 1.0,
        }
        with patch("app.services.payments.get_settings", return_value=payment_settings()):
            with patch("app.services.payments.get_applied_referral_for_checkout", new_callable=AsyncMock, return_value=referral):
                with patch("app.services.payments.get_user_referral_summary", new_callable=AsyncMock, return_value=user_referral_summary()):
                    with patch("app.services.payments.stripe.checkout.Session.create", side_effect=fake_create):
                        checkout_url = await create_tournament_pass_checkout_session(USER_ID)

        self.assertEqual(checkout_url, "https://checkout.stripe.com/c/test")
        self.assertEqual(created_kwargs["line_items"], [{"price": "price_tournament_pass_referral", "quantity": 1}])
        self.assertEqual(created_kwargs["metadata"]["checkout_price_type"], "referral")
        self.assertEqual(created_kwargs["metadata"]["checkout_price_amount"], "8.99")
        self.assertEqual(created_kwargs["metadata"]["referral_code"], "CERVANTES")
        self.assertEqual(created_kwargs["metadata"]["referral_owner_type"], "bar_partner")
        self.assertEqual(created_kwargs["metadata"]["referral_partner_id"], "partner_123")
        self.assertEqual(created_kwargs["metadata"]["referral_attribution_id"], "attr_123")
        self.assertNotIn("referral_referrer_user_id", created_kwargs["metadata"])

    async def test_checkout_session_uses_referral_price_for_user_owned_applied_code(self) -> None:
        created_kwargs = {}

        def fake_create(**kwargs):
            created_kwargs.update(kwargs)
            return SimpleNamespace(url="https://checkout.stripe.com/c/test")

        referral = {
            "attribution_id": "attr_user_123",
            "code": "MARIO",
            "owner_type": "user",
            "partner_id": None,
            "referrer_user_id": "referrer_123",
            "discount_amount": 1.0,
        }
        with patch("app.services.payments.get_settings", return_value=payment_settings()):
            with patch("app.services.payments.get_applied_referral_for_checkout", new_callable=AsyncMock, return_value=referral):
                with patch("app.services.payments.get_user_referral_summary", new_callable=AsyncMock, return_value=user_referral_summary()):
                    with patch("app.services.payments.stripe.checkout.Session.create", side_effect=fake_create):
                        checkout_url = await create_tournament_pass_checkout_session(USER_ID)

        self.assertEqual(checkout_url, "https://checkout.stripe.com/c/test")
        self.assertEqual(created_kwargs["line_items"], [{"price": "price_tournament_pass_referral", "quantity": 1}])
        self.assertEqual(created_kwargs["metadata"]["checkout_price_type"], "referral")
        self.assertEqual(created_kwargs["metadata"]["referral_code"], "MARIO")
        self.assertEqual(created_kwargs["metadata"]["referral_owner_type"], "user")
        self.assertEqual(created_kwargs["metadata"]["referral_referrer_user_id"], "referrer_123")
        self.assertEqual(created_kwargs["metadata"]["referral_attribution_id"], "attr_user_123")
        self.assertNotIn("referral_partner_id", created_kwargs["metadata"])

    async def test_checkout_session_uses_personal_insider_price_when_unlocked(self) -> None:
        created_kwargs = {}

        def fake_create(**kwargs):
            created_kwargs.update(kwargs)
            return SimpleNamespace(url="https://checkout.stripe.com/c/test")

        with patch("app.services.payments.get_settings", return_value=payment_settings()):
            with patch("app.services.payments.get_applied_referral_for_checkout", new_callable=AsyncMock, return_value=None):
                with patch(
                    "app.services.payments.get_user_referral_summary",
                    new_callable=AsyncMock,
                    return_value=user_referral_summary(has_code=True, tier_key="insider", unlocked_pass_price=4.99),
                ):
                    with patch("app.services.payments.stripe.checkout.Session.create", side_effect=fake_create):
                        checkout_url = await create_tournament_pass_checkout_session(USER_ID)

        self.assertEqual(checkout_url, "https://checkout.stripe.com/c/test")
        self.assertEqual(created_kwargs["line_items"], [{"price": "price_tournament_pass_insider", "quantity": 1}])
        self.assertEqual(created_kwargs["metadata"]["checkout_price_type"], "user_referral_insider")
        self.assertEqual(created_kwargs["metadata"]["checkout_price_amount"], "4.99")
        self.assertEqual(created_kwargs["metadata"]["referral_tier_key"], "insider")

    async def test_checkout_session_uses_personal_captain_price_when_unlocked(self) -> None:
        created_kwargs = {}

        def fake_create(**kwargs):
            created_kwargs.update(kwargs)
            return SimpleNamespace(url="https://checkout.stripe.com/c/test")

        with patch("app.services.payments.get_settings", return_value=payment_settings()):
            with patch("app.services.payments.get_applied_referral_for_checkout", new_callable=AsyncMock, return_value=None):
                with patch(
                    "app.services.payments.get_user_referral_summary",
                    new_callable=AsyncMock,
                    return_value=user_referral_summary(has_code=True, tier_key="captain", unlocked_pass_price=2.49),
                ):
                    with patch("app.services.payments.stripe.checkout.Session.create", side_effect=fake_create):
                        checkout_url = await create_tournament_pass_checkout_session(USER_ID)

        self.assertEqual(checkout_url, "https://checkout.stripe.com/c/test")
        self.assertEqual(created_kwargs["line_items"], [{"price": "price_tournament_pass_captain", "quantity": 1}])
        self.assertEqual(created_kwargs["metadata"]["checkout_price_type"], "user_referral_captain")
        self.assertEqual(created_kwargs["metadata"]["checkout_price_amount"], "2.49")
        self.assertEqual(created_kwargs["metadata"]["referral_tier_key"], "captain")

    async def test_checkout_session_grants_free_pass_without_stripe_checkout(self) -> None:
        with patch("app.services.payments.get_settings", return_value=payment_settings()):
            with patch("app.services.payments.get_applied_referral_for_checkout", new_callable=AsyncMock, return_value=None):
                with patch(
                    "app.services.payments.get_user_referral_summary",
                    new_callable=AsyncMock,
                    return_value=user_referral_summary(has_code=True, tier_key="legend", unlocked_pass_price=0.0),
                ):
                    with patch("app.services.payments.update_user_plan", new_callable=AsyncMock) as update_user_plan:
                        with patch("app.services.payments.stripe.checkout.Session.create") as create_session:
                            checkout_url = await create_tournament_pass_checkout_session(USER_ID)

        self.assertEqual(checkout_url, "http://localhost:3000/?payment=success")
        update_user_plan.assert_awaited_once_with(USER_ID, "premium")
        create_session.assert_not_called()

    async def test_create_checkout_endpoint_uses_authenticated_user(self) -> None:
        with patch(
            "app.routers.payments.get_authenticated_user",
            new_callable=AsyncMock,
            return_value=AuthenticatedUser(id=USER_ID, email="alex@example.com"),
        ):
            with patch(
                "app.routers.payments.create_tournament_pass_checkout_session",
                new_callable=AsyncMock,
                return_value="https://checkout.stripe.com/c/test",
            ) as create_session:
                result = await create_checkout_session("Bearer token")

        self.assertEqual(result, {"url": "https://checkout.stripe.com/c/test"})
        create_session.assert_awaited_once_with(USER_ID)

    async def test_webhook_updates_user_plan_on_checkout_session_completed(self) -> None:
        event = {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_test_123",
                    "payment_intent": "pi_test_123",
                    "payment_status": "paid",
                    "amount_total": 899,
                    "metadata": {"user_id": str(USER_ID), "checkout_price_type": "referral"},
                }
            },
        }

        with patch("app.services.payments.update_user_plan", new_callable=AsyncMock) as update_user_plan:
            with patch("app.services.payments.mark_referral_conversion", new_callable=AsyncMock) as mark_conversion:
                result = await handle_webhook_event(event)

        self.assertEqual(result, {"received": True, "processed": True})
        update_user_plan.assert_awaited_once_with(USER_ID, "premium")
        mark_conversion.assert_awaited_once_with(
            USER_ID,
            gross_amount=8.99,
            stripe_checkout_session_id="cs_test_123",
            stripe_payment_intent_id="pi_test_123",
            converted_price_type="referral",
        )

    async def test_webhook_does_not_process_unpaid_checkout_session(self) -> None:
        event = {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_test_unpaid",
                    "payment_status": "unpaid",
                    "amount_total": 899,
                    "metadata": {"user_id": str(USER_ID), "checkout_price_type": "referral"},
                }
            },
        }

        with patch("app.services.payments.update_user_plan", new_callable=AsyncMock) as update_user_plan:
            with patch("app.services.payments.mark_referral_conversion", new_callable=AsyncMock) as mark_conversion:
                result = await handle_webhook_event(event)

        self.assertEqual(result, {"received": True, "processed": False})
        update_user_plan.assert_not_awaited()
        mark_conversion.assert_not_awaited()

    async def test_dispute_created_cancels_matching_referral_payout(self) -> None:
        event = {
            "type": "charge.dispute.created",
            "data": {
                "object": {
                    "id": "du_test_123",
                    "payment_intent": "pi_test_123",
                    "reason": "fraudulent",
                }
            },
        }

        with patch("app.services.payments.cancel_referral_payout_for_payment_intent", new_callable=AsyncMock) as cancel_payout:
            cancel_payout.return_value = True
            result = await handle_webhook_event(event)

        self.assertEqual(result, {"received": True, "processed": True})
        cancel_payout.assert_awaited_once_with(
            "pi_test_123",
            cancellation_reason="stripe_dispute_created",
            stripe_dispute_id="du_test_123",
        )

    async def test_payment_intent_canceled_cancels_matching_referral_payout(self) -> None:
        event = {
            "type": "payment_intent.canceled",
            "data": {"object": {"id": "pi_test_cancelled"}},
        }

        with patch("app.services.payments.cancel_referral_payout_for_payment_intent", new_callable=AsyncMock) as cancel_payout:
            cancel_payout.return_value = True
            result = await handle_webhook_event(event)

        self.assertEqual(result, {"received": True, "processed": True})
        cancel_payout.assert_awaited_once_with(
            "pi_test_cancelled",
            cancellation_reason="stripe_payment_intent_canceled",
        )


if __name__ == "__main__":
    unittest.main()
