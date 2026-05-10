"""Tests for forgetting_runtime daemon."""
from __future__ import annotations

import threading
import time

import pytest


def test_start_is_idempotent(monkeypatch):
    """Calling start twice does not spawn two threads."""
    from core.services import forgetting_runtime as fr
    # Reset module state
    fr._THREAD = None
    fr._STOP.clear()
    monkeypatch.setattr(fr, "_INTERVAL_S", 3600)  # don't actually loop

    fr.start_forgetting_runtime()
    t1 = fr._THREAD
    fr.start_forgetting_runtime()
    t2 = fr._THREAD
    assert t1 is t2
    fr.stop_forgetting_runtime()


def test_stop_sets_stop_event():
    from core.services import forgetting_runtime as fr
    fr._STOP.clear()
    fr.stop_forgetting_runtime()
    assert fr._STOP.is_set()
    fr._STOP.clear()


def test_workspace_lock_prevents_concurrent_cycles(monkeypatch):
    """If a cycle is already running for a workspace, the next call skips."""
    from core.services import forgetting_runtime as fr
    from core.services import forgetting_engine

    call_count = [0]
    barrier = threading.Event()

    def slow_cycle(*, workspace_id):
        call_count[0] += 1
        barrier.wait(timeout=2)
        return {"workspace_id": workspace_id, "soft_deleted": 0}

    monkeypatch.setattr(forgetting_engine, "run_auto_cycle", slow_cycle)

    # Reset locks
    fr._WORKSPACE_LOCKS.clear()

    def runner():
        fr._run_one_cycle("default")

    t1 = threading.Thread(target=runner)
    t1.start()
    time.sleep(0.05)  # let t1 acquire the lock and enter slow_cycle

    result = fr._run_one_cycle("default")  # should skip
    assert result.get("skipped") is True

    barrier.set()
    t1.join(timeout=3)
    assert call_count[0] == 1  # only the first cycle actually ran
