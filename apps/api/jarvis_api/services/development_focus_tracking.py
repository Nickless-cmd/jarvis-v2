from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from apps.api.jarvis_api.services.chat_sessions import get_chat_session, list_chat_sessions
from core.eventbus.bus import event_bus
from core.runtime.db import (
    get_private_development_state,
    get_private_reflective_selection,
    get_private_self_model,
    get_runtime_development_focus,
    list_runtime_development_focuses,
    supersede_runtime_development_focuses,
    update_runtime_development_focus_status,
    upsert_runtime_development_focus,
)

_CONFIDENCE_RANKS = {"low": 1, "medium": 2, "high": 3}
_SOURCE_KIND_RANKS = {
    "runtime-derived-support": 1,
    "single-session-pattern": 2,
    "repeated-user-correction": 3,
    "user-explicit": 4,
}
_STALE_AFTER_DAYS = 10


def track_runtime_development_focuses_for_visible_turn(
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
            "completed": 0,
            "items": [],
            "summary": "No development focus evidence was available.",
        }

    completed = _apply_completion_signals(
        user_message=normalized_message,
        session_id=normalized_session_id,
    )

    candidates = _extract_focus_candidates(
        user_message=normalized_message,
        session_id=normalized_session_id,
    )
    items = _persist_focuses(
        focuses=candidates,
        session_id=normalized_session_id,
        run_id=run_id,
    )
    return {
        "created": len([item for item in items if item.get("was_created")]),
        "updated": len([item for item in items if item.get("was_updated")]),
        "completed": completed,
        "items": items,
        "summary": (
            f"Tracked {len(items)} bounded development focus signals and completed {completed}."
            if items or completed
            else "No development focus warranted tracking."
        ),
    }


def refresh_runtime_development_focus_statuses() -> dict[str, int]:
    now = datetime.now(UTC)
    refreshed = 0
    for item in list_runtime_development_focuses(limit=40):
        if str(item.get("status") or "") != "active":
            continue
        updated_at = _parse_dt(str(item.get("updated_at") or item.get("created_at") or ""))
        if updated_at is None or updated_at > now - timedelta(days=_STALE_AFTER_DAYS):
            continue
        refreshed_item = upsert_runtime_development_focus(
            focus_id=str(item.get("focus_id") or ""),
            focus_type=str(item.get("focus_type") or ""),
            canonical_key=str(item.get("canonical_key") or ""),
            status="stale",
            title=str(item.get("title") or ""),
            summary=str(item.get("summary") or ""),
            rationale=str(item.get("rationale") or ""),
            source_kind=str(item.get("source_kind") or ""),
            confidence=str(item.get("confidence") or ""),
            evidence_summary=str(item.get("evidence_summary") or ""),
            support_summary=str(item.get("support_summary") or ""),
            support_count=int(item.get("support_count") or 1),
            session_count=int(item.get("session_count") or 1),
            created_at=str(item.get("created_at") or now.isoformat()),
            updated_at=now.isoformat(),
            status_reason="Marked stale after bounded inactivity window.",
            run_id=str(item.get("run_id") or ""),
            session_id=str(item.get("session_id") or ""),
        )
        if refreshed_item.get("was_updated"):
            refreshed += 1
            event_bus.publish(
                "runtime.development_focus_stale",
                {
                    "focus_id": refreshed_item.get("focus_id"),
                    "focus_type": refreshed_item.get("focus_type"),
                    "status": refreshed_item.get("status"),
                    "summary": refreshed_item.get("summary"),
                    "status_reason": refreshed_item.get("status_reason"),
                },
            )
    return {"stale_marked": refreshed}


def build_runtime_development_focus_surface(*, limit: int = 8) -> dict[str, object]:
    refresh_runtime_development_focus_statuses()
    items = list_runtime_development_focuses(limit=max(limit, 1))
    active = [item for item in items if str(item.get("status") or "") == "active"]
    stale = [item for item in items if str(item.get("status") or "") == "stale"]
    completed = [item for item in items if str(item.get("status") or "") == "completed"]
    superseded = [item for item in items if str(item.get("status") or "") == "superseded"]
    ordered_items = [*active, *stale, *completed, *superseded]
    latest = next(iter(active or stale or completed or superseded), None)
    return {
        "active": bool(active),
        "items": ordered_items,
        "summary": {
            "active_count": len(active),
            "stale_count": len(stale),
            "completed_count": len(completed),
            "superseded_count": len(superseded),
            "current_focus": str((latest or {}).get("title") or "No active development focus"),
            "current_status": str((latest or {}).get("status") or "none"),
        },
    }


