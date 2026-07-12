"""Tests for background recall scheduler (recall_scheduler.py).

Verifies the scheduler runs recall_for_message on the ACTUAL user message in a
background thread, respects the kill-switch, is self-safe on empty input, and
never stacks concurrent recalls.
"""
from __future__ import annotations

import threading
import time

import pytest

import core.services.recall_scheduler as rs


@pytest.fixture(autouse=True)
def _reset_scheduler():
    with rs._recall_lock:
        rs._recall_running = False
    yield
    with rs._recall_lock:
        rs._recall_running = False


def _wait_done(timeout: float = 3.0) -> None:
    """Wait for the background recall thread to finish."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        with rs._recall_lock:
            if not rs._recall_running:
                return
        time.sleep(0.01)


def test_triggers_recall_with_actual_message(monkeypatch):
    seen: dict[str, object] = {}
    done = threading.Event()

    def _fake_recall(msg, emo):
        seen["msg"] = msg
        seen["emo"] = emo
        done.set()
        return []

    monkeypatch.setattr(rs, "background_recall_enabled", lambda: True)
    monkeypatch.setattr(rs, "_build_emotional_state", lambda: {"joy": 0.4})
    import core.services.associative_recall as ar
    monkeypatch.setattr(ar, "recall_for_message", _fake_recall)

    started = rs.trigger_background_recall("Hold kæft jeg er træt..")
    assert started is True
    assert done.wait(timeout=3.0)
    assert seen["msg"] == "Hold kæft jeg er træt.."
    assert seen["emo"] == {"joy": 0.4}


def test_kill_switch_off_skips(monkeypatch):
    called = {"n": 0}

    def _fake_recall(msg, emo):
        called["n"] += 1
        return []

    monkeypatch.setattr(rs, "background_recall_enabled", lambda: False)
    import core.services.associative_recall as ar
    monkeypatch.setattr(ar, "recall_for_message", _fake_recall)

    started = rs.trigger_background_recall("noget")
    _wait_done()
    assert started is False
    assert called["n"] == 0


def test_empty_message_is_noop(monkeypatch):
    monkeypatch.setattr(rs, "background_recall_enabled", lambda: True)
    assert rs.trigger_background_recall("") is False
    assert rs.trigger_background_recall("   ") is False


def test_does_not_stack_concurrent_recalls(monkeypatch):
    release = threading.Event()
    entered = threading.Event()

    def _slow_recall(msg, emo):
        entered.set()
        release.wait(timeout=3.0)
        return []

    monkeypatch.setattr(rs, "background_recall_enabled", lambda: True)
    monkeypatch.setattr(rs, "_build_emotional_state", lambda: {})
    import core.services.associative_recall as ar
    monkeypatch.setattr(ar, "recall_for_message", _slow_recall)

    first = rs.trigger_background_recall("besked A")
    assert first is True
    assert entered.wait(timeout=3.0)          # first recall is running
    second = rs.trigger_background_recall("besked B")
    assert second is False                     # skipped — one already running
    release.set()
    _wait_done()


def test_self_safe_when_recall_raises(monkeypatch):
    def _boom(msg, emo):
        raise RuntimeError("scoring exploded")

    monkeypatch.setattr(rs, "background_recall_enabled", lambda: True)
    monkeypatch.setattr(rs, "_build_emotional_state", lambda: {})
    import core.services.associative_recall as ar
    monkeypatch.setattr(ar, "recall_for_message", _boom)

    started = rs.trigger_background_recall("boom")
    assert started is True
    _wait_done()
    # flag must be released even though recall raised
    with rs._recall_lock:
        assert rs._recall_running is False
