"""Tests for agent_runtime — rene helpers + agents-cluster spawn-wiring.

Dækker coverage-gaten for agent_runtime og pinner at note_agent_spawn er
wired ind i spawn-stien (agents-cluster synlighed).
"""
from __future__ import annotations

from core.services import agent_runtime as ar


def test_trim_collapses_whitespace_and_limits():
    assert ar._trim("  a   b\n c ", limit=5) == "a b c"
    assert len(ar._trim("x" * 100, limit=10)) == 10


def test_parse_percent_confidence_buckets():
    assert ar._parse_percent_confidence("jeg er 90% sikker") == "high"
    assert ar._parse_percent_confidence("55% confidence here") == "medium"
    assert ar._parse_percent_confidence("kun 20% sikker") == "low"
    assert ar._parse_percent_confidence("ingen procent") == ""


def test_extract_vote_danish_and_english():
    assert ar._extract_vote("Vote: approve") == "approve"
    assert ar._extract_vote('jeg stemmer "nej"') == "reject"
    assert ar._extract_vote("vi bør udskyde") == "hold"
    assert ar._extract_vote("uklart") == ""


def test_spawn_depth_for_root_is_zero():
    assert ar._spawn_depth_for("") == 0
    assert ar._spawn_depth_for("jarvis") == 0


def test_spawn_wiring_imports_note_agent_spawn():
    # Agents-cluster: spawn-stien skal kunne importere observeren self-safe.
    from core.services.agents import note_agent_spawn
    assert callable(note_agent_spawn)


# ── Axis 3: agent tool execution (guarded flag) ────────────────────────────


def test_agent_tools_flag_defaults_off(monkeypatch):
    # Force any runtime-state read to raise → self-safe default must be off.
    def _boom(*a, **k):
        raise RuntimeError("db down")
    monkeypatch.setattr(
        "core.runtime.db_core.get_runtime_state_value", _boom, raising=False
    )
    assert ar.agent_tools_enabled() is False


def test_agent_tools_flag_reads_runtime_state(monkeypatch):
    store: dict[str, object] = {}
    monkeypatch.setattr(
        "core.runtime.db_core.get_runtime_state_value",
        lambda key, default=None: store.get(key, default),
        raising=False,
    )
    monkeypatch.setattr(
        "core.runtime.db_core.set_runtime_state_value",
        lambda key, value, **k: store.__setitem__(key, value),
        raising=False,
    )
    assert ar.agent_tools_enabled() is False
    # Fase 2 Task 3: enabling is owner-gated — a non-owner call is a no-op.
    assert ar.set_agent_tools_enabled(True) is False
    assert ar.agent_tools_enabled() is False
    assert ar.set_agent_tools_enabled(True, role="owner") is True
    assert ar.agent_tools_enabled() is True
    ar.set_agent_tools_enabled(False)
    assert ar.agent_tools_enabled() is False


def test_agent_tools_flag_string_off_reads_false(monkeypatch):
    # Regression (2026-07-14): dispatch stod reelt TÆNDT fordi flaget var lagret
    # som strengen "off" og læst med bool("off") == True. get_runtime_state_bool
    # skal coerce det til False.
    store: dict[str, object] = {"agent_tools_enabled": "off"}
    monkeypatch.setattr(
        "core.runtime.db_core.get_runtime_state_value",
        lambda key, default=None: store.get(key, default),
        raising=False,
    )
    assert ar.agent_tools_enabled() is False
    store["agent_tools_enabled"] = "on"
    assert ar.agent_tools_enabled() is True


def test_build_agent_tools_payload_filters_to_allowlist(monkeypatch):
    catalog = [
        {"type": "function", "function": {"name": "read_file"}},
        {"type": "function", "function": {"name": "search_files"}},
        {"type": "function", "function": {"name": "delete_everything"}},
    ]
    monkeypatch.setattr(
        "core.tools.simple_tools.get_tool_definitions", lambda: catalog, raising=False
    )
    out = ar._build_agent_tools_payload(["read_file", "search_files"])
    names = {t["function"]["name"] for t in out}
    assert names == {"read_file", "search_files"}
    # Empty allowlist → no tools exposed (text-only).
    assert ar._build_agent_tools_payload([]) == []
    assert ar._build_agent_tools_payload(None) == []


