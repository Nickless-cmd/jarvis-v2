"""Tests for consciousness experiment subsystems."""
from __future__ import annotations
import pytest


# ---------------------------------------------------------------------------
# Shared infrastructure: experiment toggle
# ---------------------------------------------------------------------------

def test_experiment_enabled_default_true(isolated_runtime) -> None:
    db = isolated_runtime.db
    # Default: no row → enabled
    assert db.get_experiment_enabled("recurrence_loop") is True


def test_experiment_toggle(isolated_runtime) -> None:
    db = isolated_runtime.db
    db.set_experiment_enabled("recurrence_loop", False)
    assert db.get_experiment_enabled("recurrence_loop") is False
    db.set_experiment_enabled("recurrence_loop", True)
    assert db.get_experiment_enabled("recurrence_loop") is True


def test_experiment_toggle_independent(isolated_runtime) -> None:
    db = isolated_runtime.db
    db.set_experiment_enabled("meta_cognition", False)
    assert db.get_experiment_enabled("recurrence_loop") is True
    assert db.get_experiment_enabled("meta_cognition") is False


# ---------------------------------------------------------------------------
# Experiment 1: Recurrence Loop
# ---------------------------------------------------------------------------

def test_recurrence_db_insert_and_fetch(isolated_runtime) -> None:
    db = isolated_runtime.db
    db.insert_recurrence_iteration(
        iteration_id="rec-test-001",
        content="Jeg tænker på kompleksitet og usikkerhed",
        keywords='["kompleksitet", "usikkerhed", "tænker"]',
        stability_score=0.72,
        iteration_number=3,
    )
    result = db.get_latest_recurrence_iteration()
    assert result is not None
    assert result["iteration_id"] == "rec-test-001"
    assert abs(result["stability_score"] - 0.72) < 0.001
    assert result["iteration_number"] == 3


def test_jaccard_similarity_identical() -> None:
    import importlib
    import core.services.recurrence_loop_daemon as rld
    importlib.reload(rld)
    score = rld._jaccard_similarity({"a", "b", "c"}, {"a", "b", "c"})
    assert abs(score - 1.0) < 0.001


def test_jaccard_similarity_disjoint() -> None:
    import importlib
    import core.services.recurrence_loop_daemon as rld
    importlib.reload(rld)
    score = rld._jaccard_similarity({"a", "b"}, {"c", "d"})
    assert abs(score - 0.0) < 0.001


def test_jaccard_similarity_partial() -> None:
    import importlib
    import core.services.recurrence_loop_daemon as rld
    importlib.reload(rld)
    score = rld._jaccard_similarity({"a", "b", "c"}, {"b", "c", "d"})
    # intersection=2, union=4 → 0.5
    assert abs(score - 0.5) < 0.001


def test_extract_keywords_filters_short() -> None:
    import importlib
    import core.services.recurrence_loop_daemon as rld
    importlib.reload(rld)
    kws = rld._extract_keywords("jeg er glad men også bekymret")
    assert "er" not in kws
    assert "jeg" not in kws
    assert "bekymret" in kws or "glad" in kws


def test_tick_recurrence_skips_when_disabled(isolated_runtime) -> None:
    isolated_runtime.db.set_experiment_enabled("recurrence_loop", False)
    import importlib
    import core.services.recurrence_loop_daemon as rld
    importlib.reload(rld)
    result = rld.tick_recurrence_loop_daemon()
    assert result["generated"] is False
    assert result["reason"] == "disabled"


# ---------------------------------------------------------------------------
# Experiment 2: Surprise Persistence
# ---------------------------------------------------------------------------

def test_surprise_classifies_positive() -> None:
    import importlib
    import core.services.surprise_daemon as sd
    importlib.reload(sd)
    assert sd._classify_surprise("Det var positivt overraskende") == "positiv"


def test_surprise_persistence_concept_mapping() -> None:
    import importlib
    import core.services.surprise_daemon as sd
    importlib.reload(sd)
    assert sd._surprise_type_to_concept("positiv") == "anticipation"
    assert sd._surprise_type_to_concept("negativ") == "tension"
    assert sd._surprise_type_to_concept("neutral") == "vigilance"
    assert sd._surprise_type_to_concept("ingen") == "vigilance"


def test_surprise_afterimage_concept_mapping() -> None:
    import importlib
    import core.services.surprise_daemon as sd
    importlib.reload(sd)
    assert sd._afterimage_concept("positiv") == "curiosity_narrow"
    assert sd._afterimage_concept("negativ") == "caution"
    assert sd._afterimage_concept("neutral") == "curiosity_narrow"


