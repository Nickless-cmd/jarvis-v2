"""Pending tool-approval resolution for visible runs.

Boy Scout-udtrækning (2026-07-07): udskilt fra ``core/services/visible_runs.py``.
Ren KODE-FLYTNING — ingen logik-ændring. ``resolve_pending_approval`` re-eksporteres
tilbage til ``visible_runs`` i bunden af den fil, så eksisterende imports
(``apps/api/.../chat.py``, ``cowork.py``) og test-kald mod ``visible_runs.X`` virker.

Main-residente symboler der (a) er delt state (``_PENDING_APPROVALS``,
``_persist_pending_approvals`` — brugt af ``_stream_visible_run``) eller (b)
monkeypatches i tests (``append_chat_message``, ``_get_visible_approval_state``,
``_set_visible_approval_state``) refereres via ``_vr.X`` INDE i funktions-kroppen
(lazy) → samme objekt-identitet + patches ses på kald-tidspunkt.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

import core.services.visible_runs as _vr

from core.eventbus.bus import event_bus

logger = logging.getLogger(__name__)


def resolve_pending_approval(approval_id: str, *, approved: bool) -> dict:
    """Resolve a pending tool approval.

    Resolves a pending approval in shared runtime state so a blocked streaming
    generator can resume even if the approve/deny request lands on another worker.
    """
    from core.tools.simple_tools import execute_tool_force, format_tool_result_for_model

    pending = _vr._PENDING_APPROVALS.pop(approval_id, None)
    if pending is not None:
        _vr._persist_pending_approvals()
    shared_pending = _vr._get_visible_approval_state(approval_id)
    if not pending and shared_pending:
        pending = shared_pending
    if not pending:
        return {"error": "Approval not found or expired", "status": "error"}
    if str(pending.get("status") or "pending") not in {"", "pending"}:
        return {"error": "Approval already resolved", "status": "error"}

    # ── Permission-classifier GOLD outcome (harness Part E) ──
    # The owner just approved/denied a surfaced mutating action → the real signal.
    # Compare against the earlier stashed prediction. Fail-open, never blocks.
    try:
        from core.services import permission_classifier as _pc
        _pc_stashed = _pc.pop_prediction(approval_id)
        if _pc_stashed:
            _pc.record_prediction_outcome(
                _pc_stashed["tool"],
                predicted=_pc_stashed["predicted"],
                actual="approve" if approved else "deny",
                is_owner_gold=True,
            )
    except Exception:
        pass

    if not approved:
        _vr._set_visible_approval_state(
            approval_id,
            {
                **pending,
                "approval_id": approval_id,
                "status": "denied",
                "approved": False,
                "resolved_at": datetime.now(UTC).isoformat(),
            },
        )
        event_bus.publish("tool.approval_resolved", {
            "approval_id": approval_id,
            "tool": pending["tool_name"],
            "approved": False,
            "status": "denied",
        })
        # Fire-and-forget: approval denial is both a rupture (relational) and
        # a regret (cognitive — Jarvis predicted user would approve, but didn't).
        _tool_name = pending.get("tool_name") or ""
        _session_id = str(pending.get("session_id") or "")
        try:
            from core.services.rupture_repair import (
                _ensure_tables as _rupture_ensure,
                _rupture_key,
                _upsert_rupture,
            )
            from core.runtime.db import connect as _connect
            _rupture_ensure()
            topic = f"approval:{_tool_name}"
            rkey = _rupture_key(source_kind="approval_rejected", topic=topic)
            from datetime import UTC as _UTC, datetime as _dt
            _now = _dt.now(_UTC).isoformat().replace("+00:00", "Z")
            with _connect() as _conn:
                _upsert_rupture(
                    _conn,
                    rupture_key=rkey,
                    topic=topic,
                    source_kind="approval_rejected",
                    reason=f"User denied approval for tool {_tool_name}",
                    evidence={"approval_id": approval_id, "tool": _tool_name},
                    tension_level=0.7,
                    linked_run_id=str(pending.get("run_id") or ""),
                    linked_session_id=_session_id,
                    linked_incident_id="",
                    status="open",
                    last_seen_at=_now,
                )
                _conn.commit()
        except Exception:
            pass
        try:
            from core.services.regret_engine import open_or_update_regret
            open_or_update_regret(
                decision_id=f"approval:{approval_id}",
                context={"tool": _tool_name, "approval_id": approval_id},
                expected_outcome="approved",
                actual_outcome="rejected",
                lesson=f"Bruger afviste tool-call til {_tool_name}",
                confidence_before=0.7,
                confidence_after=0.1,
                linked_run_id=str(pending.get("run_id") or ""),
                linked_session_id=_session_id,
            )
        except Exception:
            pass
        return {"status": "denied", "tool": pending["tool_name"]}

    result = execute_tool_force(pending["tool_name"], pending["arguments"])
    result_text = format_tool_result_for_model(pending["tool_name"], result)

    # 2026-05-24 (Claude): persist tool result as role=tool in chat
    # transcript here too. Previously this was only done inside the
    # streaming run's tool-loop (visible_runs.py line ~1095). When the
    # streaming run timed out or disconnected before the user clicked
    # Approve, the tool would execute on approval but the result never
    # reached chat_messages — leaving Jarvis blind to it on the next
    # turn. Now we append from here AND set a dedupe marker so the
    # streaming path can skip its own append when it sees we already
    # persisted (avoiding duplicate role=tool messages when the stream
    # is still active and racing with resolve_pending_approval).
    chat_persisted = False
    session_id = str(pending.get("session_id") or "")
    if session_id:
        try:
            # Use the module-level import so monkeypatching in tests works.
            _vr.append_chat_message(
                session_id=session_id,
                role="tool",
                content=result_text,
                tool_name=str(pending.get("tool_name") or ""),
                tool_arguments=dict(pending.get("arguments") or {}),
            )
            chat_persisted = True
        except Exception:
            logger.exception(
                "resolve_pending_approval: chat persistence failed for %s",
                approval_id,
            )

    event_bus.publish("tool.approval_resolved", {
        "approval_id": approval_id,
        "tool": pending["tool_name"],
        "approved": True,
        "status": result.get("status", "ok"),
    })
    _vr._set_visible_approval_state(
        approval_id,
        {
            **pending,
            "approval_id": approval_id,
            "status": "approved",
            "approved": True,
            "resolved_at": datetime.now(UTC).isoformat(),
            "tool_status": result.get("status", "ok"),
            "result_text": result_text,
            "chat_persisted": chat_persisted,
        },
    )

    return {
        "status": result.get("status", "ok"),
        "tool": pending["tool_name"],
        "result_text": result_text,
        "chat_persisted": chat_persisted,
    }
