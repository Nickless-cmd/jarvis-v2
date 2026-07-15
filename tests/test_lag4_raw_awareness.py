"""Tests for Lag 4 — awareness re-render (Jarvis' eget forslag, 14. jul 2026).

Rå kompakte brackets + arrow-delta nudges i stedet for genererede label-sætninger, bag flaget
`raw_awareness` (default OFF). Kontrakt: flag OFF → NØJAGTIG nuværende adfærd bevaret; flag ON →
kompakte brackets med rå tal, ingen LLM/label-sætninger. Purely additive.

Hermetisk: lag-tilstandene holdes via _hold_reading; mood-oscillatoren monkeypatches; runtime-state
kører på isolated_runtime's in-memory KV.
"""
from __future__ import annotations

import pytest

from core.runtime.db_core import set_runtime_state_value
from core.services import central_body_mood_feel as bm
from core.services import central_self_state as ss


@pytest.fixture(autouse=True)
def _reset(isolated_runtime):
    from core.services import central_layer_contract as lc
    lc._kv_set(lc._HELD_KEY, {})
    ss._kv_set(ss._STATE_KEY, {})
    yield


def _flag_on() -> None:
    set_runtime_state_value(bm._RAW_AWARENESS_FLAG, True)


def _hold_common() -> None:
    bm._hold_reading(bm._PROPRIOCEPTION, {"feel": "rolig", "cpu_pct": 17.0,
                                          "rss_mb": 11.2, "self_latency_ms": 3.0})
    bm._hold_reading(bm._MOOD, {"mood": "content", "description": "Tilfreds", "intensity": 0.5})
    bm._hold_reading(bm._DEVELOPMENTAL, {"trajectory": "blooming", "vector": 0.3})


def _patch_mood(monkeypatch, value: float = 0.37, intensity: float = 0.5) -> None:
    monkeypatch.setattr("core.services.mood_oscillator._combined_value", lambda: value)
    monkeypatch.setattr("core.services.mood_oscillator.get_mood_intensity", lambda: intensity)


def _full_self(monkeypatch) -> None:
    monkeypatch.setattr(ss, "_valence", lambda: {"tone": "blomstrende", "score": 0.17,
                                                 "intensity": 0.27, "trend": "flourishing"})
    monkeypatch.setattr(ss, "_agenda", lambda: {"counts": {"goals": 3},
                        "next_intention": {"kind": "initiative", "text": "Byg en stødigere kerne"}})
    monkeypatch.setattr(ss, "_self_model", lambda: {"surfaces_populated": 85, "completeness": 1.0})


# ── FLAG READER ──────────────────────────────────────────────────────────
def test_flag_default_off(isolated_runtime):
    assert bm.raw_awareness_enabled() is False


def test_flag_string_off_reads_false(isolated_runtime):
    # bool('off') == True-fælden: skal læses robust som False
    set_runtime_state_value(bm._RAW_AWARENESS_FLAG, "off")
    assert bm.raw_awareness_enabled() is False


def test_flag_on(isolated_runtime):
    _flag_on()
    assert bm.raw_awareness_enabled() is True


# ── FLAG OFF: nuværende sætninger bevaret (purely additive) ──────────────
def test_body_mood_off_preserves_sentences(isolated_runtime):
    _hold_common()
    parts = bm.describe_body_mood_feel()
    assert any("proprioceptivt mærker jeg mig rolig" in p for p in parts)
    assert any("stemningen er tilfreds" in p for p in parts)
    assert any("udviklings-kompas peger mod blomstring" in p for p in parts)
    # ingen brackets når flaget er OFF
    assert not any(p.startswith("[") for p in parts)


def test_describe_self_off_preserves_sentences(monkeypatch, isolated_runtime):
    _full_self(monkeypatch)
    ss.run_self_state_tick()
    desc = ss.describe_self()
    assert "85 lag af mig selv" in desc
    assert "ved at blive" in desc
    assert "[Selv:" not in desc and "[Somatic:" not in desc


# ── FLAG ON: kompakte brackets med rå tal, ingen label-sætninger ─────────
def test_body_mood_on_emits_compact_brackets(monkeypatch, isolated_runtime):
    _flag_on()
    _hold_common()
    _patch_mood(monkeypatch, value=0.37, intensity=0.5)
    parts = bm.describe_body_mood_feel()
    joined = " ".join(parts)
    assert "[Somatic: cpu 17% · ram 11.2MB · latens 3ms]" in parts
    assert "[Affekt: valens +0.37 · intensitet 0.50]" in parts
    assert "[Vækst: puls +0.30 → blooming]" in parts
    # ingen genererede label-sætninger / mood-ord
    assert "proprioceptivt" not in joined
    assert "stemningen er" not in joined
    assert "Tilfreds" not in joined and "tilfreds" not in joined


