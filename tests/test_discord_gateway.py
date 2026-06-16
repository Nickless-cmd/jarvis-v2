"""Tests for discord_gateway helpers.

Specific UI/attachment behaviour lives in test_discord_gateway_attachments.py.
This file covers the channel-resolution + auto-status helpers added
2026-05-22 with the run-closure-gate.
"""
from __future__ import annotations

from unittest.mock import patch, MagicMock


class TestResolveChannelForSession:
    def test_returns_channel_from_db_when_found(self):
        from core.services.discord_gateway import _resolve_channel_for_session

        fake_row = ("9999999999",)
        with patch("core.runtime.db.connect") as mock_connect:
            ctx = mock_connect.return_value.__enter__.return_value
            ctx.execute.return_value.fetchone.return_value = fake_row
            out = _resolve_channel_for_session("any-session-id")
        assert out == "9999999999"

    def test_falls_back_to_owner_dm_when_session_unknown(self):
        from core.services.discord_gateway import _resolve_channel_for_session

        with patch("core.runtime.db.connect") as mock_connect:
            ctx = mock_connect.return_value.__enter__.return_value
            ctx.execute.return_value.fetchone.return_value = None
            out = _resolve_channel_for_session("unknown-session")
        # Falls back to Bjørn's owner DM channel
        assert out == "1474048593219555461"

    def test_falls_back_on_db_error(self):
        from core.services.discord_gateway import _resolve_channel_for_session

        with patch("core.runtime.db.connect", side_effect=RuntimeError("db down")):
            out = _resolve_channel_for_session("any")
        assert out == "1474048593219555461"


# ── Spor B: Discord-brugerbesked annoncerer channel.chat_message_appended ────
def test_user_message_announces_chat_message_appended(monkeypatch):
    """Discord-brugerbesked SKAL udsende channel.chat_message_appended (source=
    discord-gateway, role=user), så session_inbox ser sessionen aktiv og daemon-
    notifikationer køes i stedet for at afbryde midt i et run. Echo-subscriber'en
    springer den over (kræver source=visible-run + role=assistant)."""
    import core.services.discord_gateway as dg
    import core.eventbus.bus as bus

    published: list = []
    monkeypatch.setattr(
        bus.event_bus, "publish",
        lambda kind, payload=None: published.append((kind, payload)),
    )

    dg._announce_user_message_appended("sess-123", {"role": "user", "content": "hej"})

    evts = [p for (k, p) in published if k == "channel.chat_message_appended"]
    assert evts, "channel.chat_message_appended blev ikke udsendt"
    assert evts[0]["session_id"] == "sess-123"
    assert evts[0]["source"] == "discord-gateway"
    assert evts[0]["message"]["role"] == "user"
