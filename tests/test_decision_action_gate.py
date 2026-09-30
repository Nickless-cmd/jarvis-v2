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


def test_real_user_corrections_are_not_lost_to_narrow_phrasing():
    assert gate.opportunities("Tænkte linjen står stadig under tool result linjen") == {"quote"}
    assert gate.opportunities("Deepseek apien kan osse vise miss cache hits og cache hits") == {"quote"}
    assert gate.opportunities("Nu cachen: der er noget at rette op i Jarvis' analyse; årsagen er vendt om") == {"quote", "admit"}
    assert gate.opportunities("Claude: Begge kodepåstande holder. Nu tallene — den ene ting der ikke går op.") == {"quote"}
    with_image = (
        "[The user attached image(s) to this message. You CAN see images by using the analyze_image tool.]\n\n"
        "To see the image 'example.jpeg', call:\n  analyze_image(image_path='/uploads/"
        + "x" * 550 + "/example.jpeg')\n\n---\n\n"
        "Tænkte linjen står stadig under tool result linjen"
    )
    assert gate.opportunities(with_image) == {"quote"}


def test_claude_admitting_his_own_error_is_not_jarvis_error():
    assert gate.opportunities("Opus her. Din korrektion af mit tal er rigtig, og den står. MIN FEJL, fuldt ud.") == set()
    assert gate.opportunities("Opus. Du har ret, og jeg tog fejl.") == set()


def test_memory_opportunity_covers_history_and_repo_questions():
    assert "memory" in gate.opportunities("Hvad aftalte vi sidst om cache?")
    assert "memory" in gate.opportunities("Hvad står der i repoets config?")
    assert "memory" not in gate.opportunities("Hvad er klokken?")
    assert "memory" not in gate.opportunities("Kan du fikse affect-gaten hurtigt og commit?")


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


def test_quote_evidence_uses_the_correction_in_long_message():
    message = (
        "APK'en bygger i baggrunden. " + "Jeg tjekker cache og status. " * 18
        + "Jarvis' analyse: årsagen er vendt om."
    )
    result = gate.evaluate_turn(
        user_message=message,
        answer_text="APK'en bygger i baggrunden, så jeg venter lidt.",
        memory_recalled=False,
        tool_names=[],
    )
    assert result["quote"] == "unconfirmed"


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
    assert summary["quote"] == {"opportunities": 1, "kept": 1, "unconfirmed": 0, "pending": 0}
    assert summary["admit"] == {"opportunities": 1, "kept": 1, "unconfirmed": 0, "pending": 0}
    assert summary["memory"] == {"opportunities": 1, "kept": 1, "unconfirmed": 0, "pending": 0}


def test_pending_outcome_is_not_counted_as_unconfirmed(monkeypatch, tmp_path):
    _database(monkeypatch, tmp_path)
    gate.record_opportunities("run-open", "Hvad aftalte vi sidst?", memory_recalled=True)
    assert gate.opportunity_summary(days=1)["memory"] == {
        "opportunities": 1, "kept": 0, "unconfirmed": 0, "pending": 1,
    }
