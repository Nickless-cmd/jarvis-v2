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
