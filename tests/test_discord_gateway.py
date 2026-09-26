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


class TestDowngradeUnsupportedForDiscord:
    """Discord tegner ikke `---` (thematic break) eller `####`+ overskrifter —
    de står som rå tegn. Nedgraderingen gør dem læsbare."""

    def test_thematic_break_becomes_rule(self):
        from core.services.discord_gateway import (
            _downgrade_unsupported_for_discord,
            _DISCORD_RULE,
        )

        out = _downgrade_unsupported_for_discord("Før\n---\nEfter")
        assert out == f"Før\n{_DISCORD_RULE}\nEfter"

    def test_deep_header_downgraded_to_three(self):
        from core.services.discord_gateway import _downgrade_unsupported_for_discord

        assert (
            _downgrade_unsupported_for_discord("#### Detaljer")
            == "### Detaljer"
        )
        # Fem hashes også.
        assert (
            _downgrade_unsupported_for_discord("##### Dybt")
            == "### Dybt"
        )

    def test_three_hashes_untouched(self):
        from core.services.discord_gateway import _downgrade_unsupported_for_discord

        assert _downgrade_unsupported_for_discord("### Fint") == "### Fint"

    def test_hash_without_space_is_not_a_header(self):
        from core.services.discord_gateway import _downgrade_unsupported_for_discord

        # `####5` er ikke en ATX-header (kræver whitespace efter hashes).
        assert _downgrade_unsupported_for_discord("se ####5 her") == "se ####5 her"

    def test_inside_code_fence_untouched(self):
        from core.services.discord_gateway import _downgrade_unsupported_for_discord

        text = "```\n---\n#### x\n```"
        assert _downgrade_unsupported_for_discord(text) == text

    def test_table_separator_row_is_not_a_break(self):
        from core.services.discord_gateway import _downgrade_unsupported_for_discord

        # `| --- | --- |` starter med pipe → ikke en thematic break.
        text = "| a | b |\n| --- | --- |"
        assert _downgrade_unsupported_for_discord(text) == text


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


# ── Streaming (message-edit) — 26/9-2026 ────────────────────────────────────
# Discord føltes langsommere end desk fordi svaret blev dumpet først når kørslen
# var færdig. Løsningen: placeholder + redigering mens teksten vokser, med den
# ENDELIGE tekst ejet af eventbus-abonnenten.
class TestExtractTextDeltas:
    """Preview-teksten kommer fra v2-SSE-frames — kun text_delta, ikke thinking."""

    def test_accumulates_text_deltas(self):
        from core.services.discord_gateway import _extract_text_deltas

        frames = [
            'event: content_block_delta\ndata: {"index": 0, "delta": {"type": "text_delta", "text": "Hej "}}\n\n',
            'event: content_block_delta\ndata: {"index": 0, "delta": {"type": "text_delta", "text": "Bjørn"}}\n\n',
        ]
        assert _extract_text_deltas(frames) == "Hej Bjørn"

    def test_ignores_thinking_delta(self):
        from core.services.discord_gateway import _extract_text_deltas

        frames = [
            'event: content_block_delta\ndata: {"index": 1, "delta": {"type": "thinking_delta", "thinking": "skjult tanke"}}\n\n',
            'event: content_block_delta\ndata: {"index": 0, "delta": {"type": "text_delta", "text": "svar"}}\n\n',
        ]
        assert _extract_text_deltas(frames) == "svar"

    def test_ignores_non_delta_frames(self):
        from core.services.discord_gateway import _extract_text_deltas

        frames = [
            'event: message_start\ndata: {"run_id": "r1"}\n\n',
            'event: content_block_stop\ndata: {"index": 0}\n\n',
            'event: ping\ndata: {}\n\n',
        ]
        assert _extract_text_deltas(frames) == ""

    def test_ignores_malformed_json(self):
        from core.services.discord_gateway import _extract_text_deltas

        assert _extract_text_deltas(["event: content_block_delta\ndata: ikke-json\n\n"]) == ""


