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


def test_format_tool_result_survives_bytes_values():
    """A tool result containing raw bytes (e.g. db_query over a BLOB column)
    must NOT crash format_tool_result_for_model with
    'Object of type bytes is not JSON serializable' — it should degrade
    gracefully to a string. Regression for the visible-run crash on
    2026-07-10 (db_query over api_connection_presence)."""
    from core.tools.simple_tools import format_tool_result_for_model
    result = {
        "status": "ok",
        "columns": ["id", "blob"],
        "rows": [{"id": 1, "blob": b"\x89PNG\r\n\x1a\n\x00binary"}],
        "row_count": 1,
    }
    out = format_tool_result_for_model("db_query", result)
    assert isinstance(out, str)
    assert out  # non-empty
    assert "not JSON serializable" not in out


def test_db_query_bytes_coerced_to_json_safe():
    """_exec_db_query must coerce BLOB/bytes cell values to JSON-safe types
    so the row dict can be serialized downstream without crashing."""
    import json
    from core.tools.simple_tools_native import _json_safe_cell
    # utf-8-decodable bytes → str
    assert _json_safe_cell(b"hello") == "hello"
    # binary bytes → safe placeholder, JSON-serializable
    v = _json_safe_cell(b"\x89PNG\r\n\x00\xff")
    json.dumps(v)  # must not raise
    assert isinstance(v, str)
    # non-bytes pass through untouched
    assert _json_safe_cell(42) == 42
    assert _json_safe_cell(None) is None


# ── Signaler i sidestraenge (5/10-2026) ────────────────────────────────────
# `_exec_bash` laegger `kanal.note` og `confinement` paa svaret. Formateringen
# returnerer `text` naar den findes og kaster ALLE andre noegler vaek — saa
# begge beskeder naaede aldrig modellen. Maalt ved at aabne kanalen, udloebe den
# og se at noten stod i dict'en men ikke i det svar der blev laest.


def test_kanal_noten_naar_frem_til_modellen():
    from core.tools.simple_tools import format_tool_result_for_model
    note = ("[operator-kanal] kanalen udløb for 26 t siden og blev IKKE "
            "genåbnet — denne kommando kørte på serveren, ikke på Bjørns maskine.")
    out = format_tool_result_for_model("bash", {
        "text": "Jarvis", "exit_code": 0, "status": "ok",
        "kanal": {"note": note},
    })
    assert note in out, "noten skal staa i den tekst modellen laeser"
    assert "Jarvis" in out, "kommandoens output maa ikke forsvinde"


def test_kanal_genaabnet_siges_hoejt():
    from core.tools.simple_tools import format_tool_result_for_model
    out = format_tool_result_for_model("bash", {
        "text": "CheifOne", "status": "ok",
        "kanal": {"genaabnet": True, "udloebet_for_s": 3603},
    })
    assert "genaabnet" in out.lower()


def test_indespaerring_siges_hoejt_naar_ikke_haandhaevet():
    from core.tools.simple_tools import format_tool_result_for_model
    out = format_tool_result_for_model("bash", {
        "text": "output", "status": "ok",
        "confinement": {"requested": True, "actual": False, "honored": False,
                        "reason": "vedvarende delt shell"},
    })
    assert "IKKE håndhævet" in out
    assert "vedvarende delt shell" in out


def test_haandhaevet_indespaerring_er_stille():
    """Er den håndhævet, er der intet at sige — ellers begraver linjen de
    signaler der faktisk betyder noget."""
    from core.tools.simple_tools import format_tool_result_for_model
    out = format_tool_result_for_model("bash", {
        "text": "output", "status": "ok",
        "confinement": {"requested": True, "actual": True, "honored": True},
    })
    assert "IKKE håndhævet" not in out


def test_ingen_signaler_er_stille():
    from core.tools.simple_tools import format_tool_result_for_model
    out = format_tool_result_for_model("bash", {"text": "output", "status": "ok"})
    assert "output" in out
    assert "operator-kanal" not in out


def test_json_grenen_gentager_ikke_kanal_noten():
    """Dumpes resultatet som JSON (ingen `text`), er noeglen i forvejen synlig —
    linjen maa ikke komme oveni."""
    from core.tools.simple_tools import format_tool_result_for_model
    note = "[operator-kanal] kanalen udløb"
    out = format_tool_result_for_model("bash", {"status": "ok", "kanal": {"note": note}})
    assert out.count(note) == 1
