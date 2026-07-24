"""Unit tests for Telegram bot user authorization and message handling."""

import json

import pytest
from telebot.types import Message

from home_genie.bot import (
    _clean_group_query,
    _get_accessible_systems_summary,
    create_bot,
    is_allowed,
)
from home_genie.config import Config, UserPermissions


def test_is_allowed_authorized(monkeypatch: pytest.MonkeyPatch) -> None:
    family_json = json.dumps({"12345": {"name": "Jegors"}})
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "12345:token")
    monkeypatch.setenv("GEMINI_API_KEY", "dummykey")
    monkeypatch.setenv("FAMILY_USERS", family_json)
    Config.validate()

    msg_data = {
        "message_id": 1,
        "date": 1000,
        "from": {"id": 12345, "is_bot": False, "first_name": "Jegors"},
        "chat": {"id": 12345, "type": "private"},
        "text": "hello",
    }
    msg = Message.de_json(msg_data)
    assert is_allowed(msg) is True


def test_is_allowed_unauthorized() -> None:
    msg_data = {
        "message_id": 1,
        "date": 1000,
        "from": {"id": 99999, "is_bot": False, "first_name": "Stranger"},
        "chat": {"id": 99999, "type": "private"},
        "text": "hello",
    }
    msg = Message.de_json(msg_data)
    assert is_allowed(msg) is False


def test_get_accessible_systems_summary() -> None:
    perms = UserPermissions(
        name="Test",
        paperless_token="ptoken",
        home_connect_token="hctoken",
    )
    summary = _get_accessible_systems_summary(perms)
    assert "Paperless-ngx Archive" in summary
    assert "Home Connect Appliances" in summary
    assert "GitHub Wiki" not in summary


def test_create_bot_factory(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(Config, "TELEGRAM_BOT_TOKEN", "123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ")
    bot = create_bot(Config)
    assert bot is not None
    assert bot.token == "123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ"


def test_clean_group_query() -> None:
    assert (
        _clean_group_query("@petera9a_bot какая температура?", "petera9a_bot")
        == "какая температура?"
    )
    assert _clean_group_query("какая температура?", "petera9a_bot") == "какая температура?"
