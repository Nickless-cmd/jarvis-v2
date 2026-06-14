from __future__ import annotations


def _insert(hypothesis: str, *, confidence: float, presented: int = 0) -> int:
    from core.runtime.db_core import connect
    from core.services.dream_hypothesis_generator import _ensure_table

    _ensure_table()
    with connect() as conn:
        cur = conn.execute(
            """INSERT INTO cognitive_dream_hypotheses
               (hypothesis, connection, action_suggestion, source_signals,
                basis_fingerprint, hypothesis_fingerprint, confidence,
                presented, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                hypothesis, "forbindelse", "handling", "[]",
                f"bfp-{hypothesis}", f"hfp-{hypothesis}", confidence,
                presented, "2026-05-15T00:00:00Z",
            ),
        )
        conn.commit()
        return int(cur.lastrowid)


def test_surface_none_when_no_pending(isolated_runtime) -> None:
    from core.services.dream_hypothesis_generator import build_dream_hypothesis_prompt_section

    assert build_dream_hypothesis_prompt_section() is None


def test_surface_picks_highest_confidence_pending(isolated_runtime) -> None:
    from core.services.dream_hypothesis_generator import build_dream_hypothesis_prompt_section

    _insert("lav konfidens drøm", confidence=0.3)
    hid = _insert("høj konfidens drøm", confidence=0.9)

    result = build_dream_hypothesis_prompt_section()
    assert result is not None
    text, returned_id = result
    assert returned_id == hid
    assert "høj konfidens drøm" in text
    assert "Drøm-hypotese" in text


def test_surface_skips_already_presented(isolated_runtime) -> None:
    from core.services.dream_hypothesis_generator import build_dream_hypothesis_prompt_section

    _insert("allerede vist", confidence=0.8, presented=1)
    assert build_dream_hypothesis_prompt_section() is None


def test_mark_presented_removes_from_surface(isolated_runtime) -> None:
    from core.services.dream_hypothesis_generator import (
        build_dream_hypothesis_prompt_section,
        mark_hypothesis_presented,
    )

    hid = _insert("en drøm", confidence=0.7)
    first = build_dream_hypothesis_prompt_section()
    assert first is not None and first[1] == hid

    assert mark_hypothesis_presented(hypothesis_id=hid) is True
    # Once presented, it must not surface again.
    assert build_dream_hypothesis_prompt_section() is None
