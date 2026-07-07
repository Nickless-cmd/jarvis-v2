from __future__ import annotations

from collections import deque
from datetime import UTC, datetime


def test_calm_anchor_reports_distance_and_prompt(monkeypatch):
    from core.services import calm_anchor as anchor

    monkeypatch.setattr(anchor, "get_anchor_signature", lambda: {"valence": 0.6, "tension_count": 1.0})
    monkeypatch.setattr(anchor, "_current_snapshot", lambda: {"valence": 0.2, "tension_count": 3.0})

    state = anchor.get_anchor_state()
    surface = anchor.build_calm_anchor_surface()
    prompt = anchor.build_calm_anchor_prompt_section()

    assert state["has_anchor"] is True
    assert surface["active"] is True
    assert surface["distance_from_anchor"] > 0.25
    assert prompt is not None
    assert "Calm-anker" in prompt


def test_developmental_valence_uses_component_vector(monkeypatch):
    from core.services import developmental_valence as valence

    monkeypatch.setattr(
        valence,
        "_compute_components",
        lambda: {
            "intention_closure": 0.8,
            "dream_confirmation": 0.8,
            "loop_health": 0.8,
            "relation_sustained": 0.8,
            "metabolism": 0.8,
        },
    )
    valence._last_state = {}
    valence._last_computed_ts = 0.0

    state = valence.get_developmental_state()
    surface = valence.build_developmental_valence_surface()

    assert state["trajectory"] == "steady-bright"
    assert state["vector"] > 0.0
    assert surface["active"] is True
    assert surface["summary"].startswith("Udviklings-valence:")


def test_temporal_rhythm_surfaces_racing_tempo(monkeypatch):
    from core.services import temporal_rhythm as rhythm

    monkeypatch.setattr(rhythm, "_pending_initiatives_count", lambda: 8)
    monkeypatch.setattr(rhythm, "_recent_tool_calls_per_min", lambda: 3.0)
    monkeypatch.setattr(rhythm, "_recent_chat_activity_per_min", lambda: 3.0)
    monkeypatch.setattr(rhythm, "_eventbus_queue_depth", lambda: 40)

    snap = rhythm.tick()
    surface = rhythm.build_temporal_rhythm_surface()
    prompt = rhythm.build_temporal_rhythm_prompt_section()

    assert snap["subjective_time_pressure"] == "racing"
    assert surface["active"] is True
    assert surface["summary"].startswith("Puls=")
    assert prompt is not None
    # Wording changed to sober English prose in commit 1471da77
    # ("teater-runde 3"): "jager … presset" → "racing … high subjective
    # pressure band".
    assert "racing" in prompt
    assert "high subjective pressure band" in prompt


def test_valence_trajectory_flourishes_from_window(monkeypatch):
    from core.services import valence_trajectory as trajectory

    now = datetime.now(UTC).timestamp()
    trajectory._samples = deque(
        [
            (now - 3000, -0.4),
            (now - 2000, -0.2),
            (now - 1000, 0.6),
            (now, 0.8),
        ],
        maxlen=trajectory._WINDOW_MAX,
    )
    trajectory._last_summary = {}
    trajectory._last_computed_ts = 0.0

    state = trajectory.get_trajectory()
    surface = trajectory.build_valence_trajectory_surface()

    assert state["trend"] == "flourishing"
    assert surface["active"] is True
    assert surface["summary"].startswith("Bevæger sig mod blomstring")


def test_relational_warmth_updates_and_prompts(monkeypatch):
    from core.services import relational_warmth as warmth

    state = {
        "relations": {
            "bjorn": {
                "trust_level": 0.9,
                "playfulness": 0.8,
                "vulnerability_received": 1,
                "care_given": 1,
                "last_interaction_at": None,
                "recent_signals": [],
            }
        }
    }

    def load():
        return state

    def save(data):
        snapshot = dict(data)
        state.clear()
        state.update(snapshot)

    monkeypatch.setattr(warmth, "_load", load)
    monkeypatch.setattr(warmth, "_save", save)

    incoming = warmth.observe_incoming_text("jeg har det svært")
    outgoing = warmth.observe_outgoing_text("jeg forstår dig")
    surface = warmth.build_relational_warmth_surface()
    prompt = warmth.build_relational_warmth_prompt_section()

    assert incoming["vulnerability"] is True
    assert outgoing["care_given"] is True
    assert surface["trust_level"] > 0.9
    assert surface["care_given"] >= 2
    assert prompt == "Relationel varme er høj — vær åben, nysgerrig, legende."
