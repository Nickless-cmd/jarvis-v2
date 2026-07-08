"""Tests for core/services/central_layer_contract.py — den generelle tovejs lag-kontrakt (§11 #6).

Beviser at kontrakten fanger de 3 arketype-former uden tab: kun-OP (world_model), OP+NED
(central_self_state), OP+BESTEM+NED (inner_salience). Hermetisk — kv i hukommelsen, sink fanget.
"""
from __future__ import annotations

import pytest

from core.services import central_layer_contract as lc
from core.services.central_layer_contract import LayerContract, Egress, DecideMode


@pytest.fixture(autouse=True)
def _mem(monkeypatch):
    store: dict[str, object] = {}
    monkeypatch.setattr(lc, "_kv_get", lambda k, d: store.get(k, d))
    monkeypatch.setattr(lc, "_kv_set", lambda k, v: store.__setitem__(k, v))
    sinks: list[dict] = []
    monkeypatch.setattr(lc, "_sink", lambda c, value, meta, reason="":
                        sinks.append({"nerve": getattr(c, "nerve", None), "value": value,
                                      "meta": meta, "reason": reason}))
    lc._CONTRACTS.clear()
    yield {"store": store, "sinks": sinks}
    lc._CONTRACTS.clear()


def test_register_layer_registers_producer(monkeypatch):
    specs = []
    import core.services.internal_cadence as ic
    monkeypatch.setattr(ic, "register_producer", lambda spec: specs.append(spec))
    lc.register_layer(LayerContract(name="l1", cluster="cognition", nerve="n1",
                                    signal_fn=lambda: {"value": 1.0}))
    assert specs and specs[0].name == "l1"
    assert "l1" in lc._CONTRACTS


def test_archetype_A_op_only(_mem):
    # world_model-form: kun signal_fn → ét sink-kald med value+meta, intet consume.
    c = LayerContract(name="wm", cluster="cognition", nerve="world_model",
                      signal_fn=lambda: {"value": 0.72, "meta": {"resolved": 11}})
    r = lc._run_contract_tick(c)
    assert r["observed"] is True
    assert _mem["sinks"] == [{"nerve": "world_model", "value": 0.72, "meta": {"resolved": 11}, "reason": ""}]


def test_archetype_B_op_plus_ned(_mem):
    # self_state-form: signal_fn + consume_fn → OP-sink + consume-trace.
    c = LayerContract(name="ss", cluster="cognition", nerve="self_state",
                      signal_fn=lambda: {"value": 0.5, "meta": {"tone": "let"}},
                      consume_fn=lambda: "Jeg er her.")
    lc._run_contract_tick(c)
    reasons = [s["reason"] for s in _mem["sinks"]]
    assert "" in reasons and "consume" in reasons  # både OP og NED-trace


def test_archetype_C_decide_off_shadow_on(_mem):
    # inner_salience-form: BESTEM-gate. Registrér for TTL, brug note_held/get_held/decide.
    lc._CONTRACTS["isal"] = LayerContract(name="isal", cluster="cognition", nerve="inner_salience",
                                          signal_fn=lambda: {"value": 1.0})
    lc.note_held("isal", "voice", key="let|midt|ro", value="En rolig linje.")

    _mem["store"]["layer_mode:isal"] = "off"
    assert lc.decide("isal", key="let|midt|ro", held_key="voice")["reuse"] is False

    _mem["store"]["layer_mode:isal"] = "shadow"
    d = lc.decide("isal", key="let|midt|ro", held_key="voice")
    assert d["reuse"] is False and d["would_reuse"] is True   # måler, ændrer ikke

    _mem["store"]["layer_mode:isal"] = "on"
    d = lc.decide("isal", key="let|midt|ro", held_key="voice")
    assert d["reuse"] is True and d["held"] == "En rolig linje."   # NED-genbrug


def test_decide_reenriches_when_moved(_mem):
    lc._CONTRACTS["isal"] = LayerContract(name="isal", cluster="cognition", nerve="inner_salience",
                                          signal_fn=lambda: {"value": 1.0})
    lc.note_held("isal", "voice", key="let|midt|ro", value="En rolig linje.")
    _mem["store"]["layer_mode:isal"] = "on"
    assert lc.decide("isal", key="tung|hvile|pres", held_key="voice")["reuse"] is False


def test_get_held_roundtrip(_mem):
    lc.note_held("x", "default", key="k", value="v")
    assert lc.get_held("x") == "v"
    assert lc.get_held("mangler") is None


def test_self_safe_signal_raises(_mem):
    c = LayerContract(name="boom", cluster="cognition", nerve="b",
                      signal_fn=lambda: (_ for _ in ()).throw(RuntimeError("x")))
    r = lc._run_contract_tick(c)   # må ikke kaste
    assert r["observed"] is False


import time as _time_hg
from core.services import central_layer_contract as _clc_hg


def test_get_held_age_recent(monkeypatch):
    monkeypatch.setattr(_clc_hg, "_held_get", lambda n, k: {"value": "x", "ts": _time_hg.time()})
    age = _clc_hg.get_held_age("foo")
    assert age is not None and age < 5


def test_get_held_age_absent(monkeypatch):
    monkeypatch.setattr(_clc_hg, "_held_get", lambda n, k: {})
    assert _clc_hg.get_held_age("foo") is None


def test_get_held_age_old(monkeypatch):
    monkeypatch.setattr(_clc_hg, "_held_get", lambda n, k: {"value": "x", "ts": _time_hg.time() - 4000})
    age = _clc_hg.get_held_age("foo")
    assert age is not None and age > 3000
