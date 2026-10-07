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

    # Snublesnor paa den eneste raads-indgang der findes.
    #
    # Den laa foer paa `autonomous_council_daemon._run_autonomous_council` og
    # `._call_llm`. Begge er vaek 7/10-2026, og `raising=False` betoed at
    # fixturet ville vaere blevet GROENT uden at maale noget den dag modulet
    # forsvandt — havde importen ikke selv braekket. Snoren er derfor flyttet
    # til `agent_runtime_council.run_council_round`, som stadig er den vej et
    # raad samles ad. `raising=False` er med vilje droppet: forsvinder ogsaa den
    # funktion, skal denne test braekke og ikke tie.
    import core.services.agent_runtime_council as arc

    def _boom_council(*a, **k):
        calls["council"] += 1
        raise AssertionError("council convened in shadow mode")

    monkeypatch.setattr(arc, "run_council_round", _boom_council)

    return {"records": records, "calls": calls}


def test_shadow_modulet_naevner_INGEN_llm_eller_raads_sti():
    """Modulets egen paastand: «importerer overhovedet ikke nogen LLM- eller
    council-sti». En snublesnor fanger kun den gren der koeres; kilde-vagten
    her gaelder hele modulet.

    Vagten laeser AST'ens import-knuder, ikke tekst: en kommentar eller en
    docstring der FORKLARER hvorfor vejen er vaek, maa ikke faelde den.
    """
    import ast
    import inspect

    from core.services import event_trigger_shadow as mod

    traed = ast.parse(inspect.getsource(mod))
    moduler: list[str] = []
    for knude in ast.walk(traed):
        if isinstance(knude, ast.Import):
            moduler += [a.name for a in knude.names]
        elif isinstance(knude, ast.ImportFrom):
            moduler.append(knude.module or "")

    forbudt = ("council", "agent_runtime", "llm", "provider")
    fundet = [m for m in moduler if any(ord in m.lower() for ord in forbudt)
              # grund-dommeren er en REN beregning og er modulets styreflag
              and not m.startswith("core.services.central_convene_judge")]
    assert fundet == [], (
        "event_trigger_shadow importerer %s — modulet er observerende og maa "
        "aldrig kunne naa en LLM eller et raad" % ", ".join(fundet)
    )


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
