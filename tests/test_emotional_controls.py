from __future__ import annotations

from datetime import UTC, datetime


def test_repeated_failures_of_one_tool_are_one_fatigue_signal(monkeypatch):
    from core.services import emotional_controls as ec

    now = datetime.now(UTC).isoformat()
    events = [
        {"kind": "tool.completed", "created_at": now,
         "payload": {"tool": "operator_bash", "status": "error"}}
        for _ in range(20)
    ]
    monkeypatch.setattr(ec.event_bus, "recent", lambda limit: events)

    assert ec._recent_tool_errors_last_10min() == 1


def test_failures_of_different_tools_remain_distinct_signals(monkeypatch):
    from core.services import emotional_controls as ec

    now = datetime.now(UTC).isoformat()
    events = [
        {"kind": "tool.completed", "created_at": now,
         "payload": {"tool": tool, "status": "error"}}
        for tool in ("operator_bash", "edit_file", "schedule_task")
    ]
    monkeypatch.setattr(ec.event_bus, "recent", lambda limit: events)

    assert ec._recent_tool_errors_last_10min() == 3


# ── A7-analogien for affekt-gaten (målt 11/11-2026) ───────────────────────
# Uden risk-grænsen kunne joy≥0.50 løfte en high-risk handling til execute,
# fordi kaldsstedet kun blokerer verify_first ved high/medium. Glæde var
# dermed den ENESTE vej en high-risk handling med lav confidence kunne køre på.
# Testen her FEJLER på koden før 11/11-2026 (dér gav high-risk 'execute').


def _snap_low_confidence():
    from core.services import emotional_controls as ec

    return ec.EmotionalSnapshot(
        confidence=0.20, frustration=0.0, fatigue=0.0,
        primary_mood="neutral", intensity=0.5,
    )


def _gate(monkeypatch, *, joy: float, risk: str):
    from core.services import emotional_controls as ec
    from core.services import emotion_concepts as emc

    fake = [{"concept": "joy", "intensity": joy}] if joy else []
    monkeypatch.setattr(emc, "get_active_emotion_concepts", lambda: fake)
    return ec.apply_emotional_controls(
        kernel_action="execute", snapshot=_snap_low_confidence(), risk=risk,
    )


def test_joy_loefter_ikke_ved_hoej_risiko(monkeypatch):
    action, reason = _gate(monkeypatch, joy=0.9, risk="high")

    assert action == "verify_first", (
        f"joy løftede en high-risk handling til {action!r} — A7 brudt"
    )
    assert reason == "low_confidence_guard"


def test_joy_loefter_ikke_ved_mellem_risiko(monkeypatch):
    action, reason = _gate(monkeypatch, joy=0.9, risk="medium")

    assert action == "verify_first", (
        f"joy løftede en medium-risk handling til {action!r} — A7 brudt"
    )


def test_joy_loefter_stadig_ved_lav_risiko(monkeypatch):
    """Den positive gate skal bevares — ellers er rettelsen en regression."""
    action, reason = _gate(monkeypatch, joy=0.9, risk="low")

    assert action == "execute"
    assert reason == "joy_lifts_low_confidence"


def test_uden_joy_er_lav_confidence_uanset_risiko(monkeypatch):
    action, reason = _gate(monkeypatch, joy=0.0, risk="low")

    assert action == "verify_first"
    assert reason == "low_confidence_guard"
