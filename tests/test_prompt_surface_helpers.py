from __future__ import annotations

import sys
from types import ModuleType, SimpleNamespace


def test_affirmation_anchor_binds_short_confirmation(monkeypatch):
    from core.services import affirmation_anchor as anchor

    monkeypatch.setattr(
        anchor,
        "recent_chat_session_messages",
        lambda session_id, limit=6: [
            {"role": "assistant", "content": "Vil du have listen?"}
        ],
    )

    anchored = anchor.maybe_anchor_short_reply("ja", session_id="sess-1")

    assert anchored.startswith("[TURN ANCHOR")
    assert "Vil du have listen?" in anchored
    assert "This is a confirmation" in anchored


def test_agreement_streak_detects_repeated_agreements(monkeypatch):
    from core.services import agreement_streak as streak

    rows = [
        {"created_at": "2026-05-12T10:00:00+00:00", "content": "Du har ret. Jeg gør det."},
        {"created_at": "2026-05-12T09:00:00+00:00", "content": "Helt enig, vi justerer det."},
        {"created_at": "2026-05-12T08:00:00+00:00", "content": "Du har en pointe. Lad os se."},
        {"created_at": "2026-05-12T07:00:00+00:00", "content": "Neutral opening."},
    ]

    class FakeCursor:
        def fetchall(self):
            return rows

    class FakeConn:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def execute(self, *args, **kwargs):
            return FakeCursor()

    import core.runtime.db as db

    monkeypatch.setattr(db, "connect", lambda: FakeConn())

    result = streak.detect_agreement_streak(lookback=5, threshold=3)
    section = streak.build_agreement_streak_section()

    assert result is not None
    assert result["count"] == 3
    assert result["lookback"] == 4
    assert section is not None
    assert "Agreement-streak observation" in section


def test_decision_adherence_gate_escalates_low_scores(monkeypatch):
    from core.services import decision_adherence_gate as gate

    behavioral = ModuleType("core.services.behavioral_decisions")
    behavioral.list_active_decisions = lambda limit=20: [
        {"decision_id": "d1", "directive": "ship tests", "adherence_score": 0.2},
        {"decision_id": "d2", "directive": "write notes", "adherence_score": 0.5},
    ]
    monkeypatch.setitem(sys.modules, "core.services.behavioral_decisions", behavioral)

    section = gate.decision_adherence_section()

    assert section.startswith("\n[DECISION-ADHERENCE-GATE]")
    assert "kritisk band" in section
    assert "revokes decision automatisk" in section


def test_predictive_self_model_uses_internal_signals(monkeypatch):
    from core.services import self_model_predictive as predictive

    monkeypatch.setattr(
        predictive,
        "_tick_quality_stats",
        lambda days=14: {"avg": 73, "last_5_avg": 75, "trend": "up", "samples": 9},
    )
    monkeypatch.setattr(
        predictive,
        "_mood_baseline",
        lambda days=14: {"curiosity": {"mean": 0.7, "stdev": 0.05}},
    )
    monkeypatch.setattr(
        predictive,
        "_decision_adherence",
        lambda: {"total": 8, "adherence_rate": 0.75, "flag": None},
    )
    monkeypatch.setattr(
        predictive,
        "_crisis_frequency",
        lambda days=30: {"count": 2, "per_week": 0.5, "by_kind": {"glitch": 2}},
    )
    monkeypatch.setattr(predictive, "_productive_idle_ratio", lambda days=7: 0.42)

    model = predictive.build_predictive_self_model(days=14)
    section = predictive.predictive_self_model_section()

    assert model["tick_quality"]["avg"] == 73
    assert model["productive_idle_ratio_7d"] == 0.42
    assert "Hvem du *empirisk* er" in section
    assert "Tick-kvalitet" in section
    assert "Beslutnings-adherence" in section


def test_self_monitor_flags_repeated_tool_errors(monkeypatch):
    from core.services import self_monitor as monitor

    events = [
        {"kind": "tool.completed", "payload": {"tool": "search", "status": "error"}},
        {"kind": "tool.completed", "payload": {"tool": "search", "status": "error"}},
        {"kind": "tool.completed", "payload": {"tool": "search", "status": "error"}},
        {"kind": "tool.invoked", "payload": {"tool": "search"}},
    ]
    monkeypatch.setattr(
        "core.eventbus.bus.event_bus",
        SimpleNamespace(recent=lambda limit=90: events),
    )

    section = monitor.self_monitor_section()

    assert section is not None
    assert "search: 3 konsekutive fejlede kald" in section