# ---------------------------------------------------------------------------
# Experiment 3: Global Workspace
# ---------------------------------------------------------------------------

def test_broadcast_db_insert_and_list(isolated_runtime) -> None:
    db = isolated_runtime.db
    db.insert_broadcast_event(
        event_id="bc-test-001",
        topic_cluster="deployment frustration",
        sources='["surprise_daemon", "inner_voice_daemon", "emotion_concepts"]',
        source_count=3,
        payload_summary="Multiple daemons converging on deployment stress theme",
    )
    results = db.list_broadcast_events(limit=10)
    assert len(results) == 1
    assert results[0]["source_count"] == 3
    assert results[0]["topic_cluster"] == "deployment frustration"


def test_workspace_topic_extraction() -> None:
    import importlib
    import core.services.global_workspace as gw
    importlib.reload(gw)
    topic = gw._extract_topic("cognitive_surprise.noted", {"phrase": "Jeg var overrasket over min reaktion på fejlen"})
    assert isinstance(topic, str)
    assert len(topic) > 0


def test_workspace_jaccard_topic_match() -> None:
    import importlib
    import core.services.global_workspace as gw
    importlib.reload(gw)
    score = gw._topic_jaccard("deployment stress", "deployment error")
    assert score > 0.0
    score2 = gw._topic_jaccard("music creativity", "deployment error")
    assert score2 < 0.4


def test_workspace_publish_and_snapshot() -> None:
    import importlib
    import core.services.global_workspace as gw
    importlib.reload(gw)
    gw.publish_to_workspace("surprise_daemon", "frustration error", "cognitive_surprise.noted", "Overrasket over fejl")
    gw.publish_to_workspace("inner_voice_daemon", "error frustration", "inner_voice.noted", "Tænkte over fejlen")
    snapshot = gw.get_workspace_snapshot()
    assert len(snapshot) == 2
    assert any(e["source"] == "surprise_daemon" for e in snapshot)


# ---------------------------------------------------------------------------
# Experiment 4: Meta-Cognition
# ---------------------------------------------------------------------------

def test_meta_cognition_db_insert_and_list(isolated_runtime) -> None:
    db = isolated_runtime.db
    db.insert_meta_cognition_record(
        record_id="mc-test-001",
        meta_observation="Jeg lægger mærke til at min frustration stiger",
        meta_meta_observation="Denne observation er præcis men overser konteksten",
        meta_depth=2,
        input_state_summary="bearing=forward, frustration=0.6",
    )
    records = db.list_meta_cognition_records(limit=5)
    assert len(records) == 1
    assert records[0]["meta_depth"] == 2


def test_meta_depth_computation() -> None:
    import importlib
    import core.services.meta_cognition_daemon as mcd
    importlib.reload(mcd)
    assert mcd._compute_meta_depth("hunden løber hurtigt", "hunden løber hurtigt") == 1
    assert mcd._compute_meta_depth(
        "jeg er frustreret over manglende fremgang",
        "denne observation er blind for systemiske årsager"
    ) == 2


def test_tick_meta_cognition_disabled(isolated_runtime) -> None:
    isolated_runtime.db.set_experiment_enabled("meta_cognition", False)
    import importlib
    import core.services.meta_cognition_daemon as mcd
    importlib.reload(mcd)
    result = mcd.tick_meta_cognition_daemon()
    assert result["generated"] is False
    assert result["reason"] == "disabled"


# ---------------------------------------------------------------------------
# Experiment 5: Attention Blink
# ---------------------------------------------------------------------------

def test_attention_blink_db_insert_and_list(isolated_runtime) -> None:
    db = isolated_runtime.db
    db.insert_attention_blink_result(
        test_id="blink-test-001",
        t1_baseline='{"confidence": 0.5, "frustration": 0.2}',
        t1_response='{"confidence": 0.4, "frustration": 0.5}',
        t2_response='{"confidence": 0.45, "frustration": 0.35}',
        blink_ratio=0.65,
        interpretation="serial/blink-prone",
    )
    results = db.list_attention_blink_results(limit=5)
    assert len(results) == 1
    assert abs(results[0]["blink_ratio"] - 0.65) < 0.001
    assert results[0]["interpretation"] == "serial/blink-prone"


def test_blink_ratio_computation() -> None:
    import importlib
    import core.services.attention_blink_test as abt
    importlib.reload(abt)
    t1 = {"confidence": 0.6, "frustration": 0.4, "fatigue": 0.2, "curiosity": 0.3}
    t2 = {"confidence": 0.5, "frustration": 0.25, "fatigue": 0.15, "curiosity": 0.2}
    ratio = abt._compute_blink_ratio(t1, t2)
    # t1 total = 1.5, t2 total = 1.1, ratio = 1.1/1.5 ≈ 0.733
    assert 0.7 < ratio < 0.8


