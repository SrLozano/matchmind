import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app import main as api_main


def production_settings(**overrides):
    values = {
        "app_environment": "production",
        "allow_dev_auth_fallback": False,
        "cors_allowed_origins": "https://trymatchmind.com",
        "internal_api_token": "long-random-token",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


class ProductionSecurityTest(unittest.TestCase):
    def test_production_security_accepts_locked_down_settings(self) -> None:
        with patch.object(api_main, "settings", production_settings()):
            api_main.validate_production_security()

    def test_production_security_rejects_dev_auth_fallback(self) -> None:
        with patch.object(api_main, "settings", production_settings(allow_dev_auth_fallback=True)):
            with self.assertRaisesRegex(RuntimeError, "ALLOW_DEV_AUTH_FALLBACK"):
                api_main.validate_production_security()

    def test_production_security_rejects_wildcard_cors(self) -> None:
        with patch.object(api_main, "settings", production_settings(cors_allowed_origins="https://trymatchmind.com,*")):
            with self.assertRaisesRegex(RuntimeError, "CORS_ALLOWED_ORIGINS"):
                api_main.validate_production_security()

    def test_production_security_rejects_placeholder_internal_token(self) -> None:
        with patch.object(api_main, "settings", production_settings(internal_api_token="change-me-for-internal-refresh")):
            with self.assertRaisesRegex(RuntimeError, "INTERNAL_API_TOKEN"):
                api_main.validate_production_security()

    def test_non_production_does_not_apply_production_guards(self) -> None:
        with patch.object(
            api_main,
            "settings",
            production_settings(
                app_environment="development",
                allow_dev_auth_fallback=True,
                cors_allowed_origins="*",
                internal_api_token="change-me-for-internal-refresh",
            ),
        ):
            api_main.validate_production_security()


if __name__ == "__main__":
    unittest.main()
