"""Tests for DIASTOLE — KONSUMTIONS-skridtet (§28, owner Bjørn samtykkede).

Tempo-skalaren ganges nu på hver NON-exempt producers effektive cooldown.
Invarianter: flag OFF → byte-identisk gammel adfærd · exempt ALDRIG moduleret ·
klemme [0.5, 2.0] respekteret · self-safe (ødelagt sense → 1.0 → gammel adfærd).
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import core.services.central_cadence_conductor as cc
import core.services.internal_cadence as ic


# --- effective_cooldown: kernen i konsumtionen ---

def test_exempt_producer_never_modulated_even_at_max_tempo():
    assert cc.effective_cooldown("central_membrane_watch", 15.0, 2.0) == 15.0
    assert cc.effective_cooldown("central_membrane_watch", 15.0, 0.5) == 15.0


def test_all_exempt_names_are_fixed_cadence():
    for name in cc.CADENCE_TEMPO_EXEMPT:
        assert cc.effective_cooldown(name, 5.0, 0.5) == 5.0
        assert cc.effective_cooldown(name, 5.0, 2.0) == 5.0


def test_nonexempt_halved_at_tempo_floor():
    assert cc.effective_cooldown("inner_voice_daemon", 10.0, 0.5) == 5.0


def test_nonexempt_doubled_at_tempo_ceiling():
    assert cc.effective_cooldown("inner_voice_daemon", 10.0, 2.0) == 20.0


def test_nonexempt_unchanged_at_baseline():
    assert cc.effective_cooldown("inner_voice_daemon", 10.0, 1.0) == 10.0


def test_effective_cooldown_clamps_out_of_band_tempo():
    assert cc.effective_cooldown("inner_voice_daemon", 10.0, 10.0) == 20.0   # klemt til 2.0
    assert cc.effective_cooldown("inner_voice_daemon", 10.0, 0.01) == 5.0    # klemt til 0.5


def test_effective_cooldown_self_safe_on_bad_tempo():
    assert cc.effective_cooldown("inner_voice_daemon", 10.0, "nonsense") == 10.0  # type: ignore[arg-type]
    assert cc.effective_cooldown("inner_voice_daemon", 10.0, None) == 10.0        # type: ignore[arg-type]


# --- tempo_live_enabled + current_tick_tempo: flag-porten ---

def test_flag_default_on(monkeypatch):
    monkeypatch.setattr(cc, "_kv_get", lambda k, default: default)
    assert cc.tempo_live_enabled() is True


def test_flag_off_disables(monkeypatch):
    monkeypatch.setattr(cc, "_kv_get", lambda k, default: False)
    assert cc.tempo_live_enabled() is False


def test_current_tick_tempo_baseline_when_flag_off(monkeypatch):
    monkeypatch.setattr(cc, "tempo_live_enabled", lambda: False)
    monkeypatch.setattr(cc, "sense_tempo", lambda: {"available": True, "tempo": 0.5})
    assert cc.current_tick_tempo() == 1.0


def test_current_tick_tempo_baseline_when_unavailable(monkeypatch):
    monkeypatch.setattr(cc, "tempo_live_enabled", lambda: True)
    monkeypatch.setattr(cc, "sense_tempo", lambda: {"available": False})
    assert cc.current_tick_tempo() == 1.0


def test_current_tick_tempo_reads_sense_when_on(monkeypatch):
    monkeypatch.setattr(cc, "tempo_live_enabled", lambda: True)
    monkeypatch.setattr(cc, "sense_tempo",
                        lambda: {"available": True, "tempo": 0.5, "throttled_by_loop_lag": False})
    assert cc.current_tick_tempo() == 0.5


def test_current_tick_tempo_self_safe_on_broken_sense(monkeypatch):
    monkeypatch.setattr(cc, "tempo_live_enabled", lambda: True)
    def boom():
        raise RuntimeError("sense korrupt")
    monkeypatch.setattr(cc, "sense_tempo", boom)
    assert cc.current_tick_tempo() == 1.0


def test_current_tick_tempo_respects_clamp(monkeypatch):
    monkeypatch.setattr(cc, "tempo_live_enabled", lambda: True)
    monkeypatch.setattr(cc, "sense_tempo", lambda: {"available": True, "tempo": 99.0})
    assert cc.current_tick_tempo() == 2.0


# --- _evaluate_producer: ende-til-ende modulation af cooldown-gaten ---

def _spec(name: str, cooldown: float):
    return ic.ProducerSpec(
        name=name, cooldown_minutes=cooldown, visible_grace_minutes=0,
        run_fn=lambda **_kw: {}, priority=10,
    )


def test_evaluate_default_tempo_is_byte_identical():
    # UDEN tempo-kwarg → gammel adfærd: 6 min inde i 10-min cooldown → cooling_down,
    # og reason-strengen har INTET modulations-suffix.
    now = datetime.now(UTC)
    ic._last_run_at["byteid_test"] = (now - timedelta(minutes=6)).isoformat()
    try:
        status, reason = ic._evaluate_producer(
            _spec("byteid_test", 10.0), now=now, last_visible_at=None, ran_this_tick=set())
        assert status == "cooling_down"
        assert reason == "cooldown:6m<10m"   # ingen "~"-suffix → identisk med i dag
    finally:
        ic._last_run_at.pop("byteid_test", None)


def test_evaluate_nonexempt_faster_at_tempo_floor():
    now = datetime.now(UTC)
    ic._last_run_at["fast_test"] = (now - timedelta(minutes=6)).isoformat()
    try:
        status, _ = ic._evaluate_producer(
            _spec("fast_test", 10.0), now=now, last_visible_at=None,
            ran_this_tick=set(), tempo=0.5)
        assert status == "due"          # effektiv 5 min → 6 ≥ 5 → due (ånder hurtigere)
    finally:
        ic._last_run_at.pop("fast_test", None)


def test_evaluate_exempt_ignores_tempo():
    now = datetime.now(UTC)
    ic._last_run_at["central_membrane_watch"] = (now - timedelta(minutes=6)).isoformat()
    try:
        status, _ = ic._evaluate_producer(
            _spec("central_membrane_watch", 10.0), now=now, last_visible_at=None,
            ran_this_tick=set(), tempo=0.5)
        assert status == "cooling_down"   # muren vogtes på fast kadence
    finally:
        ic._last_run_at.pop("central_membrane_watch", None)


def test_evaluate_nonexempt_slower_at_tempo_ceiling():
    now = datetime.now(UTC)
    ic._last_run_at["slow_test"] = (now - timedelta(minutes=12)).isoformat()
    try:
        status, _ = ic._evaluate_producer(
            _spec("slow_test", 10.0), now=now, last_visible_at=None,
            ran_this_tick=set(), tempo=2.0)
        assert status == "cooling_down"   # effektiv 20 min → 12 < 20 → ånder langsommere
    finally:
        ic._last_run_at.pop("slow_test", None)


# --- §28 burn-watch: gør tempo-drevet omkostning synlig ---

def test_burn_watch_emits_cost_nerve_with_spike_flag(monkeypatch):
    monkeypatch.setattr("core.costing.ledger.today_cost", lambda: 0.25)  # spike (>0.10)
    emitted = {}
    monkeypatch.setattr("core.services.central_private_observe.record_private",
                        lambda c, n, **kw: emitted.update({"c": c, "n": n, **kw}))
    cc._observe_tempo_burn(0.5, consuming=True)
    assert emitted["c"] == "cost" and emitted["n"] == "tempo_burn_watch"
    assert emitted["value"] == 0.25
    assert emitted["meta"]["spiking"] is True and emitted["meta"]["accelerating"] is True


def test_burn_watch_no_spike_under_threshold(monkeypatch):
    monkeypatch.setattr("core.costing.ledger.today_cost", lambda: 0.03)  # baseline
    emitted = {}
    monkeypatch.setattr("core.services.central_private_observe.record_private",
                        lambda c, n, **kw: emitted.update(kw))
    cc._observe_tempo_burn(1.5, consuming=True)  # decelererer → ikke accelerating
    assert emitted["meta"]["spiking"] is False and emitted["meta"]["accelerating"] is False


def test_burn_watch_self_safe_on_broken_ledger(monkeypatch):
    def boom():
        raise RuntimeError("ledger nede")
    monkeypatch.setattr("core.costing.ledger.today_cost", boom)
    cc._observe_tempo_burn(0.5, consuming=True)  # må ikke kaste
