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


# ── Discord-formatering: tabeller i kode-fence + linjebevidst splitter ──────
class TestWrapTablesForDiscord:
    """Discord har ingen tabel-renderer. Normalizeren producerer GFM-tabeller
    for ALLE kanaler, så Discord-stien pakker dem i ```-blokke. Uden dette står
    rækkerne som rå `| a | b |`-tegn i kanalen."""

    def test_wraps_gfm_table_in_code_fence(self):
        from core.services.discord_gateway import _wrap_tables_for_discord

        text = (
            "Her er tallene:\n\n"
            "| Navn | Tal |\n| --- | --- |\n| a | 1 |\n| b | 2 |\n\n"
            "Og lidt prosa."
        )
        out = _wrap_tables_for_discord(text)
        assert "```\n| Navn | Tal |\n| --- | --- |\n| a | 1 |\n| b | 2 |\n```" in out
        assert out.startswith("Her er tallene:")
        assert out.endswith("Og lidt prosa.")

    def test_leaves_prose_without_tables_untouched(self):
        from core.services.discord_gateway import _wrap_tables_for_discord

        text = "Ingen tabel her.\nBare to linjer."
        assert _wrap_tables_for_discord(text) == text

    def test_does_not_double_wrap_table_already_in_fence(self):
        from core.services.discord_gateway import _wrap_tables_for_discord

        text = "```\n| a | b |\n| --- | --- |\n| 1 | 2 |\n```"
        assert _wrap_tables_for_discord(text) == text

    def test_pipe_in_prose_without_separator_is_not_a_table(self):
        from core.services.discord_gateway import _wrap_tables_for_discord

        # En linje med pipe-tegn, men UDEN separator-række, er ikke en tabel.
        text = "Enten | eller — det er et valg."
        assert _wrap_tables_for_discord(text) == text


class TestSplitMessage:
    """Splitteren må ikke flække en kodeblok midt over: en fence der krydser
    grænsen lukkes ved chunk-slut og genåbnes ved næste chunks start."""

    def test_short_text_is_single_chunk(self):
        from core.services.discord_gateway import _split_message

        assert _split_message("kort", 1900) == ["kort"]

    def test_every_chunk_within_limit(self):
        from core.services.discord_gateway import _split_message

        text = "\n".join(f"linje {i} " + "x" * 80 for i in range(100))
        chunks = _split_message(text, 200)
        assert len(chunks) > 1
        assert all(len(c) <= 200 for c in chunks)
        assert "\n".join(chunks) == text

    def test_splits_at_line_boundary_not_mid_line(self):
        from core.services.discord_gateway import _split_message

        text = "a" * 50 + "\n" + "b" * 50 + "\n" + "c" * 50
        chunks = _split_message(text, 60)
        # Ved loft 60 passer præcis én linje pr. chunk — ingen linje flækkes.
        assert chunks == ["a" * 50, "b" * 50, "c" * 50]

    def test_fence_is_closed_and_reopened_across_chunks(self):
        from core.services.discord_gateway import _split_message

        kode = "\n".join("x" * 60 for _ in range(10))
        text = "Før:\n```python\n" + kode + "\n```\nEfter."
        chunks = _split_message(text, 200)
        assert len(chunks) > 1
        # Hver chunk skal have et LIGE antal ``` — ellers står resten af koden
        # som løs tekst hos Discord.
        for c in chunks:
            assert c.count("```") % 2 == 0, f"uafsluttet fence: {c[:50]!r}"
            assert len(c) <= 200
        assert "x" * 60 in "\n".join(chunks)
        assert "Efter." in chunks[-1]

    def test_single_overlong_line_is_hard_split(self):
        from core.services.discord_gateway import _split_message

        text = "y" * 450
        chunks = _split_message(text, 200)
        assert all(len(c) <= 200 for c in chunks)
        assert "".join(chunks) == text
