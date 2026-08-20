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


# Kontrakten jarvis-desk afhænger af: ChatView.tsx:110 og CodeView.tsx:282 læser
# tokens/overhead_tokens/compacting, api.ts:707 typer hele svaret. Fjernes et felt
# herfra, går composer-ringen i stykker — derfor er sættet LUKKET: en ny nøgle skal
# tilføjes bevidst her OG i api.ts's type, i samme ombæring.
_DESK_CONTRACT = {
    "tokens", "compact_at", "effective", "model_window",
    "overhead_tokens", "compacting", "compacted",
}


def test_shape_and_self_safe_on_empty_session():
    r = _call(session_id="", provider="ollama", model="glm-5.2:cloud")
    assert set(r) == _DESK_CONTRACT
    assert r["tokens"] == 0
    assert isinstance(r["compacting"], bool) and isinstance(r["compacted"], bool)


def test_model_aware_window_and_effective():
    # Model-BEVIDST (2026-07-18): glm-5.2 → 1M reelt vindue; ringen måler mod
    # attention-budgettet, så effective = min(vindue, budget).
    r = _call(session_id="", provider="ollama", model="glm-5.2:cloud")
    assert r["model_window"] == 1_000_000          # model-map-fix + endpoint model-awareness
    assert r["effective"] == min(r["model_window"], r["compact_at"])
    # glm-5.1 har et MINDRE vindue → verificér at endpointet skelner
    r51 = _call(session_id="", provider="ollama", model="glm-5.1:cloud")
    assert r51["model_window"] == 256_000


def test_compact_at_foelger_det_LEVENDE_attention_budget():
    """Ringen skal måle mod det budget compaction FAKTISK bruger — ikke en konstant.

    Den gamle test låste `compact_at <= 60_000`. Da Bjørn hævede budgettet 35k→80k
    (hans "glemmer 4 beskeder"-fix) blev testen rød uden at noget var i stykker:
    den målte en værdi, ikke en invariant. Invarianten er koblingen — ringen og
    compaction-triggeren skal læse SAMME tal, ellers viser composeren et loft
    Jarvis ikke har.
    """
    from core.runtime.settings import load_settings
    budget = int(getattr(load_settings(), "context_attention_budget_tokens", 35_000) or 35_000)
    r = _call(session_id="", provider="ollama", model="glm-5.2:cloud")
    assert r["compact_at"] == budget


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


# ── Manual /compact endpoint (2026-07-18) ───────────────────────────────────

def _compact_now(**kw):
    from apps.api.jarvis_api.routes.chat import chat_compact_now, _CompactNowBody
    return asyncio.run(chat_compact_now(_CompactNowBody(**kw)))


def test_manual_compact_spawns_and_sets_inflight(monkeypatch):
    import core.services.prompt_contract as pc
    captured = {}

    def _fake_run(sid, keep_recent, *, low_water_tokens=15_000, focus=None):
        captured["sid"] = sid
        captured["focus"] = focus
        captured["low_water"] = low_water_tokens

    monkeypatch.setattr(pc, "_run_session_compaction", _fake_run)
    pc._compact_inflight.discard("manual-1")
    r = _compact_now(session_id="manual-1", focus="behold API-kontrakten")
    assert r["started"] is True
    import time
    for _ in range(50):
        if "sid" in captured:
            break
        time.sleep(0.01)
    assert captured["sid"] == "manual-1"
    assert captured["focus"] == "behold API-kontrakten"


def test_manual_compact_missing_session_is_safe():
    r = _compact_now(session_id="", focus="")
    assert r["started"] is False
    assert "session" in r["reason"]


def test_manual_compact_deduped_when_already_inflight(monkeypatch):
    import core.services.prompt_contract as pc
    monkeypatch.setattr(pc, "_run_session_compaction", lambda *a, **k: None)
    pc._compact_inflight.add("busy-1")
    try:
        r = _compact_now(session_id="busy-1")
        assert r["started"] is False
        assert r["reason"] == "already compacting"
    finally:
        pc._compact_inflight.discard("busy-1")
