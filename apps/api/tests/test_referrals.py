import unittest
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

from fastapi import HTTPException

from app.models.referrals import BarPartnerCreate
from app.services.referrals import (
    apply_referral_code,
    base_code_from_business_name,
    base_code_from_user,
    create_bar_partner,
    create_user_referral_code,
    get_referral_dashboard,
    mark_referral_conversion,
    normalize_referral_code,
    user_referral_perks,
    validate_referral_code,
)


PARTNER_USER_ID = UUID("11111111-1111-4111-8111-111111111111")
REFERRED_USER_ID = UUID("22222222-2222-4222-8222-222222222222")
OTHER_USER_ID = UUID("33333333-3333-4333-8333-333333333333")


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


def partner_payload(name: str = "Bar Cervantes") -> BarPartnerCreate:
    return BarPartnerCreate(
        business_name=name,
        location="Madrid, Chamberi",
        responsible_name="Carlos Garcia",
        phone="+34600111222",
        terms_accepted=True,
    )


def seeded_client() -> FakeSupabase:
    partner_id = str(uuid4())
    code_id = str(uuid4())
    return FakeSupabase(
        {
            "users": [
                {"id": str(PARTNER_USER_ID), "name": "Carlos Garcia", "email": "carlos@example.com"},
                {"id": str(REFERRED_USER_ID), "name": "Mario Lozano", "email": "mario@example.com"},
                {"id": str(OTHER_USER_ID), "name": "Alex Perez", "email": "alex@example.com"},
            ],
            "referral_partners": [
                {
                    "id": partner_id,
                    "user_id": str(PARTNER_USER_ID),
                    "partner_type": "bar",
                    "business_name": "Bar Cervantes",
                    "location": "Madrid",
                    "responsible_name": "Carlos Garcia",
                    "phone": "+34600111222",
                    "status": "active",
                    "terms_accepted_at": "2026-05-25T10:00:00+00:00",
                    "created_at": "2026-05-25T10:00:00+00:00",
                    "updated_at": "2026-05-25T10:00:00+00:00",
                }
            ],
            "referral_codes": [
                {
                    "id": code_id,
                    "code": "CERVANTES",
                    "owner_type": "bar_partner",
                    "partner_id": partner_id,
                    "owner_user_id": None,
                    "discount_type": "fixed_amount",
                    "discount_amount": 1.0,
                    "commission_amount": 2.0,
                    "active": True,
                    "created_at": "2026-05-25T10:00:00+00:00",
                }
            ],
            "referral_attributions": [],
        }
    )


