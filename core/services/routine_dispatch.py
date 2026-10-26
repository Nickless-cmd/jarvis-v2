"""Deterministic execution-path routing for queued Routine occurrences."""
from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass
from typing import Any

from core.runtime import db_routines
from core.services.routine_types import RoutineExecutionMode

logger = logging.getLogger(__name__)

_SESSION_LEASE_SECONDS = 900


@dataclass(frozen=True)
class RouteOutcome:
    path: str
    run_id: str
    reason: str = ""


def _classification(row: dict[str, Any]) -> dict[str, Any]:
    definition = dict(row.get("definition_snapshot") or {})
    delivery = dict(definition.get("delivery_policy") or {})
    return dict(delivery.get("classification") or {})


def resolve_owner_session(owner_user_id: str) -> tuple[str, str]:
    """Return (session, state); only a positive ownership stamp may wake."""
    owner = str(owner_user_id or "").strip()
    if not owner:
        return "", "unknown-owner"
    try:
        from core.identity.session_access import ejerstempel_tilhoerer_bruger
        from core.services.autonomous_sessions import is_system_session
        from core.services.chat_sessions import (
            get_session_owner,
            list_chat_sessions,
            parse_channel_from_session_title,
        )

        for item in list_chat_sessions(user_id=owner):
            session_id = str(item.get("id") or "").strip()
            stamped_owner = str(get_session_owner(session_id) or "").strip()
            if not session_id or not stamped_owner:
                continue
            if not ejerstempel_tilhoerer_bruger(stamped_owner, owner):
                continue
            if is_system_session(session_id):
                continue
            if parse_channel_from_session_title(str(item.get("title") or ""))[0] in {
                "discord", "telegram",
            }:
                continue
            return session_id, "valid"
        return "", "offline"
    except Exception as exc:  # ownership uncertainty must never select a chat
        logger.warning("routine dispatch: session ownership unavailable: %s", type(exc).__name__)
        return "", "unknown-owner"


def runtime_presence(session_id: str) -> tuple[str, str]:
    """Return idle/busy/unknown from shared runtime truth and cooldown state."""
    try:
        from core.services.in_flight_runs import levende_koersler

        if levende_koersler():
            return "busy", "active-run"
        from core.services.wakeup_dispatcher import _active_turn_blocks

        reason = str(_active_turn_blocks(session_id) or "")
        return ("busy", reason) if reason else ("idle", "")
    except Exception as exc:
        logger.warning("routine dispatch: runtime presence unavailable: %s", type(exc).__name__)
        return "unknown", "presence-unavailable"


def _context(row: dict[str, Any], generation: int):
    from core.services.routine_runner import RoutineRunner

    return RoutineRunner()._context(row, generation)


def _settle_session_run(
    *, routine_run_id: str, generation: int, routine_id: str,
    owner_user_id: str, outcome: str, visible_run_id: str,
    session_id: str, error: str = "",
) -> None:
    evidence = json.dumps({
        "execution_path": "session",
        "visible_run_id": visible_run_id,
        "session_id": session_id,
        "outcome": outcome,
    }, sort_keys=True).encode("utf-8")
    if outcome == "completed":
        db_routines.complete_run_success(
            routine_run_id,
            expected_generation=generation,
            result=evidence,
            delivery_channel=None,
        )
        return
    db_routines.transition_run(
        routine_run_id,
        to_status="failed",
        expected_generation=generation,
        result=evidence,
        diagnostic_code=f"session_{outcome}",
    )
    from core.services.routine_inbox import project_event_to_inbox

    project_event_to_inbox({
        "owner_user_id": owner_user_id,
        "routine_id": routine_id,
        "run_id": routine_run_id,
        "event_id": f"{routine_run_id}:session-{outcome}",
        "event_type": "failed",
        "evidence": str(error or "")[:200],
    })


