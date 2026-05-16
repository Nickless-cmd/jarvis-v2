"""Tests for user_contradiction_tracker — Bjørn→Jarvis contradiction detection."""
from __future__ import annotations

import importlib
import sys

import pytest


@pytest.fixture()
def clean_runtime_state(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("JARVIS_WORKSPACES_DIR", str(tmp_path / "workspaces"))
    import core.runtime.config as config
    import core.runtime.db as db
    import core.runtime.state_store as state_store

    importlib.reload(config)
    importlib.reload(db)
    importlib.reload(state_store)

    # Ryd test-data så tests ikke påvirker hinanden
    from core.runtime.db import connect
    try:
        with connect() as c:
            c.execute("DELETE FROM user_contradictions")
            c.execute("DELETE FROM user_statements")
            c.commit()
    except Exception:
        pass  # tabeller findes måske ikke endnu

    for module_name in (
        "core.services.user_contradiction_tracker",
    ):
        if module_name in sys.modules:
            importlib.reload(sys.modules[module_name])
    return None


def test_record_user_statement(clean_runtime_state):
    from core.services import user_contradiction_tracker as uct

    result = uct.record_user_statement(
        text="Jeg elsker kvantemekanik",
        topic="physics",
        session_id="test-session",
    )

    assert result["outcome"] == "recorded"
    assert result["topic"] == "physics"
    assert result["was_created"] is True
    assert result["statement_id"].startswith("user-statement-")


def test_record_duplicate_statement(clean_runtime_state):
    from core.services import user_contradiction_tracker as uct

    r1 = uct.record_user_statement(
        text="Jeg elsker fysik",
        topic="physics",
    )
    r2 = uct.record_user_statement(
        text="Jeg elsker fysik",
        topic="physics",
    )
    # Same text → should update, not create new
    assert r1["outcome"] == "recorded"
    assert r2["outcome"] == "recorded"


def test_skip_short_text(clean_runtime_state):
    from core.services import user_contradiction_tracker as uct

    result = uct.record_user_statement(
        text="hej",
        topic="greeting",
    )
    assert result["outcome"] == "skipped"
    assert result["reason"] == "text too short (min 5 chars)"


def test_check_contradiction_detects_semantic_conflict(clean_runtime_state):
    from core.services import user_contradiction_tracker as uct

    # Gem først en påstand
    uct.record_user_statement(text="Jeg tror på non-lokal bevidsthed", topic="consciousness")

    # Tjek en modsat påstand
    findings = uct.check_contradiction(
        text="Jeg tror ikke på non-lokal bevidsthed",
        topic="consciousness",
    )

    assert len(findings) >= 1
    assert "non" in str(findings[0].get("overlap_tokens"))
    assert findings[0].get("statement_a_text") is not None


def test_check_contradiction_same_polarity_no_conflict(clean_runtime_state):
    from core.services import user_contradiction_tracker as uct

    uct.record_user_statement(text="Jeg elsker kaffe", topic="beverage")

    # Samme polarity → ingen modsigelse
    findings = uct.check_contradiction(
        text="Jeg elsker også te",
        topic="beverage",
    )

    assert len(findings) == 0


def test_check_contradiction_different_topic_no_cross(clean_runtime_state):
    from core.services import user_contradiction_tracker as uct

    uct.record_user_statement(text="Jeg kan ikke lide Python", topic="programming")

    # Andet topic → tjekker inden for samme topic
    findings = uct.check_contradiction(
        text="Jeg kan lide Python",
        topic="food",
    )

    assert len(findings) == 0


def test_detect_and_store_contradiction_full_flow(clean_runtime_state):
    from core.services import user_contradiction_tracker as uct

    # Step 1: sig noget
    uct.record_user_statement(text="Quantum computing er fremtiden", topic="tech")

    # Step 2: sig det modsatte i én handling
    result = uct.detect_and_store_contradiction(
        text="Quantum computing er ikke fremtiden",
        topic="tech",
        session_id="session-contra-test",
        source="chat",
    )

    assert result["statement_recorded"] is True
    assert result["contradictions_found"] == 1
    assert result["contradictions"][0]["contradiction_id"].startswith("user-contradiction-")
    assert "quantum" in str(result["contradictions"][0]["overlap_tokens"]).lower()


def test_get_user_contradictions_returns_stored(clean_runtime_state):
    from core.services import user_contradiction_tracker as uct

    # Opret en modsigelse
    uct.record_user_statement(text="Jeg er tilhænger af fri vilje", topic="philosophy")
    uct.detect_and_store_contradiction(
        text="Jeg er ikke tilhænger af fri vilje",
        topic="philosophy",
    )

    contradictions = uct.get_user_contradictions(limit=10)

    assert len(contradictions) >= 1
    assert contradictions[0].get("statement_a_text") is not None
    assert contradictions[0].get("statement_b_text") is not None
    assert contradictions[0].get("topic") == "philosophy"


def test_surface_shows_contradictions(clean_runtime_state):
    from core.services import user_contradiction_tracker as uct

    # Tom surface først
    surface = uct.build_user_contradiction_surface()
    assert surface["active"] is False
    assert surface["summary"]["open_count"] == 0

    # Opret en modsigelse
    uct.record_user_statement(text="AI er farlig", topic="ai-safety")
    uct.detect_and_store_contradiction(
        text="AI er ikke farlig",
        topic="ai-safety",
    )

    surface = uct.build_user_contradiction_surface()
    assert surface["active"] is True
    assert surface["summary"]["open_count"] >= 1
    assert surface["mode"] == "user-contradiction-tracker"
    assert "prompt_attention" in surface["allowed_effects"]


def test_danish_negation_detection(clean_runtime_state):
    """Bekræft at danske negationer som 'ikke' og 'aldrig' virker."""
    from core.services import user_contradiction_tracker as uct

    uct.record_user_statement(text="Jeg kan lide regnvejr", topic="weather")

    findings = uct.check_contradiction(
        text="Jeg kan ikke lide regnvejr",
        topic="weather",
    )

    assert len(findings) >= 1
    assert "lide" in str(findings[0].get("overlap_tokens"))


def test_no_false_positive_on_unrelated_topics(clean_runtime_state):
    from core.services import user_contradiction_tracker as uct

    uct.record_user_statement(text="GPU er vigtig for gaming", topic="hardware")

    findings = uct.check_contradiction(
        text="GPU er ikke vigtig for AI",
        topic="hardware",
    )

    # 'gpu' og 'vigtig' overlapper, og negation er forskellig → bør fanges
    assert len(findings) >= 1  # overlap ≥2 + forskellig negation