class TestStreamRunToDiscord:
    """Streameren sender beskeden ved første tekst og redigerer den derefter."""

    def _fake_client(self, sent, edits):
        class FakeMessage:
            async def edit(self, content=None):
                edits.append(content)

        class FakeChannel:
            async def send(self, content=None):
                sent.append(content)
                return FakeMessage()

        class FakeClient:
            def get_channel(self, cid):
                return FakeChannel()

        return FakeClient()

    def test_sends_message_on_first_text_and_edits(self, monkeypatch):
        import asyncio

        import core.services.discord_gateway as dg

        sent: list = []
        edits: list = []
        monkeypatch.setattr(dg, "_client", self._fake_client(sent, edits))
        monkeypatch.setattr(dg, "_STREAM_EDIT_INTERVAL_S", 0.0)
        monkeypatch.setattr(dg, "_STREAM_POLL_S", 0.0)

        batches = [
            (['event: content_block_delta\ndata: {"delta": {"type": "text_delta", "text": "Hej"}}\n\n'], False, 1),
            ([], True, 1),
        ]
        calls = {"n": 0}

        def fake_snapshot(sid, idx):
            b = batches[min(calls["n"], len(batches) - 1)]
            calls["n"] += 1
            return b

        import core.services.run_follow as rf
        monkeypatch.setattr(rf, "snapshot_from", fake_snapshot)

        asyncio.run(dg._stream_run_to_discord(123, "sess-x"))
        try:
            # Første rigtige tekst sendes som besked — ingen «…»-placeholder.
            assert sent == ["Hej"]
            assert edits == [], "beskeden indeholder allerede teksten → ingen edit"
            # Runnet er done → staten står til finalize. Ryddede vi den her,
            # ville finalize sende svaret som en DUBLET i stedet for at redigere.
            st = dg._stream_state.get("sess-x")
            assert st is not None and st["run_done"] and st["stopped"]
        finally:
            dg._stream_state.pop("sess-x", None)

    def test_sends_nothing_when_no_text_arrives(self, monkeypatch):
        """Ingen tekst → ingen besked. Typing-indikatoren bar livstegnet."""
        import asyncio

        import core.services.discord_gateway as dg

        sent: list = []
        edits: list = []
        monkeypatch.setattr(dg, "_client", self._fake_client(sent, edits))
        monkeypatch.setattr(dg, "_STREAM_POLL_S", 0.0)

        import core.services.run_follow as rf
        monkeypatch.setattr(rf, "snapshot_from", lambda sid, idx: ([], True, idx))

        asyncio.run(dg._stream_run_to_discord(123, "sess-tom"))
        try:
            assert sent == [], "ingen tekst → ingen besked i kanalen"
            assert dg._stream_state.get("sess-tom") is not None, "staten står til finalize"
        finally:
            dg._stream_state.pop("sess-tom", None)

    def test_done_before_finalize_edits_instead_of_duplicating(self, monkeypatch):
        """Streameren ser done FØR finalize → staten skal stå, så finalize
        REDIGERER beskeden. Ellers står svaret to gange i kanalen."""
        import asyncio

        import core.services.discord_gateway as dg

        sent: list = []
        edits: list = []
        monkeypatch.setattr(dg, "_client", self._fake_client(sent, edits))
        monkeypatch.setattr(dg, "_STREAM_POLL_S", 0.0)

        import core.services.run_follow as rf
        frames = ['event: content_block_delta\ndata: {"delta": {"type": "text_delta", "text": "Hej"}}\n\n']
        monkeypatch.setattr(rf, "snapshot_from", lambda sid, idx: (frames, True, 1))

        q: list = []
        monkeypatch.setattr(
            dg, "_outbound_queue", type("Q", (), {"put_nowait": lambda self, i: q.append(i)})()
        )
        try:
            asyncio.run(dg._stream_run_to_discord(123, "sess-done"))
            st = dg._stream_state.get("sess-done")
            assert st is not None and st["run_done"], "staten skal stå til finalize"

            dg._finalize_stream_or_send("sess-done", 123, "Hej")

            assert sent == ["Hej"], "ingen NY besked — svaret må ikke dubleres"
            assert q and q[0]["edit_session"] == "sess-done"
        finally:
            dg._stream_state.pop("sess-done", None)


