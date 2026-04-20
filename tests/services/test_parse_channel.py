"""Tests for parse_channel_from_session_title."""
from core.services.chat_sessions import parse_channel_from_session_title


def test_discord_dm():
    channel, detail = parse_channel_from_session_title("Discord DM")
    assert channel == "discord"
    assert detail == "DM"


def test_discord_public_channel():
    channel, detail = parse_channel_from_session_title("Discord #123456789")
    assert channel == "discord"
    assert detail == "#123456789"


def test_telegram_dm():
    channel, detail = parse_channel_from_session_title("Telegram DM")
    assert channel == "telegram"
    assert detail == "DM"


def test_webchat_new_chat():
    channel, detail = parse_channel_from_session_title("New chat")
    assert channel == "webchat"
    assert detail is None


def test_webchat_none_input():
    channel, detail = parse_channel_from_session_title(None)
    assert channel == "webchat"
    assert detail is None


def test_unknown_title():
    channel, detail = parse_channel_from_session_title("Something weird")
    assert channel == "unknown"
    assert detail is None
