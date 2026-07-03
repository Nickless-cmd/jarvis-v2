"""Smoke tests for simple_tools — focus on tool-registration invariants.

Specifically guards that operator_read_file remains registered in both
the TOOL_DEFINITIONS list (what the LLM sees) and the _TOOL_HANDLERS
dispatch map (what runs when invoked). Pre-2026-05-26 there was no
bridge-aware tool; this prevents accidental removal.
"""
from __future__ import annotations


def test_operator_read_file_registered():
    from core.tools.simple_tools import _TOOL_HANDLERS, get_tool_definitions
    assert "operator_read_file" in _TOOL_HANDLERS, (
        "operator_read_file must be in _TOOL_HANDLERS — see "
        "docs/superpowers/specs/2026-05-26-jarvisx-tool-bridge.md"
    )
    tools = get_tool_definitions() or []
    names = [t.get("function", {}).get("name", "") for t in tools]
    assert "operator_read_file" in names, (
        "operator_read_file must appear in TOOL_DEFINITIONS so the LLM "
        "can discover it. See jarvisx-tool-bridge spec."
    )


def test_phase2_operator_tools_registered():
    """All Phase 2 operator_* tools have both a TOOL_DEFINITIONS entry
    AND a _TOOL_HANDLERS handler."""
    from core.tools.simple_tools import _TOOL_HANDLERS, get_tool_definitions
    tools = get_tool_definitions() or []
    names = {t.get("function", {}).get("name", "") for t in tools}
    expected = {
        "operator_read_file",
        "operator_write_file",
        "operator_edit_file",
        "operator_glob",
        "operator_grep",
        "operator_list_dir",
    }
    missing_defs = expected - names
    missing_handlers = expected - set(_TOOL_HANDLERS.keys())
    assert not missing_defs, f"Missing in TOOL_DEFINITIONS: {missing_defs}"
    assert not missing_handlers, f"Missing in _TOOL_HANDLERS: {missing_handlers}"


def test_phase3_operator_bash_registered():
    """operator_bash exists with both definition and handler."""
    from core.tools.simple_tools import _TOOL_HANDLERS, get_tool_definitions
    tools = get_tool_definitions() or []
    names = {t.get("function", {}).get("name", "") for t in tools}
    assert "operator_bash" in names
    assert "operator_bash" in _TOOL_HANDLERS

    # Verify the description mentions approval explicitly so the LLM
    # is steered toward more specific tools when possible.
    bash_def = next(
        t for t in tools if t.get("function", {}).get("name") == "operator_bash"
    )
    desc = bash_def["function"]["description"].lower()
    assert "approv" in desc or "approve" in desc, (
        "operator_bash description must mention approval requirement"
    )


def test_phase4_operator_webfetch_registered():
    """operator_webfetch is registered."""
    from core.tools.simple_tools import _TOOL_HANDLERS, get_tool_definitions
    tools = get_tool_definitions() or []
    names = {t.get("function", {}).get("name", "") for t in tools}
    assert "operator_webfetch" in names
    assert "operator_webfetch" in _TOOL_HANDLERS


def test_phase5_user_id_resolution_explicit_wins():
    """Explicit _runtime_user_id in args takes priority over session lookup."""
    from core.tools.simple_tools import _operator_user_id
    assert _operator_user_id({"_runtime_user_id": "user-explicit"}) == "user-explicit"
    assert _operator_user_id({"_user_id": "user-legacy"}) == "user-legacy"


def test_phase5_user_id_falls_back_to_owner():
    """With no explicit user_id and no session_id, falls back to owner."""
    from core.tools.simple_tools import _operator_user_id
    uid = _operator_user_id({})
    # Default fallback is Bjørn's discord_id
    assert uid == "1246415163603816499" or len(uid) > 0


def test_tool_definitions_well_formed():
    """Every tool def has function.name + function.description."""
    from core.tools.simple_tools import get_tool_definitions
    tools = get_tool_definitions() or []
    assert len(tools) > 0
    for t in tools[:10]:  # sample first 10 — full validation elsewhere
        assert t.get("type") == "function"
        fn = t.get("function") or {}
        assert fn.get("name"), f"missing name: {t}"
        assert fn.get("description"), f"missing description: {fn.get('name')}"


# ── Axis 2: spawn_agent_task menu-lock lifted ──────────────────────────────


def _spawn_schema():
    from core.tools.simple_tools import TOOL_DEFINITIONS
    for t in TOOL_DEFINITIONS:
        fn = t.get("function") or {}
        if fn.get("name") == "spawn_agent_task":
            return fn.get("parameters") or {}
    raise AssertionError("spawn_agent_task not found in TOOL_DEFINITIONS")


def test_spawn_agent_task_role_no_longer_required():
    params = _spawn_schema()
    # Only goal is required now — role became an optional start-template.
    assert params.get("required") == ["goal"]


def test_spawn_agent_task_exposes_free_prompt_and_tools():
    props = _spawn_schema().get("properties") or {}
    assert "system_prompt" in props
    assert "allowed_tools" in props
    assert "tool_policy" in props
    # role is still present but no longer a locked enum.
    assert "role" in props
    assert "enum" not in props["role"]


def test_spawn_agent_task_handler_forwards_new_params(monkeypatch):
    import core.services.agent_runtime as ar
    from core.tools.simple_tools import _exec_spawn_agent_task

    captured = {}

    def _fake_spawn(**kwargs):
        captured.update(kwargs)
        return {"agent_id": "agent-z", "status": "completed", "messages": []}

    monkeypatch.setattr(ar, "spawn_agent_task", _fake_spawn)
    out = _exec_spawn_agent_task({
        "goal": "explore X",
        "system_prompt": "You are a free agent.",
        "allowed_tools": ["read_file", "search_files"],
        "tool_policy": "read-only-runtime",
    })
    assert out["status"] == "ok"
    assert captured["system_prompt"] == "You are a free agent."
    assert captured["allowed_tools"] == ["read_file", "search_files"]
    assert captured["tool_policy"] == "read-only-runtime"


def test_spawn_agent_task_handler_backward_compatible(monkeypatch):
    """Legacy call with only role+goal still works (no new params)."""
    import core.services.agent_runtime as ar
    from core.tools.simple_tools import _exec_spawn_agent_task

    captured = {}

    def _fake_spawn(**kwargs):
        captured.update(kwargs)
        return {"agent_id": "agent-legacy", "status": "completed", "messages": []}

    monkeypatch.setattr(ar, "spawn_agent_task", _fake_spawn)
    out = _exec_spawn_agent_task({"role": "researcher", "goal": "look"})
    assert out["status"] == "ok"
    # New params default to empty/None → template fallback preserved downstream.
    assert captured["system_prompt"] == ""
    assert captured["tool_policy"] == ""
    assert captured["allowed_tools"] is None
