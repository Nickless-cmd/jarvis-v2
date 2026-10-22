"""Prepared associative recall is query-gated and non-blocking."""
from __future__ import annotations


def test_background_recall_never_serves_previous_query(monkeypatch):
    from core.services import associative_recall, prompt_memory_recall

    monkeypatch.setattr(associative_recall, "build_recall_prompt_section", lambda query: "")
    first, first_inputs, errors = [], [], []
    prompt_memory_recall.append_background_recall(
        "Et helt nyt emne", "session", first, first_inputs, lambda *args: errors.append(args),
    )
    assert first == []
    assert first_inputs == []
    assert errors == []


def test_background_recall_surfaces_query_matched_prepared_association(monkeypatch):
    from core.services import associative_recall, prompt_memory_recall

    seen = []
    monkeypatch.setattr(
        associative_recall,
        "build_recall_prompt_section",
        lambda query: seen.append(query) or "[ASSOCIATIONER]\n→ relevant minde",
    )
    sections, inputs = [], []
    prompt_memory_recall.append_background_recall(
        "Fortsæt om deploy", "session", sections, inputs, lambda *args: None,
    )
    assert seen == ["Fortsæt om deploy"]
    assert sections == ["[ASSOCIATIONER]\n→ relevant minde"]
    assert inputs == ["associative recall (prepared, query-matched)"]
