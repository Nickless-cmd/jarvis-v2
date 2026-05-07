import threading
import time
import pytest

from core.services import counterfactual_engine_runtime as cer


def test_get_workspace_lock_returns_same_lock_for_same_workspace(monkeypatch):
    monkeypatch.setattr(cer, "_WORKSPACE_LOCKS", {})
    a = cer._get_workspace_lock("default")
    b = cer._get_workspace_lock("default")
    assert a is b


def test_get_workspace_lock_returns_different_locks(monkeypatch):
    monkeypatch.setattr(cer, "_WORKSPACE_LOCKS", {})
    a = cer._get_workspace_lock("default")
    b = cer._get_workspace_lock("mikkel")
    assert a is not b


def test_run_one_cycle_with_lock_held_skips(monkeypatch):
    """If the per-workspace lock is held, _run_one_cycle returns skipped."""
    monkeypatch.setattr(cer, "_WORKSPACE_LOCKS", {})
    lock = cer._get_workspace_lock("default")
    lock.acquire()
    try:
        # Simulate concurrent attempt
        called = []
        def fake_run(**kwargs):
            called.append(kwargs)
            return {"counterfactuals_generated": 1}
        monkeypatch.setattr(
            "core.services.counterfactual_engine.run", fake_run
        )
        out = cer._run_one_cycle("default")
        assert out["skipped"] is True
        assert out["skipped_reason"] == "lock-held"
        assert called == []  # engine.run was not invoked
    finally:
        lock.release()


def test_run_one_cycle_invokes_engine_when_lock_free(monkeypatch):
    monkeypatch.setattr(cer, "_WORKSPACE_LOCKS", {})
    called = []
    def fake_run(**kwargs):
        called.append(kwargs)
        return {"workspace_id": "default", "counterfactuals_generated": 2}
    monkeypatch.setattr("core.services.counterfactual_engine.run", fake_run)
    out = cer._run_one_cycle("default")
    assert called == [{"workspace_id": "default"}]
    assert out["counterfactuals_generated"] == 2


def test_run_one_cycle_swallows_engine_exception(monkeypatch):
    """A crashing engine.run must not crash the daemon."""
    monkeypatch.setattr(cer, "_WORKSPACE_LOCKS", {})
    def boom(**kwargs):
        raise RuntimeError("engine exploded")
    monkeypatch.setattr("core.services.counterfactual_engine.run", boom)
    out = cer._run_one_cycle("default")
    assert "error" in out


def test_start_is_idempotent(monkeypatch):
    """Calling start twice must not create two threads."""
    monkeypatch.setattr(cer, "_THREAD", None)
    monkeypatch.setattr(cer, "_STOP", threading.Event())
    monkeypatch.setattr(cer, "_INTERVAL_S", 0.05)  # fast loop for test

    # Stub the loop body so it doesn't actually do work
    monkeypatch.setattr(cer, "_run_one_cycle", lambda ws: {"skipped": True})

    cer.start_counterfactual_runtime()
    first_thread = cer._THREAD
    cer.start_counterfactual_runtime()  # second call
    second_thread = cer._THREAD
    assert first_thread is second_thread
    cer.stop_counterfactual_runtime()
    time.sleep(0.1)
