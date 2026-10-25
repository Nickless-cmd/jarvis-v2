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


# ---------------------------------------------------------------------------
# Adherence-helbred — den manglende læser (24/10-2026).
#
# `decision_breach_reader.health_report()` kunne svare på om forpligtelserne
# holdes, men havde NUL kaldere i drift. Dommen blev skrevet, scoren dannet,
# og ingen læste den — samme fejlform som `breach_stats` indtil 22/10.
# ---------------------------------------------------------------------------


def test_heartbeat_line_viser_svage_beslutninger(isolated_runtime, monkeypatch) -> None:
    """En svag beslutning skal nå heartbeat-prompten med id og årsag."""
    pc = isolated_runtime.prompt_contract
    dbr = importlib.import_module("core.services.decision_breach_reader")
    monkeypatch.setattr(
        dbr,
        "health_report",
        lambda *a, **k: {
            "total": 12,
            "weak": 1,
            "rows": [
                {"decision_id": "dec_aaaa1111bbbb", "weak": True,
                 "why_weak": "aldrig målt, men 3 brud i 7 dage"},
                {"decision_id": "dec_cccc2222dddd", "weak": False,
                 "why_weak": None},
            ],
        },
    )

    line = pc._heartbeat_living_context_line()

    assert "decision_health:" in line
    assert "dec_aaaa1111" in line
    assert "3 brud" in line
    # Den sunde beslutning må ikke støje i linjen.
    assert "dec_cccc2222" not in line


def test_heartbeat_line_er_tavs_naar_alt_er_sundt(isolated_runtime, monkeypatch) -> None:
    """Ingen svage beslutninger → ingen tom decision_health-linje."""
    pc = isolated_runtime.prompt_contract
    dbr = importlib.import_module("core.services.decision_breach_reader")
    monkeypatch.setattr(
        dbr,
        "health_report",
        lambda *a, **k: {"total": 12, "weak": 0, "rows": []},
    )

    line = pc._heartbeat_living_context_line()

    assert "decision_health:" not in line
