from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from apps.api.jarvis_api.services.chat_sessions import get_chat_session, list_chat_sessions
from core.eventbus.bus import event_bus
from core.runtime.db import (
    list_runtime_world_model_signals,
    update_runtime_world_model_signal_status,
    upsert_runtime_world_model_signal,
)

_CONFIDENCE_RANKS = {"low": 1, "medium": 2, "high": 3}
_SOURCE_KIND_RANKS = {
    "runtime-derived-support": 1,
    "session-evidence": 2,
    "repeated-session-evidence": 3,
    "user-explicit": 4,
}
_STALE_AFTER_DAYS = 10


def track_runtime_world_model_signals_for_visible_turn(
    *,
    session_id: str | None,
    run_id: str,
    user_message: str,
) -> dict[str, object]:
    normalized_session_id = str(session_id or "").strip()
    normalized_message = " ".join(str(user_message or "").split()).strip()
    if not normalized_message and not normalized_session_id:
        return {
            "created": 0,
            "updated": 0,
            "corrected": 0,
            "items": [],
            "summary": "No world-model evidence was available.",
        }

    corrected = _apply_correction_signals(user_message=normalized_message)
    signals = _extract_world_model_candidates(
        user_message=normalized_message,
        session_id=normalized_session_id,
    )
    items = _persist_world_model_signals(
        signals=signals,
        session_id=normalized_session_id,
        run_id=run_id,
    )
    return {
        "created": len([item for item in items if item.get("was_created")]),
        "updated": len([item for item in items if item.get("was_updated")]),
        "corrected": corrected,
        "items": items,
        "summary": (
            f"Tracked {len(items)} bounded world-model signals and corrected {corrected}."
            if items or corrected
            else "No bounded world-model assumption warranted tracking."
        ),
    }


def refresh_runtime_world_model_signal_statuses() -> dict[str, int]:
    now = datetime.now(UTC)
    refreshed = 0
    for item in list_runtime_world_model_signals(limit=40):
        if str(item.get("status") or "") not in {"active", "uncertain"}:
            continue
        updated_at = _parse_dt(str(item.get("updated_at") or item.get("created_at") or ""))
        if updated_at is None or updated_at > now - timedelta(days=_STALE_AFTER_DAYS):
            continue
        refreshed_item = update_runtime_world_model_signal_status(
            str(item.get("signal_id") or ""),
            status="stale",
            updated_at=now.isoformat(),
            status_reason="Marked stale after bounded inactivity window.",
        )
        if refreshed_item is not None:
            refreshed += 1
            event_bus.publish(
                "world_model_signal.stale",
                {
                    "signal_id": refreshed_item.get("signal_id"),
                    "signal_type": refreshed_item.get("signal_type"),
                    "status": refreshed_item.get("status"),
                    "summary": refreshed_item.get("summary"),
                },
            )
    return {"stale_marked": refreshed}


def build_runtime_world_model_signal_surface(*, limit: int = 8) -> dict[str, object]:
    refresh_runtime_world_model_signal_statuses()
    items = list_runtime_world_model_signals(limit=max(limit, 1))
    active = [item for item in items if str(item.get("status") or "") == "active"]
    uncertain = [item for item in items if str(item.get("status") or "") == "uncertain"]
    corrected = [item for item in items if str(item.get("status") or "") == "corrected"]
    stale = [item for item in items if str(item.get("status") or "") == "stale"]
    superseded = [item for item in items if str(item.get("status") or "") == "superseded"]
    ordered_items = [*active, *uncertain, *corrected, *stale, *superseded]
    latest = next(iter(active or uncertain or corrected or stale or superseded), None)
    return {
        "active": bool(active),
        "items": ordered_items,
        "summary": {
            "active_count": len(active),
            "uncertain_count": len(uncertain),
            "corrected_count": len(corrected),
            "stale_count": len(stale),
            "superseded_count": len(superseded),
            "current_signal": str((latest or {}).get("title") or "No active world-model signal"),
            "current_status": str((latest or {}).get("status") or "none"),
        },
    }


