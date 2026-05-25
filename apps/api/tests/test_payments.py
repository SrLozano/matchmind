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
        app_url="http://localhost:3000",
    )


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
                with patch("app.services.payments.stripe.checkout.Session.create", side_effect=fake_create):
                    checkout_url = await create_tournament_pass_checkout_session(USER_ID)

        self.assertEqual(checkout_url, "https://checkout.stripe.com/c/test")
        self.assertEqual(created_kwargs["mode"], "payment")
        self.assertEqual(created_kwargs["line_items"], [{"price": "price_tournament_pass", "quantity": 1}])
        self.assertEqual(created_kwargs["client_reference_id"], str(USER_ID))
        self.assertEqual(created_kwargs["metadata"]["user_id"], str(USER_ID))
        self.assertEqual(created_kwargs["metadata"]["checkout_price_type"], "standard")
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
                with patch("app.services.payments.stripe.checkout.Session.create", side_effect=fake_create):
                    checkout_url = await create_tournament_pass_checkout_session(USER_ID)

        self.assertEqual(checkout_url, "https://checkout.stripe.com/c/test")
        self.assertEqual(created_kwargs["line_items"], [{"price": "price_tournament_pass_referral", "quantity": 1}])
        self.assertEqual(created_kwargs["metadata"]["checkout_price_type"], "referral")
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
                    "metadata": {"user_id": str(USER_ID)},
                }
            },
        }

        with patch("app.services.payments.update_user_plan", new_callable=AsyncMock) as update_user_plan:
            with patch("app.services.payments.mark_referral_conversion", new_callable=AsyncMock) as mark_conversion:
                result = await handle_webhook_event(event)

        self.assertEqual(result, {"received": True, "processed": True})
        update_user_plan.assert_awaited_once_with(USER_ID, "premium")
        mark_conversion.assert_awaited_once_with(USER_ID, gross_amount=None)


if __name__ == "__main__":
    unittest.main()
