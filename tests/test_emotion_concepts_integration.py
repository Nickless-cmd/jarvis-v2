from __future__ import annotations


def test_emotion_concept_tone_section_includes_active_hint(
    isolated_runtime, monkeypatch,
) -> None:
    from core.services import emotion_concepts as ec
    from core.services.prompt_contract import _emotion_concept_tone_section

    ec._last_trigger_at.clear()
    monkeypatch.setattr(
        ec, "get_active_emotion_concepts",
        lambda: [{"concept": "wonder", "intensity": 0.6}],
    )

    section = _emotion_concept_tone_section()
    assert section is not None
    assert "Tone right now" in section
    assert "Wonder er aktiv" in section


def test_emotion_concept_tone_section_returns_none_when_no_active(
    isolated_runtime, monkeypatch,
) -> None:
    from core.services import emotion_concepts as ec
    from core.services.prompt_contract import _emotion_concept_tone_section

    monkeypatch.setattr(ec, "get_active_emotion_concepts", lambda: [])
    assert _emotion_concept_tone_section() is None


def test_active_warmth_appears_in_sensory_record_note(
    isolated_runtime, monkeypatch,
) -> None:
    from core.services import emotion_concepts as ec
    from core.services.sensory_archive import record_visual
    from core.runtime.db_sensory import list_sensory_memories

    ec._last_trigger_at.clear()
    monkeypatch.setattr(
        ec, "get_active_emotion_concepts",
        lambda: [{"concept": "warmth", "intensity": 0.5}],
    )

    record_visual("rolige toner i rummet", mood_tone="rolig")
    rows = list_sensory_memories(modality="visual", limit=5)
    assert len(rows) >= 1
    assert "concept-focus" in rows[0]["content"]
    assert "menneskelig" in rows[0]["content"]


def test_episode_completion_records_to_baseline_tracker(
    isolated_runtime,
) -> None:
    """Full chain: record_runtime_episode → joy fires → baseline tracker sees it."""
    from core.runtime.db import get_concept_baseline_stat
    from core.services import emotion_concepts as ec
    from core.services.cognitive_episodes import record_runtime_episode

    ec._last_trigger_at.clear()

    record_runtime_episode(
        source_run_id="e2e-1", session_id="s",
        trigger="visible-run:test", outcome_status="completed",
        summary="ok", tool_names=["a"],
    )

    row = get_concept_baseline_stat("joy")
    assert row is not None
    assert row["total_triggers"] >= 1


def test_simulated_drift_triggers_proposer_call(
    isolated_runtime, monkeypatch,
) -> None:
    """Simulate dominant cluster → daily evaluation → identity_drift_proposer called."""
    from core.runtime import settings as settings_mod
    from core.services import concept_baseline_tracker as cbt

    # Lower thresholds so v1's hardcoded sustained=1 passes
    original = settings_mod.load_settings
    def patched():
        s = original()
        s.concept_baseline_drift_min_sustained_days = 1
        s.concept_baseline_drift_min_confidence = 0.5
        return s
    monkeypatch.setattr(settings_mod, "load_settings", patched)

    proposer_calls = []
    monkeypatch.setattr(
        cbt, "_propose_identity_update",
        lambda signal: (proposer_calls.append(signal) or {"status": "ok"}),
    )

    # 12 joy + 4 frustration → 75% JOY_APPROACH (above 0.55 dominance threshold)
    for _ in range(12):
        cbt.record_concept_trigger(
            concept="joy", intensity=0.5,
            triggered_at="2026-05-05T10:00:00+00:00", source="t",
        )
    for _ in range(4):
        cbt.record_concept_trigger(
            concept="frustration_blocked", intensity=0.5,
            triggered_at="2026-05-05T10:00:00+00:00", source="t",
        )

    result = cbt.evaluate_baseline_drift()

    assert len(proposer_calls) >= 1
    assert any(s.get("type") == "cluster_dominance" for s in proposer_calls)
