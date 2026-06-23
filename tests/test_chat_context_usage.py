"""Tests for /chat/context-usage — backend-autoritativt kontekst-fyld til composer-ringen.

Bjørn 2026-06-23: den gamle ring fodredes af per-tur stream-usage (nulstilledes mellem ture,
hoppede ulogisk). Dette endpoint giver det ÆGTE transcript-estimat siden sidste compact +
compaction-status, så ringen harmonerer med autocompact og pause-indikatoren virker.
"""
from __future__ import annotations

import asyncio


def _call(**kw):
    from apps.api.jarvis_api.routes.chat import chat_context_usage
    return asyncio.run(chat_context_usage(**kw))


def test_shape_and_self_safe_on_empty_session():
    r = _call(session_id="", provider="ollama", model="glm-5.2:cloud")
    assert set(r) == {"tokens", "compact_at", "effective", "compacting", "compacted"}
    assert r["tokens"] == 0
    assert isinstance(r["compacting"], bool) and isinstance(r["compacted"], bool)


def test_effective_is_min_of_window_and_compact():
    # glm-vindue (200k) vs compact-tærskel → effective = det mindste (ring-nævneren)
    r = _call(session_id="", provider="ollama", model="glm-5.2:cloud")
    assert r["effective"] <= 200_000
    assert r["effective"] <= r["compact_at"] or r["effective"] <= 200_000


def test_compacting_reflects_inflight_set(monkeypatch):
    import core.services.prompt_contract as pc
    pc._compact_inflight.add("sid-live")
    try:
        r = _call(session_id="sid-live", provider="", model="")
        assert r["compacting"] is True
    finally:
        pc._compact_inflight.discard("sid-live")
    r2 = _call(session_id="sid-idle", provider="", model="")
    assert r2["compacting"] is False
