"""Tests for dispatch_code_mode_task tool-wrapper (§19 live agent-dispatch)."""
from __future__ import annotations


def test_missing_task_errors() -> None:
    from core.tools.agent_dispatch_tool import _exec_dispatch_code_mode_task
    r = _exec_dispatch_code_mode_task({})
    assert r["status"] == "error"


def test_plan_only_default_no_spawn() -> None:
    # Uden execute=true må intet spawnes (dry_run). Tving dispatch-sti.
    from core.tools.agent_dispatch_tool import _exec_dispatch_code_mode_task
    r = _exec_dispatch_code_mode_task({"task": "byg en stor multi-fil feature", "inline": False})
    assert r.get("ok") is True
    # dispatch-mode → plan til stede, intet spawnet (dry_run)
    if r.get("mode") == "dispatch":
        assert r.get("dry_run") is True
        assert r.get("spawned") == []


def test_executor_count_clamped() -> None:
    from core.tools.agent_dispatch_tool import _exec_dispatch_code_mode_task
    r = _exec_dispatch_code_mode_task({"task": "x", "inline": False, "executor_count": 99})
    # clamp til ≤4 — planen (hvis dispatch) må ikke have >4 executor-roller
    if r.get("mode") == "dispatch":
        execs = [s for s in r.get("plan", []) if s.get("role") == "executor"]
        assert len(execs) <= 4


def test_tool_registered_in_executors() -> None:
    from core.tools.simple_tools import _TOOL_HANDLERS
    assert "dispatch_code_mode_task" in _TOOL_HANDLERS


def test_tool_in_definitions() -> None:
    from core.tools.agent_dispatch_tool import AGENT_DISPATCH_TOOL_DEFINITIONS
    names = {d["name"] for d in AGENT_DISPATCH_TOOL_DEFINITIONS}
    assert "dispatch_code_mode_task" in names
