"""Smoke tests for db_cognitive.py — exercise the read/write paths against an isolated DB."""
from __future__ import annotations

import importlib


def _fresh_module():
    # isolated_runtime reloads core.runtime.db_core (which owns connect()/DB_PATH
    # bound to the tmp HOME). db_cognitive captured `connect`/`_now_iso` from the
    # PREVIOUS db_core at its own import time, so reload it here to rebind them to
    # the freshly-isolated tmp DB before exercising any SQL.
    import core.runtime.db_cognitive as m
    return importlib.reload(m)


def test_db_cognitive_read_paths_are_callable(isolated_runtime):
    m = _fresh_module()

    # LIST functions: empty list on a fresh DB (each lazily ensures its table).
    assert m.list_cognitive_personality_vectors() == []
    assert m.list_cognitive_episodes() == []
    assert m.list_cognitive_habit_patterns() == []
    assert m.list_cognitive_friction_signals() == []
    assert m.list_cognitive_decisions() == []
    assert m.list_cognitive_counterfactuals() == []
    assert m.list_cognitive_shared_language() == []
    assert m.list_cognitive_seeds() == []
    assert m.list_cognitive_experiments() == []
    assert m.list_cognitive_conversation_signatures() == []
    assert m.list_cognitive_user_emotional_states() == []
    assert m.list_cognitive_experiential_memories(user_id="test-user") == []
    assert m.list_cognitive_self_surprises() == []
    assert m.list_cognitive_narrative_identities() == []
    assert m.list_cognitive_gratitude_signals() == []
    assert m.list_cognitive_emergent_goals() == []
    assert m.list_cognitive_formed_values() == []
    assert m.list_cognitive_conflict_memories() == []
    assert m.list_active_cognitive_emotion_concept_signals(now_iso="2999-01-01T00:00:00Z") == []
    assert m.list_cognitive_chronicle_entries() == []
    assert m.get_experiential_memory_candidates(user_id="test-user") == []

    # GET/latest singleton reads: None on a fresh DB.
    assert m.get_latest_cognitive_personality_vector() is None
    assert m.get_latest_cognitive_taste_profile() is None
    assert m.get_latest_cognitive_chronicle_entry() is None
    assert m.get_latest_cognitive_episode() is None
    assert m.get_latest_cognitive_relationship_texture() is None
    assert m.get_latest_cognitive_compass_state() is None
    assert m.get_latest_cognitive_rhythm_state() is None
    assert m.get_cognitive_gut_state() is None
    assert m.get_latest_cognitive_user_emotional_state() is None
    assert m.get_latest_cognitive_narrative_identity() is None
    assert m.get_session_distillation_record("does-not-exist") is None


def test_cognitive_decision_round_trip(isolated_runtime):
    m = _fresh_module()

    assert m.list_cognitive_decisions() == []
    m.insert_cognitive_decision(
        decision_id="dec-1",
        title="Pick storage backend",
        context="ctx",
        decision="sqlite",
        why="simple",
    )
    rows = m.list_cognitive_decisions()
    assert len(rows) == 1
    assert rows[0]["decision_id"] == "dec-1"
    assert rows[0]["title"] == "Pick storage backend"
    assert rows[0]["decision"] == "sqlite"


def test_cognitive_seed_write_and_status(isolated_runtime):
    m = _fresh_module()

    m.insert_cognitive_seed(seed_id="seed-1", title="water it later", summary="s")
    planted = m.list_cognitive_seeds(status="planted")
    assert [r["seed_id"] for r in planted] == ["seed-1"]
    assert planted[0]["status"] == "planted"

    m.update_cognitive_seed_status(seed_id="seed-1", status="activated")
    assert m.list_cognitive_seeds(status="planted") == []
    activated = m.list_cognitive_seeds(status="activated")
    assert [r["seed_id"] for r in activated] == ["seed-1"]


def test_personality_vector_list_and_latest_agree_on_fields(isolated_runtime):
    """De to læsere skal give SAMME nøglesæt — ikke bare hver sit.

    Maalt 23/11-2026: `list_cognitive_personality_vectors` havde sin egen kopi af
    row-mappingen og manglede `learned_preferences`, `recurring_mistakes` og
    `strengths_discovered`. En læser der brugte list-varianten saa en tom liste
    og konkluderede «alt er rent», mens den nyeste vektor havde 16 poster.
    Testen maaler nøglesæt-LIGHED, ikke at et bestemt felt findes — en ny kolonne
    skal komme med i BEGGE læsere uden at nogen opdaterer en liste.
    """
    m = _fresh_module()
    m.upsert_cognitive_personality_vector(
        learned_preferences='["a"]',
        recurring_mistakes='["b"]',
        strengths_discovered='["c"]',
        current_bearing="test",
    )

    latest = m.get_latest_cognitive_personality_vector()
    listed = m.list_cognitive_personality_vectors(limit=1)

    assert latest is not None
    assert len(listed) == 1
    assert set(listed[0]) == set(latest), (
        "list og get_latest maa ikke divergere i felter: "
        f"kun i latest={set(latest) - set(listed[0])}, "
        f"kun i list={set(listed[0]) - set(latest)}"
    )
    # Og vaerdierne skal vaere de samme — ikke bare noeglerne.
    assert listed[0] == latest
