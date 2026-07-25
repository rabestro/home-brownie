"""Unit tests for Config and UserPermissions RBAC validation."""

import json

import pytest

from home_brownie.config import Config


def test_config_validation_success(monkeypatch: pytest.MonkeyPatch) -> None:
    family_json = json.dumps(
        {
            "12345": {
                "name": "TestUser",
                "paperless_token": "token123",
                "github_token": "ghp_abc",
            }
        }
    )
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "12345:dummytoken")
    monkeypatch.setenv("GEMINI_API_KEY", "dummykey")
    monkeypatch.setenv("FAMILY_USERS", family_json)

    Config.validate()

    perms = Config.get_user_permissions(12345)
    assert perms.name == "TestUser"
    assert perms.paperless_token == "token123"
    assert perms.github_token == "ghp_abc"
    assert perms.home_assistant_token is None


def test_unauthorized_user_raises_keyerror() -> None:
    with pytest.raises(KeyError, match="User ID 99999 is not authorized"):
        Config.get_user_permissions(99999)
