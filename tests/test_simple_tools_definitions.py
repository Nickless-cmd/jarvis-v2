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
