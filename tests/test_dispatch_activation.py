"""Fase 2 Task 3 — activate server dispatch: owner-gated flag flip, strictest-
mode inheritance (never-escalate ceiling), and sibling context isolation.

Does NOT rebuild the dispatch machinery (agent_runtime_base/spawn/council) —
only guards the flag flip and the tool-ceiling intersection on top of it.
The flag stays default OFF in committed code; activation is a runtime
`set_agent_tools_enabled(True, role="owner")` toggle, never a code default.
"""
from __future__ import annotations

import importlib
import json


def _load_agent_runtime():
    module = importlib.import_module("core.services.agent_runtime")
    return importlib.reload(module)


def test_flag_defaults_off(isolated_runtime):
    ar = _load_agent_runtime()
    assert ar.agent_tools_enabled() is False


def test_non_owner_cannot_enable(isolated_runtime):
    ar = _load_agent_runtime()
    assert ar.set_agent_tools_enabled(True, role="user") is False
    assert ar.agent_tools_enabled() is False
    assert ar.set_agent_tools_enabled(True) is False  # default role="" also denied
    assert ar.agent_tools_enabled() is False


def test_owner_can_enable_and_disable(isolated_runtime):
    ar = _load_agent_runtime()
    assert ar.set_agent_tools_enabled(True, role="owner") is True
    assert ar.agent_tools_enabled() is True
    assert ar.set_agent_tools_enabled(False, role="owner") is False
    assert ar.agent_tools_enabled() is False
    # Disabling never needs the gate — de-escalation is always allowed.
    ar.set_agent_tools_enabled(True, role="owner")
    assert ar.set_agent_tools_enabled(False) is False
    assert ar.agent_tools_enabled() is False


def test_child_tools_intersect_parent_ceiling(isolated_runtime):
    ar = _load_agent_runtime()
    from core.runtime.db_agent_runtime import create_agent_registry_entry

    parent = create_agent_registry_entry(
        agent_id="agent-parent-1",
        role="researcher",
        goal="parent goal",
        allowed_tools_json=json.dumps(["read_file"]),
    )
    child = ar.spawn_agent_task(
        role="researcher",
        goal="child goal",
        allowed_tools=["read_file", "bash"],
        parent_agent_id=parent["agent_id"],
        auto_execute=False,
    )
    persisted = json.loads(str(child.get("allowed_tools_json") or "[]"))
    assert persisted == ["read_file"]
    assert "bash" not in persisted


def test_root_parent_has_no_ceiling(isolated_runtime):
    ar = _load_agent_runtime()
    child = ar.spawn_agent_task(
        role="researcher",
        goal="child of root",
        allowed_tools=["bash"],
        parent_agent_id="jarvis",
        auto_execute=False,
    )
    persisted = json.loads(str(child.get("allowed_tools_json") or "[]"))
    assert persisted == ["bash"]


def test_child_ceiling_intersects_even_with_empty_parent_request(isolated_runtime):
    """A parent with a non-empty allowlist that shares NOTHING with the
    request yields an empty child allowlist (text-only), not an error."""
    ar = _load_agent_runtime()
    from core.runtime.db_agent_runtime import create_agent_registry_entry

    parent = create_agent_registry_entry(
        agent_id="agent-parent-2",
        role="researcher",
        goal="parent goal",
        allowed_tools_json=json.dumps(["read_file"]),
    )
    child = ar.spawn_agent_task(
        role="researcher",
        goal="child goal",
        allowed_tools=["bash", "write_file"],
        parent_agent_id=parent["agent_id"],
        auto_execute=False,
    )
    persisted = json.loads(str(child.get("allowed_tools_json") or "[]"))
    assert persisted == []


def test_sibling_agents_context_isolated(isolated_runtime):
    ar = _load_agent_runtime()
    from core.runtime.db_agent_runtime import list_agent_messages

    a1 = ar.spawn_agent_task(
        role="researcher", goal="investigate topic A — secret alpha",
        parent_agent_id="jarvis", auto_execute=False,
    )
    a2 = ar.spawn_agent_task(
        role="researcher", goal="investigate topic B — secret beta",
        parent_agent_id="jarvis", auto_execute=False,
    )
    assert a1["agent_id"] != a2["agent_id"]
    ctx1 = json.loads(str(a1.get("context_json") or "{}"))
    ctx2 = json.loads(str(a2.get("context_json") or "{}"))
    assert "beta" not in json.dumps(ctx1)
    assert "alpha" not in json.dumps(ctx2)
    assert a1["goal"] != a2["goal"]
    assert "beta" not in a1["goal"]
    assert "alpha" not in a2["goal"]

    # Each spawn writes its OWN thread of task-brief/system-prompt messages
    # (agent_runtime_spawn.spawn_agent_task, unchanged by this task) — assert
    # they are actually disjoint per-agent, not just per-field on the
    # registry row (the isolation the plan's acceptance criterion cares about).
    msgs1 = list_agent_messages(agent_id=str(a1["agent_id"]))
    msgs2 = list_agent_messages(agent_id=str(a2["agent_id"]))
    assert msgs1 and msgs2
    blob1 = json.dumps(msgs1)
    blob2 = json.dumps(msgs2)
    assert "beta" not in blob1
    assert "alpha" not in blob2


def test_build_payload_respects_ceiling(isolated_runtime, monkeypatch):
    ar = _load_agent_runtime()
    catalog = [
        {"type": "function", "function": {"name": "read_file"}},
        {"type": "function", "function": {"name": "bash"}},
    ]
    monkeypatch.setattr(
        "core.tools.simple_tools.get_tool_definitions", lambda: catalog, raising=False
    )
    out = ar._build_agent_tools_payload(["read_file", "bash"], ceiling=["read_file"])
    names = {t["function"]["name"] for t in out}
    assert names == {"read_file"}


def test_build_payload_no_ceiling_is_unrestricted(isolated_runtime, monkeypatch):
    ar = _load_agent_runtime()
    catalog = [
        {"type": "function", "function": {"name": "read_file"}},
        {"type": "function", "function": {"name": "bash"}},
    ]
    monkeypatch.setattr(
        "core.tools.simple_tools.get_tool_definitions", lambda: catalog, raising=False
    )
    out = ar._build_agent_tools_payload(["read_file", "bash"], ceiling=None)
    names = {t["function"]["name"] for t in out}
    assert names == {"read_file", "bash"}
