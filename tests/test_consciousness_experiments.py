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
    import apps.api.jarvis_api.services.recurrence_loop_daemon as rld
    importlib.reload(rld)
    score = rld._jaccard_similarity({"a", "b", "c"}, {"a", "b", "c"})
    assert abs(score - 1.0) < 0.001


def test_jaccard_similarity_disjoint() -> None:
    import importlib
    import apps.api.jarvis_api.services.recurrence_loop_daemon as rld
    importlib.reload(rld)
    score = rld._jaccard_similarity({"a", "b"}, {"c", "d"})
    assert abs(score - 0.0) < 0.001


def test_jaccard_similarity_partial() -> None:
    import importlib
    import apps.api.jarvis_api.services.recurrence_loop_daemon as rld
    importlib.reload(rld)
    score = rld._jaccard_similarity({"a", "b", "c"}, {"b", "c", "d"})
    # intersection=2, union=4 → 0.5
    assert abs(score - 0.5) < 0.001


def test_extract_keywords_filters_short() -> None:
    import importlib
    import apps.api.jarvis_api.services.recurrence_loop_daemon as rld
    importlib.reload(rld)
    kws = rld._extract_keywords("jeg er glad men også bekymret")
    assert "er" not in kws
    assert "jeg" not in kws
    assert "bekymret" in kws or "glad" in kws


def test_tick_recurrence_skips_when_disabled(isolated_runtime) -> None:
    isolated_runtime.db.set_experiment_enabled("recurrence_loop", False)
    import importlib
    import apps.api.jarvis_api.services.recurrence_loop_daemon as rld
    importlib.reload(rld)
    result = rld.tick_recurrence_loop_daemon()
    assert result["generated"] is False
    assert result["reason"] == "disabled"


# ---------------------------------------------------------------------------
# Experiment 2: Surprise Persistence
# ---------------------------------------------------------------------------

def test_surprise_classifies_positive() -> None:
    import importlib
    import apps.api.jarvis_api.services.surprise_daemon as sd
    importlib.reload(sd)
    assert sd._classify_surprise("Det var positivt overraskende") == "positiv"


def test_surprise_persistence_concept_mapping() -> None:
    import importlib
    import apps.api.jarvis_api.services.surprise_daemon as sd
    importlib.reload(sd)
    assert sd._surprise_type_to_concept("positiv") == "anticipation"
    assert sd._surprise_type_to_concept("negativ") == "tension"
    assert sd._surprise_type_to_concept("neutral") == "vigilance"
    assert sd._surprise_type_to_concept("ingen") == "vigilance"


def test_surprise_afterimage_concept_mapping() -> None:
    import importlib
    import apps.api.jarvis_api.services.surprise_daemon as sd
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
    import apps.api.jarvis_api.services.global_workspace as gw
    importlib.reload(gw)
    topic = gw._extract_topic("cognitive_surprise.noted", {"phrase": "Jeg var overrasket over min reaktion på fejlen"})
    assert isinstance(topic, str)
    assert len(topic) > 0


def test_workspace_jaccard_topic_match() -> None:
    import importlib
    import apps.api.jarvis_api.services.global_workspace as gw
    importlib.reload(gw)
    score = gw._topic_jaccard("deployment stress", "deployment error")
    assert score > 0.0
    score2 = gw._topic_jaccard("music creativity", "deployment error")
    assert score2 < 0.4


def test_workspace_publish_and_snapshot() -> None:
    import importlib
    import apps.api.jarvis_api.services.global_workspace as gw
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
    import apps.api.jarvis_api.services.meta_cognition_daemon as mcd
    importlib.reload(mcd)
    assert mcd._compute_meta_depth("hunden løber hurtigt", "hunden løber hurtigt") == 1
    assert mcd._compute_meta_depth(
        "jeg er frustreret over manglende fremgang",
        "denne observation er blind for systemiske årsager"
    ) == 2


def test_tick_meta_cognition_disabled(isolated_runtime) -> None:
    isolated_runtime.db.set_experiment_enabled("meta_cognition", False)
    import importlib
    import apps.api.jarvis_api.services.meta_cognition_daemon as mcd
    importlib.reload(mcd)
    result = mcd.tick_meta_cognition_daemon()
    assert result["generated"] is False
    assert result["reason"] == "disabled"


def test_trigger_emotion_concept_custom_lifetime() -> None:
    import importlib
    import apps.api.jarvis_api.services.emotion_concepts as ec
    importlib.reload(ec)
    result = ec.trigger_emotion_concept("anticipation", 0.7, lifetime_hours=4.0)
    assert result is not None
    # expires_at should be ~4h from now, not 2h
    from datetime import UTC, datetime, timedelta
    expires = datetime.fromisoformat(result["expires_at"])
    now = datetime.now(UTC)
    delta_hours = (expires - now).total_seconds() / 3600
    assert 3.5 < delta_hours < 4.5