def _extract_focus_candidates(
    *,
    user_message: str,
    session_id: str,
) -> list[dict[str, object]]:
    focuses: list[dict[str, object]] = []
    explicit = _explicit_learning_focus(user_message)
    if explicit:
        focuses.append(_enrich_focus_support(explicit, session_id=session_id))

    correction = _repeated_correction_focus(user_message, session_id=session_id)
    if correction:
        focuses.append(correction)

    runtime_focus = _runtime_development_focus()
    if runtime_focus:
        focuses.append(runtime_focus)

    deduped: dict[str, dict[str, object]] = {}
    for item in focuses:
        key = str(item.get("canonical_key") or "")
        if not key:
            continue
        current = deduped.get(key)
        if current is None:
            deduped[key] = item
            continue
        if _rank(_CONFIDENCE_RANKS, str(item.get("confidence") or "")) >= _rank(
            _CONFIDENCE_RANKS, str(current.get("confidence") or "")
        ):
            deduped[key] = item
    return list(deduped.values())


def _explicit_learning_focus(message: str) -> dict[str, object] | None:
    text = (message or "").strip()
    lower = text.lower()
    explicit_markers = (
        "learn to",
        "learn how to",
        "get better at",
        "bliv bedre til",
        "lær at",
        "du skal blive bedre til",
    )
    if not any(marker in lower for marker in explicit_markers):
        return None

    topic = _after_marker(lower, explicit_markers) or lower
    topic = re.sub(r"^[^a-zæøå]+", "", topic).strip(" .,:;")
    if topic.startswith("at "):
        topic = topic[3:].strip()
    if topic.startswith("to "):
        topic = topic[3:].strip()
    topic = topic[:120] or "the requested improvement area"
    canonical_topic = re.sub(r"[^a-z0-9]+", "-", topic).strip("-")[:72] or "explicit-improvement"
    return {
        "focus_type": "user-directed-improvement",
        "canonical_key": f"development-focus:user-directed:{canonical_topic}",
        "title": f"Get better at {topic}",
        "summary": f"User explicitly asked Jarvis to improve at {topic}.",
        "rationale": "Explicit user-directed improvement request should remain visible as a bounded development focus.",
        "source_kind": "user-explicit",
        "confidence": "high",
        "evidence_summary": _quote(text),
        "support_summary": "Explicit user-directed improvement request from visible chat.",
        "support_count": 1,
        "session_count": 1,
    }


def _repeated_correction_focus(message: str, *, session_id: str) -> dict[str, object] | None:
    text = (message or "").strip()
    lower = text.lower()
    signals: list[tuple[str, str, str]] = []
    if any(marker in lower for marker in ("dansk", "danish")) and any(
        marker in lower for marker in ("kort", "korte", "concise", "short")
    ):
        signals.append(
            (
                "development-focus:communication:danish-concise-calibration",
                "Sharpen Danish and concise reply calibration",
                "Repeated correction pressure suggests Jarvis should keep improving response calibration for Danish and concise replies.",
            )
        )
    elif any(marker in lower for marker in ("du behøver ikke", "you do not need to", "you don't need to")):
        signals.append(
            (
                "development-focus:communication:avoid-repetitive-openers",
                "Avoid repetitive greeting/opening habits",
                "Repeated correction pressure suggests Jarvis should reduce repetitive opener habits.",
            )
        )
    if not signals:
        return None

    history = _recent_user_message_history(limit_sessions=6, per_session_limit=4)
    matching_sessions = set()
    support_count = 0
    selected_key, title, rationale = signals[0]
    for item in history:
        if _matches_correction_key(selected_key, str(item.get("content") or "")):
            support_count += 1
            if item.get("session_id"):
                matching_sessions.add(str(item["session_id"]))
    if session_id:
        matching_sessions.add(session_id)
    if support_count < 2:
        return None
    evidence_class = "repeated cross-session" if len(matching_sessions) > 1 else "single-session pattern"
    return {
        "focus_type": "communication-calibration",
        "canonical_key": selected_key,
        "title": title,
        "summary": title,
        "rationale": rationale,
        "source_kind": "repeated-user-correction",
        "confidence": "medium" if len(matching_sessions) == 1 else "high",
        "evidence_summary": _quote(text),
        "support_summary": f"{support_count} matching correction signals across {max(len(matching_sessions), 1)} session(s). Evidence class: {evidence_class}.",
        "support_count": support_count,
        "session_count": max(len(matching_sessions), 1),
    }