def _extract_world_model_candidates(*, user_message: str, session_id: str) -> list[dict[str, object]]:
    signals: list[dict[str, object]] = []

    project_context = _project_context_signal(user_message, session_id=session_id)
    if project_context:
        signals.append(project_context)

    workspace_scope = _workspace_scope_signal(user_message)
    if workspace_scope:
        signals.append(workspace_scope)

    deduped: dict[str, dict[str, object]] = {}
    for item in signals:
        key = str(item.get("canonical_key") or "")
        if not key:
            continue
        current = deduped.get(key)
        if current is None:
            deduped[key] = item
            continue
        current_rank = _rank(_CONFIDENCE_RANKS, str(current.get("confidence") or ""))
        next_rank = _rank(_CONFIDENCE_RANKS, str(item.get("confidence") or ""))
        if next_rank >= current_rank:
            deduped[key] = item
    return list(deduped.values())


def _project_context_signal(message: str, *, session_id: str) -> dict[str, object] | None:
    text = (message or "").strip()
    lower = text.lower()
    if not any(marker in lower for marker in ("bygger jarvis", "building jarvis", "jarvis together")):
        return None
    history = _recent_user_message_history(limit_sessions=6, per_session_limit=4)
    support_count = 0
    matching_sessions: set[str] = set()
    for item in history:
        if _matches_project_context(str(item.get("content") or "")):
            support_count += 1
            if item.get("session_id"):
                matching_sessions.add(str(item["session_id"]))
    if session_id:
        matching_sessions.add(session_id)
    status = "active" if support_count >= 2 else "uncertain"
    confidence = "high" if support_count >= 2 and len(matching_sessions) > 1 else "medium"
    source_kind = "repeated-session-evidence" if support_count >= 2 else "session-evidence"
    return {
        "signal_type": "project-context-assumption",
        "canonical_key": "world-model:project-context:building-jarvis-together",
        "status": status,
        "title": "Current project context: building Jarvis together",
        "summary": "Jarvis is carrying a bounded assumption that the current work is building Jarvis together.",
        "rationale": "Repeated visible project-context cues suggest this is part of Jarvis' active situational understanding.",
        "source_kind": source_kind,
        "confidence": confidence,
        "evidence_summary": _quote(text),
        "support_summary": f"{support_count} matching project-context cues across {max(len(matching_sessions), 1)} session(s).",
        "support_count": max(support_count, 1),
        "session_count": max(len(matching_sessions), 1),
        "status_reason": "Repeated project-context cues keep this assumption active." if status == "active" else "Single-session project-context cue kept as uncertain situational understanding.",
    }


def _workspace_scope_signal(message: str) -> dict[str, object] | None:
    text = (message or "").strip()
    lower = text.lower()
    if not any(marker in lower for marker in ("inside jarvis-v2", "inside jarvis v2", "kun i jarvis-v2", "work only inside jarvis-v2")):
        return None
    return {
        "signal_type": "workspace-scope-assumption",
        "canonical_key": "world-model:workspace-scope:jarvis-v2",
        "status": "active",
        "title": "Current workspace scope: jarvis-v2",
        "summary": "Jarvis is carrying a bounded assumption that the active workspace scope is jarvis-v2.",
        "rationale": "Explicit workspace-scope instruction is a situational assumption Jarvis should carry visibly while it remains relevant.",
        "source_kind": "user-explicit",
        "confidence": "high",
        "evidence_summary": _quote(text),
        "support_summary": "Explicit workspace-scope instruction from visible user message.",
        "support_count": 1,
        "session_count": 1,
        "status_reason": "Explicit situational scope instruction is active.",
    }


