"""Tests for user_temperature_runtime daemon."""
from __future__ import annotations

import threading
import time

import pytest


def test_start_is_idempotent(monkeypatch):
    from core.services import user_temperature_runtime as rt
    rt._THREAD = None
    rt._STOP.clear()
    monkeypatch.setattr(rt, "_TRIGGER_CHECK_S", 3600)

    rt.start_user_temperature_runtime()
    t1 = rt._THREAD
    rt.start_user_temperature_runtime()
    t2 = rt._THREAD
    assert t1 is t2
    rt.stop_user_temperature_runtime()


def test_stop_sets_stop_event():
    from core.services import user_temperature_runtime as rt
    rt._STOP.clear()
    rt.stop_user_temperature_runtime()
    assert rt._STOP.is_set()
    rt._STOP.clear()


def test_workspace_lock_prevents_concurrent_cycles(monkeypatch):
    from core.services import user_temperature_runtime as rt
    from core.services import user_temperature_engine

    call_count = [0]
    barrier = threading.Event()

    def slow_cycle(*, workspace_id, force=False):
        call_count[0] += 1
        barrier.wait(timeout=2)
        return {"status": "ok"}

    monkeypatch.setattr(user_temperature_engine, "run_llm_stream", slow_cycle)
    rt._WORKSPACE_LOCKS.clear()

    def runner():
        rt._run_one_cycle("default", force=True)

    t1 = threading.Thread(target=runner)
    t1.start()
    time.sleep(0.05)

    result = rt._run_one_cycle("default", force=True)
    assert result.get("skipped") is True

    barrier.set()
    t1.join(timeout=3)
    assert call_count[0] == 1
