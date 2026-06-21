"""Test: owner-override (`!override`) wiret ind i webchat/desk-stien (chat_stream_v2).

Root cause (Bjørn 2026-06-21): override-kommandoen var KUN wiret i discord/telegram,
så Bjørns `!override <TOTP>` i desk-appen aldrig aktiverede → operator-tools i en
member-session (mors Mac) forblev tool_not_permitted.
"""
from __future__ import annotations

import asyncio

from apps.api.jarvis_api.routes import chat_stream_v2 as mod


def _drain(resp) -> str:
    async def _run() -> str:
        out = []
        async for frame in resp.body_iterator:
            out.append(frame if isinstance(frame, str) else frame.decode())
        return "".join(out)
    return asyncio.run(_run())


def test_plain_text_is_not_an_override_command(monkeypatch):
    # get_owner/seed stubbes så testen ikke afhænger af users.json i miljøet.
    monkeypatch.setattr(mod, "maybe_handle_override", mod.maybe_handle_override)
    res = mod.maybe_handle_override("hej Jarvis, hvad er klokken?", "chat-x")
    assert res is None  # normal besked → ingen kortslutning


def test_override_v2_response_emits_full_protocol_sequence():
    resp = _override_v2_response_text("Owner-override aktiveret (help).")
    body = _drain(resp)
    # Klienten forlader kun 'working' på message_stop → hele sekvensen SKAL være der.
    for ev in ("message_start", "content_block_start", "content_block_delta",
               "content_block_stop", "message_delta", "message_stop"):
        assert f"event: {ev}" in body, f"mangler {ev}"
    assert "Owner-override aktiveret" in body
    assert body.rstrip().endswith("}")  # velformet sidste frame


def _override_v2_response_text(reply: str):
    return mod._override_v2_response(
        reply, session_id="chat-x", model="m", provider="p", lane="primary"
    )


def test_revoke_is_handled_as_override(monkeypatch):
    # revoke kræver ingen seed → handler returnerer et dict (ikke None).
    monkeypatch.setattr(mod, "get_owner", lambda: None, raising=False)
    res = mod.maybe_handle_override("!revoke-override", "chat-x")
    assert res is not None
    assert res.get("action") == "revoked"