def _dispatch_session_claimed(row: dict[str, Any], *, session_id: str) -> RouteOutcome:
    run_id = str(row["run_id"])
    holder = f"routine-session-{uuid.uuid4().hex}"
    claim = db_routines.claim_run(
        run_id, holder=holder, lease_seconds=_SESSION_LEASE_SECONDS,
    )
    if claim is None:
        return RouteOutcome("pending", run_id, "already-claimed")
    generation = int(claim["lease_generation"])
    private = db_routines.get_run(run_id, decrypt_for=str(claim["owner_user_id"]))
    if private is None:
        db_routines.release_run_claim(
            run_id, holder=holder, expected_generation=generation,
        )
        return RouteOutcome("pending", run_id, "run-unavailable")
    context = _context(private, generation)
    definition = dict(private["definition_snapshot"])
    permission = dict(definition.get("permission_policy") or {})
    from core.services.routine_prompt import build_session_routine_prompt
    from core.services.visible_autonomous_run import start_autonomous_run

    def completed(**result: Any) -> None:
        try:
            _settle_session_run(
                routine_run_id=run_id,
                generation=generation,
                routine_id=str(claim["routine_id"]),
                owner_user_id=str(claim["owner_user_id"]),
                outcome=str(result.get("outcome") or "failed"),
                visible_run_id=str(result.get("visible_run_id") or ""),
                session_id=str(result.get("session_id") or session_id),
                error=str(result.get("error") or ""),
            )
        except Exception:
            logger.exception("routine dispatch: session completion could not settle %s", run_id)

    try:
        started = start_autonomous_run(
            build_session_routine_prompt(
                context, instruction=bytes(definition["instruction"]),
            ),
            session_id=session_id,
            origin="routine",
            task_id=run_id,
            max_tool_calls=int(permission.get("max_tool_calls") or 0),
            max_seconds=float(permission.get("max_seconds") or 600),
            tool_scope=str(definition.get("capability_scope") or "chat"),
            force_user_id=str(claim["owner_user_id"]),
            completion_callback=completed,
        )
    except Exception:
        db_routines.release_run_claim(
            run_id, holder=holder, expected_generation=generation,
        )
        raise
    if not started:
        db_routines.release_run_claim(
            run_id, holder=holder, expected_generation=generation,
        )
        return RouteOutcome("pending", run_id, "session-start-refused")
    db_routines.append_run_event(
        run_id=run_id,
        kind="session_dispatched",
        payload={"session_id": session_id},
        event_id=f"{run_id}:session-dispatched",
        expected_generation=generation,
    )
    return RouteOutcome("session", run_id)


def _dispatch_session(row: dict[str, Any], *, session_id: str) -> RouteOutcome:
    """Serialize the final presence check and synchronous visible-run birth."""
    from core.services.background_start_reservation import reserve_background_start

    run_id = str(row["run_id"])
    with reserve_background_start(session_id) as reservation:
        if not reservation.acquired:
            return RouteOutcome("pending", run_id, reservation.reason)
        return _dispatch_session_claimed(row, session_id=session_id)


def route_next(runner: Any) -> Any:
    """Route one occurrence. Unknown state leaves it visibly queued."""
    queued = runner.repository.next_queued_run()
    if queued is None:
        return None
    run_id = str(queued.run_id)
    metadata = db_routines.get_run(run_id)
    if metadata is None:
        return None
    owner = str(metadata.get("owner_user_id") or "").strip()
    if not owner:
        return RouteOutcome("pending", run_id, "unknown-owner")
    private = db_routines.get_run(run_id, decrypt_for=owner)
    if private is None:
        return RouteOutcome("pending", run_id, "run-unavailable")
    mode_token = str(_classification(private).get("execution_mode") or "background")
    try:
        mode = RoutineExecutionMode(mode_token)
    except ValueError:
        logger.warning("routine dispatch: unknown execution mode %r", mode_token)
        return RouteOutcome("pending", run_id, "unknown-execution-mode")
    if mode is RoutineExecutionMode.BACKGROUND:
        return runner.run_once(run_id)

    session_id, session_state = resolve_owner_session(owner)
    if session_state == "unknown-owner":
        return RouteOutcome("pending", run_id, session_state)
    if not session_id:
        if mode is RoutineExecutionMode.ADAPTIVE:
            return runner.run_once(run_id)
        return RouteOutcome("pending", run_id, "no-valid-session")

    presence, reason = runtime_presence(session_id)
    if presence == "unknown":
        return RouteOutcome("pending", run_id, reason)
    if presence == "busy":
        if mode is RoutineExecutionMode.ADAPTIVE:
            return runner.run_once(run_id)
        return RouteOutcome("pending", run_id, reason)
    return _dispatch_session(private, session_id=session_id)


__all__ = ["RouteOutcome", "resolve_owner_session", "route_next", "runtime_presence"]
