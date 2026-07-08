"""Tests for theory_of_mind.py (Step A.v1).

Communication ledger: track facts told to / stated by partner.
Detect repetition. Provide awareness surface when Jarvis repeats himself.
"""
import sqlite3
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def tmp_db(monkeypatch):
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    path = Path(tmp.name)
    import core.services.theory_of_mind as mod
    monkeypatch.setattr(mod, "DB_PATH", path)
    yield path
    path.unlink(missing_ok=True)


# ── Normalization ────────────────────────────────────────────────────────


def test_normalize_to_key_collapses_word_order():
    """Order-insensitive dedupe — same content words → same key."""
    from core.services.theory_of_mind import _normalize_to_key
    a = _normalize_to_key("Cache hit ratio er 38 procent på flash modellen")
    b = _normalize_to_key("På flash modellen er cache hit ratio 38 procent")
    assert a == b
    assert a != ""


def test_normalize_to_key_strips_punctuation():
    from core.services.theory_of_mind import _normalize_to_key
    a = _normalize_to_key("Cache er 38 procent.")
    b = _normalize_to_key("Cache er 38 procent")
    assert a == b


def test_normalize_to_key_empty_for_trivial():
    from core.services.theory_of_mind import _normalize_to_key
    assert _normalize_to_key("") == ""
    assert _normalize_to_key("og det er") == ""  # all stopwords


# ── Factual sentence extraction ──────────────────────────────────────────


def test_extract_factual_sentences():
    from core.services.theory_of_mind import _split_factual_sentences
    text = (
        "Hej! Hvordan har du det? "
        "Cache kører på 38 procent. "
        "Modellen virker fint nu."
    )
    sents = _split_factual_sentences(text)
    # Greeting + question dropped, two claims kept
    assert len(sents) == 2
    assert any("Cache" in s for s in sents)
    assert any("Modellen" in s for s in sents)


def test_extract_skips_questions():
    from core.services.theory_of_mind import _split_factual_sentences
    text = "Kan modellen virke i dag? Det skal undersøges nu."
    sents = _split_factual_sentences(text)
    assert all(not s.endswith("?") for s in sents)


# ── record_fact ──────────────────────────────────────────────────────────


def test_record_fact_inserts_new(tmp_db):
    from core.services.theory_of_mind import (
        record_fact, ORIGIN_TOLD_BY_JARVIS, DEFAULT_PARTNER_ID,
    )
    out = record_fact(
        partner_id=DEFAULT_PARTNER_ID,
        origin=ORIGIN_TOLD_BY_JARVIS,
        fact_summary="Cache hit er 38 procent",
    )
    assert out is not None
    assert out["status"] == "inserted"
    assert out["reference_count"] == 1


def test_record_fact_increments_on_duplicate(tmp_db):
    from core.services.theory_of_mind import (
        record_fact, ORIGIN_TOLD_BY_JARVIS, DEFAULT_PARTNER_ID,
    )
    fact = "Cache hit er 38 procent på flash modellen"
    record_fact(
        partner_id=DEFAULT_PARTNER_ID,
        origin=ORIGIN_TOLD_BY_JARVIS, fact_summary=fact,
    )
    out = record_fact(
        partner_id=DEFAULT_PARTNER_ID,
        origin=ORIGIN_TOLD_BY_JARVIS,
        fact_summary="På flash modellen er cache hit 38 procent",  # same content
    )
    assert out["status"] == "incremented"
    assert out["reference_count"] == 2


def test_record_fact_resets_streak_after_window(tmp_db):
    """Windowed repetition: if the previous mention is older than the repeat window, the
    count restarts at 1 instead of carrying a stale lifetime total (the ×N-forever bug that
    kept the communication-ledger loud and made Jarvis parrot it)."""
    from datetime import UTC, datetime, timedelta
    from core.services import theory_of_mind as tom
    fact = "Rod-årsag ramt fire gange"
    tom.record_fact(partner_id=tom.DEFAULT_PARTNER_ID,
                    origin=tom.ORIGIN_TOLD_BY_JARVIS, fact_summary=fact)
    # Backdate the last mention beyond the window.
    stale = (datetime.now(UTC) - timedelta(hours=tom._REPEAT_WINDOW_HOURS + 1)).isoformat()
    with tom._connect() as conn:
        conn.execute("UPDATE partner_knowledge_facts SET last_at = ?", (stale,))
        conn.commit()
    out = tom.record_fact(partner_id=tom.DEFAULT_PARTNER_ID,
                          origin=tom.ORIGIN_TOLD_BY_JARVIS, fact_summary=fact)
    assert out["reference_count"] == 1   # streak reset, NOT 2