class ReferralsTest(unittest.IsolatedAsyncioTestCase):
    def test_normalizes_codes_without_discount_or_spaces(self) -> None:
        self.assertEqual(base_code_from_business_name("Bar Cervantes"), "CERVANTES")
        self.assertEqual(normalize_referral_code(" cervantes "), "CERVANTES")
        self.assertEqual(normalize_referral_code("Cervantes 20%"), "CERVANTES20")

    def test_personal_code_base_uses_name_or_email_and_normalizes(self) -> None:
        self.assertEqual(base_code_from_user({"name": "Marío Lozano", "email": "mario@example.com"}), "MARIO")
        self.assertEqual(base_code_from_user({"name": "", "email": "ana.soto@example.com"}), "ANASOTO")
        self.assertEqual(base_code_from_user({"name": "", "email": ""}), "MATCHMIND")

    def test_user_referral_perks_follow_product_ladder(self) -> None:
        no_perk = user_referral_perks(0, 0)
        self.assertIsNone(no_perk["current_tier"])
        self.assertEqual(no_perk["next_tier"]["key"], "scout")
        self.assertEqual(no_perk["unlocked_pass_price"], 9.99)

        scout = user_referral_perks(1, 0)
        self.assertEqual(scout["current_tier"]["key"], "scout")
        self.assertEqual(scout["unlocked_pass_price"], 8.99)
        self.assertEqual(scout["next_tier"]["key"], "insider")

        insider = user_referral_perks(1, 2)
        self.assertEqual(insider["current_tier"]["key"], "insider")
        self.assertEqual(insider["unlocked_pass_price"], 4.99)

        captain = user_referral_perks(1, 5)
        self.assertEqual(captain["current_tier"]["key"], "captain")
        self.assertEqual(captain["unlocked_pass_price"], 2.49)

        legend = user_referral_perks(1, 7)
        self.assertEqual(legend["current_tier"]["key"], "legend")
        self.assertEqual(legend["unlocked_pass_price"], 0.0)

        founder = user_referral_perks(1, 10)
        self.assertEqual(founder["current_tier"]["key"], "founder_circle")
        self.assertTrue(founder["beta_priority"])
        self.assertIsNone(founder["next_tier"])

    async def test_creates_bar_partner_and_generates_correct_code(self) -> None:
        client = FakeSupabase({"users": [{"id": str(PARTNER_USER_ID)}]})
        with patch("app.services.referrals.get_supabase", new_callable=AsyncMock, return_value=client):
            response = await create_bar_partner(PARTNER_USER_ID, partner_payload())

        self.assertEqual(response["code"], "CERVANTES")
        self.assertEqual(response["business_name"], "Bar Cervantes")
        self.assertEqual(client.tables["referral_codes"][0]["discount_amount"], 1.0)
        self.assertEqual(client.tables["referral_codes"][0]["commission_amount"], 2.0)

    async def test_duplicate_code_generates_unique_alternative(self) -> None:
        client = FakeSupabase(
            {
                "users": [{"id": str(OTHER_USER_ID)}],
                "referral_codes": [{"id": str(uuid4()), "code": "CERVANTES"}],
            }
        )
        with patch("app.services.referrals.get_supabase", new_callable=AsyncMock, return_value=client):
            response = await create_bar_partner(OTHER_USER_ID, partner_payload())

        self.assertEqual(response["code"], "CERVANTES2")

    async def test_validates_existing_code(self) -> None:
        client = seeded_client()
        with patch("app.services.referrals.get_supabase", new_callable=AsyncMock, return_value=client):
            response = await validate_referral_code(" cervantes ")

        self.assertTrue(response["valid"])
        self.assertEqual(response["code"], "CERVANTES")
        self.assertEqual(response["partner_name"], "Bar Cervantes")
        self.assertEqual(response["discount_label"], "€1 discount")

    async def test_rejects_nonexistent_code(self) -> None:
        client = seeded_client()
        with patch("app.services.referrals.get_supabase", new_callable=AsyncMock, return_value=client):
            response = await validate_referral_code("missing")

        self.assertFalse(response["valid"])

    async def test_allows_applying_code_once(self) -> None:
        client = seeded_client()
        with patch("app.services.referrals.get_supabase", new_callable=AsyncMock, return_value=client):
            response = await apply_referral_code(REFERRED_USER_ID, "CERVANTES")

        self.assertTrue(response["applied"])
        self.assertEqual(len(client.tables["referral_attributions"]), 1)
        self.assertEqual(client.tables["referral_attributions"][0]["referred_user_id"], str(REFERRED_USER_ID))

    async def test_rejects_second_code_for_same_user(self) -> None:
        client = seeded_client()
        with patch("app.services.referrals.get_supabase", new_callable=AsyncMock, return_value=client):
            await apply_referral_code(REFERRED_USER_ID, "CERVANTES")
            with self.assertRaises(HTTPException) as raised:
                await apply_referral_code(REFERRED_USER_ID, "CERVANTES")

        self.assertEqual(raised.exception.status_code, 409)
        self.assertEqual(raised.exception.detail, "You have already applied a code.")

    async def test_blocks_self_referral(self) -> None:
        client = seeded_client()
        with patch("app.services.referrals.get_supabase", new_callable=AsyncMock, return_value=client):
            with self.assertRaises(HTTPException) as raised:
                await apply_referral_code(PARTNER_USER_ID, "CERVANTES")

        self.assertEqual(raised.exception.status_code, 400)
        self.assertEqual(raised.exception.detail, "You cannot apply your own referral code.")

    async def test_creates_personal_user_referral_code(self) -> None:
        client = FakeSupabase({"users": [{"id": str(REFERRED_USER_ID), "name": "Mario Lozano", "email": "mario@example.com"}]})

        with patch("app.services.referrals.get_supabase", new_callable=AsyncMock, return_value=client):
            response = await create_user_referral_code(REFERRED_USER_ID)

        self.assertEqual(response["code"], "MARIO")
        self.assertEqual(response["registered_referrals"], 0)
        self.assertEqual(client.tables["referral_codes"][0]["owner_type"], "user")
        self.assertEqual(client.tables["referral_codes"][0]["owner_user_id"], str(REFERRED_USER_ID))
        self.assertIsNone(client.tables["referral_codes"][0]["partner_id"])
        self.assertEqual(client.tables["referral_codes"][0]["commission_amount"], 0.0)

    async def test_duplicate_personal_code_gets_numeric_suffix(self) -> None:
        client = FakeSupabase(
            {
                "users": [{"id": str(REFERRED_USER_ID), "name": "Mario Lozano", "email": "mario@example.com"}],
                "referral_codes": [{"id": str(uuid4()), "code": "MARIO"}],
            }
        )

        with patch("app.services.referrals.get_supabase", new_callable=AsyncMock, return_value=client):
            response = await create_user_referral_code(REFERRED_USER_ID)

        self.assertEqual(response["code"], "MARIO2")

    async def test_validates_user_owned_code(self) -> None:
        client = seeded_client()
        user_code_id = str(uuid4())
        client.tables["referral_codes"].append(
            {
                "id": user_code_id,
                "code": "MARIO",
                "owner_type": "user",
                "partner_id": None,
                "owner_user_id": str(REFERRED_USER_ID),
                "discount_type": "fixed_amount",
                "discount_amount": 1.0,
                "commission_amount": 0.0,
                "active": True,
            }
        )

        with patch("app.services.referrals.get_supabase", new_callable=AsyncMock, return_value=client):
            response = await validate_referral_code("mario")

        self.assertTrue(response["valid"])
        self.assertEqual(response["code"], "MARIO")
        self.assertEqual(response["partner_name"], "Mario Lozano")
        self.assertEqual(response["owner_type"], "user")

    async def test_applies_user_owned_code_to_another_user(self) -> None:
        client = seeded_client()
        code_id = str(uuid4())
        client.tables["referral_codes"].append(
            {
                "id": code_id,
                "code": "MARIO",
                "owner_type": "user",
                "partner_id": None,
                "owner_user_id": str(REFERRED_USER_ID),
                "discount_type": "fixed_amount",
                "discount_amount": 1.0,
                "commission_amount": 0.0,
                "active": True,
            }
        )

        with patch("app.services.referrals.get_supabase", new_callable=AsyncMock, return_value=client):
            response = await apply_referral_code(OTHER_USER_ID, "MARIO")

        self.assertTrue(response["applied"])
        self.assertEqual(response["owner_type"], "user")
        self.assertEqual(client.tables["referral_attributions"][0]["referrer_user_id"], str(REFERRED_USER_ID))
        self.assertIsNone(client.tables["referral_attributions"][0]["partner_id"])

    async def test_blocks_self_referral_for_user_owned_code(self) -> None:
        client = seeded_client()
        client.tables["referral_codes"].append(
            {
                "id": str(uuid4()),
                "code": "MARIO",
                "owner_type": "user",
                "partner_id": None,
                "owner_user_id": str(REFERRED_USER_ID),
                "discount_type": "fixed_amount",
                "discount_amount": 1.0,
                "commission_amount": 0.0,
                "active": True,
            }
        )

        with patch("app.services.referrals.get_supabase", new_callable=AsyncMock, return_value=client):
            with self.assertRaises(HTTPException) as raised:
                await apply_referral_code(REFERRED_USER_ID, "MARIO")

        self.assertEqual(raised.exception.status_code, 400)
        self.assertEqual(raised.exception.detail, "You cannot apply your own referral code.")

    async def test_calculates_basic_dashboard_metrics(self) -> None:
        client = seeded_client()
        partner = client.tables["referral_partners"][0]
        code = client.tables["referral_codes"][0]
        client.tables["referral_attributions"] = [
            {
                "id": str(uuid4()),
                "referred_user_id": str(REFERRED_USER_ID),
                "referral_code_id": code["id"],
                "partner_id": partner["id"],
                "referrer_user_id": None,
                "converted_at": "2026-06-12T10:00:00+00:00",
                "discount_amount": 1.0,
                "commission_amount": 2.0,
            },
            {
                "id": str(uuid4()),
                "referred_user_id": str(OTHER_USER_ID),
                "referral_code_id": code["id"],
                "partner_id": partner["id"],
                "referrer_user_id": None,
                "converted_at": None,
                "discount_amount": 1.0,
                "commission_amount": 2.0,
            },
        ]

        with patch("app.services.referrals.get_supabase", new_callable=AsyncMock, return_value=client):
            dashboard = await get_referral_dashboard(PARTNER_USER_ID)

        self.assertTrue(dashboard["has_bar_partner"])
        self.assertEqual(dashboard["code"], "CERVANTES")
        self.assertEqual(dashboard["registered_referrals"], 2)
        self.assertEqual(dashboard["paid_referrals"], 1)
        self.assertEqual(dashboard["estimated_payout"], 2.0)

    async def test_dashboard_includes_user_referral_metrics(self) -> None:
        client = seeded_client()
        user_code_id = str(uuid4())
        client.tables["referral_codes"].append(
            {
                "id": user_code_id,
                "code": "MARIO",
                "owner_type": "user",
                "partner_id": None,
                "owner_user_id": str(REFERRED_USER_ID),
                "discount_type": "fixed_amount",
                "discount_amount": 1.0,
                "commission_amount": 0.0,
                "active": True,
            }
        )
        client.tables["referral_attributions"] = [
            {
                "id": str(uuid4()),
                "referred_user_id": str(PARTNER_USER_ID),
                "referral_code_id": user_code_id,
                "partner_id": None,
                "referrer_user_id": str(REFERRED_USER_ID),
                "converted_at": "2026-06-12T10:00:00+00:00",
                "discount_amount": 1.0,
                "commission_amount": 0.0,
            },
            {
                "id": str(uuid4()),
                "referred_user_id": str(OTHER_USER_ID),
                "referral_code_id": user_code_id,
                "partner_id": None,
                "referrer_user_id": str(REFERRED_USER_ID),
                "converted_at": None,
                "discount_amount": 1.0,
                "commission_amount": 0.0,
            },
        ]

        with patch("app.services.referrals.get_supabase", new_callable=AsyncMock, return_value=client):
            dashboard = await get_referral_dashboard(REFERRED_USER_ID)

        self.assertEqual(dashboard["user_referral"]["code"], "MARIO")
        self.assertEqual(dashboard["user_referral"]["registered_referrals"], 2)
        self.assertEqual(dashboard["user_referral"]["paid_referrals"], 1)
        self.assertEqual(dashboard["user_referral"]["status_label"], "scout")
        self.assertEqual(dashboard["user_referral"]["perks"]["current_tier"]["key"], "scout")
        self.assertEqual(dashboard["user_referral"]["perks"]["next_tier"]["key"], "insider")

    async def test_referral_conversion_appears_in_user_referral_paid_metrics(self) -> None:
        client = seeded_client()
        user_code_id = str(uuid4())
        client.tables["referral_codes"].append(
            {
                "id": user_code_id,
                "code": "MARIO",
                "owner_type": "user",
                "partner_id": None,
                "owner_user_id": str(REFERRED_USER_ID),
                "discount_type": "fixed_amount",
                "discount_amount": 1.0,
                "commission_amount": 0.0,
                "active": True,
            }
        )
        client.tables["referral_attributions"] = [
            {
                "id": str(uuid4()),
                "referred_user_id": str(OTHER_USER_ID),
                "referral_code_id": user_code_id,
                "partner_id": None,
                "referrer_user_id": str(REFERRED_USER_ID),
                "converted_at": None,
                "discount_amount": 1.0,
                "commission_amount": 0.0,
            }
        ]

        with patch("app.services.referrals.get_supabase", new_callable=AsyncMock, return_value=client):
            converted = await mark_referral_conversion(OTHER_USER_ID, gross_amount=8.99)
            dashboard = await get_referral_dashboard(REFERRED_USER_ID)

        self.assertTrue(converted)
        self.assertEqual(dashboard["user_referral"]["paid_referrals"], 1)


if __name__ == "__main__":
    unittest.main()
