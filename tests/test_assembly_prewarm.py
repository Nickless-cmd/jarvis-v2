"""Tests for periodic assembly pre-warm (assembly_prewarm.py).

Verifies the kill-switch, the prewarm-active flag lifecycle, telemetry
suppression during prewarm, and self-safety on build failure.
"""
from __future__ import annotations

import core.services.assembly_prewarm as ap


def test_prewarm_active_flag_defaults_false():
    assert ap.is_prewarm_active() is False


def test_kill_switch_off_by_default(monkeypatch):
    # No runtime-state override → default OFF (shadow).
    monkeypatch.setattr(
        "core.runtime.db_core.get_runtime_state_value",
        lambda key, default=None: default,
    )
    assert ap.assembly_prewarm_enabled() is False


def test_kill_switch_reads_runtime_state(monkeypatch):
    monkeypatch.setattr(
        "core.runtime.db_core.get_runtime_state_value",
        lambda key, default=None: True if key == "assembly_prewarm_enabled" else default,
    )
    assert ap.assembly_prewarm_enabled() is True


def test_prewarm_once_sets_and_clears_flag(monkeypatch):
    seen = {}

    def _fake_build(**kwargs):
        seen["active_during_build"] = ap.is_prewarm_active()
        seen["session_id"] = kwargs.get("session_id")
        seen["provider"] = kwargs.get("provider")
        return object()

    monkeypatch.setattr(
        "core.services.prompt_contract.build_visible_chat_prompt_assembly", _fake_build
    )
    monkeypatch.setattr(ap, "_should_prewarm", lambda: True)   # test af flag, ikke event-gate
    elapsed = ap.prewarm_once()
    assert elapsed is not None and elapsed >= 0.0
    assert seen["active_during_build"] is True          # flag set during build
    assert ap.is_prewarm_active() is False              # cleared after
    assert seen["session_id"] == "__prewarm__"
    assert seen["provider"] == "deepseek"               # non-ollama → compact=False


def test_prewarm_once_self_safe_on_failure(monkeypatch):
    def _boom(**kwargs):
        raise RuntimeError("assembly exploded")

    monkeypatch.setattr(
        "core.services.prompt_contract.build_visible_chat_prompt_assembly", _boom
    )
    assert ap.prewarm_once() is None                    # swallowed, returns None
    assert ap.is_prewarm_active() is False              # flag cleared even on error


def test_observe_composition_suppressed_during_prewarm(monkeypatch):
    """observe_composition must no-op while a prewarm build is active."""
    import core.services.central_prompt_composer as cpc

    recorded = {"n": 0}
    monkeypatch.setattr(
        "core.services.central_private_observe.record_private",
        lambda *a, **k: recorded.__setitem__("n", recorded["n"] + 1),
    )

    # Not in prewarm → records.
    ap._local.prewarm_active = False
    cpc.observe_composition("samtale", sections_total=10, sections_included=8)
    assert recorded["n"] == 1

    # In prewarm → suppressed.
    ap._local.prewarm_active = True
    try:
        cpc.observe_composition("samtale", sections_total=10, sections_included=8)
    finally:
        ap._local.prewarm_active = False
    assert recorded["n"] == 1                            # unchanged — suppressed


def test_start_loop_is_idempotent(monkeypatch):
    monkeypatch.setattr(ap, "_loop_started", False)
    started_threads = []
    monkeypatch.setattr(
        ap.threading, "Thread",
        lambda *a, **k: type("T", (), {"start": lambda self: started_threads.append(1)})(),
    )
    assert ap.start_prewarm_loop() is True               # first start
    assert ap.start_prewarm_loop() is False              # already started
    assert len(started_threads) == 1


class TestEventDrivenPrewarmGate:
    """15. jul: event-drevet gate dræber 292M-tokens/13d-burnet. Warm KUN når det
    tilføjer værdi (aktiv bruger + kold cache + ikke nylig warmet)."""

    def _patch(self, monkeypatch, *, warm=None, real=None, activity=None):
        import core.services.assembly_prewarm as P
        monkeypatch.setattr(P, "_seconds_since_last_prewarm", lambda: warm)
        monkeypatch.setattr(P, "_seconds_since_last_real_deepseek_call", lambda: real)
        monkeypatch.setattr(P, "_seconds_since_last_user_activity", lambda: activity)
        monkeypatch.setattr(P, "_interval_s", lambda: 300.0)
        monkeypatch.setattr(P, "_skip_if_recent_s", lambda: 300.0)
        monkeypatch.setattr(P, "_idle_window_s", lambda: 900.0)
        return P

    def test_idle_no_activity_skips(self, monkeypatch):
        P = self._patch(monkeypatch, warm=None, real=None, activity=None)
        assert P._should_prewarm() is False

    def test_idle_stale_activity_skips(self, monkeypatch):
        P = self._patch(monkeypatch, warm=None, real=None, activity=1200.0)
        assert P._should_prewarm() is False

    def test_active_cold_cache_warms(self, monkeypatch):
        P = self._patch(monkeypatch, warm=None, real=None, activity=120.0)
        assert P._should_prewarm() is True

    def test_active_but_warm_cache_skips(self, monkeypatch):
        P = self._patch(monkeypatch, warm=None, real=60.0, activity=120.0)
        assert P._should_prewarm() is False

    def test_recently_warmed_throttles(self, monkeypatch):
        P = self._patch(monkeypatch, warm=100.0, real=None, activity=120.0)
        assert P._should_prewarm() is False
