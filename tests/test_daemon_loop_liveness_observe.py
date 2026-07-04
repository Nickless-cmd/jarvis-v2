"""Tests for the "die-hidden" loop-liveness wiring.

Standalone daemon loops that caught iteration errors used to ONLY log — a loop
failing every tick looked alive from outside, and per Bjørn's notes log files
are often stale/unread. Each such loop-except now also calls
``central_private_observe.observe_operational_liveness(<daemon>, "error", None)``
so *persistent* loop failure becomes visible to the Central drift-monitor.

Invariants asserted per file:
  * observe IS called (with the daemon's name) when the inner work raises.
  * loop behaviour is UNCHANGED — the original logger call still fires and the
    loop still spins / continues (never re-raises).
  * the observe hook is self-safe — if observe itself raises, the loop is
    unaffected.
"""
from __future__ import annotations

import queue
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# scheduled_tasks._poller_loop
# ---------------------------------------------------------------------------


def test_scheduled_tasks_loop_observes_on_error():
    from core.services import scheduled_tasks as mod

    # Stop after one failing iteration: wait() returns → loop re-checks is_set.
    mod._poller_stop.clear()

    def _boom():
        raise RuntimeError("boom")

    with patch.object(mod, "_fire_due_tasks", side_effect=_boom), \
         patch.object(mod, "logger") as log, \
         patch("core.services.central_private_observe.observe_operational_liveness") as obs, \
         patch.object(mod._poller_stop, "wait", side_effect=lambda *_: mod._poller_stop.set()):
        mod._poller_loop()

    obs.assert_called_once_with("scheduled_tasks", "error", None)
    assert log.error.called  # original logging behaviour preserved


def test_scheduled_tasks_loop_self_safe_when_observe_raises():
    from core.services import scheduled_tasks as mod

    mod._poller_stop.clear()
    with patch.object(mod, "_fire_due_tasks", side_effect=RuntimeError("boom")), \
         patch.object(mod, "logger"), \
         patch("core.services.central_private_observe.observe_operational_liveness",
               side_effect=RuntimeError("observe down")), \
         patch.object(mod._poller_stop, "wait", side_effect=lambda *_: mod._poller_stop.set()):
        # Must not raise — observe failure is swallowed, loop exits cleanly.
        mod._poller_loop()


# ---------------------------------------------------------------------------
# jarvis_brain_daemon.reindex_loop
# ---------------------------------------------------------------------------


def test_jarvis_brain_reindex_loop_observes_on_error():
    import threading

    from core.services import jarvis_brain_daemon as mod

    stop = threading.Event()
    with patch.object(mod, "reindex_once", side_effect=RuntimeError("boom")), \
         patch.object(mod, "logger") as log, \
         patch("core.services.central_private_observe.observe_operational_liveness") as obs, \
         patch.object(stop, "wait", side_effect=lambda *_: stop.set()):
        mod.reindex_loop(stop)

    obs.assert_called_once_with("jarvis_brain_reindex", "error", None)
    assert log.warning.called


# ---------------------------------------------------------------------------
# recurring_tasks._poller_loop
# ---------------------------------------------------------------------------


def test_recurring_tasks_loop_observes_on_error():
    from core.services import recurring_tasks as mod

    mod._poller_stop.clear()
    with patch.object(mod, "_fire_due", side_effect=RuntimeError("boom")), \
         patch.object(mod, "logger") as log, \
         patch("core.services.central_private_observe.observe_operational_liveness") as obs, \
         patch.object(mod._poller_stop, "wait", side_effect=lambda *_: mod._poller_stop.set()):
        mod._poller_loop()

    obs.assert_called_once_with("recurring_tasks", "error", None)
    assert log.error.called


# ---------------------------------------------------------------------------
# decision_enforcement._poll_loop  (per-item except that continues)
# ---------------------------------------------------------------------------


def test_decision_enforcement_loop_observes_on_error():
    from core.services import decision_enforcement as mod

    # Queue yields one item that trips the handler, then a sentinel None to stop.
    q = queue.Queue()
    q.put({"kind": "channel.chat_message_appended"})  # .get on this raises below
    q.put(None)

    fake_bus = MagicMock()
    fake_bus.subscribe.return_value = q

    # Force the per-item body to raise: item.get() raising simulates a broken item.
    bad_item = MagicMock()
    bad_item.get.side_effect = RuntimeError("boom")
    q2 = queue.Queue()
    q2.put(bad_item)
    q2.put(None)
    fake_bus.subscribe.return_value = q2

    with patch.dict("sys.modules", {"core.eventbus.bus": MagicMock(event_bus=fake_bus)}), \
         patch("core.services.central_private_observe.observe_operational_liveness") as obs:
        mod._poll_loop()

    obs.assert_called_once_with("decision_enforcement", "error", None)


