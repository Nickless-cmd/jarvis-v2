"""B3: central_agents_surface — /central/agents + /central/council surfaces.

Gør de nye agent-/council-observabilitets-data synlige (owner-only). Læser
costs-aggregat (lane in agent/council) + agents-cluster-signal (trace: status/nerve).
Selv-sikker: en DB/read-fejl må aldrig vælte surfacen.
"""
from __future__ import annotations

import core.services.central_agents_surface as cas
from core.costing.ledger import record_cost
from core.services import agents as agents_mod
from core.services import central_trace


def _clear_trace():
    # Trace-sinken er proces-global (ikke isoleret af isolated_runtime) → ryd for
    # deterministiske status-tællinger.
    central_trace.sink()._buf.clear()


def test_build_agents_surface(isolated_runtime):
    _clear_trace()
    # Agent-forbrug (costs, lane=agent) — et par kald.
    for _ in range(3):
        record_cost(lane="agent", provider="groq", model="x",
                    input_tokens=100, output_tokens=50, cost_usd=0.01)
    # + én council-lane række (skal også tælles i aggregatet).
    record_cost(lane="council", provider="groq", model="x",
                input_tokens=40, output_tokens=20, cost_usd=0.005)
    # Agent-udfald (trace).
    agents_mod.note_agent_result("a1", "completed", tokens_in=100, tokens_out=50,
                                 cost_usd=0.01, role="researcher")
    agents_mod.note_agent_result("a2", "failed", tokens_in=10, tokens_out=0,
                                 role="critic")
    agents_mod.note_agent_blocked("a3", reason="needs context", role="worker")

    s = cas.build_agents_surface(window="today")
    assert isinstance(s, dict)

    # Token+cost-aggregat (today) for lane in (agent, council).
    today = s["windows"]["today"]
    assert today["calls"] == 4                     # 3 agent + 1 council
    assert today["input_tokens"] == 3 * 100 + 40
    assert today["output_tokens"] == 3 * 50 + 20
    assert today["cost_usd"] > 0
    assert "7d" in s["windows"]

    # Dispatches + per-status.
    disp = s["dispatches"]
    assert disp["total"] == 3
    assert disp["by_status"]["completed"] == 1
    assert disp["by_status"]["failed"] == 1
    assert disp["by_status"]["blocked"] == 1

    # Recent results til stede.
    assert isinstance(s["recent"], list) and len(s["recent"]) >= 3


def test_build_council_surface(isolated_runtime):
    _clear_trace()
    # Tom → zeros, ingen crash.
    empty = cas.build_council_surface(window="today")
    assert isinstance(empty, dict)
    assert empty["convocations"] == 0
    assert empty["deadlocks"] == 0
    assert empty["roles"] == {}
    assert empty["split"] == {"event": 0, "ondemand": 0}

    # Med council-data.
    agents_mod.note_council("skal-vi-deploye", rounds=2, deadlocked=True,
                            recruited="witness")
    agents_mod.note_council("kode-review", rounds=1, escalated=True)

    s = cas.build_council_surface(window="today")
    assert s["convocations"] == 2
    assert s["deadlocks"] == 1
    assert s["escalations"] == 1
    assert s["roles"].get("witness") == 1


def test_surface_self_safe(isolated_runtime, monkeypatch):
    # DB/read-fejl inde i surfacen → valid dict, aldrig raise.
    def boom(*a, **k):
        raise RuntimeError("db offline")

    monkeypatch.setattr(cas, "connect", boom)
    a = cas.build_agents_surface(window="today")
    assert isinstance(a, dict) and "windows" in a
    c = cas.build_council_surface(window="today")
    assert isinstance(c, dict) and "convocations" in c
