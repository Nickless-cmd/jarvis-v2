from __future__ import annotations
from core.services import dream_consolidation_daemon as d


def test_session_gate_skips_when_too_few(isolated_runtime, monkeypatch):
    monkeypatch.setattr(d, "_load", lambda: {"consolidations": [], "last_run_at": "2020-01-01T00:00:00+00:00"})
    monkeypatch.setattr(d, "_is_idle_enough", lambda: (True, 99))
    monkeypatch.setattr(d, "_sessions_since", lambda last: 2)  # < 5
    called = {"n": 0}
    monkeypatch.setattr(d, "consolidate_now", lambda: called.__setitem__("n", 1) or {})
    r = d.tick()
    assert r["skipped"] is True and "too-few-sessions" in r["reason"]
    assert called["n"] == 0


def test_lock_skips_when_held(isolated_runtime, monkeypatch):
    monkeypatch.setattr(d, "_load", lambda: {"consolidations": [], "last_run_at": None})
    monkeypatch.setattr(d, "_is_idle_enough", lambda: (True, 99))
    monkeypatch.setattr(d, "_sessions_since", lambda last: 10)
    monkeypatch.setattr(d, "_acquire_consolidation_lock", lambda: False)
    called = {"n": 0}
    monkeypatch.setattr(d, "consolidate_now", lambda: called.__setitem__("n", 1) or {})
    r = d.tick()
    assert r["skipped"] is True and r["reason"] == "already-dreaming"
    assert called["n"] == 0


def test_runs_and_releases_lock_when_gates_pass(isolated_runtime, monkeypatch):
    monkeypatch.setattr(d, "_load", lambda: {"consolidations": [], "last_run_at": None})
    monkeypatch.setattr(d, "_is_idle_enough", lambda: (True, 99))
    monkeypatch.setattr(d, "_sessions_since", lambda last: 10)
    monkeypatch.setattr(d, "_acquire_consolidation_lock", lambda: True)
    released = {"n": 0}
    monkeypatch.setattr(d, "_release_consolidation_lock", lambda: released.__setitem__("n", released["n"] + 1))
    monkeypatch.setattr(d, "consolidate_now", lambda: {"consolidations": ["x"]})
    r = d.tick()
    assert r == {"consolidations": ["x"]}
    assert released["n"] == 1