def test_build_agent_tools_payload_self_safe_on_error(monkeypatch):
    def _boom():
        raise RuntimeError("catalog broken")
    monkeypatch.setattr(
        "core.tools.simple_tools.get_tool_definitions", _boom, raising=False
    )
    assert ar._build_agent_tools_payload(["read_file"]) == []


def test_execute_agent_tool_call_routes_through_execute_tool(monkeypatch):
    calls: list[tuple[str, dict]] = []

    def _fake_execute(name, arguments):
        calls.append((name, arguments))
        return {"status": "ok", "echo": arguments}

    monkeypatch.setattr(
        "core.tools.simple_tools.execute_tool", _fake_execute, raising=False
    )
    tc = {
        "id": "call_1",
        "function": {"name": "read_file", "arguments": '{"path": "a.txt"}'},
    }
    out = ar._execute_agent_tool_call(tc, agent_id="agent-x")
    assert calls == [("read_file", {"path": "a.txt"})]
    assert '"status": "ok"' in out


def test_execute_agent_tool_call_self_safe(monkeypatch):
    def _boom(name, arguments):
        raise RuntimeError("tool exploded")
    monkeypatch.setattr(
        "core.tools.simple_tools.execute_tool", _boom, raising=False
    )
    out = ar._execute_agent_tool_call(
        {"id": "c", "function": {"name": "x", "arguments": "{}"}}, agent_id="a"
    )
    assert "error" in out
    # Missing name → structured error, never raises.
    out2 = ar._execute_agent_tool_call({"function": {}}, agent_id="a")
    assert "error" in out2


def test_run_agent_tool_loop_executes_and_stops(monkeypatch):
    # Model asks for a tool once, then returns final text.
    responses = [
        {"text": "", "tool_calls": [
            {"id": "c1", "function": {"name": "read_file", "arguments": "{}"}},
        ], "input_tokens": 5, "output_tokens": 2, "cost_usd": 0.0},
        {"text": "done", "tool_calls": [], "input_tokens": 3, "output_tokens": 4, "cost_usd": 0.0},
    ]

    def _fake_role(**kwargs):
        return responses.pop(0)

    monkeypatch.setattr(ar, "execute_with_role_or_fallback", _fake_role)
    monkeypatch.setattr(
        ar, "_build_agent_tools_payload",
        lambda allowed: [{"type": "function", "function": {"name": "read_file"}}],
    )
    monkeypatch.setattr(
        "core.tools.simple_tools.execute_tool",
        lambda name, arguments: {"status": "ok"}, raising=False,
    )
    agent = {"agent_id": "a", "provider": "deepseek", "model": "x",
             "allowed_tools_json": '["read_file"]'}
    result = ar._run_agent_tool_loop(agent=agent, prompt="go", requires_tools=True)
    assert result["text"] == "done"
    assert result["tool_rounds"] == 2
    assert result["execution_mode"] == "role-primary-tool-loop"


def test_run_agent_tool_loop_no_tools_falls_back_to_text(monkeypatch):
    monkeypatch.setattr(ar, "_build_agent_tools_payload", lambda allowed: [])
    seen: dict[str, object] = {}

    def _fake_role(**kwargs):
        seen.update(kwargs)
        return {"text": "plain", "tool_calls": []}

    monkeypatch.setattr(ar, "execute_with_role_or_fallback", _fake_role)
    agent = {"agent_id": "a", "provider": "p", "model": "m", "allowed_tools_json": "[]"}
    result = ar._run_agent_tool_loop(agent=agent, prompt="hi", requires_tools=False)
    assert result["text"] == "plain"
    # Fell back to the text-only signature (message=, no tools=).
    assert seen.get("message") == "hi"
    assert "tools" not in seen


# ── Axis 5: council/swarm lifecycle + landing ──────────────────────────────


def test_derive_initiative_prefers_action_sentence():
    synth = "The system is stable. We recommend migrating the cache next."
    assert ar._derive_initiative(synth) == "We recommend migrating the cache next."


def test_derive_initiative_falls_back_to_first_sentence():
    synth = "The core tension is between autonomy and safety here."
    assert ar._derive_initiative(synth).startswith("The core tension")


def test_derive_initiative_empty_is_empty_string():
    assert ar._derive_initiative("") == ""
    assert ar._derive_initiative("   ") == ""
    # Never returns None → truthiness check is safe.
    assert ar._derive_initiative(None) == ""