def test_record_fact_returns_none_for_empty(tmp_db):
    from core.services.theory_of_mind import (
        record_fact, ORIGIN_TOLD_BY_JARVIS,
    )
    assert record_fact(
        partner_id="x", origin=ORIGIN_TOLD_BY_JARVIS, fact_summary="",
    ) is None


# ── record_message ───────────────────────────────────────────────────────


def test_record_assistant_message_records_as_told(tmp_db):
    from core.services.theory_of_mind import (
        record_message, recent_facts, ORIGIN_TOLD_BY_JARVIS,
    )
    record_message(
        role="assistant",
        content="Cache kører på 38 procent. Modellen virker fint.",
    )
    facts = recent_facts(origin=ORIGIN_TOLD_BY_JARVIS, hours=1)
    assert len(facts) == 2


def test_record_user_message_records_as_stated(tmp_db):
    from core.services.theory_of_mind import (
        record_message, recent_facts, ORIGIN_STATED_BY_PARTNER,
    )
    record_message(
        role="user",
        content="Modellen skal bruge port 8011. Cache virker bedst med pre-warm.",
    )
    facts = recent_facts(origin=ORIGIN_STATED_BY_PARTNER, hours=1)
    assert len(facts) >= 1


def test_record_unknown_role_ignored(tmp_db):
    from core.services.theory_of_mind import record_message, recent_facts
    record_message(role="system", content="Cache er 38 procent")
    assert recent_facts(hours=1) == []


# ── has_been_told ────────────────────────────────────────────────────────


def test_has_been_told_true(tmp_db):
    from core.services.theory_of_mind import record_message, has_been_told
    record_message(
        role="assistant",
        content="Cache hit er 38 procent på flash modellen.",
    )
    assert has_been_told("Cache hit er 38 procent på flash modellen") is True


def test_has_been_told_false_for_unrelated(tmp_db):
    from core.services.theory_of_mind import record_message, has_been_told
    record_message(
        role="assistant",
        content="Cache hit er 38 procent.",
    )
    assert has_been_told("Modellen kører på port 8011") is False


# ── repetition_warnings + awareness surface ──────────────────────────────


def test_repetition_warnings_threshold(tmp_db):
    from core.services.theory_of_mind import (
        record_fact, repetition_warnings, ORIGIN_TOLD_BY_JARVIS,
    )
    fact = "Cache hit er 38 procent på flash modellen"
    for _ in range(3):
        record_fact(
            partner_id="primary_user",
            origin=ORIGIN_TOLD_BY_JARVIS,
            fact_summary=fact,
        )
    warnings = repetition_warnings(hours=1, threshold=3)
    assert len(warnings) == 1
    assert warnings[0]["reference_count"] == 3


def test_awareness_quiet_when_no_repetition(tmp_db):
    from core.services.theory_of_mind import (
        record_message, communication_ledger_section,
    )
    record_message(
        role="assistant",
        content="Cache er 38 procent. Modellen virker fint.",
    )
    # one-shot facts → no warning surfaced
    assert communication_ledger_section() is None


def test_awareness_surfaces_when_repeating(tmp_db):
    from core.services.theory_of_mind import (
        record_fact, communication_ledger_section, ORIGIN_TOLD_BY_JARVIS,
    )
    fact = "Cache hit er 38 procent på flash modellen"
    for _ in range(4):
        record_fact(
            partner_id="primary_user",
            origin=ORIGIN_TOLD_BY_JARVIS, fact_summary=fact,
        )
    section = communication_ledger_section()
    assert section is not None
    assert "gentaget" in section
    assert "×4" in section


# ── Scaffolding-filter (2026-06-22): runtime-injicerede resume-noter må ikke ind i ledger ──
def test_scaffolding_resume_note_not_recorded_as_fact():
    from core.services.theory_of_mind import _split_factual_sentences
    scaffold = ("Jeg blev afbrudt i agentic loopet (timeout). "
                "Next message can continue from here instead of starting over.")
    assert _split_factual_sentences(scaffold) == []


def test_real_claim_still_recorded():
    from core.services.theory_of_mind import _split_factual_sentences
    real = "Jarvis kører nu på localhost og bruger nomic-embed-text til embeddings."
    assert real in _split_factual_sentences(real)