def _persist_world_model_signals(
    *,
    signals: list[dict[str, object]],
    session_id: str,
    run_id: str,
) -> list[dict[str, object]]:
    now = datetime.now(UTC).isoformat()
    persisted: list[dict[str, object]] = []
    for signal in signals:
        persisted_item = upsert_runtime_world_model_signal(
            signal_id=f"worldmodel-{uuid4().hex}",
            signal_type=str(signal.get("signal_type") or "world-model-signal"),
            canonical_key=str(signal.get("canonical_key") or ""),
            status=str(signal.get("status") or "uncertain"),
            title=str(signal.get("title") or ""),
            summary=str(signal.get("summary") or ""),
            rationale=str(signal.get("rationale") or ""),
            source_kind=str(signal.get("source_kind") or ""),
            confidence=str(signal.get("confidence") or "low"),
            evidence_summary=str(signal.get("evidence_summary") or ""),
            support_summary=str(signal.get("support_summary") or ""),
            support_count=int(signal.get("support_count") or 1),
            session_count=int(signal.get("session_count") or 1),
            created_at=now,
            updated_at=now,
            status_reason=str(signal.get("status_reason") or ""),
            run_id=run_id,
            session_id=session_id,
        )
        if persisted_item.get("was_created"):
            event_bus.publish(
                "world_model_signal.created",
                {
                    "signal_id": persisted_item.get("signal_id"),
                    "signal_type": persisted_item.get("signal_type"),
                    "status": persisted_item.get("status"),
                    "summary": persisted_item.get("summary"),
                },
            )
        elif persisted_item.get("was_updated"):
            event_bus.publish(
                "world_model_signal.updated",
                {
                    "signal_id": persisted_item.get("signal_id"),
                    "signal_type": persisted_item.get("signal_type"),
                    "status": persisted_item.get("status"),
                    "summary": persisted_item.get("summary"),
                },
            )
        persisted.append(persisted_item)
    return persisted


def _apply_correction_signals(*, user_message: str) -> int:
    lower = str(user_message or "").lower()
    corrected = 0
    corrections = [
        (
            "world-model:project-context:building-jarvis-together",
            any(marker in lower for marker in ("bygger ikke jarvis", "not building jarvis", "ikke jarvis sammen længere", "not jarvis together anymore")),
        ),
        (
            "world-model:workspace-scope:jarvis-v2",
            any(marker in lower for marker in ("ikke kun i jarvis-v2", "not inside jarvis-v2", "not only inside jarvis-v2", "ikke i jarvis-v2 længere")),
        ),
    ]
    now = datetime.now(UTC).isoformat()
    active_items = list_runtime_world_model_signals(limit=20)
    for canonical_key, should_correct in corrections:
        if not should_correct:
            continue
        for item in active_items:
            if str(item.get("canonical_key") or "") != canonical_key:
                continue
            if str(item.get("status") or "") not in {"active", "uncertain"}:
                continue
            updated = update_runtime_world_model_signal_status(
                str(item.get("signal_id") or ""),
                status="corrected",
                updated_at=now,
                status_reason="User explicitly corrected this situational assumption.",
            )
            if updated is None:
                continue
            corrected += 1
            event_bus.publish(
                "world_model_signal.corrected",
                {
                    "signal_id": updated.get("signal_id"),
                    "signal_type": updated.get("signal_type"),
                    "status": updated.get("status"),
                    "summary": updated.get("summary"),
                },
            )
    return corrected


def _recent_user_message_history(*, limit_sessions: int, per_session_limit: int) -> list[dict[str, object]]:
    items: list[dict[str, object]] = []
    for session in list_chat_sessions()[: max(limit_sessions, 1)]:
        session_id = str(session.get("id") or "")
        if not session_id:
            continue
        detail = get_chat_session(session_id)
        if not detail:
            continue
        user_messages = [
            {
                "session_id": session_id,
                "content": " ".join(str(message.get("content") or "").split()).strip(),
            }
            for message in reversed(detail.get("messages") or [])
            if str(message.get("role") or "") == "user"
        ]
        items.extend(user_messages[: max(per_session_limit, 1)])
    return items


def _matches_project_context(message: str) -> bool:
    lower = str(message or "").lower()
    return any(marker in lower for marker in ("bygger jarvis", "building jarvis", "jarvis together"))


def _parse_dt(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(str(value or "").replace("Z", "+00:00"))
    except ValueError:
        return None


def _rank(ranks: dict[str, int], value: str) -> int:
    return int(ranks.get(str(value or "").strip().lower(), 0))


def _quote(text: str) -> str:
    normalized = " ".join(str(text or "").split()).strip()
    if len(normalized) > 180:
        normalized = normalized[:179].rstrip() + "…"
    return f'"{normalized}"' if normalized else ""
