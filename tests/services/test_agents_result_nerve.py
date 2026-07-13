"""B1 + B2: agent_result-nerve + envelope-timeserier + typet agent_blocked.

Verificerer at ``agents.note_agent_result`` emitter ét observe (cluster=agents,
nerve=agent_result) med status + envelope-felter, OG registrerer to tidsserier
(agent_duration_ms + agent_tokens). Og at ``agents.note_agent_blocked`` er en
TYPET ikke-fejl (distinkt nerve/kind, router ALDRIG gennem note_agent_error →
ellers ville den falsk inflatere fejl-raten Centralens drift-detektion vogter).

Patch-punkter: ``central`` resolves i agents._observe via
``core.services.central_core.central``; tidsserien via
``core.services.central_timeseries.record``.
"""

import core.services.agents as agents
import core.services.central_core as central_core
import core.services.central_timeseries as cts


def test_note_agent_result_observes_and_records_two_series(monkeypatch):
    observed: list[dict] = []
    records: list[tuple] = []

    class _FakeCentral:
        def observe(self, event):
            observed.append(event)

    monkeypatch.setattr(central_core, "central", lambda: _FakeCentral())
    monkeypatch.setattr(
        cts, "record",
        lambda cluster, nerve, value=None, *, meta=None: records.append(
            (cluster, nerve, value, meta)
        ),
    )

    agents.note_agent_result(
        agent_id="a1", status="completed",
        tokens_in=100, tokens_out=50, cost_usd=0.0,
        duration_ms=1200, tool_calls=2, role="researcher",
    )

    # 1) observe: agents-cluster, agent_result-nerve, status + envelope-felter
    assert len(observed) == 1
    ev = observed[0]
    assert ev["cluster"] == "agents"
    assert ev["nerve"] == "agent_result"
    assert ev["agent_id"] == "a1"
    assert ev["status"] == "completed"
    assert ev["role"] == "researcher"
    assert ev["tokens_in"] == 100
    assert ev["tokens_out"] == 50
    assert ev["cost_usd"] == 0.0
    assert ev["duration_ms"] == 1200
    assert ev["tool_calls"] == 2

    # 2) to tidsserier: agent_duration_ms=1200 + agent_tokens=150 (in+out)
    series = {(c, n): (v, meta) for (c, n, v, meta) in records}
    assert ("agents", "agent_duration_ms") in series
    assert ("agents", "agent_tokens") in series
    dur_v, _dur_meta = series[("agents", "agent_duration_ms")]
    tok_v, tok_meta = series[("agents", "agent_tokens")]
    assert dur_v == 1200
    assert tok_v == 150
    assert tok_meta.get("cost_usd") == 0.0
    assert tok_meta.get("status") == "completed"


def test_note_agent_result_self_safe(monkeypatch):
    def _boom():
        raise RuntimeError("nope")

    monkeypatch.setattr(central_core, "central", _boom)
    # Må ALDRIG kaste ind i dispatch-stien.
    agents.note_agent_result(agent_id="a1", status="completed")


def test_note_agent_blocked_typed_non_error(monkeypatch):
    observed: list[dict] = []

    class _FakeCentral:
        def observe(self, event):
            observed.append(event)

    monkeypatch.setattr(central_core, "central", lambda: _FakeCentral())

    # note_agent_error må ALDRIG kaldes af blocked-stien (ellers falsk fejl-rate).
    calls = {"error": 0}
    monkeypatch.setattr(
        agents, "note_agent_error",
        lambda *a, **k: calls.__setitem__("error", calls["error"] + 1),
    )

    agents.note_agent_blocked(
        agent_id="a1", status="blocked",
        reason="mangler container-adgang", role="repro",
    )

    assert calls["error"] == 0
    assert len(observed) == 1
    ev = observed[0]
    assert ev["cluster"] == "agents"
    assert ev["nerve"] == "agent_blocked"
    assert ev["kind"] == "blocked"
    assert ev["agent_id"] == "a1"
    assert ev["status"] == "blocked"
    assert ev["role"] == "repro"
    assert ev["reason"] == "mangler container-adgang"
