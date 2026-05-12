from __future__ import annotations

import sqlite3
import types
from datetime import UTC, datetime


def test_metacognitive_integration_reports_coherent_state(monkeypatch):
    from core.services import metacognitive_integration as meta

    monkeypatch.setattr(meta, "_autonomy_enabled", lambda: True)

    state = {
        "mood": {
            "curiosity": 0.8,
            "confidence": 0.9,
            "frustration": 0.1,
            "fatigue": 0.1,
        },
        "bearing": "forward",
        "mode": "epistemic",
        "attention": "skærpt",
        "precision": "forsigtig",
        "presence": "afternoon · calm · grounded",
        "temporal": "recall: 0.7 anticipation: 0.8",
        "resonance": "genklang",
        "context_pressure": "high",
    }

    line = meta.get_metacognitive_line(state)
    detail = meta.get_metacognitive_detail(state)

    assert line.startswith("meta:")
    assert "readiness" in line
    assert detail["enabled"] is True
    assert detail["quality_label"] in {"hel", "sammenhængende", "uafklaret"}
    assert 0.0 <= detail["coherence"] <= 1.0
    assert 0.0 <= detail["integration"] <= 1.0


def test_epistemic_pragmatic_prefers_epistemic_when_confidence_is_low(monkeypatch):
    from core.services import epistemic_pragmatic as balance

    monkeypatch.setattr(balance, "_autonomy_enabled", lambda: True)
    monkeypatch.setattr(
        "core.runtime.db.get_latest_cognitive_personality_vector",
        lambda: {"confidence_by_domain": {"a": 2, "b": 3, "c": 2}},
    )
    monkeypatch.setattr(
        "core.services.signal_pressure_accumulator.get_dominant_pressures",
        lambda min_accumulated=0.10: [types.SimpleNamespace(direction="explore", accumulated=0.9)],
    )
    monkeypatch.setattr(
        "core.services.emotional_chords.compute_active_chords",
        lambda: [],
    )

    mode = balance.compute_epistemic_pragmatic()
    line = balance.get_mode_line()

    assert mode is not None
    assert mode.mode == "epistemic"
    assert line == "mode: udforskende — søg viden før handling"


def test_precision_bias_prefers_frustration_style(monkeypatch):
    from core.services import precision_bias as bias

    monkeypatch.setattr(bias, "_autonomy_enabled", lambda: True)
    monkeypatch.setattr(
        "core.services.signal_pressure_accumulator.get_dominant_pressures",
        lambda min_accumulated=0.15: [
            types.SimpleNamespace(direction="fix", accumulated=0.8),
            types.SimpleNamespace(direction="explore", accumulated=0.2),
        ],
    )

    profile = bias.compute_precision_bias()
    line = bias.get_precision_line()

    assert profile is not None
    assert profile.dominant_signal == "frustration"
    assert "skarp" in line
    assert "præcist" in line or "kort" in line


def test_embodied_presence_uses_recent_sensory_rows():
    from core.services import embodied_presence as presence

    conn = sqlite3.connect(":memory:")
    conn.execute(
        "CREATE TABLE sensory_memories (modality TEXT, content TEXT, mood_tone TEXT, created_at TEXT)"
    )
    rows = [
        ("visual", "movement busy", None),
        ("audio", "music amplitude 0.8", None),
        ("atmosphere", "quiet room", "warm and calm"),
    ]
    for row in rows:
        conn.execute(
            "INSERT INTO sensory_memories (modality, content, mood_tone, created_at) VALUES (?, ?, ?, datetime('now'))",
            row,
        )
    conn.commit()

    signal = presence.compute_embodied_presence(db_conn=conn, now=datetime(2026, 5, 12, 10, 0, tzinfo=UTC))
    line = presence.get_presence_line(db_conn=conn)

    assert signal is not None
    assert signal.temporal_context == "morning"
    assert signal.grounding > 0.9
    assert signal.arousal > 0.5
    assert line is not None
    assert line.startswith("presence: ")
    assert "rooted" in line


def test_temporal_depth_caches_and_invalidates():
    from core.services import temporal_depth as depth

    td = depth.get_temporal_depth()
    td.invalidate()

    state_a = {
        "pressure_summary": [{"activation": 0.9}, {"activation": 0.8}],
        "cognitive_cadence": {"state": "flow"},
    }
    state_b = {
        "pressure_summary": [{"activation": 0.0}],
        "cognitive_cadence": {"state": "stuck"},
    }

    first = td.assess(state_a, "2026-05-12T10:00:00+00:00")
    second = td.assess(state_b, "2026-05-12T11:00:00+00:00")
    td.invalidate()
    third = td.assess(state_b, "2026-05-12T11:00:00+00:00")

    assert first.summary == "↑ momentum"
    assert first.anticipation_match == 0.9
    assert second.summary == first.summary
    assert third.summary in {"⚡ surprise", "→ steady", "· neutral", "↓ surprise"}
    assert third.recall_strength <= 0.4
