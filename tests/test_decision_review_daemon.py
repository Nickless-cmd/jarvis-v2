"""Tests for core.services.decision_review_daemon — adherence-loop daemon.

Covers:
  - No active decisions → 0 reviewed
  - Normal tick calls review_pending_decisions
  - Import failure returns error dict
  - Daemon registry entry exists with correct cadence
  - Heartbeat wiring pattern matches consolidation_judge
"""
from __future__ import annotations

from unittest import mock

import pytest


class TestDecisionReviewDaemonTick:
    """Test the daemon tick function in isolation."""

    def test_no_active_decisions(self):
        """When there are no active decisions, reviewed should be 0."""
        from core.services.decision_review_daemon import tick_decision_review_daemon

        with mock.patch(
            "core.services.decision_review_prompter.review_pending_decisions",
            return_value={
                "status": "ok",
                "considered": 0,
                "reviewed": 0,
                "skipped_recent": 0,
                "failed": 0,
            },
        ):
            result = tick_decision_review_daemon()
        assert result["status"] == "ok"
        assert result["reviewed"] == 0
        assert result["considered"] == 0

    def test_happy_path_reviews_decisions(self):
        """Normal tick: 3 decisions reviewed, 2 skipped, 0 failed."""
        from core.services.decision_review_daemon import tick_decision_review_daemon

        with mock.patch(
            "core.services.decision_review_prompter.review_pending_decisions",
            return_value={
                "status": "ok",
                "considered": 5,
                "reviewed": 3,
                "skipped_recent": 2,
                "failed": 0,
            },
        ):
            result = tick_decision_review_daemon()
        assert result["status"] == "ok"
        assert result["reviewed"] == 3
        assert result["skipped_recent"] == 2

    def test_import_failure_returns_error(self):
        """When the prompter module can't be imported, return error dict.

        We simulate this by patching __import__ inside the daemon module
        to raise ImportError when 'decision_review_prompter' is requested.
        """
        from core.services.decision_review_daemon import tick_decision_review_daemon
        import builtins

        original_import = builtins.__import__

        def _fake_import(name, *args, **kwargs):
            if "decision_review_prompter" in name:
                raise ImportError(f"no module named '{name}'")
            return original_import(name, *args, **kwargs)

        with mock.patch.object(builtins, "__import__", side_effect=_fake_import):
            result = tick_decision_review_daemon()
        assert result["status"] == "error"
        assert "import" in result["error"].lower()
        # Must not crash
        assert isinstance(result, dict)

    def test_tick_propagates_llm_failure_as_failed_count(self):
        """LLM failure inside the prompter increments failed count."""
        from core.services.decision_review_daemon import tick_decision_review_daemon

        with mock.patch(
            "core.services.decision_review_prompter.review_pending_decisions",
            return_value={
                "status": "ok",
                "considered": 5,
                "reviewed": 2,
                "skipped_recent": 1,
                "failed": 2,
            },
        ):
            result = tick_decision_review_daemon()
        assert result["status"] == "ok"
        assert result["failed"] == 2

    def test_tick_handles_unexpected_return_type(self):
        """If the prompter returns something other than dict, handle gracefully."""
        from core.services.decision_review_daemon import tick_decision_review_daemon

        with mock.patch(
            "core.services.decision_review_prompter.review_pending_decisions",
            return_value="unexpected string",
        ):
            result = tick_decision_review_daemon()
        assert result["status"] == "error"

    def test_tick_handles_exception_gracefully(self):
        """If the prompter raises, return error dict without crashing."""
        from core.services.decision_review_daemon import tick_decision_review_daemon

        with mock.patch(
            "core.services.decision_review_prompter.review_pending_decisions",
            side_effect=RuntimeError("DB connection lost"),
        ):
            result = tick_decision_review_daemon()
        assert result["status"] == "error"
        assert result["error"] == "DB connection lost"


class TestDecisionReviewDaemonRegistry:
    """Test daemon registration in daemon_manager."""

    def test_registry_entry_exists(self):
        """Decision review daemon is registered with correct cadence."""
        from core.services.daemon_manager import _REGISTRY

        assert "decision_review" in _REGISTRY
        entry = _REGISTRY["decision_review"]
        assert entry["module"] == "core.services.decision_review_daemon"
        assert entry["default_cadence_minutes"] == 360
        # 2026-06-11 (Bjørn frustration crisis fix C1): DEAKTIVERET. The daemon
        # let Jarvis self-grade adherence to his own behavioral decisions →
        # positive-bias self-validation loop (1.0 adherence while hallucinating
        # tool-work). It stays registered but default-disabled until replaced by
        # external-truth review (git-log + tool-history).
        assert entry["default_enabled"] is False

    def test_alias_tick_exists(self):
        """The module exposes a 'tick' alias for consistent import pattern."""
        from core.services import decision_review_daemon

        assert hasattr(decision_review_daemon, "tick")
        assert decision_review_daemon.tick is decision_review_daemon.tick_decision_review_daemon


class TestHeartbeatWiring:
    """Test that the daemon is wired in heartbeat_runtime."""

    def test_decision_review_wired_after_consolidation_judge(self):
        """The wiring block appears after consolidation_judge in the heartbeat
        influence-trace module (extracted from heartbeat_runtime, Boy-Scout split)."""
        with open(
            "/media/projects/jarvis-v2/core/services/heartbeat_runtime_influence.py",
            "r",
            encoding="utf-8",
        ) as f:
            content = f.read()

        # Both must be present
        assert "decision_review" in content
        assert "consolidation_judge" in content

        # The wiring must use _daemon_tick_with_deadline pattern
        assert "_daemon_tick_with_deadline(\n" in content or "_daemon_tick_with_deadline(" in content
        assert "_dm.record_daemon_tick(\"decision_review\"" in content or '_dm.record_daemon_tick("decision_review"' in content
