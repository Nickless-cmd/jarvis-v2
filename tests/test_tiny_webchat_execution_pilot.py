from __future__ import annotations

import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from apps.api.jarvis_api.services.chat_sessions import (
    create_chat_session,
    get_chat_session,
)


def _insert_autonomy_question_pressure(db, *, weight: str = "high") -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_autonomy_pressure_signal(
        signal_id=f"autonomy-pressure-{uuid4().hex}",
        signal_type="autonomy-pressure",
        canonical_key="autonomy-pressure:question-pressure",
        status="active",
        title="Autonomy pressure: question carry",
        summary="Bounded autonomy pressure is carrying question-worthiness.",
        rationale="Validation autonomy pressure",
        source_kind="runtime-derived-support",
        confidence="high",
        evidence_summary="question pressure evidence",
        support_summary=(
            "autonomy-pressure-state=question-worthy | autonomy-pressure-type=question-pressure | "
            f"autonomy-pressure-weight={weight} | autonomy-pressure-confidence=high | source-anchor=autonomy-anchor"
        ),
        support_count=2,
        session_count=1,
        created_at=now,
        updated_at=now,
        status_reason="Validation autonomy pressure status",
        run_id="test-run",
        session_id="test-session",
    )


def _insert_question_loop(db, *, readiness: str = "high") -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_proactive_loop_lifecycle_signal(
        signal_id=f"question-loop-{uuid4().hex}",
        signal_type="proactive-loop-lifecycle",
        canonical_key="proactive-loop-lifecycle:question-loop:current-thread",
        status="active",
        title="Proactive loop lifecycle: Current thread",
        summary="Bounded proactive-loop lifecycle is carrying a question-capable thread.",
        rationale="Validation proactive loop lifecycle",
        source_kind="runtime-derived-support",
        confidence="high",
        evidence_summary="question loop evidence",
        support_summary=(
            "loop-state=loop-question-worthy | loop-kind=question-loop | loop-focus=current thread | "
            f"loop-weight=high | loop-confidence=high | question-readiness={readiness} | closure-readiness=low | source-anchor=loop-anchor"
        ),
        support_count=2,
        session_count=1,
        created_at=now,
        updated_at=now,
        status_reason="Validation proactive loop lifecycle status",
        run_id="test-run",
        session_id="test-session",
    )


def _insert_question_gate(db) -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_proactive_question_gate(
        gate_id=f"proactive-question-gate-{uuid4().hex}",
        gate_type="proactive-question-gate",
        canonical_key="proactive-question-gate:current-thread",
        status="active",
        title="Proactive question gate: current thread",
        summary="Bounded proactive-question gating is surfacing a runtime question candidate only. This is not send permission and not proactive execution.",
        rationale="Validation proactive-question gate",
        source_kind="runtime-derived-support",
        confidence="high",
        evidence_summary="question gate evidence",
        support_summary=(
            "question-gate-state=question-gated-candidate | question-gate-reason=relationally-held | "
            "question-gate-weight=high | question-gate-confidence=high | send-permission-state=gated-candidate-only | "
            "source-anchor=question-gate-anchor"
        ),
        status_reason="Validation proactive-question gate status",
        run_id="test-run",
        session_id="test-session",
        support_count=2,
        session_count=1,
        created_at=now,
        updated_at=now,
    )


def _policy(*, allow_ping: bool = True, ping_channel: str = "webchat", kill_switch: str = "enabled") -> dict[str, object]:
    return {
        "allow_ping": allow_ping,
        "ping_channel": ping_channel,
        "kill_switch": kill_switch,
    }


def test_execution_pilot_stays_empty_without_valid_question_gate(
    isolated_runtime,
) -> None:
    pilot = isolated_runtime.tiny_webchat_execution_pilot

    result = pilot.maybe_run_tiny_webchat_execution_pilot(
        policy=_policy(),
        heartbeat_tick_id="tick-1",
        decision_summary="Heartbeat wants to ping.",
        ping_text="",
    )
    surface = pilot.build_runtime_webchat_execution_pilot_surface(limit=8)

    assert result["created"] == 0
    assert result["delivery_state"] == "skipped"
    assert surface["active"] is False
    assert surface["items"] == []
    assert isolated_runtime.db.runtime_contract_file_write_counts() == {}


