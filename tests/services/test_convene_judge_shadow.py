"""C5 — event-trigger SHADOW-meter tests (observe-only, ZERO behaviour change).

The shadow tick wires the pure NON-LLM signal-delta trigger onto the heartbeat
in SHADOW: it gathers the live signals, asks `signal_delta_trigger.evaluate`
what it WOULD dispatch, consults the dispatch guards, and records telemetry to
`central_timeseries` — but it must NEVER fire an LLM and NEVER convene a council.

These tests prove:
  * a decision → telemetry with would_dispatch=True + crossed populated,
    and ZERO LLM / ZERO council calls;
  * a flat (None) evaluate → telemetry with would_dispatch=False, again zero;
  * a signal-source error → safe skip (records nothing), never raises.
"""
from __future__ import annotations

import pytest


@pytest.fixture()
def captured(monkeypatch):
    """Capture central_timeseries.record calls + install LLM/council tripwires."""
    from core.services import central_timeseries as ts

    records: list[dict] = []

    def _rec(cluster, nerve, value=None, *, meta=None):
        records.append({"cluster": cluster, "nerve": nerve, "value": value, "meta": dict(meta or {})})

    monkeypatch.setattr(ts, "record", _rec)

    calls = {"llm": 0, "council": 0}

    # Tripwires on the real LLM + council seams the daemon would use. The shadow
    # module must NEVER reach these.
    import core.services.autonomous_council_daemon as acd

    def _boom_council(*a, **k):
        calls["council"] += 1
        raise AssertionError("council convened in shadow mode")

    def _boom_llm(*a, **k):
        calls["llm"] += 1
        raise AssertionError("LLM fired in shadow mode")

    monkeypatch.setattr(acd, "_run_autonomous_council", _boom_council, raising=False)
    monkeypatch.setattr(acd, "_call_llm", _boom_llm, raising=False)

    return {"records": records, "calls": calls}


@pytest.fixture()
def shadow_mode(monkeypatch):
    import core.services.central_convene_judge as cj

    monkeypatch.setattr(cj, "current_mode", lambda: "shadow")
    return cj


def _load():
    import importlib

    return importlib.import_module("core.services.event_trigger_shadow")


def test_decision_records_would_dispatch_true_no_llm_no_council(monkeypatch, captured, shadow_mode):
    mod = _load()
    import core.services.signal_delta_trigger as sdt

    monkeypatch.setattr(
        sdt, "evaluate",
        lambda signals: {
            "crossed": ["autonomy_pressure", "open_loop"],
            "movements": {"autonomy_pressure": 0.4, "open_loop": 0.33},
            "reason": "signal-delta dispatch: autonomy_pressure Δ+0.400",
        },
    )
    # Guards are read-only here; keep them cheap + deterministic.
    import core.services.dispatch_guards as dg
    import core.services.autonomous_lease as al

    monkeypatch.setattr(dg, "budget_allows", lambda *a, **k: True)
    monkeypatch.setattr(dg, "is_tripped", lambda *a, **k: False)
    monkeypatch.setattr(al, "visible_active", lambda *a, **k: False)

    out = mod.tick_event_trigger_shadow(signals={"autonomy_pressure": 0.7, "open_loop": 0.6})

    assert out["recorded"] is True
    assert out["would_dispatch"] is True
    assert captured["calls"]["llm"] == 0
    assert captured["calls"]["council"] == 0

    assert len(captured["records"]) == 1
    rec = captured["records"][0]
    assert rec["cluster"] == "agents"
    assert rec["nerve"] == "event_trigger"
    meta = rec["meta"]
    assert meta["mode"] == "shadow"
    assert meta["would_dispatch"] is True
    assert meta["crossed"] == ["autonomy_pressure", "open_loop"]
    assert meta["budget_ok"] is True
    assert meta["visible_active"] is False
    assert meta["breaker_tripped"] is False
    # value = max abs movement
    assert rec["value"] == pytest.approx(0.4)


def test_flat_records_would_dispatch_false_no_llm_no_council(monkeypatch, captured, shadow_mode):
    mod = _load()
    import core.services.signal_delta_trigger as sdt
    import core.services.dispatch_guards as dg
    import core.services.autonomous_lease as al

    monkeypatch.setattr(sdt, "evaluate", lambda signals: None)
    monkeypatch.setattr(dg, "budget_allows", lambda *a, **k: True)
    monkeypatch.setattr(dg, "is_tripped", lambda *a, **k: False)
    monkeypatch.setattr(al, "visible_active", lambda *a, **k: False)

    out = mod.tick_event_trigger_shadow(signals={"autonomy_pressure": 0.1})

    assert out["recorded"] is True
    assert out["would_dispatch"] is False
    assert captured["calls"]["llm"] == 0
    assert captured["calls"]["council"] == 0

    assert len(captured["records"]) == 1
    meta = captured["records"][0]["meta"]
    assert meta["would_dispatch"] is False
    assert meta["crossed"] == []
    assert captured["records"][0]["value"] == pytest.approx(0.0)


def test_signal_source_error_is_safe_skip(monkeypatch, captured, shadow_mode):
    mod = _load()

    # Force the signal-source read to blow up; the tick must NOT record + NOT raise.
    def _boom():
        raise RuntimeError("surface read failed")

    monkeypatch.setattr(mod, "_gather_signals", _boom)

    out = mod.tick_event_trigger_shadow(signals=None)  # None → read the surfaces

    assert out["recorded"] is False
    assert out.get("skipped") == "signal_source_error"
    assert captured["records"] == []
    assert captured["calls"]["llm"] == 0
    assert captured["calls"]["council"] == 0
