"""Tests for core/services/central_body_mood_feel.py — Spec §8 KROP + STEMNING.

De to selv-spor (krop: proprioception/embodied · stemning: mood/developmental/affective) bundet
TOVEJS: OP (signal_fn → puls + durabelt hold) + NED (describe_body_mood_feel → tale). Hermetisk:
lag-tilstandene monkeypatches; hold-store kører på isolated_runtime's in-memory KV.
"""
from __future__ import annotations

import pytest

from core.services import central_body_mood_feel as bm


@pytest.fixture(autouse=True)
def _reset(isolated_runtime):
    # ryd holdt-store mellem tests (durabel KV lever i lag-kontraktens _HELD_KEY)
    from core.services import central_layer_contract as lc
    lc._kv_set(lc._HELD_KEY, {})
    yield


# ── OP KROP: signal_fn læser lagets nuværende aflæsning + holder den durabelt ──
def test_proprioception_signal_reads_and_holds(monkeypatch, isolated_runtime):
    monkeypatch.setattr("core.services.proprioception_metrics.recent_snapshots",
                        lambda limit=1: [{"cpu_pct": 12.0, "rss_mb": 340.0, "self_latency_ms": 3.0}])
    sig = bm._proprioception_signal()
    assert sig is not None and sig["value"] == 12.0 and sig["meta"]["feel"] == "rolig"
    held = bm.get_proprioception_reading()
    assert held["feel"] == "rolig" and held["rss_mb"] == 340.0


def test_proprioception_signal_strained_label(monkeypatch, isolated_runtime):
    monkeypatch.setattr("core.services.proprioception_metrics.recent_snapshots",
                        lambda limit=1: [{"cpu_pct": 88.0, "rss_mb": 900.0, "self_latency_ms": 20.0}])
    sig = bm._proprioception_signal()
    assert sig["meta"]["feel"] == "spændt"
    assert bm.get_proprioception_reading()["feel"] == "spændt"


def test_proprioception_signal_none_without_snapshot(monkeypatch, isolated_runtime):
    monkeypatch.setattr("core.services.proprioception_metrics.recent_snapshots", lambda limit=1: [])
    assert bm._proprioception_signal() is None
    assert bm.get_proprioception_reading() == {}


def test_embodied_signal_reads_and_holds(monkeypatch, isolated_runtime):
    monkeypatch.setattr("core.services.embodied_state.build_embodied_state_surface",
                        lambda: {"state": "strained", "primary_state": "strained",
                                 "strain_level": "high"})
    sig = bm._embodied_signal()
    assert sig is not None and sig["value"] == 2.0 and sig["meta"]["state"] == "strained"
    held = bm.get_embodied_reading()
    assert held["state"] == "strained" and held["strain_level"] == "high"


def test_embodied_signal_none_when_unknown(monkeypatch, isolated_runtime):
    monkeypatch.setattr("core.services.embodied_state.build_embodied_state_surface",
                        lambda: {"state": "unknown"})
    assert bm._embodied_signal() is None


# ── OP STEMNING ──
def test_mood_signal_reads_and_holds(monkeypatch, isolated_runtime):
    monkeypatch.setattr("core.services.mood_oscillator.get_current_mood", lambda: "content")
    monkeypatch.setattr("core.services.mood_oscillator.get_mood_intensity", lambda: 0.55)
    monkeypatch.setattr("core.services.mood_oscillator.get_mood_description", lambda: "Tilfreds")
    sig = bm._mood_signal()
    assert sig is not None and sig["value"] == 0.55 and sig["meta"]["mood"] == "content"
    held = bm.get_mood_reading()
    assert held["mood"] == "content" and held["description"] == "Tilfreds"


def test_developmental_signal_reads_and_holds(monkeypatch, isolated_runtime):
    monkeypatch.setattr("core.services.developmental_valence.get_developmental_state",
                        lambda: {"trajectory": "blooming", "vector": 0.42})
    sig = bm._developmental_signal()
    assert sig is not None and sig["value"] == 0.42 and sig["meta"]["trajectory"] == "blooming"
    assert bm.get_developmental_reading()["trajectory"] == "blooming"


def test_developmental_signal_none_when_vector_missing(monkeypatch, isolated_runtime):
    monkeypatch.setattr("core.services.developmental_valence.get_developmental_state",
                        lambda: {"trajectory": "forming", "vector": None})
    assert bm._developmental_signal() is None
    assert bm.get_developmental_reading() == {}


def test_affective_signal_reads_and_holds(monkeypatch, isolated_runtime):
    monkeypatch.setattr("core.services.affective_meta_state.build_affective_meta_state_surface",
                        lambda: {"state": "reflective", "bearing": "inward"})
    sig = bm._affective_signal()
    assert sig is not None and sig["value"] == 1.0 and sig["meta"]["state"] == "reflective"
    assert bm.get_affective_reading()["bearing"] == "inward"


# ── NED: describe_body_mood_feel taler kun meningsfulde aflæsninger ──
def test_describe_speaks_body_and_mood_when_meaningful(isolated_runtime):
    bm._hold_reading(bm._PROPRIOCEPTION, {"feel": "rolig"})
    bm._hold_reading(bm._EMBODIED, {"state": "strained"})
    bm._hold_reading(bm._MOOD, {"description": "Tilfreds"})
    bm._hold_reading(bm._DEVELOPMENTAL, {"trajectory": "blooming"})
    bm._hold_reading(bm._AFFECTIVE, {"state": "reflective"})
    parts = bm.describe_body_mood_feel()
    assert any("proprioceptivt mærker jeg mig rolig" in p for p in parts)
    assert any("min krop føles spændt" in p for p in parts)
    assert any("stemningen er tilfreds" in p for p in parts)
    assert any("udviklings-kompas peger mod blomstring" in p for p in parts)
    assert any("affektivt er jeg reflekterende" in p for p in parts)