def test_execution_pilot_kill_switch_blocks_webchat_delivery(
    isolated_runtime,
) -> None:
    db = isolated_runtime.db
    pilot = isolated_runtime.tiny_webchat_execution_pilot

    _insert_autonomy_question_pressure(db)
    _insert_question_loop(db)
    _insert_question_gate(db)
    session = create_chat_session(title="Pilot test")

    result = pilot.maybe_run_tiny_webchat_execution_pilot(
        policy=_policy(kill_switch="disabled"),
        heartbeat_tick_id="tick-kill-switch",
        decision_summary="Heartbeat wants to ping.",
        ping_text="",
    )
    surface = pilot.build_runtime_webchat_execution_pilot_surface(limit=8)
    chat = get_chat_session(session["id"])

    assert result["created"] == 1
    assert result["delivery_state"] == "blocked"
    assert result["blocked_reason"] == "kill-switch-disabled"
    assert surface["active"] is True
    assert surface["items"][0]["kill_switch_state"] == "disabled"
    assert surface["items"][0]["delivery_state"] == "blocked"
    assert chat is not None
    assert chat["messages"] == []


def test_execution_pilot_respects_cooldown_and_webchat_only_send(
    isolated_runtime,
) -> None:
    db = isolated_runtime.db
    pilot = isolated_runtime.tiny_webchat_execution_pilot

    _insert_autonomy_question_pressure(db)
    _insert_question_loop(db)
    _insert_question_gate(db)
    session = create_chat_session(title="Pilot cooldown")

    first = pilot.maybe_run_tiny_webchat_execution_pilot(
        policy=_policy(),
        heartbeat_tick_id="tick-send-1",
        decision_summary="Heartbeat wants to ping.",
        ping_text="",
    )
    second = pilot.maybe_run_tiny_webchat_execution_pilot(
        policy=_policy(),
        heartbeat_tick_id="tick-send-2",
        decision_summary="Heartbeat wants to ping again.",
        ping_text="",
    )
    chat = get_chat_session(session["id"])
    surface = pilot.build_runtime_webchat_execution_pilot_surface(limit=8)

    assert first["delivery_state"] == "sent"
    assert second["delivery_state"] == "blocked"
    assert second["blocked_reason"] == "cooldown-active"
    assert chat is not None
    assert len(chat["messages"]) == 1
    assert chat["messages"][0]["role"] == "assistant"
    assert "Hvad vil du helst have" in chat["messages"][0]["content"]
    assert surface["summary"]["sent_count"] >= 1
    assert surface["summary"]["current_cooldown_state"] == "cooling-down"


def test_execution_pilot_blocks_when_channel_is_not_webchat(
    isolated_runtime,
) -> None:
    db = isolated_runtime.db
    pilot = isolated_runtime.tiny_webchat_execution_pilot

    _insert_autonomy_question_pressure(db)
    _insert_question_loop(db)
    _insert_question_gate(db)
    create_chat_session(title="Pilot non-webchat")

    result = pilot.maybe_run_tiny_webchat_execution_pilot(
        policy=_policy(ping_channel="internal-only"),
        heartbeat_tick_id="tick-non-webchat",
        decision_summary="Heartbeat wants to ping.",
        ping_text="",
    )

    assert result["delivery_state"] == "blocked"
    assert result["blocked_reason"] == "webchat-only-channel-required"


def test_execution_pilot_is_exposed_in_mission_control_and_stays_non_authoritative(
    isolated_runtime,
) -> None:
    db = isolated_runtime.db
    pilot = isolated_runtime.tiny_webchat_execution_pilot
    mission_control = isolated_runtime.mission_control

    _insert_autonomy_question_pressure(db)
    _insert_question_loop(db)
    _insert_question_gate(db)
    create_chat_session(title="Pilot mission control")

    pilot.maybe_run_tiny_webchat_execution_pilot(
        policy=_policy(),
        heartbeat_tick_id="tick-mc",
        decision_summary="Heartbeat wants to ping.",
        ping_text="",
    )

    development = mission_control.mc_jarvis()["development"]["webchat_execution_pilot"]
    runtime = mission_control.mc_runtime()["runtime_webchat_execution_pilot"]

    assert development["active"] is True
    assert runtime["active"] is True
    assert runtime["summary"]["planner_authority_state"] == "not-planner-authority"
    assert runtime["summary"]["proactive_execution_state"] == "tiny-governed-webchat-only"
    assert runtime["summary"]["discord_execution_state"] == "not-enabled"
    assert isolated_runtime.db.runtime_contract_file_write_counts() == {}