def test_run_council_round_always_closes_even_on_exception(monkeypatch):
    closed: list[str] = []
    monkeypatch.setattr(
        ar, "_close_council_agents", lambda cid: closed.append(cid)
    )

    def _boom(council_id, *, mode):
        raise RuntimeError("deliberation failed")

    monkeypatch.setattr(ar, "_run_collective_round", _boom)
    import pytest as _pytest
    with _pytest.raises(RuntimeError):
        ar.run_council_round("council-1")
    # try/finally guarantees the close ran despite the exception.
    assert closed == ["council-1"]


def test_run_swarm_round_always_closes_even_on_exception(monkeypatch):
    closed: list[str] = []
    monkeypatch.setattr(
        ar, "_close_council_agents", lambda cid: closed.append(cid)
    )
    monkeypatch.setattr(
        ar, "_run_collective_round",
        lambda council_id, *, mode: (_ for _ in ()).throw(RuntimeError("x")),
    )
    import pytest as _pytest
    with _pytest.raises(RuntimeError):
        ar.run_swarm_round("council-2")
    assert closed == ["council-2"]


def test_augment_council_surface_stamps_contract_fields(monkeypatch):
    monkeypatch.setattr(
        ar, "build_council_detail_surface", lambda cid: {"council_id": cid}
    )
    out = ar._augment_council_surface("c9", conclusion="C", initiative="I")
    assert out["council_id"] == "c9"
    assert out["conclusion"] == "C"
    assert out["initiative"] == "I"
    # initiative is always a string, never None.
    out2 = ar._augment_council_surface("c9", conclusion="C")
    assert out2["initiative"] == ""


# ── maxTurns per subagent ──────────────────────────────────────────────────


def test_check_max_turns_and_expire_noop_when_no_limit():
    """max_turns=0 means unlimited — never expires."""
    result = ar._check_max_turns_and_expire("no-such-agent")
    assert result is False


def test_check_max_turns_and_expire_noop_when_below_limit(isolated_runtime):
    agent_id = "agent-maxturns-ok"
    ar.create_agent_registry_entry(agent_id=agent_id, role="researcher", goal="test")
    # turns_completed=0, max_turns=5 → below limit
    ar.update_agent_registry_entry(agent_id, max_turns=5)
    assert ar._check_max_turns_and_expire(agent_id) is False
    entry = ar.get_agent_registry_entry(agent_id)
    assert entry is not None
    assert entry["status"] != "expired"


def test_check_max_turns_and_expire_expires_when_limit_reached(isolated_runtime):
    agent_id = "agent-maxturns-limit"
    ar.create_agent_registry_entry(agent_id=agent_id, role="researcher", goal="test")
    ar.update_agent_registry_entry(agent_id, max_turns=3, turns_completed_delta=3)
    assert ar._check_max_turns_and_expire(agent_id) is True
    entry = ar.get_agent_registry_entry(agent_id)
    assert entry is not None
    assert entry["status"] == "expired"
    assert "max_turns" in entry["last_error"]


def test_check_max_turns_and_expire_expires_when_over_limit(isolated_runtime):
    """turns_completed > max_turns should also trigger expiry."""
    agent_id = "agent-maxturns-over"
    ar.create_agent_registry_entry(agent_id=agent_id, role="researcher", goal="test")
    ar.update_agent_registry_entry(agent_id, max_turns=2, turns_completed_delta=5)
    assert ar._check_max_turns_and_expire(agent_id) is True
    entry = ar.get_agent_registry_entry(agent_id)
    assert entry is not None
    assert entry["status"] == "expired"


def test_execute_agent_task_skips_when_max_turns_exhausted(isolated_runtime, monkeypatch):
    """execute_agent_task should return immediately without calling the model
    when max_turns is already reached."""
    agent_id = "agent-maxskips"
    ar.create_agent_registry_entry(agent_id=agent_id, role="researcher", goal="test")
    ar.update_agent_registry_entry(agent_id, max_turns=1, turns_completed_delta=1)
    # If execute_agent_task called the model, this would fail. It should instead
    # detect max_turns exhausted and return early.
    def _boom(*a, **k):
        raise RuntimeError("model should not be called")
    monkeypatch.setattr(ar, "execute_with_role_or_fallback", _boom)
    result = ar.execute_agent_task(agent_id=agent_id)
    assert result.get("status") == "completed" or result.get("note") == "max_turns exhausted"
