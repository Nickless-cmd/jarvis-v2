"""Tests for runtime_action_executor — leverings-kontrakten.

23/9-2026: `delivery_succeeded` afløste `delivery.get("status") == "ok"` i
denne fil. `send_session_notification` har tre udfald (ok / queued / fejl),
og "queued" er en succes: sessionen var aktiv, så beskeden ligger i
session_inbox og leveres efter turen. Uden denne skelnen meldte de to
funktioner her "blocked" om en levering der gik igennem.
"""
from __future__ import annotations


def _stub_delivery(monkeypatch, result: dict):
    monkeypatch.setattr(
        "core.services.runtime_action_executor.send_session_notification",
        lambda content, source="runtime-proposal": dict(result),
    )


# ── execute_propose_next_user_step ────────────────────────────────────────


def test_propose_next_user_step_queued_er_succes(monkeypatch):
    _stub_delivery(monkeypatch, {"status": "queued", "session_id": "chat-1"})

    from core.services.runtime_action_executor import execute_propose_next_user_step
    result = execute_propose_next_user_step({"current_mode": "respond"})

    assert result.status == "proposed"
    assert result.error == ""
    assert "visible-proposal" in result.side_effects


def test_propose_next_user_step_blocked_forbliver_blocked(monkeypatch):
    _stub_delivery(monkeypatch, {"status": "blocked", "error": "no active session"})

    from core.services.runtime_action_executor import execute_propose_next_user_step
    result = execute_propose_next_user_step({"current_mode": "respond"})

    assert result.status == "blocked"
    assert "no active session" in result.error


# ── execute_promote_initiative_to_visible_lane ────────────────────────────


def test_promote_initiative_queued_er_succes(monkeypatch):
    _stub_delivery(monkeypatch, {"status": "queued", "session_id": "chat-1"})
    marked: list[str] = []
    monkeypatch.setattr(
        "core.services.runtime_action_executor.mark_acted",
        lambda initiative_id, **kw: marked.append(initiative_id),
    )

    from core.services.runtime_action_executor import (
        execute_promote_initiative_to_visible_lane,
    )
    result = execute_promote_initiative_to_visible_lane(
        {"initiative_id": "init-1", "focus": "Følg op på X"}
    )

    assert result.status == "proposed"
    assert marked == ["init-1"]


def test_promote_initiative_blocked_markerer_ikke_som_acted(monkeypatch):
    _stub_delivery(monkeypatch, {"status": "blocked", "error": "no active session"})
    marked: list[str] = []
    attempted: list[str] = []
    monkeypatch.setattr(
        "core.services.runtime_action_executor.mark_acted",
        lambda initiative_id, **kw: marked.append(initiative_id),
    )
    monkeypatch.setattr(
        "core.services.runtime_action_executor.mark_attempted",
        lambda initiative_id, **kw: attempted.append(initiative_id),
    )

    from core.services.runtime_action_executor import (
        execute_promote_initiative_to_visible_lane,
    )
    result = execute_promote_initiative_to_visible_lane(
        {"initiative_id": "init-1", "focus": "Følg op på X"}
    )

    assert result.status == "blocked"
    assert marked == []
    assert attempted == ["init-1"]


# ── emotional-gaten skriver til veto_events (side-3e59d5dbe2) ─────────────


def _stub_snapshot():
    from types import SimpleNamespace
    return SimpleNamespace(
        frustration=0.0, confidence=0.5, fatigue=0.95,
        primary_mood="neutral", intensity=0.0,
    )


def _stub_gate(monkeypatch, gated_action: str, reason: str):
    from core.services import runtime_action_executor as ex
    monkeypatch.setattr(ex, "read_emotional_snapshot", _stub_snapshot)
    monkeypatch.setattr(
        ex, "apply_emotional_controls",
        lambda *, kernel_action, snapshot: (gated_action, reason),
    )


def test_en_emotional_blokering_skriver_til_veto_events(monkeypatch):
    """Uden en række i veto_events findes intet event_id at armere imod."""
    _stub_gate(monkeypatch, "escalate_user", "frustration_threshold_exceeded")
    skrevet: dict = {}
    monkeypatch.setattr(
        "core.services.veto_gate.log_veto_event",
        lambda **kw: skrevet.update(kw) or "veto-test",
    )
    monkeypatch.setattr(
        "core.services.gate_override.consume_override", lambda t, f: None,
    )

    from core.services.runtime_action_executor import execute_runtime_action
    r = execute_runtime_action(action_id="bounded_self_check", payload={})

    assert r.status == "blocked"
    assert skrevet["tool_name"] == "bounded_self_check"
    assert skrevet["feeling"] == "frustration"
    assert skrevet["veto_result"] == "blocked"


def test_en_armeret_overstyring_slipper_emotional_gaten_igennem(monkeypatch):
    _stub_gate(monkeypatch, "escalate_user", "frustration_threshold_exceeded")
    logget: list = []
    monkeypatch.setattr(
        "core.services.veto_gate.log_veto_event", lambda **kw: logget.append(kw),
    )
    monkeypatch.setattr(
        "core.services.gate_override.consume_override",
        lambda t, f: "set efter" if (t, f) == ("bounded_self_check", "frustration") else None,
    )

    from core.services.runtime_action_executor import execute_runtime_action
    r = execute_runtime_action(action_id="bounded_self_check", payload={})

    assert r.status == "executed"
    assert logget == []  # en overstyring logger ingen ny blokering


def test_uden_armering_blokeres_den_stadig(monkeypatch):
    _stub_gate(monkeypatch, "escalate_user", "frustration_threshold_exceeded")
    monkeypatch.setattr(
        "core.services.gate_override.consume_override", lambda t, f: None,
    )

    from core.services.runtime_action_executor import execute_runtime_action
    r = execute_runtime_action(action_id="bounded_self_check", payload={})

    assert r.status == "blocked"
    assert "emotional-gate-blocked" in r.side_effects
    assert r.details["gate"] == "emotional_controls"
