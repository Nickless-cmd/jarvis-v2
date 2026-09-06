"""Autonomous run outcomes (redesign 2026-09-04): "run finished" is TELEMETRY
(runtime.autonomous_run_finished + Central), never a nudge — 89 % of the nudge
well was this line and 0 were ever sent. Failures/interruptions become a
proactive candidate that proactivity_bridge delivers when Bjørn has been away."""
from __future__ import annotations

import types

import core.services.visible_runs as vr


def _run():
    return types.SimpleNamespace(
        run_id="run-abc", user_message="ryd stale markers",
        provider="ollama", model="glm")


def _silence_central(monkeypatch):
    monkeypatch.setattr(
        "core.services.central_core.central",
        lambda: types.SimpleNamespace(observe=lambda *a, **k: None))


def _capture(monkeypatch):
    events: list[tuple[str, dict]] = []
    cands: list[dict] = []
    monkeypatch.setattr("core.eventbus.bus.event_bus.publish",
                        lambda kind, payload=None, **kw: events.append((kind, payload or {})))
    monkeypatch.setattr("core.services.proactive_candidates.add_candidate",
                        lambda **kw: (cands.append(kw), {"status": "added", "candidate_id": "pc-1"})[1])
    monkeypatch.setattr("core.services.nudge_broend.push",
                        lambda **kw: (_ for _ in ()).throw(AssertionError("well must not be used")))
    return events, cands


def test_completed_is_telemetry_only(monkeypatch):
    _silence_central(monkeypatch)
    events, cands = _capture(monkeypatch)
    vr._observe_autonomous_run(run=_run(), session_id="s", outcome="completed", frames=5)
    assert [k for k, _ in events if k == "runtime.autonomous_run_finished"]
    assert cands == []


def test_failed_becomes_medium_candidate_with_err_id(monkeypatch):
    _silence_central(monkeypatch)
    events, cands = _capture(monkeypatch)
    vr._observe_autonomous_run(run=_run(), session_id="s", outcome="failed", frames=2, error="boom")
    assert len(cands) == 1
    assert "err_id=run-abc" in cands[0]["text"] and "boom" in cands[0]["text"]
    assert cands[0]["priority"] == "medium" and cands[0]["source"] == "autonomous_run"


def test_interrupted_becomes_candidate(monkeypatch):
    _silence_central(monkeypatch)
    _events, cands = _capture(monkeypatch)
    vr._observe_autonomous_run(run=_run(), session_id="s", outcome="interrupted", frames=1)
    assert len(cands) == 1 and "⏸ interrupted" in cands[0]["text"]


def test_empty_completed_tick_no_candidate(monkeypatch):
    _silence_central(monkeypatch)
    events, cands = _capture(monkeypatch)
    vr._observe_autonomous_run(run=_run(), session_id="s", outcome="completed", frames=0)
    assert cands == []
    assert any(k == "runtime.autonomous_run_finished" for k, _ in events)
