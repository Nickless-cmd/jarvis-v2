from __future__ import annotations


def test_capture_mood_for_heading_returns_legacy_dict_shape(
    isolated_runtime, monkeypatch
) -> None:
    from core.services import emotional_memory_engine as em
    from core.services.memory_emotional_context import capture_mood_for_heading

    monkeypatch.setattr(em, "_read_current_mood", lambda: ("content", 0.42))
    monkeypatch.setattr(em, "_read_current_dimensions", lambda: {})

    result = capture_mood_for_heading("## My Heading")
    assert result is not None
    assert set(result.keys()) >= {
        "heading_normalized", "heading_display", "mood",
        "intensity", "captured_at", "source", "notes",
    }
    assert result["mood"] == "content"
    assert abs(result["intensity"] - 0.42) < 1e-6
    assert result["heading_display"] == "## My Heading"


def test_get_mood_for_heading_reads_from_new_table(
    isolated_runtime, monkeypatch
) -> None:
    from core.services import emotional_memory_engine as em
    from core.services.memory_emotional_context import (
        capture_mood_for_heading,
        get_mood_for_heading,
    )

    monkeypatch.setattr(em, "_read_current_mood", lambda: ("calm", 0.3))
    monkeypatch.setattr(em, "_read_current_dimensions", lambda: {})

    capture_mood_for_heading("## A Heading")
    fetched = get_mood_for_heading("## A Heading")
    assert fetched is not None
    assert fetched["mood"] == "calm"


def test_enrich_headings_with_mood_annotates_known_heading(
    isolated_runtime, monkeypatch
) -> None:
    from core.services import emotional_memory_engine as em
    from core.services.memory_emotional_context import (
        capture_mood_for_heading,
        enrich_headings_with_mood,
    )

    monkeypatch.setattr(em, "_read_current_mood", lambda: ("content", 0.5))
    monkeypatch.setattr(em, "_read_current_dimensions", lambda: {})
    # Real call-sites pass the heading without the ## prefix — enrich's
    # regex strips the prefix before normalize, so they must match.
    capture_mood_for_heading("Project X")

    text = "## Project X\n\nSome body text here."
    enriched = enrich_headings_with_mood(text)
    assert "[felt: content" in enriched


def test_legacy_capture_does_not_set_dimension_fields(
    isolated_runtime, monkeypatch
) -> None:
    from core.runtime.db import get_emotional_memory_anchor
    from core.services import emotional_memory_engine as em
    from core.services.memory_emotional_context import capture_mood_for_heading

    monkeypatch.setattr(em, "_read_current_mood", lambda: ("calm", 0.3))
    monkeypatch.setattr(em, "_read_current_dimensions", lambda: {})

    capture_mood_for_heading("## H")
    import re
    norm = re.sub(r"\s+", " ", "## H".strip().lower())
    row = get_emotional_memory_anchor("memory_heading", norm)
    assert row is not None
    assert row["confidence"] is None
    assert row["frustration"] is None
