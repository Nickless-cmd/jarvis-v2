"""Tests for telegram_gateway send-path — fokus på communication-guard wiring.

Verificerer at send_message() scrubber hårde afslutnings-fraser (godnat/
sov godt) før de når Telegram-API'et, beholder resten, og skipper helt hvis
intet er tilbage. Bløde fraser (lad mig) passerer urørt.
"""
from __future__ import annotations

from pathlib import Path
from unittest import mock

import pytest


def _clean_guard_state():
    p = Path.home() / ".jarvis-v2" / "state" / "communication_guard.json"
    if p.exists():
        p.unlink()


@pytest.fixture(autouse=True)
def _clean():
    _clean_guard_state()
    yield
    _clean_guard_state()


def _patched_send(text: str):
    """Kald send_message med _load_config + _api mocket. Returnerer
    (result, captured_payload_or_None)."""
    from core.services import telegram_gateway as tg

    captured: dict = {}

    def _fake_api(token, method, payload):
        captured["payload"] = payload
        return {"ok": True, "result": {"message_id": 42}}

    with mock.patch.object(tg, "_load_config", return_value={"token": "x", "chat_id": "123"}), \
         mock.patch.object(tg, "_api", side_effect=_fake_api):
        result = tg.send_message(text)
    return result, captured.get("payload")


def test_scrubs_hard_closing_keeps_content():
    result, payload = _patched_send("Opgaven er løst. Godnat, Bjørn.")
    assert result["status"] == "sent"
    assert payload is not None
    assert "godnat" not in payload["text"].lower()
    assert "Opgaven er løst" in payload["text"]


def test_only_closing_is_skipped_not_sent():
    result, payload = _patched_send("Godnat!")
    assert result["status"] == "skipped"
    assert payload is None  # _api blev aldrig kaldt


def test_safe_text_passes_through():
    result, payload = _patched_send("Status: alt grønt.")
    assert result["status"] == "sent"
    assert payload["text"] == "Status: alt grønt."


def test_soft_phrase_passes_through():
    result, payload = _patched_send("Lad mig tjekke det for dig.")
    assert result["status"] == "sent"
    assert payload["text"] == "Lad mig tjekke det for dig."
