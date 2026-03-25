from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4


def _insert_reflection_signal(db, *, status: str = "integrating") -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_reflection_signal(
        signal_id=f"reflection-{uuid4().hex}",
        signal_type="slow-integration",
        canonical_key="reflection-signal:slow-integration:danish-concise-calibration",
        status=status,
        title="Slow integration thread: Danish concise calibration",
        summary="Jarvis is carrying a slow integration thread around Danish concise calibration.",
        rationale="Validation reflection support.",
        source_kind="multi-signal-runtime-derivation",
        confidence="high",
        evidence_summary="Validation evidence should stay out of the helper block.",
        support_summary="Validation support should stay out of the helper block.",
        support_count=3,
        session_count=2,
        created_at=now,
        updated_at=now,
        status_reason="Validation integrating reflection.",
        run_id="validation-run",
        session_id="validation-session",
    )


def _system_text_from_visible_input(visible_model, message: str = "Hello") -> str:
    payload = visible_model._build_visible_input(message, session_id="test-session")
    assert payload[0]["role"] == "system"
    return payload[0]["content"][0]["text"]


def test_visible_input_omits_reflection_support_block_when_no_relevant_signals_exist(isolated_runtime) -> None:
    system_text = _system_text_from_visible_input(isolated_runtime.visible_model)

    assert "Reflection support signal:" not in system_text


def test_visible_input_includes_small_subordinate_reflection_support_block(isolated_runtime) -> None:
    _insert_reflection_signal(isolated_runtime.db)

    system_text = _system_text_from_visible_input(isolated_runtime.visible_model)

    assert "Reflection support signal:" in system_text
    assert "dominant_reflection=Slow integration thread: Danish concise calibration" in system_text
    assert "reflection_state=integrating" in system_text
    assert "reflection_direction=slow-integration" in system_text
    assert "reflection_confidence=high" in system_text
    assert "Use only as subordinate support. Runtime and visible truth outrank it." in system_text


def test_visible_input_reflection_support_block_stays_bounded(isolated_runtime) -> None:
    _insert_reflection_signal(isolated_runtime.db)

    system_text = _system_text_from_visible_input(isolated_runtime.visible_model)
    reflection_block = next(
        part for part in system_text.split("\n\n")
        if part.startswith("Reflection support signal:")
    )

    assert "evidence_summary" not in reflection_block
    assert "support_summary" not in reflection_block
    assert "rationale" not in reflection_block
    assert "recent_history" not in reflection_block