def test_describe_body_order_is_body_then_mood(isolated_runtime):
    bm._hold_reading(bm._PROPRIOCEPTION, {"feel": "rolig"})
    bm._hold_reading(bm._MOOD, {"description": "Neutral"})
    parts = bm.describe_body_mood_feel()
    assert parts[0].startswith("proprioceptivt") and parts[1].startswith("stemningen")


def test_describe_embodied_steady_stays_silent(isolated_runtime):
    # steady er hvile-værdien → tales IKKE (nøgtern, ikke støjende)
    bm._hold_reading(bm._EMBODIED, {"state": "steady"})
    assert bm.describe_body_mood_feel() == []


def test_describe_developmental_steady_stays_silent(isolated_runtime):
    bm._hold_reading(bm._DEVELOPMENTAL, {"trajectory": "steady"})
    assert bm.describe_body_mood_feel() == []


def test_describe_affective_settled_stays_silent(isolated_runtime):
    bm._hold_reading(bm._AFFECTIVE, {"state": "settled"})
    assert bm.describe_body_mood_feel() == []


def test_describe_wilting_compass(isolated_runtime):
    bm._hold_reading(bm._DEVELOPMENTAL, {"trajectory": "steady-dim"})
    parts = bm.describe_body_mood_feel()
    assert parts == ["mit udviklings-kompas peger mod visnen"]


def test_describe_empty_when_nothing_held(isolated_runtime):
    assert bm.describe_body_mood_feel() == []


def test_describe_guarded_on_partial(isolated_runtime):
    # kun stemning holdt → kun stemning tales (guarded pr. lag)
    bm._hold_reading(bm._MOOD, {"description": "Melankolsk"})
    parts = bm.describe_body_mood_feel()
    assert parts == ["stemningen er melankolsk"]


# ── self-safe: lag-fejl → intet pulses, describe kaster aldrig ──
def test_signals_self_safe_on_layer_error(monkeypatch, isolated_runtime):
    monkeypatch.setattr("core.services.proprioception_metrics.recent_snapshots",
                        lambda limit=1: (_ for _ in ()).throw(RuntimeError("x")))
    monkeypatch.setattr("core.services.embodied_state.build_embodied_state_surface",
                        lambda: (_ for _ in ()).throw(RuntimeError("x")))
    monkeypatch.setattr("core.services.mood_oscillator.get_current_mood",
                        lambda: (_ for _ in ()).throw(RuntimeError("x")))
    assert bm._proprioception_signal() is None
    assert bm._embodied_signal() is None
    assert bm._mood_signal() is None


def test_describe_self_safe_on_corrupt_hold(monkeypatch, isolated_runtime):
    monkeypatch.setattr(bm, "get_mood_reading",
                        lambda: (_ for _ in ()).throw(RuntimeError("x")))
    # ét lags fejl må ikke sprede sig — describe returnerer stadig en liste
    assert isinstance(bm.describe_body_mood_feel(), list)


# ── OP-registrering: fem lag registreres på cadence-motoren, egress PRIVATE, cluster cognition ──
def test_register_wires_five_layers(monkeypatch, isolated_runtime):
    from core.services import central_layer_contract as lc
    specs = []
    import core.services.internal_cadence as ic
    monkeypatch.setattr(ic, "register_producer", lambda spec: specs.append(spec))
    lc._CONTRACTS.clear()
    bm.register_body_mood_feel_layers()
    names = {s.name for s in specs}
    assert names == {bm._PROPRIOCEPTION, bm._EMBODIED, bm._MOOD,
                     bm._DEVELOPMENTAL, bm._AFFECTIVE}
    for name in names:
        assert lc._CONTRACTS[name].egress is lc.Egress.PRIVATE
        assert lc._CONTRACTS[name].cluster == "cognition"


def test_run_contract_tick_pulses_private(monkeypatch, isolated_runtime):
    # OP end-to-end: lag-kontraktens tick kalder signal_fn → record_private (egress-frit), aldrig bussen
    from core.services import central_layer_contract as lc
    monkeypatch.setattr("core.services.mood_oscillator.get_current_mood", lambda: "euphoric")
    monkeypatch.setattr("core.services.mood_oscillator.get_mood_intensity", lambda: 0.7)
    monkeypatch.setattr("core.services.mood_oscillator.get_mood_description", lambda: "Meget Euforisk")
    published = []
    import core.eventbus.bus as bus_mod
    monkeypatch.setattr(bus_mod.event_bus, "publish", lambda *a, **k: published.append((a, k)))
    recorded = []
    monkeypatch.setattr("core.services.central_private_observe.record_private",
                        lambda *a, **k: recorded.append((a, k)))
    c = lc.LayerContract(name=bm._MOOD, cluster="cognition", nerve="mood",
                         signal_fn=bm._mood_signal, egress=lc.Egress.PRIVATE)
    r = lc._run_contract_tick(c)
    assert r["observed"] is True
    assert recorded and not published            # egress-frit
    assert bm.get_mood_reading()["mood"] == "euphoric"   # durabelt hold sat via side-effekt


def test_build_surface_shows_both_tracks(isolated_runtime):
    bm._hold_reading(bm._EMBODIED, {"state": "loaded"})
    bm._hold_reading(bm._MOOD, {"description": "Neutral"})
    surface = bm.build_body_mood_feel_surface()
    assert surface["active"] is True
    assert surface["body"]["embodied"]["state"] == "loaded"
    assert surface["mood"]["oscillator"]["description"] == "Neutral"
    assert any("belastet" in p for p in surface["spoken"])
