"""Tests for run_control_state — især touch_active_visible_run heartbeat
(cross-proces liveness; Bjørn 2026-06-13)."""
from __future__ import annotations

from unittest.mock import patch

from core.services.visible_runs_sections import run_control_state as rcs


def test_touch_updates_heartbeat_for_matching_run():
    store = {"run_id": "auto-1", "session_id": "s1"}

    def fake_get(default=None):
        return store

    saved = {}

    def fake_set(value):
        saved.update(value)

    with patch.object(rcs, "_get_active_visible_run_state", return_value=store), \
         patch.object(rcs, "set_runtime_state_value", side_effect=lambda k, v: saved.update(v)):
        rcs.touch_active_visible_run("auto-1")
    assert "last_activity_at" in saved
    assert saved.get("run_id") == "auto-1"


def test_touch_noops_for_different_run():
    store = {"run_id": "auto-1", "session_id": "s1"}
    saved = {}
    with patch.object(rcs, "_get_active_visible_run_state", return_value=store), \
         patch.object(rcs, "set_runtime_state_value", side_effect=lambda k, v: saved.update(v)):
        rcs.touch_active_visible_run("some-other-run")  # ikke det aktive run
    assert saved == {}  # rørte ikke state'en (undgår at genoplive en afløst)
