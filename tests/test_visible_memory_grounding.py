"""Explicit memory questions are grounded from current sources before chat."""
from __future__ import annotations

from core.services.visible_memory_grounding import (
    ground_memory_question,
    needs_memory_grounding,
)


def test_detects_conversation_failure_examples():
    examples = (
        "kan du ikk huske Liva?",
        "har du glemt jeg arbejder på en kirke?",
        "hvad ved du om mig?",
        "hvem er Christina?",
        "så hvor arbejder jeg?",
        "hvilken slags arbejde udfører jeg?",
        "først min datter, så min mor og i går min farmor",
    )
    assert all(needs_memory_grounding(text) for text in examples)


def test_ordinary_chat_is_unchanged_and_does_not_search():
    calls = []
    message = "skal vi finde på noget sjovt?"
    assert ground_memory_question(
        message, search_fn=lambda *a, **k: calls.append((a, k)) or [],
    ) == message
    assert calls == []


def test_current_source_evidence_is_appended():
    def search(query, *, limit):
        assert query == "hvem er Christina?"
        assert limit == 6
        return [{
            "source": "MEMORY.md",
            "section": "Bjørns navnerulle",
            "text": "Christina er chef på Assistens Kirkegård.",
        }]

    grounded = ground_memory_question("hvem er Christina?", search_fn=search)
    assert grounded.startswith("hvem er Christina?")
    assert "CURRENT WORKSPACE SOURCES" in grounded
    assert "MEMORY.md § Bjørns navnerulle" in grounded
    assert "Christina er chef på Assistens Kirkegård" in grounded
    assert "USER.md.bak-*" in grounded


def test_empty_lookup_requires_tool_instead_of_guess():
    grounded = ground_memory_question(
        "hvor arbejder jeg?", search_fn=lambda query, *, limit: [],
    )
    assert "Call search_memory or recall" in grounded
    assert "do not guess" in grounded
