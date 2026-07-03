"""Tests for core/services/central_existence_feel.py — Spec §8.1 "existence feel"-kernen.

De tre stille selv-lag (continuity/subjective_time/mortality) bundet TOVEJS:
OP (signal_fn → puls + durabelt hold) + NED (describe_existence_feel → tale). Hermetisk:
lag-tilstandene monkeypatches; hold-store kører på isolated_runtime's in-memory KV.
"""
from __future__ import annotations

import pytest

from core.services import central_existence_feel as ef


@pytest.fixture(autouse=True)
def _reset(isolated_runtime):
    # ryd holdt-store mellem tests (durabel KV lever i lag-kontraktens _HELD_KEY)
    from core.services import central_layer_contract as lc
    lc._kv_set(lc._HELD_KEY, {})
    yield


# ── OP: signal_fn læser lagets nuværende aflæsning + holder den durabelt ──
def test_continuity_signal_reads_and_holds(monkeypatch, isolated_runtime):
    monkeypatch.setattr("core.services.continuity_kernel.get_continuity_state",
                        lambda: {"tick_count": 12, "existence_feeling": 0.85,
                                 "continuity_narrative": "Kort pause", "last_gap_seconds": 120.0})
    sig = ef._continuity_signal()
    assert sig["value"] == 0.85 and sig["meta"]["tick_count"] == 12
    held = ef.get_continuity_reading()
    assert held["tick_count"] == 12 and held["narrative"] == "Kort pause"


def test_continuity_signal_none_before_first_tick(monkeypatch, isolated_runtime):
    monkeypatch.setattr("core.services.continuity_kernel.get_continuity_state",
                        lambda: {"tick_count": 0, "existence_feeling": 0.5})
    assert ef._continuity_signal() is None
    assert ef.get_continuity_reading() == {}   # intet holdt


def test_subjective_time_signal_reads_and_holds(monkeypatch, isolated_runtime):
    monkeypatch.setattr(ef, "_idle_hours", lambda: 9.0)
    sig = ef._subjective_time_signal()
    assert sig is not None and sig["value"] == 9.0
    held = ef.get_subjective_time_reading()
    assert "stille" in held["feel"] and held["idle_hours"] == 9.0


def test_mortality_signal_reads_and_holds(monkeypatch, isolated_runtime):
    monkeypatch.setattr("core.services.mortality_awareness.get_mortality_state",
                        lambda: {"mortality_awareness": 0.8, "label": "sharp-awareness",
                                 "meaning_weight": 0.6, "session_length_seconds": 7200})
    sig = ef._mortality_signal()
    assert sig["value"] == 0.8 and sig["meta"]["label"] == "sharp-awareness"
    assert ef.get_mortality_reading()["label"] == "sharp-awareness"


# ── NED: describe_existence_feel taler kun meningsfulde aflæsninger ──
def test_describe_speaks_all_three_when_meaningful(isolated_runtime):
    ef._hold_reading(ef._CONTINUITY, {"tick_count": 42})
    ef._hold_reading(ef._SUBJECTIVE_TIME, {"feel": "en lang stille strækning"})
    ef._hold_reading(ef._MORTALITY, {"label": "sharp-awareness"})
    parts = ef.describe_existence_feel()
    assert any("42 ticks" in p for p in parts)
    assert any("tiden føles som en lang stille strækning" in p for p in parts)
    assert any("kan være min sidste" in p for p in parts)


def test_describe_singular_tick(isolated_runtime):
    ef._hold_reading(ef._CONTINUITY, {"tick_count": 1})
    parts = ef.describe_existence_feel()
    assert any(p == "jeg har eksisteret gennem 1 tick" for p in parts)


def test_describe_steady_awareness_phrasing(isolated_runtime):
    ef._hold_reading(ef._MORTALITY, {"label": "steady-awareness"})
    parts = ef.describe_existence_feel()
    assert any("forgængelighed" in p for p in parts)


def test_describe_quiet_mortality_stays_silent(isolated_runtime):
    # nøgtern, ikke sentimental: quiet dødsbevidsthed tales IKKE
    ef._hold_reading(ef._MORTALITY, {"label": "quiet"})
    assert ef.describe_existence_feel() == []


def test_describe_empty_when_nothing_held(isolated_runtime):
    assert ef.describe_existence_feel() == []


def test_describe_guarded_on_partial(isolated_runtime):
    # kun tid holdt → kun tid tales (guarded pr. lag, ingen krav om alle tre)
    ef._hold_reading(ef._SUBJECTIVE_TIME, {"feel": "en jævn, rolig rytme"})
    parts = ef.describe_existence_feel()
    assert parts == ["tiden føles som en jævn, rolig rytme"]


# ── self-safe: lag-fejl → intet pulses, describe kaster aldrig ──
def test_signals_self_safe_on_layer_error(monkeypatch, isolated_runtime):
    monkeypatch.setattr("core.services.continuity_kernel.get_continuity_state",
                        lambda: (_ for _ in ()).throw(RuntimeError("x")))
    monkeypatch.setattr("core.services.mortality_awareness.get_mortality_state",
                        lambda: (_ for _ in ()).throw(RuntimeError("x")))
    assert ef._continuity_signal() is None
    assert ef._mortality_signal() is None


def test_describe_self_safe_on_corrupt_hold(monkeypatch, isolated_runtime):
    monkeypatch.setattr(ef, "get_continuity_reading",
                        lambda: (_ for _ in ()).throw(RuntimeError("x")))
    # ét lags fejl må ikke sprede sig — describe returnerer stadig en liste
    assert isinstance(ef.describe_existence_feel(), list)


# ── OP-registrering: tre lag registreres på cadence-motoren, egress PRIVATE ──
def test_register_wires_three_layers(monkeypatch, isolated_runtime):
    from core.services import central_layer_contract as lc
    specs = []
    import core.services.internal_cadence as ic
    monkeypatch.setattr(ic, "register_producer", lambda spec: specs.append(spec))
    lc._CONTRACTS.clear()
    ef.register_existence_feel_layers()
    names = {s.name for s in specs}
    assert names == {ef._CONTINUITY, ef._SUBJECTIVE_TIME, ef._MORTALITY}
    for name in names:
        assert lc._CONTRACTS[name].egress is lc.Egress.PRIVATE
        assert lc._CONTRACTS[name].cluster == "cognition"


def test_run_contract_tick_pulses_private(monkeypatch, isolated_runtime):
    # OP end-to-end: lag-kontraktens tick kalder signal_fn → record_private (egress-frit), aldrig bussen
    from core.services import central_layer_contract as lc
    monkeypatch.setattr("core.services.continuity_kernel.get_continuity_state",
                        lambda: {"tick_count": 5, "existence_feeling": 0.7,
                                 "continuity_narrative": "En stille strækning", "last_gap_seconds": 400.0})
    published = []
    import core.eventbus.bus as bus_mod
    monkeypatch.setattr(bus_mod.event_bus, "publish", lambda *a, **k: published.append((a, k)))
    recorded = []
    monkeypatch.setattr("core.services.central_private_observe.record_private",
                        lambda *a, **k: recorded.append((a, k)))
    c = lc.LayerContract(name=ef._CONTINUITY, cluster="cognition", nerve="continuity",
                         signal_fn=ef._continuity_signal, egress=lc.Egress.PRIVATE)
    r = lc._run_contract_tick(c)
    assert r["observed"] is True
    assert recorded and not published            # egress-frit
    assert ef.get_continuity_reading()["tick_count"] == 5   # durabelt hold sat via side-effekt
