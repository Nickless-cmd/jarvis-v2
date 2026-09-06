"""Tests for core.tools.simple_tools_definitions — tool-schema-integritet.

Fokus: master-listen TOOL_DEFINITIONS er velformet, og det klient-lokale
`task`/explore-subagent-schema (Path B) er til stede og korrekt formet, så
serveren kan annoncere det til modellen i jarvis-code.
"""
from __future__ import annotations

from core.tools.simple_tools_definitions import TOOL_DEFINITIONS


def _by_name() -> dict[str, dict]:
    out: dict[str, dict] = {}
    for d in TOOL_DEFINITIONS:
        fn = (d.get("function") or {})
        name = fn.get("name")
        if name:
            out[str(name)] = d
    return out


class TestSchemaIntegrity:
    def test_function_defs_are_well_formed(self):
        # Alle function-typede entries skal have et navn + parameters-objekt.
        for d in TOOL_DEFINITIONS:
            if d.get("type") != "function":
                continue
            fn = d.get("function") or {}
            assert isinstance(fn.get("name"), str) and fn["name"], d
            assert isinstance(fn.get("parameters"), dict)


class TestTaskSubagentSchema:
    """`task` = nested subagent / explore, forwardet klient-lokalt i Path B."""

    def test_task_definition_present(self):
        assert "task" in _by_name(), "task-schema mangler → jarvis-code får intet explore-tool"

    def test_task_schema_shape(self):
        fn = _by_name()["task"]["function"]
        params = fn["parameters"]
        props = params.get("properties") or {}
        # Matcher klientens jarvis-code/src/tools.py-kontrakt
        assert set(params.get("required") or []) == {"description", "prompt"}
        for key in ("description", "prompt", "subagent_type"):
            assert key in props, f"task-param {key!r} mangler"
        assert "subagent" in fn["description"].lower()


# ── Ensretning af det flettede array (6/9-2026) ──────────────────────────

def test_alle_definitioner_er_openai_formede():
    """Fire dispatch-vaerktoejer lå i Anthropic-format og var ukaldbare."""
    from core.tools.simple_tools_definitions import TOOL_DEFINITIONS
    forkerte = [t for t in TOOL_DEFINITIONS if t.get("type") != "function"
                or not (t.get("function") or {}).get("name")]
    assert forkerte == [], forkerte[:3]


def test_ingen_dublerede_vaerktoejsnavne():
    """To definitioner af samme navn = to sandheder; provideren vaelger."""
    from collections import Counter
    from core.tools.simple_tools_definitions import TOOL_DEFINITIONS
    navne = [(t.get("function") or {}).get("name") for t in TOOL_DEFINITIONS]
    dubletter = [n for n, c in Counter(navne).items() if c > 1]
    assert dubletter == [], dubletter


def test_dispatch_vaerktoejerne_kan_naas():
    from core.tools.simple_tools_definitions import TOOL_DEFINITIONS
    navne = {(t.get("function") or {}).get("name") for t in TOOL_DEFINITIONS}
    for n in ("dispatch_to_claude_code", "dispatch_status", "dispatch_cancel",
              "dispatch_code_mode_task"):
        assert n in navne, n


def test_anthropic_form_oversaettes_med_skema():
    from core.tools.simple_tools_definitions import _til_openai_form
    ud = _til_openai_form({
        "name": "x", "description": "d",
        "input_schema": {"type": "object", "properties": {"a": {"type": "string"}}},
    })
    assert ud["type"] == "function"
    assert ud["function"]["name"] == "x"
    assert ud["function"]["parameters"]["properties"]["a"]["type"] == "string"


def test_dedup_beholder_den_sidste():
    """Handlere registreres sidst-vinder; definitionen skal matche."""
    from core.tools.simple_tools_definitions import _ensret_tool_definitions
    ud = _ensret_tool_definitions([
        {"type": "function", "function": {"name": "g", "description": "gammel"}},
        {"type": "function", "function": {"name": "g", "description": "ny"}},
    ])
    assert len(ud) == 1
    assert ud[0]["function"]["description"] == "ny"
