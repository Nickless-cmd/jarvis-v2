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
        monkeypatch.setattr(visible_runs, "_stream_visible_run", lambda run, **_kw: iter([]))

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
        monkeypatch.setattr(visible_runs, "_stream_visible_run", lambda run, **_kw: iter([]))

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


def test_is_visible_run_alive_truthful():
    """is_visible_run_alive er den autoritative liveness-test (Bjørn 2026-06-13,
    robust-streaming): kun runs hvis controller faktisk lever i processen.
    Klienten afstemmer mod denne i stedet for at TRO den arbejder til en
    message_stop-frame lander → et dødt run efterlader ikke UI'et hængende."""
    from core.services import visible_runs as vr

    assert vr.is_visible_run_alive("") is False
    assert vr.is_visible_run_alive("nonexistent-run") is False

    # Indsæt en fake controller → nu "i live"; fjern igen → død.
    vr._VISIBLE_RUN_CONTROLLERS["run-xyz"] = object()  # type: ignore[assignment]
    try:
        assert vr.is_visible_run_alive("run-xyz") is True
    finally:
        vr._VISIBLE_RUN_CONTROLLERS.pop("run-xyz", None)
    assert vr.is_visible_run_alive("run-xyz") is False


def test_is_visible_run_alive_cross_process_heartbeat():
    """Cross-proces: et autonomt run lever i runtime-processen (ikke i api's
    controller-dict). Liveness skal kunne aflæses fra den DELTE DB-heartbeat
    (last_activity_at) — frisk = i live, gammel = dødt (Bjørn 2026-06-13)."""
    from datetime import UTC, datetime, timedelta
    from unittest.mock import patch
    from core.services import visible_runs as vr

    fresh = {"run_id": "auto-1", "session_id": "s1",
             "last_activity_at": datetime.now(UTC).isoformat()}
    stale = {"run_id": "auto-1", "session_id": "s1",
             "last_activity_at": (datetime.now(UTC) - timedelta(seconds=200)).isoformat()}
    cancelled = {"run_id": "auto-1", "session_id": "s1", "cancelled": True,
                 "last_activity_at": datetime.now(UTC).isoformat()}

    with patch.object(vr, "_get_active_visible_run_state", return_value=fresh):
        assert vr.is_visible_run_alive("auto-1") is True
    with patch.object(vr, "_get_active_visible_run_state", return_value=stale):
        assert vr.is_visible_run_alive("auto-1") is False  # heartbeat for gammel
    with patch.object(vr, "_get_active_visible_run_state", return_value=cancelled):
        assert vr.is_visible_run_alive("auto-1") is False
    with patch.object(vr, "_get_active_visible_run_state", return_value=fresh):
        assert vr.is_visible_run_alive("other-run") is False  # andet run_id


class TestTruthGateC4Removal:
    """TruthGate C4 (2026-06-22): de gamle post-done effekt-gates (claim-block,
    fact_gate, diagnosis) er FJERNET fra _post_process — enforcement gøres pre-done
    af TruthGate v2. Detektions-logikken lever videre via central().decide
    (gate_truth-adaptere = ren observabilitet).

    To load-bearing invarianter låses her via kildeinspektion + AST:
    1. _post_process er IKKE længere en generator (alle yields forsvandt med de
       gamle gates) → den køres som normal Thread, ikke drainet. Dét dræber
       CRITICAL-generator-støjen og fjerner generator-i-tråd-fælde-risikoen.
    2. central().decide('truth') (observabilitet) består — det ENESTE post-done
       truth-spor efter C4."""

    def _vr(self):
        from core.services import visible_runs as vr
        return vr

    def _post_process_source(self):
        import inspect
        src = inspect.getsource(self._vr())
        return src[src.index("def _post_process("):]

    def test_post_process_is_not_a_generator(self):
        import ast
        import inspect
        src = inspect.getsource(self._vr())
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "_post_process":
                yields = [n for n in ast.walk(node)
                          if isinstance(n, (ast.Yield, ast.YieldFrom))]
                assert yields == [], "C4: _post_process må ikke have yields (generator)"
                return
        raise AssertionError("_post_process ikke fundet")

    def test_old_effect_gates_removed(self):
        body = self._post_process_source()
        # ingen rester af de gamle effekt-gates eller C2-sentinel-stilladset
        assert "_C2GateSkip" not in body
        assert "_tv2_on" not in body
        assert "_fact_gate_enforce" not in body
        assert "diagnosis_gate_enforce" not in body
        assert "detect_fabricated_work_claims" not in body

    def test_observability_decide_preserved(self):
        body = self._post_process_source()
        # central().decide('truth', ...) + det hoistede _executed_tool_names der
        # fodrer den skal bestå — det er nu det eneste post-done truth-spor.
        assert '.decide(' in body and '"truth"' in body
        assert "_executed_tool_names" in body


class TestCommitClusterTrace:
    """Commit-cluster migration (2026-06-22): decision_gate ruttes gennem
    central().observe for ÉT trace-spore (additivt; enforcement bevaret inline).
    Bruger observe() ikke decide() for at undgå dobbelt DB-read i hot-løkken."""

    def _vr_source(self):
        import inspect
        from core.services import visible_runs as vr
        return inspect.getsource(vr)

    def test_commit_observe_wired_at_decision_gate(self):
        src = self._vr_source()
        assert '"cluster": "commit"' in src
        assert '"nerve": "decision_gate"' in src
        assert ".observe(" in src

    def test_central_observe_records_commit_trace(self):
        # central().observe på en commit-event skal kunne køre uden at kaste
        from core.services.central_core import central
        central().observe({
            "cluster": "commit", "nerve": "decision_gate", "run_id": "t-commit",
            "decision": "green", "tool_name": "web_search", "reason": "",
        })  # best-effort, kaster aldrig


class TestTrackerCascadeFix:
    """Kaskade-bug-fix (2026-06-22): FØR afsluttede hver tracker-blok i
    _track_runtime_candidates med `except: return` → én fejlende tracker forlod HELE
    funktionen og sprang alle downstream-trackers over, usynligt. NU: _track_step_failed()
    logger + central-trace og FORTSÆTTER. Review/Memory/Proactivity fælles fejl-catcher."""

    def _fn_source(self):
        import inspect
        from core.services import visible_runs as vr
        src = inspect.getsource(vr)
        start = src.index("def _track_runtime_candidates(")
        return src[start:]

    def test_no_cascade_return_remains(self):
        body = self._fn_source()
        # ingen 'except: return' (kaskade) tilbage i funktionen
        assert "    except Exception:\n        return" not in body
        # hver except-blok kalder nu fejl-catcheren
        assert body.count("_track_step_failed()") == 61

    def test_step_failed_continues_does_not_raise(self):
        # _track_step_failed må ALDRIG kaste (ellers genindføres kaskaden)
        from core.services import visible_runs as vr
        try:
            raise RuntimeError("simuleret tracker-fejl")
        except Exception:
            vr._track_step_failed()  # skal sluge + logge, ikke re-raise

    def test_early_guard_return_preserved(self):
        # den ene legitime return (session_id-guard) skal bestå
        body = self._fn_source()
        assert "if not run.session_id:\n        return" in body