# ---------------------------------------------------------------------------
# semantic_indexer._sweeper_loop + _subscriber_loop
# ---------------------------------------------------------------------------


def test_semantic_indexer_sweeper_observes_on_error():
    from core.services import semantic_indexer as mod

    mod._SWEEPER_STOP.clear()

    # First wait() returns False (proceed to backfill), backfill raises, then in
    # the next loop check we stop. We use a call counter on wait.
    calls = {"n": 0}

    def _wait(timeout=None):
        calls["n"] += 1
        if calls["n"] == 1:
            return False  # proceed into the try-block
        mod._SWEEPER_STOP.set()
        return True

    with patch("core.services.semantic_memory.backfill_all",
               side_effect=RuntimeError("boom")), \
         patch.object(mod, "logger") as log, \
         patch("core.services.central_private_observe.observe_operational_liveness") as obs, \
         patch.object(mod._SWEEPER_STOP, "wait", side_effect=_wait):
        mod._sweeper_loop()

    obs.assert_called_once_with("semantic_indexer_sweep", "error", None)
    assert log.debug.called


def test_semantic_indexer_subscriber_observes_on_error():
    from core.services import semantic_indexer as mod

    mod._SUBSCRIBER_STOP.clear()

    sub = MagicMock()
    # First get() → an item that dispatches to a handler that raises; then stop.
    sub.get.side_effect = [{"kind": mod._SENSORY_EVENT, "payload": {"id": "x"}}, None]

    def _stop_after(*_a, **_k):
        mod._SUBSCRIBER_STOP.set()

    with patch.object(mod, "_handle_sensory", side_effect=RuntimeError("boom")), \
         patch.object(mod, "logger") as log, \
         patch("core.services.central_private_observe.observe_operational_liveness",
               side_effect=_stop_after) as obs:
        mod._subscriber_loop(subscriber=sub)

    obs.assert_called_once_with("semantic_indexer_subscriber", "error", None)
    assert log.debug.called


# ---------------------------------------------------------------------------
# mood_oscillator._listener_loop
# ---------------------------------------------------------------------------


def test_mood_oscillator_listener_observes_on_error():
    from core.services import mood_oscillator as mod

    q = MagicMock()
    q.get.return_value = {"kind": "heartbeat.tick_completed", "payload": {}}

    mod._listener_running = True

    def _stop_after(*_a, **_k):
        mod._listener_running = False

    with patch.object(mod, "_handle_event", side_effect=RuntimeError("boom")), \
         patch.object(mod, "logger") as log, \
         patch("core.services.central_private_observe.observe_operational_liveness",
               side_effect=_stop_after) as obs:
        mod._listener_loop(q)

    obs.assert_called_once_with("mood_oscillator_listener", "error", None)
    assert log.debug.called


# ---------------------------------------------------------------------------
# theory_of_mind._listener_loop
# ---------------------------------------------------------------------------


def test_theory_of_mind_loop_observes_on_error():
    from core.services import theory_of_mind as mod

    mod._listener_running = True

    def _stop_after(*_a, **_k):
        mod._listener_running = False

    # _connect raises inside the poll try-block → except path fires.
    with patch.object(mod, "_connect", side_effect=RuntimeError("boom")), \
         patch.object(mod, "logger") as log, \
         patch("time.sleep", return_value=None), \
         patch("core.services.central_private_observe.observe_operational_liveness",
               side_effect=_stop_after) as obs:
        mod._listener_loop()

    obs.assert_called_once_with("theory_of_mind", "error", None)
    assert log.exception.called


# ---------------------------------------------------------------------------
# forgetting_runtime._loop
# ---------------------------------------------------------------------------


def test_forgetting_runtime_loop_observes_on_error():
    from core.services import forgetting_runtime as mod

    mod._STOP.clear()
    with patch.object(mod, "_list_active_workspaces", side_effect=RuntimeError("boom")), \
         patch.object(mod, "logger") as log, \
         patch.object(mod, "_resolve_interval_seconds", return_value=0), \
         patch("core.services.central_private_observe.observe_operational_liveness") as obs, \
         patch.object(mod._STOP, "wait", side_effect=lambda *_: mod._STOP.set()):
        mod._loop()

    obs.assert_called_once_with("forgetting_runtime", "error", None)
    assert log.warning.called