class TestFinalizeStreamOrSend:
    """Ved run-slut: redigér streamerens besked, ellers send en ny."""

    def test_queues_edit_intent_when_message_exists(self, monkeypatch):
        import core.services.discord_gateway as dg

        class FakeMessage:
            pass

        class FakeQ:
            def __init__(self):
                self.items = []

            def put_nowait(self, item):
                self.items.append(item)

        fq = FakeQ()
        monkeypatch.setattr(dg, "_outbound_queue", fq)
        sent: list = []
        monkeypatch.setattr(dg, "send_discord_message", lambda cid, txt: sent.append((cid, txt)))
        dg._stream_state["s"] = {"message": FakeMessage(), "stopped": True, "finished": False}
        try:
            dg._finalize_stream_or_send("s", 42, "endelig tekst")
        finally:
            dg._stream_state.pop("s", None)

        assert sent == [], "besked findes → ingen ny besked"
        assert fq.items and fq.items[0]["edit_session"] == "s"
        assert fq.items[0]["text"] == "endelig tekst"

    def test_falls_back_to_send_without_state(self, monkeypatch):
        import core.services.discord_gateway as dg

        sent: list = []
        monkeypatch.setattr(dg, "send_discord_message", lambda cid, txt: sent.append((cid, txt)))
        dg._finalize_stream_or_send("ukendt-session", 42, "tekst")

        assert sent == [(42, "tekst")]

    def test_falls_back_when_streamer_never_sent(self, monkeypatch):
        """State findes, men streameren fik aldrig tekst → normal send + ryd."""
        import core.services.discord_gateway as dg

        sent: list = []
        monkeypatch.setattr(dg, "send_discord_message", lambda cid, txt: sent.append((cid, txt)))
        dg._stream_state["s2"] = {"message": None, "stopped": True, "finished": False}
        try:
            dg._finalize_stream_or_send("s2", 42, "tekst")
        finally:
            dg._stream_state.pop("s2", None)

        assert sent == [(42, "tekst")]
        assert "s2" not in dg._stream_state


class TestSweepStaleStreams:
    """Efterladte streamer-states (intet finalize-kald) skal ryddes."""

    def test_removes_old_stopped_keeps_fresh_and_active(self):
        import time

        import core.services.discord_gateway as dg

        now = time.monotonic()
        dg._stream_state["gammel"] = {"stopped": True, "stopped_at": now - 9999}
        dg._stream_state["frisk"] = {"stopped": True, "stopped_at": now}
        dg._stream_state["aktiv"] = {"stopped": False, "stopped_at": 0.0}
        try:
            dg._sweep_stale_streams()
            assert "gammel" not in dg._stream_state
            assert "frisk" in dg._stream_state
            assert "aktiv" in dg._stream_state
        finally:
            for k in ("gammel", "frisk", "aktiv"):
                dg._stream_state.pop(k, None)


class TestApplyEditIntent:
    """Edit-intentet redigerer beskeden til den endelige, formaterede tekst."""

    def test_edits_message_and_wraps_tables(self, monkeypatch):
        import asyncio

        import core.services.discord_gateway as dg

        edits: list = []

        class FakeMessage:
            async def edit(self, content=None):
                edits.append(content)

        class FakeChannel:
            async def send(self, content=None):
                pass

        class Msg(FakeMessage):
            channel = FakeChannel()

        monkeypatch.setattr(dg, "_persist_status", lambda: None)
        dg._stream_state["s"] = {"message": Msg(), "stopped": True}
        try:
            asyncio.run(dg._apply_edit_intent({
                "edit_session": "s",
                "channel_id": 42,
                "text": "| a | b |\n| --- | --- |\n| 1 | 2 |",
            }))
        finally:
            dg._stream_state.pop("s", None)

        assert edits, "beskeden blev ikke redigeret"
        assert "```" in edits[0], "tabellen skulle være pakket i kode-fence"
        assert "s" not in dg._stream_state, "state skulle være ryddet"

    def test_falls_back_to_send_without_message(self, monkeypatch):
        import asyncio

        import core.services.discord_gateway as dg

        sent: list = []
        monkeypatch.setattr(dg, "send_discord_message", lambda cid, txt: sent.append((cid, txt)))
        asyncio.run(dg._apply_edit_intent({"edit_session": "x", "channel_id": 7, "text": "hej"}))

        assert sent == [(7, "hej")]

