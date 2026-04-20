"""Tests for _channel_context_section in prompt_contract."""
from unittest.mock import patch


def test_discord_dm_with_workspace_file(tmp_path):
    channels_dir = tmp_path / "channels"
    channels_dir.mkdir()
    (channels_dir / "discord.md").write_text("Discord er uformelt.")

    with patch("core.services.prompt_contract._channel_workspace_path", return_value=channels_dir):
        with patch("core.services.chat_sessions.get_chat_session", return_value={"title": "Discord DM", "session_id": "s1"}):
            from core.services.prompt_contract import _channel_context_section
            result = _channel_context_section("s1")

    assert result is not None
    assert "Discord DM" in result
    assert "Discord er uformelt." in result


def test_discord_dm_without_workspace_file(tmp_path):
    channels_dir = tmp_path / "channels"
    channels_dir.mkdir()

    with patch("core.services.prompt_contract._channel_workspace_path", return_value=channels_dir):
        with patch("core.services.chat_sessions.get_chat_session", return_value={"title": "Discord DM", "session_id": "s1"}):
            from core.services.prompt_contract import _channel_context_section
            result = _channel_context_section("s1")

    assert result is not None
    assert "Discord DM" in result


def test_none_session_id_returns_none():
    from core.services.prompt_contract import _channel_context_section
    assert _channel_context_section(None) is None


def test_webchat_without_workspace_file_returns_none(tmp_path):
    channels_dir = tmp_path / "channels"
    channels_dir.mkdir()

    with patch("core.services.prompt_contract._channel_workspace_path", return_value=channels_dir):
        with patch("core.services.chat_sessions.get_chat_session", return_value={"title": "New chat", "session_id": "s2"}):
            from core.services.prompt_contract import _channel_context_section
            result = _channel_context_section("s2")

    assert result is None


def test_unknown_channel_returns_none(tmp_path):
    channels_dir = tmp_path / "channels"
    channels_dir.mkdir()

    with patch("core.services.prompt_contract._channel_workspace_path", return_value=channels_dir):
        with patch("core.services.chat_sessions.get_chat_session", return_value={"title": "Something weird", "session_id": "s3"}):
            from core.services.prompt_contract import _channel_context_section
            result = _channel_context_section("s3")

    assert result is None