def test_affekt_uses_number_not_mood_label(monkeypatch, isolated_runtime):
    # Requirement #3: mood-label droppet til fordel for tallet når raw ON
    _flag_on()
    bm._hold_reading(bm._MOOD, {"mood": "euphoric", "description": "Meget Euforisk"})
    _patch_mood(monkeypatch, value=0.82, intensity=0.82)
    parts = bm.describe_body_mood_feel()
    joined = " ".join(parts)
    assert "[Affekt: valens +0.82 · intensitet 0.82]" in parts
    assert "Euforisk" not in joined and "euphoric" not in joined


def test_describe_self_on_emits_brackets_no_sentences(monkeypatch, isolated_runtime):
    _flag_on()
    _full_self(monkeypatch)
    _hold_common()
    _patch_mood(monkeypatch, value=0.37, intensity=0.5)
    # ægte oppetid → [Tid: ... kørt] renderes deterministisk (first_boot 2 dage siden)
    from datetime import UTC, datetime, timedelta
    ss._kv_set(ss._FIRST_BOOT_TS, (datetime.now(UTC) - timedelta(days=2)).isoformat())
    ss.run_self_state_tick()
    desc = ss.describe_self()
    # rå brackets — én pr. linje
    assert "[Selv: 85 lag · 100% · lys → agens]" in desc
    assert "[Tid:" in desc and "kørt" in desc
    assert "[Somatic: cpu 17%" in desc
    assert "[Affekt: valens +0.37" in desc
    # ingen af de genererede label-sætninger
    assert "85 lag af mig selv" not in desc
    assert "ved at blive" not in desc
    assert "stemningen er" not in desc


def test_describe_self_on_baseline_unchanged_when_empty(monkeypatch, isolated_runtime):
    # selv-tilstand uden mål og uden holdte aflæsninger → [baseline uændret]
    _flag_on()
    monkeypatch.setattr(ss, "_valence", lambda: {})
    monkeypatch.setattr(ss, "_agenda", lambda: {})
    monkeypatch.setattr(ss, "_self_model", lambda: {})
    # ingen holdte krop/vækst-aflæsninger (reset) + mood utilgængelig → intet meningsfuldt at tale
    monkeypatch.setattr("core.services.mood_oscillator._combined_value",
                        lambda: (_ for _ in ()).throw(RuntimeError("x")))
    ss.run_self_state_tick()
    desc = ss.describe_self()
    assert desc == "[baseline uændret]"


# ── ARROW-DELTA NUDGE ────────────────────────────────────────────────────
def test_valence_delta_nudge_latches_and_renders(monkeypatch, isolated_runtime):
    _flag_on()
    # tick 1: valens 0.17
    monkeypatch.setattr(ss, "_valence", lambda: {"tone": "blomstrende", "score": 0.17,
                                                 "trend": "flourishing"})
    monkeypatch.setattr(ss, "_agenda", lambda: {"next_intention": {"text": "x"}})
    monkeypatch.setattr(ss, "_self_model", lambda: {"surfaces_populated": 85, "completeness": 1.0})
    ss.run_self_state_tick()
    # tick 2: valens hopper til 0.55 (|Δ| ≥ 0.15) → nudge latches
    monkeypatch.setattr(ss, "_valence", lambda: {"tone": "blomstrende", "score": 0.55,
                                                 "trend": "flourishing"})
    ss.run_self_state_tick()
    desc = ss.describe_self()
    assert "[⚠️ valens +0.17→+0.55]" in desc


def test_valence_delta_no_nudge_when_stable(monkeypatch, isolated_runtime):
    _flag_on()
    monkeypatch.setattr(ss, "_valence", lambda: {"tone": "blomstrende", "score": 0.30,
                                                 "trend": "flourishing"})
    monkeypatch.setattr(ss, "_agenda", lambda: {"next_intention": {"text": "x"}})
    monkeypatch.setattr(ss, "_self_model", lambda: {"surfaces_populated": 85, "completeness": 1.0})
    ss.run_self_state_tick()
    ss.run_self_state_tick()   # ingen ændring
    desc = ss.describe_self()
    assert "[⚠️ valens" not in desc


# ── SELF-SAFE ────────────────────────────────────────────────────────────
def test_raw_render_self_safe_on_mood_error(monkeypatch, isolated_runtime):
    _flag_on()
    _hold_common()
    monkeypatch.setattr("core.services.mood_oscillator._combined_value",
                        lambda: (_ for _ in ()).throw(RuntimeError("x")))
    # ét lags fejl må ikke sprede sig — stadig en liste med de andre brackets
    parts = bm.describe_body_mood_feel()
    assert isinstance(parts, list)
    assert any(p.startswith("[Somatic:") for p in parts)
    assert not any(p.startswith("[Affekt:") for p in parts)


def test_flag_read_error_defaults_off(monkeypatch, isolated_runtime):
    monkeypatch.setattr("core.runtime.db_core.get_runtime_state_bool",
                        lambda k, d=False: (_ for _ in ()).throw(RuntimeError("x")))
    assert bm.raw_awareness_enabled() is False