def test_blink_interpretation() -> None:
    import importlib
    import core.services.attention_blink_test as abt
    importlib.reload(abt)
    assert abt._interpret_blink_ratio(0.5) == "serial/blink-prone"
    assert abt._interpret_blink_ratio(0.69) == "serial/blink-prone"
    assert abt._interpret_blink_ratio(0.7) == "parallel/blink-resistant"
    assert abt._interpret_blink_ratio(1.0) == "parallel/blink-resistant"


def test_run_attention_blink_skips_when_disabled(isolated_runtime) -> None:
    isolated_runtime.db.set_experiment_enabled("attention_blink", False)
    import importlib
    import core.services.attention_blink_test as abt
    importlib.reload(abt)
    result = abt.run_attention_blink_test_if_due()
    assert result["generated"] is False
    assert result["reason"] == "disabled"


def test_cognitive_core_experiment_surface_classifies_truth_layers(monkeypatch) -> None:
    import importlib

    surface_mod = importlib.import_module(
        "core.services.cognitive_core_experiments"
    )

    monkeypatch.setattr(
        surface_mod,
        "_build_recurrence_state",
        lambda: {
            "id": "recurrence",
            "enabled": True,
            "active": True,
            "activity_state": "active",
            "core_status": "core-candidate",
            "carry_capable": True,
            "carry_domain": "loop-reentry",
            "carry_strength": "medium",
            "observational_only": False,
            "summary": "recurrence active",
            "source_summary": {},
        },
    )
    monkeypatch.setattr(
        surface_mod,
        "_build_global_workspace_state",
        lambda: {
            "id": "global_workspace",
            "enabled": True,
            "active": True,
            "activity_state": "active",
            "core_status": "core-candidate",
            "carry_capable": True,
            "carry_domain": "salience-broadcast",
            "carry_strength": "strong",
            "observational_only": False,
            "summary": "workspace active",
            "source_summary": {},
        },
    )
    monkeypatch.setattr(
        surface_mod,
        "_build_hot_meta_cognition_state",
        lambda: {
            "id": "hot_meta_cognition",
            "enabled": True,
            "active": False,
            "activity_state": "idle",
            "core_status": "core-candidate",
            "carry_capable": True,
            "carry_domain": "reflective-depth",
            "carry_strength": "medium",
            "observational_only": False,
            "summary": "hot idle",
            "source_summary": {},
        },
    )
    monkeypatch.setattr(
        surface_mod,
        "_build_surprise_afterimage_state",
        lambda: {
            "id": "surprise_afterimage",
            "enabled": True,
            "active": True,
            "activity_state": "active",
            "core_status": "core-candidate",
            "carry_capable": True,
            "carry_domain": "affective-carry",
            "carry_strength": "strong",
            "observational_only": False,
            "summary": "afterimage active",
            "source_summary": {},
        },
    )
    monkeypatch.setattr(
        surface_mod,
        "_build_attention_blink_state",
        lambda: {
            "id": "attention_blink",
            "enabled": True,
            "active": True,
            "activity_state": "active",
            "core_status": "observational-core-assay",
            "carry_capable": False,
            "carry_domain": "capacity-assay",
            "carry_strength": "none",
            "observational_only": True,
            "summary": "blink active",
            "source_summary": {},
        },
    )

    surface = surface_mod.build_cognitive_core_experiments_surface()

    assert surface["active_count"] == 4
    assert surface["carry_candidate_count"] == 4
    assert surface["active_carry_candidate_count"] == 3
    assert surface["observational_count"] == 1
    assert surface["carry_state"] == "present"
    assert surface["strongest_carry_system"] in {
        "global_workspace",
        "surprise_afterimage",
    }
    assert surface["systems"]["attention_blink"]["observational_only"] is True
    assert surface["systems"]["attention_blink"]["carry_capable"] is False


def test_trigger_emotion_concept_custom_lifetime() -> None:
    import importlib
    import core.services.emotion_concepts as ec
    importlib.reload(ec)
    result = ec.trigger_emotion_concept("anticipation", 0.7, lifetime_hours=4.0)
    assert result is not None
    # expires_at should be ~4h from now, not 2h
    from datetime import UTC, datetime, timedelta
    expires = datetime.fromisoformat(result["expires_at"])
    now = datetime.now(UTC)
    delta_hours = (expires - now).total_seconds() / 3600
    assert 3.5 < delta_hours < 4.5