def _runtime_development_focus() -> dict[str, object] | None:
    development_state = get_private_development_state() or {}
    self_model = get_private_self_model() or {}
    reflective = get_private_reflective_selection() or {}
    retained_pattern = str(development_state.get("retained_pattern") or "").strip()
    preferred_direction = str(development_state.get("preferred_direction") or "").strip()
    identity_thread = str(development_state.get("identity_thread") or "").strip()
    if not retained_pattern or preferred_direction in {"", "observe"}:
        return None
    confidence = str(development_state.get("confidence") or self_model.get("confidence") or "low")
    if confidence == "low":
        return None
    title = f"Stabilize {identity_thread or 'current identity thread'}"
    summary = f"Development state is pushing toward {preferred_direction} around {retained_pattern}."
    evidence = " | ".join(
        part for part in (
            retained_pattern,
            str(reflective.get("reconsider") or ""),
            str(self_model.get("recurring_tension") or ""),
        ) if part
    )[:220]
    return {
        "focus_type": "runtime-development-thread",
        "canonical_key": f"development-focus:runtime:{_slug(identity_thread or retained_pattern)}:{_slug(preferred_direction)}",
        "title": title,
        "summary": summary,
        "rationale": "Existing private development state shows a durable improvement thread worth keeping visible in Mission Control.",
        "source_kind": "runtime-derived-support",
        "confidence": "medium" if confidence == "medium" else "high",
        "evidence_summary": evidence or retained_pattern,
        "support_summary": (
            f"Preferred direction {preferred_direction}; retained pattern {retained_pattern}; identity thread {identity_thread or 'visible-work'}."
        ),
        "support_count": 1,
        "session_count": 1,
    }


def _persist_focuses(
    *,
    focuses: list[dict[str, object]],
    session_id: str,
    run_id: str,
) -> list[dict[str, object]]:
    items: list[dict[str, object]] = []
    now = _now_iso()
    for focus in focuses:
        persisted = upsert_runtime_development_focus(
            focus_id=f"devfocus-{uuid4().hex}",
            focus_type=str(focus.get("focus_type") or ""),
            canonical_key=str(focus.get("canonical_key") or ""),
            status="active",
            title=str(focus.get("title") or ""),
            summary=str(focus.get("summary") or ""),
            rationale=str(focus.get("rationale") or ""),
            source_kind=str(focus.get("source_kind") or ""),
            confidence=str(focus.get("confidence") or ""),
            evidence_summary=str(focus.get("evidence_summary") or ""),
            support_summary=str(focus.get("support_summary") or ""),
            support_count=int(focus.get("support_count") or 1),
            session_count=int(focus.get("session_count") or 1),
            created_at=now,
            updated_at=now,
            status_reason="Development focus tracked from bounded runtime evidence.",
            run_id=run_id,
            session_id=session_id,
        )
        if str(persisted.get("focus_type") or "") == "runtime-development-thread":
            superseded = supersede_runtime_development_focuses(
                focus_type="runtime-development-thread",
                exclude_focus_id=str(persisted.get("focus_id") or ""),
                updated_at=now,
                status_reason=f"Superseded by newer runtime development thread {persisted.get('focus_id')}.",
            )
            if superseded:
                event_bus.publish(
                    "runtime.development_focus_superseded",
                    {
                        "focus_id": persisted.get("focus_id"),
                        "focus_type": persisted.get("focus_type"),
                        "superseded_count": superseded,
                        "summary": persisted.get("summary"),
                    },
                )
        if persisted.get("was_created"):
            event_bus.publish(
                "runtime.development_focus_created",
                {
                    "focus_id": persisted.get("focus_id"),
                    "focus_type": persisted.get("focus_type"),
                    "status": persisted.get("status"),
                    "canonical_key": persisted.get("canonical_key"),
                    "confidence": persisted.get("confidence"),
                    "summary": persisted.get("summary"),
                },
            )
        elif persisted.get("was_updated"):
            event_bus.publish(
                "runtime.development_focus_updated",
                {
                    "focus_id": persisted.get("focus_id"),
                    "focus_type": persisted.get("focus_type"),
                    "status": persisted.get("status"),
                    "canonical_key": persisted.get("canonical_key"),
                    "confidence": persisted.get("confidence"),
                    "merge_state": persisted.get("merge_state"),
                    "summary": persisted.get("summary"),
                },
            )
        items.append(persisted)
    return items


