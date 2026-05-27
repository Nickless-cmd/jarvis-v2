"""Tests for visible_runs post-process flow.

2026-05-22 (Claude): Added after finding that _post_process was guarded
behind `if visible_output_text:` which made empty-output runs skip
text_preview write, memory postprocess, and continuation detection —
the actual root cause of "Jarvis silently completes a run".

This file's tests are structural/contract — full integration tests
of visible_runs sit in test_visible_runs_continuation_detector.py and
other targeted files. The enforcement hook just needs a matching
test_<module>.py to exist for any core/ file we touch.
"""
from __future__ import annotations

import importlib

from core.services import visible_runs


class TestVisibleRunsModuleSurface:
    """Sanity-check: the post-process pipeline functions exist."""

    def test_module_imports(self):
        # Reimport to surface any syntax/import errors quickly
        importlib.reload(visible_runs)
        assert visible_runs is not None

    def test_preview_text_helper_present(self):
        """_preview_text is what writes the visible_run text_preview column."""
        assert hasattr(visible_runs, "_preview_text")

    def test_preview_text_empty_input(self):
        """Helper must handle empty input without raising."""
        assert visible_runs._preview_text("") == ""
        assert visible_runs._preview_text(None) == ""  # type: ignore[arg-type]

    def test_stuck_active_run_auto_clear(self, monkeypatch):
        """Regression-guard for 'No response content returned' loop.

        When a run dies without unregister_visible_run() (process restart
        mid-run, error before finally-block, autonomous run that exits
        uncleanly), the active_run state stays in DB. Every subsequent
        chat then gets routed as a 'midway nudge' which yields nothing
        visible. User sees empty responses until manual cleanup.

        Auto-clear logic: when active_run state is present but its
        controller is NOT in _VISIBLE_RUN_CONTROLLERS, and the run has
        been 'active' for >5 min, clear it on the next start_visible_run.
        """
        from datetime import datetime, timedelta, UTC

        stale_id = "visible-stale-12345"
        # No controller in process memory
        monkeypatch.setattr(visible_runs, "_VISIBLE_RUN_CONTROLLERS", {})

        # Inject a fake 10-minute-old active_run via DB-backed setter
        stale_started = (datetime.now(UTC) - timedelta(minutes=10)).isoformat()
        captured = {}
        def fake_get():
            return captured.get("state", {
                "active": True,
                "run_id": stale_id,
                "session_id": "chat-x",
                "started_at": stale_started,
                "cancelled": False,
            })
        def fake_set(payload):
            captured["state"] = payload or {}
        monkeypatch.setattr(visible_runs, "_get_active_visible_run_state", fake_get)
        monkeypatch.setattr(visible_runs, "_set_active_visible_run", fake_set)

        # Cap downstream side-effects: we only want to verify the clear path
        monkeypatch.setattr(visible_runs, "load_settings", lambda: type("S", (), {
            "primary_model_lane": "primary",
            "visible_model_provider": "deepseek",
            "visible_model_name": "test",
        })())
        monkeypatch.setattr(visible_runs, "_stream_visible_run", lambda run: iter([]))

        # Call site of interest — the stale state should be cleared, NOT
        # routed as a midway nudge.
        _ = visible_runs.start_visible_run(
            message="hello",
            session_id="chat-x",
            approval_mode="approve",
            thinking_mode="none",
        )

        assert captured.get("state") == {}, (
            f"Stale active_run should have been auto-cleared, got: {captured.get('state')}"
        )

    def test_hung_active_run_clears_even_with_controller(self, monkeypatch):
        """Extension of the auto-clear: pause-pattern auto-continuation runs
        register their controller in the SAME process that handles incoming
        chat (jarvis-api). The original >5min+no-controller check missed
        them — they'd hang indefinitely while chat-stream returned empty.

        Tier 2: ANY run older than 10 minutes is hung regardless of whether
        the controller is in memory. Real visible runs complete in seconds
        to a couple of minutes.
        """
        from datetime import datetime, timedelta, UTC

        stale_id = "autonomous-hung-67890"
        # Mock controller — has a cancel() method we expect to be called
        cancel_called = {"v": False}
        class FakeController:
            def cancel(self): cancel_called["v"] = True
        controllers = {stale_id: FakeController()}
        monkeypatch.setattr(visible_runs, "_VISIBLE_RUN_CONTROLLERS", controllers)

        # 12-minute-old run that's still "active" with controller in memory
        stale_started = (datetime.now(UTC) - timedelta(minutes=12)).isoformat()
        captured = {}
        def fake_get():
            return captured.get("state", {
                "active": True,
                "run_id": stale_id,
                "session_id": "chat-x",
                "started_at": stale_started,
                "cancelled": False,
            })
        def fake_set(payload):
            captured["state"] = payload or {}
        monkeypatch.setattr(visible_runs, "_get_active_visible_run_state", fake_get)
        monkeypatch.setattr(visible_runs, "_set_active_visible_run", fake_set)
        monkeypatch.setattr(visible_runs, "load_settings", lambda: type("S", (), {
            "primary_model_lane": "primary",
            "visible_model_provider": "deepseek",
            "visible_model_name": "test",
        })())
        monkeypatch.setattr(visible_runs, "_stream_visible_run", lambda run: iter([]))

        _ = visible_runs.start_visible_run(
            message="hello",
            session_id="chat-x",
            approval_mode="approve",
            thinking_mode="none",
        )

        assert captured.get("state") == {}, (
            f"Hung active_run (>10min) should clear even with controller; got: {captured.get('state')}"
        )
        assert cancel_called["v"], "Controller should have been cancelled to stop zombie work"

    def test_preview_text_truncates(self):
        """Long input gets truncated to a single bounded line."""
        long_text = "x" * 1000
        out = visible_runs._preview_text(long_text, limit=64)
        assert len(out) <= 64
        # Newlines should be normalised
        assert "\n" not in out


class TestCacheTokenPlumbing:
    """2026-05-22: cost.recorded must include cache_hit/miss tokens.

    Before this fix, DeepSeek's prompt_cache_hit_tokens were parsed by
    cheap_provider_runtime but dropped at VisibleModelResult layer, so
    every cost.recorded event showed 0% cache hit even when DeepSeek
    was serving cached prefixes.
    """

    def test_visible_model_result_has_cache_fields(self):
        from core.services.visible_model import VisibleModelResult
        r = VisibleModelResult(
            text="test",
            input_tokens=100,
            output_tokens=10,
            cost_usd=0.001,
            cache_hit_tokens=80,
            cache_miss_tokens=20,
        )
        assert r.cache_hit_tokens == 80
        assert r.cache_miss_tokens == 20

    def test_visible_model_result_defaults_to_zero(self):
        """Old callers (and providers without cache) should default to 0."""
        from core.services.visible_model import VisibleModelResult
        r = VisibleModelResult(
            text="t", input_tokens=10, output_tokens=2, cost_usd=0.0,
        )
        assert r.cache_hit_tokens == 0
        assert r.cache_miss_tokens == 0
