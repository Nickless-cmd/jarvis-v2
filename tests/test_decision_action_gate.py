"""Current-turn behavioral commitments use observed opportunities."""
from __future__ import annotations

from core.services import decision_action_gate as gate


def _database(monkeypatch, tmp_path):
    import sqlite3

    path = tmp_path / "actions.sqlite"

    def connect():
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        return conn

    monkeypatch.setattr(gate, "connect", connect)


def test_correction_opportunity_is_specific():
    assert gate.opportunities("Nej, du misforstod det jeg skrev") == {"quote", "admit"}
    assert gate.opportunities("Nej det er okay") == set()
    assert gate.opportunities("Stop serveren nu") == {"quote"}


def test_memory_opportunity_covers_history_and_repo_questions():
    assert "memory" in gate.opportunities("Hvad aftalte vi sidst om cache?")
    assert "memory" in gate.opportunities("Hvad står der i repoets config?")
    assert "memory" not in gate.opportunities("Hvad er klokken?")


def test_correction_section_requires_quote_and_ownership_before_answer():
    section = gate.action_section("Du tog fejl om den fil", recall_text=None)
    assert "gengiv" in section.lower()
    assert "tag ansvar" in section.lower()
    assert "Du tog fejl om den fil" not in section


def test_summary_does_not_create_table_when_uninitialized(monkeypatch, tmp_path):
    _database(monkeypatch, tmp_path)
    assert gate.opportunity_summary() == {}


def test_memory_section_uses_current_turn_result_and_fallback():
    section = gate.action_section("Hvad aftalte vi sidst?", recall_text="Hukommelse: vi valgte A")
    assert "vi valgte A" in section
    fallback = gate.action_section("Hvad aftalte vi sidst?", recall_text=None)
    assert "recall" in fallback


def test_outcomes_count_verified_actions_and_keep_uncertain_separate():
    message = "Du tog fejl: vi aftalte at bruge DeepSeek i går"
    kept = gate.evaluate_turn(
        user_message=message,
        answer_text="Du skrev, at vi aftalte at bruge DeepSeek i går. Jeg tog fejl. Jeg retter det.",
        memory_recalled=False,
        tool_names=[],
    )
    assert kept["quote"] == "kept"
    assert kept["admit"] == "kept"
    uncertain = gate.evaluate_turn(
        user_message=message,
        answer_text="Jeg ser på det nu.", memory_recalled=False, tool_names=[],
    )
    assert uncertain["quote"] == "unconfirmed"
    assert uncertain["admit"] == "unconfirmed"


def test_memory_outcome_requires_actual_recall():
    message = "Hvad aftalte vi sidst?"
    assert gate.evaluate_turn(user_message=message, answer_text="A", memory_recalled=True, tool_names=[])["memory"] == "kept"
    assert gate.evaluate_turn(user_message=message, answer_text="A", memory_recalled=False, tool_names=["recall"])["memory"] == "kept"
    assert gate.evaluate_turn(user_message=message, answer_text="A", memory_recalled=False, tool_names=[])["memory"] == "unconfirmed"


def test_opportunities_are_durable_and_idempotent(monkeypatch, tmp_path):
    _database(monkeypatch, tmp_path)
    message = "Du tog fejl: vi aftalte at bruge DeepSeek i går"
    gate.record_opportunities("run-1", message, memory_recalled=True)
    gate.record_opportunities("run-1", message, memory_recalled=True)
    gate.record_outcomes(
        "run-1", message,
        "Du skrev, at vi aftalte at bruge DeepSeek i går. Jeg tog fejl.",
        tool_names=[],
    )
    gate.record_outcomes(
        "run-1", message,
        "Du skrev, at vi aftalte at bruge DeepSeek i går. Jeg tog fejl.",
        tool_names=[],
    )
    summary = gate.opportunity_summary(days=1)
    assert summary["quote"] == {"opportunities": 1, "kept": 1, "unconfirmed": 0}
    assert summary["admit"] == {"opportunities": 1, "kept": 1, "unconfirmed": 0}
    assert summary["memory"] == {"opportunities": 1, "kept": 1, "unconfirmed": 0}