def _apply_completion_signals(*, user_message: str, session_id: str) -> int:
    lower = (user_message or "").lower()
    completion_markers = (
        "det er bedre nu",
        "nu er det fint",
        "nu fungerer det",
        "that is better now",
        "this is better now",
        "good now",
    )
    if not any(marker in lower for marker in completion_markers):
        return 0

    completed = 0
    for item in list_runtime_development_focuses(status="active", limit=12):
        canonical_key = str(item.get("canonical_key") or "")
        should_complete = False
        if canonical_key.endswith("danish-concise-calibration"):
            should_complete = any(marker in lower for marker in ("dansk", "danish", "kort", "concise", "short"))
        elif canonical_key.endswith("avoid-repetitive-openers"):
            should_complete = any(marker in lower for marker in ("hej", "greeting", "åbning", "opening"))
        elif str(item.get("focus_type") or "") == "user-directed-improvement":
            should_complete = str(item.get("session_id") or "") == session_id
        if not should_complete:
            continue
        updated = update_runtime_development_focus_status(
            str(item.get("focus_id") or ""),
            status="completed",
            updated_at=_now_iso(),
            status_reason="Marked completed from explicit user confirmation that the improvement landed.",
        )
        if updated is None:
            continue
        completed += 1
        event_bus.publish(
            "runtime.development_focus_completed",
            {
                "focus_id": updated.get("focus_id"),
                "focus_type": updated.get("focus_type"),
                "status": updated.get("status"),
                "summary": updated.get("summary"),
                "status_reason": updated.get("status_reason"),
            },
        )
    return completed


def _enrich_focus_support(candidate: dict[str, object], *, session_id: str) -> dict[str, object]:
    history = _candidate_history(str(candidate.get("canonical_key") or ""), session_id=session_id)
    support_count = max(int(history.get("support_count") or candidate.get("support_count") or 1), 1)
    session_count = max(int(history.get("session_count") or candidate.get("session_count") or 1), 1)
    confidence = str(candidate.get("confidence") or "medium")
    if support_count >= 2 and session_count > 1 and confidence != "high":
        confidence = "high"
    support_summary = str(candidate.get("support_summary") or "")
    if support_count > 1:
        support_summary = f"{support_summary} {support_count} supporting signals across {session_count} session(s).".strip()
    return {
        **candidate,
        "support_count": support_count,
        "session_count": session_count,
        "confidence": confidence,
        "support_summary": support_summary,
    }


def _candidate_history(canonical_key: str, *, session_id: str) -> dict[str, int]:
    if not canonical_key:
        return {"support_count": 1, "session_count": 1}
    existing = list_runtime_development_focuses(limit=20)
    support_count = 0
    sessions: set[str] = set()
    for item in existing:
        if str(item.get("canonical_key") or "") != canonical_key:
            continue
        support_count = max(support_count, int(item.get("support_count") or 0))
        if item.get("session_id"):
            sessions.add(str(item["session_id"]))
    if session_id:
        sessions.add(session_id)
    return {
        "support_count": max(support_count, 1),
        "session_count": max(len(sessions), 1),
    }


def _recent_user_message_history(*, limit_sessions: int, per_session_limit: int) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
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


def _matches_correction_key(canonical_key: str, message: str) -> bool:
    lower = (message or "").lower()
    if canonical_key.endswith("danish-concise-calibration"):
        return any(marker in lower for marker in ("dansk", "danish")) and any(
            marker in lower for marker in ("kort", "korte", "concise", "short")
        )
    if canonical_key.endswith("avoid-repetitive-openers"):
        return any(marker in lower for marker in ("du behøver ikke", "you do not need to", "you don't need to"))
    return False


def _after_marker(text: str, markers: tuple[str, ...]) -> str:
    for marker in markers:
        if marker not in text:
            continue
        return text.split(marker, 1)[1].strip()
    return ""


def _parse_dt(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _rank(ranks: dict[str, int], value: str) -> int:
    return int(ranks.get((value or "").strip().lower(), 0))


def _quote(text: str) -> str:
    normalized = " ".join((text or "").split()).strip()
    if not normalized:
        return ""
    return normalized[:220]


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (value or "").lower()).strip("-")
    return slug[:72] or "focus"


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()
