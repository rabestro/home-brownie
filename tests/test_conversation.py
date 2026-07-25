"""Unit tests for ConversationHistory in conversation.py."""

from home_brownie.conversation import ConversationHistory


def test_conversation_history_add_and_trim() -> None:
    history = ConversationHistory()
    for i in range(12):
        history.add(f"user_{i}", f"bot_{i}")

    assert len(history.turns) == 10
    assert history.turns[0] == ("user_2", "bot_2")
    assert history.turns[-1] == ("user_11", "bot_11")


def test_build_context_empty() -> None:
    history = ConversationHistory()
    ctx = history.build_context("Hello")
    assert ctx == "User: Hello"


def test_build_context_with_turns() -> None:
    history = ConversationHistory()
    history.add("Search roof docs", "Found roof-repair-2026")
    ctx = history.build_context("How much did it cost?")

    assert "User: Search roof docs" in ctx
    assert "Assistant: Found roof-repair-2026" in ctx
    assert "User: How much did it cost?" in ctx


def test_clear() -> None:
    history = ConversationHistory()
    history.add("u", "b")
    history.clear()
    assert len(history.turns) == 0
