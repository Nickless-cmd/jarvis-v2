from __future__ import annotations

import importlib

import pytest


@pytest.fixture()
def clean_runtime_state(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("JARVIS_WORKSPACES_DIR", str(tmp_path / "workspaces"))
    import core.runtime.db as db
    import core.runtime.state_store as state_store

    importlib.reload(db)
    importlib.reload(state_store)
    return None


def test_contradiction_engine_surface_is_side_effect_free(clean_runtime_state):
    from core.services import contradiction_engine as engine

    surface = engine.build_contradiction_engine_surface()

    assert surface["mode"] == "semantic-decision-review-contradictions"
    assert surface["summary"]["finding_count"] == 0
    assert "do_not_auto_mutate_decisions" in surface["allowed_effects"]


def test_emergence_surface_reads_persisted_patterns(clean_runtime_state):
    from core.services import emergence

    emergence._create_or_update_pattern(
        pattern_key="pattern:test",
        title="Test pattern",
        summary="Evidence-backed test pattern.",
        confidence=0.72,
        evidence_count=7,
        competing_explanations=["noise"],
        confounders=["small_sample"],
        status="candidate",
    )

    surface = emergence.build_emergence_surface()

    assert surface["active"] is True
    assert surface["summary"]["candidate"] == 1
    assert surface["items"][0]["pattern_key"] == "pattern:test"
    assert "do_not_treat_candidate_as_identity_truth" in surface["allowed_effects"]


def test_prospective_memory_surface_shows_planted_seed(clean_runtime_state):
    from core.services import prospective_memory as pm

    planted = pm.plant_seed(
        title="Check calibration drift",
        summary="Look again when a calibration event arrives.",
        activate_on_event=["world_model_signal.prediction_resolved"],
        relevance_score=0.8,
    )
    assert planted["outcome"] == "completed"

    surface = pm.build_prospective_memory_surface()

    assert surface["active"] is True
    assert surface["summary"]["planted"] == 1
    assert surface["items"][0]["title"] == "Check calibration drift"
    assert "do_not_auto_execute_seed" in surface["allowed_effects"]


def test_jarvis_brain_reflection_surface_has_bounded_preview(monkeypatch):
    from core.services import jarvis_brain_reflection as reflection

    monkeypatch.setattr(reflection, "_was_active_today", lambda: True)
    monkeypatch.setattr(
        reflection,
        "_build_today_chronicle_summary",
        lambda: "One grounded chronicle item.",
    )

    surface = reflection.build_jarvis_brain_reflection_surface()

    assert surface["active"] is True
    assert surface["mode"] == "daily-visible-reflection-slot"
    assert surface["items"][0]["chronicle_summary"] == "One grounded chronicle item."
    assert "do_not_write_memory_without_remember_this" in surface["allowed_effects"]


def test_latent_surfaces_registered_in_signal_surface_router():
    from core.services.signal_surface_router import get_surface_names

    names = set(get_surface_names())

    assert "contradiction_engine" in names
    assert "emergence" in names
    assert "jarvis_brain_reflection" in names
    assert "prospective_memory" in names
