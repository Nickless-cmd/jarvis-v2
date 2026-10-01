"""Tests for heartbeat_sections — prompt-linjer i heartbeat-cyklussen.

Fase 2 af lærings-sløjfen (2026-10-01): ventende automations-forslag skal nå
heartbeat-prompten med deres id, så de kan lukkes (accept/reject). Forslagene
blev skrevet i 5½ måned uden en læser — denne fil pinner at koblingen findes.

Ligger her (og ikke i test_prompt_contract_capability_rules.py) fordi
test-coverage-vagten kræver tests/test_heartbeat_sections.py for
core/services/prompt_sections/heartbeat_sections.py.
"""
from __future__ import annotations

import importlib


def test_heartbeat_line_injicerer_pending_suggestions(isolated_runtime, monkeypatch) -> None:
    """Ventende forslag skal nå prompten — med id, så de kan lukkes."""
    pc = isolated_runtime.prompt_contract
    hp = importlib.import_module("core.services.habits_pipeline")
    monkeypatch.setattr(
        hp,
        "format_pending_suggestions_for_heartbeat",
        lambda **_: "[as_test] «ryd op i rodet» ×8",
    )

    line = pc._heartbeat_living_context_line()

    assert "pending_suggestions:" in line
    assert "as_test" in line


def test_heartbeat_line_udelader_pending_suggestions_naar_tom(isolated_runtime, monkeypatch) -> None:
    """Ingen forslag → ingen tom 'pending_suggestions:'-linje i prompten."""
    pc = isolated_runtime.prompt_contract
    hp = importlib.import_module("core.services.habits_pipeline")
    monkeypatch.setattr(hp, "format_pending_suggestions_for_heartbeat", lambda **_: "")

    line = pc._heartbeat_living_context_line()

    assert "pending_suggestions:" not in line
