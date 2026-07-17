"""Autonomous runs must nudge Jarvis into awareness of his own runs — he is
otherwise blind to them unless he actively looks. _observe_autonomous_run drops
a nudge_broend nudge on completion/failure (→ outbound_nudges → his prompt)."""
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


def _capture_push(monkeypatch):
    pushed: list[dict] = []
    monkeypatch.setattr("core.services.nudge_broend.push",
                        lambda **kw: (pushed.append(kw), "nudge-1")[1])
    return pushed


def test_completed_with_frames_pushes_nudge(monkeypatch):
    _silence_central(monkeypatch)
    pushed = _capture_push(monkeypatch)
    vr._observe_autonomous_run(run=_run(), session_id="s", outcome="completed", frames=5)
    assert len(pushed) == 1
    assert "✓ færdig" in pushed[0]["message"]
    assert pushed[0]["importance"] == "normal"
    assert pushed[0]["raw_payload"]["run_id"] == "run-abc"


def test_failed_pushes_high_with_err_id(monkeypatch):
    _silence_central(monkeypatch)
    pushed = _capture_push(monkeypatch)
    vr._observe_autonomous_run(run=_run(), session_id="s", outcome="failed",
                               error="provider timeout")
    assert len(pushed) == 1
    assert "err_id=run-abc" in pushed[0]["message"]
    assert "provider timeout" in pushed[0]["message"]
    assert pushed[0]["importance"] == "high"


def test_interrupted_pushes_high(monkeypatch):
    _silence_central(monkeypatch)
    pushed = _capture_push(monkeypatch)
    vr._observe_autonomous_run(run=_run(), session_id="s", outcome="interrupted", frames=2)
    assert len(pushed) == 1
    assert pushed[0]["importance"] == "high"


def test_empty_completed_tick_no_nudge(monkeypatch):
    _silence_central(monkeypatch)
    pushed = _capture_push(monkeypatch)
    vr._observe_autonomous_run(run=_run(), session_id="s", outcome="completed", frames=0)
    assert pushed == []
