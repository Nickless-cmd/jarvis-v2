from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from apps.api.jarvis_api.services.chat_sessions import get_chat_session, list_chat_sessions
from core.eventbus.bus import event_bus
from core.runtime.db import (
    list_runtime_development_focuses,
    list_runtime_reflective_critics,
    supersede_runtime_reflective_critics,
    update_runtime_reflective_critic_status,
    upsert_runtime_reflective_critic,
)

_CONFIDENCE_RANKS = {"low": 1, "medium": 2, "high": 3}
_SOURCE_KIND_RANKS = {
    "runtime-derived-support": 1,
    "single-session-pattern": 2,
    "repeated-user-correction": 3,
    "focus-mismatch": 4,
}
_STALE_AFTER_DAYS = 10


def track_runtime_reflective_critics_for_visible_turn(
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
            "resolved": 0,
            "items": [],
            "summary": "No reflective critic evidence was available.",
        }

    resolved = _apply_resolution_signals(
        user_message=normalized_message,
    )
    critics = _extract_critic_candidates(
        user_message=normalized_message,
        session_id=normalized_session_id,
    )
    items = _persist_critics(
        critics=critics,
        session_id=normalized_session_id,
        run_id=run_id,
    )
    return {
        "created": len([item for item in items if item.get("was_created")]),
        "updated": len([item for item in items if item.get("was_updated")]),
        "resolved": resolved,
        "items": items,
        "summary": (
            f"Tracked {len(items)} bounded reflective critic signals and resolved {resolved}."
            if items or resolved
            else "No reflective critic signal warranted tracking."
        ),
    }


def refresh_runtime_reflective_critic_statuses() -> dict[str, int]:
    now = datetime.now(UTC)
    refreshed = 0
    for item in list_runtime_reflective_critics(limit=40):
        if str(item.get("status") or "") != "active":
            continue
        updated_at = _parse_dt(str(item.get("updated_at") or item.get("created_at") or ""))
        if updated_at is None or updated_at > now - timedelta(days=_STALE_AFTER_DAYS):
            continue
        refreshed_item = update_runtime_reflective_critic_status(
            str(item.get("critic_id") or ""),
            status="stale",
            updated_at=now.isoformat(),
            status_reason="Marked stale after bounded inactivity window.",
        )
        if refreshed_item is not None:
            refreshed += 1
            event_bus.publish(
                "reflective_critic.stale",
                {
                    "critic_id": refreshed_item.get("critic_id"),
                    "critic_type": refreshed_item.get("critic_type"),
                    "status": refreshed_item.get("status"),
                    "summary": refreshed_item.get("summary"),
                    "status_reason": refreshed_item.get("status_reason"),
                },
            )
    return {"stale_marked": refreshed}


def build_runtime_reflective_critic_surface(*, limit: int = 8) -> dict[str, object]:
    refresh_runtime_reflective_critic_statuses()
    items = list_runtime_reflective_critics(limit=max(limit, 1))
    active = [item for item in items if str(item.get("status") or "") == "active"]
    stale = [item for item in items if str(item.get("status") or "") == "stale"]
    resolved = [item for item in items if str(item.get("status") or "") == "resolved"]
    superseded = [item for item in items if str(item.get("status") or "") == "superseded"]
    ordered_items = [*active, *stale, *resolved, *superseded]
    latest = next(iter(active or stale or resolved or superseded), None)
    return {
        "active": bool(active),
        "items": ordered_items,
        "summary": {
            "active_count": len(active),
            "stale_count": len(stale),
            "resolved_count": len(resolved),
            "superseded_count": len(superseded),
            "current_critic": str((latest or {}).get("title") or "No active critic signal"),
            "current_status": str((latest or {}).get("status") or "none"),
        },
    }


def _extract_critic_candidates(*, user_message: str, session_id: str) -> list[dict[str, object]]:
    critics: list[dict[str, object]] = []

    correction_mismatch = _repeated_correction_mismatch(user_message, session_id=session_id)
    if correction_mismatch:
        critics.append(correction_mismatch)

    deduped: dict[str, dict[str, object]] = {}
    for item in critics:
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


def _repeated_correction_mismatch(message: str, *, session_id: str) -> dict[str, object] | None:
    text = (message or "").strip()
    matched_focus = _matching_active_focus(text)
    if matched_focus is None:
        return None
    if int(matched_focus.get("merge_count") or 0) < 1:
        return None

    history = _recent_user_message_history(limit_sessions=6, per_session_limit=4)
    support_count = 0
    matching_sessions: set[str] = set()
    canonical_key = str(matched_focus.get("canonical_key") or "")
    for item in history:
        if _message_matches_focus_key(canonical_key, str(item.get("content") or "")):
            support_count += 1
            if item.get("session_id"):
                matching_sessions.add(str(item["session_id"]))
    if session_id:
        matching_sessions.add(session_id)
    if support_count < 2:
        return None

    evidence_class = "repeated cross-session" if len(matching_sessions) > 1 else "single-session pattern"
    short_title = str(matched_focus.get("title") or "Active development focus")
    return {
        "critic_type": "development-focus-mismatch",
        "canonical_key": f"reflective-critic:mismatch:{canonical_key}",
        "title": f"Active focus is not landing yet: {short_title}",
        "summary": f"Repeated correction still conflicts with the active focus '{short_title}'.",
        "rationale": "Repeated corrective pressure suggests the active development focus has not yet translated into visible behavior reliably enough.",
        "source_kind": "focus-mismatch",
        "confidence": "high" if len(matching_sessions) > 1 else "medium",
        "evidence_summary": _quote(text),
        "support_summary": f"{support_count} matching correction signals across {max(len(matching_sessions), 1)} session(s). Evidence class: {evidence_class}.",
        "support_count": support_count,
        "session_count": max(len(matching_sessions), 1),
    }


def _matching_active_focus(message: str) -> dict[str, object] | None:
    active_focuses = [
        item for item in list_runtime_development_focuses(limit=12)
        if str(item.get("status") or "") == "active"
    ]
    for item in active_focuses:
        if _message_matches_focus_key(str(item.get("canonical_key") or ""), message):
            return item
    return None


def _persist_critics(
    *,
    critics: list[dict[str, object]],
    session_id: str,
    run_id: str,
) -> list[dict[str, object]]:
    now = datetime.now(UTC).isoformat()
    persisted: list[dict[str, object]] = []
    for critic in critics:
        persisted_item = upsert_runtime_reflective_critic(
            critic_id=f"critic-{uuid4().hex}",
            critic_type=str(critic.get("critic_type") or "reflective-critic"),
            canonical_key=str(critic.get("canonical_key") or ""),
            status="active",
            title=str(critic.get("title") or ""),
            summary=str(critic.get("summary") or ""),
            rationale=str(critic.get("rationale") or ""),
            source_kind=str(critic.get("source_kind") or ""),
            confidence=str(critic.get("confidence") or "low"),
            evidence_summary=str(critic.get("evidence_summary") or ""),
            support_summary=str(critic.get("support_summary") or ""),
            support_count=int(critic.get("support_count") or 1),
            session_count=int(critic.get("session_count") or 1),
            created_at=now,
            updated_at=now,
            status_reason=str(critic.get("status_reason") or "Active reflective mismatch signal."),
            run_id=run_id,
            session_id=session_id,
        )

        # Suppress near-duplicate critics of same type with similar canonical_key
        critic_type = str(critic.get("critic_type") or "")
        canonical_key = str(critic.get("canonical_key") or "")
        if critic_type == "development-focus-mismatch" and persisted_item.get("was_created"):
            superseded_count = supersede_runtime_reflective_critics(
                critic_type=critic_type,
                exclude_critic_id=str(persisted_item.get("critic_id") or ""),
                updated_at=now,
                status_reason=f"Superseded by newer development-focus-mismatch critic {persisted_item.get('critic_id')}.",
            )
            if superseded_count > 0:
                event_bus.publish(
                    "reflective_critic.superseded",
                    {
                        "new_critic_id": persisted_item.get("critic_id"),
                        "new_critic_type": critic_type,
                        "superseded_count": superseded_count,
                        "canonical_key": canonical_key,
                        "summary": persisted_item.get("summary"),
                    },
                )

        if persisted_item.get("was_created"):
            event_bus.publish(
                "reflective_critic.created",
                {
                    "critic_id": persisted_item.get("critic_id"),
                    "critic_type": persisted_item.get("critic_type"),
                    "status": persisted_item.get("status"),
                    "summary": persisted_item.get("summary"),
                },
            )
        elif persisted_item.get("was_updated"):
            event_bus.publish(
                "reflective_critic.updated",
                {
                    "critic_id": persisted_item.get("critic_id"),
                    "critic_type": persisted_item.get("critic_type"),
                    "status": persisted_item.get("status"),
                    "summary": persisted_item.get("summary"),
                },
            )
        persisted.append(persisted_item)
    return persisted


def _apply_resolution_signals(*, user_message: str) -> int:
    lower = str(user_message or "").lower()
    resolution_markers = (
        "det er bedre nu",
        "nu er det bedre",
        "that's better now",
        "that is better now",
        "works better now",
        "det fungerer bedre",
        "it works better",
        "good now",
        "fine now",
    )
    if not any(marker in lower for marker in resolution_markers):
        return 0

    # Find which active critics might be relevant to resolve
    active_critics = list_runtime_reflective_critics(status="active", limit=20)
    if not active_critics:
        return 0

    # Check if the resolution message contains context that matches a specific critic
    # by looking at what development focus the user might be referring to
    matching_critic_keys = _detect_resolution_context(lower, active_critics)

    now = datetime.now(UTC).isoformat()
    resolved = 0
    for item in active_critics:
        canonical_key = str(item.get("canonical_key") or "")

        # Only resolve if:
        # 1. We detected specific resolution context that matches this critic's key
        # 2. OR there are very few active critics (resolve all if just 1-2)
        should_resolve = False
        if len(active_critics) <= 2:
            should_resolve = True
        elif matching_critic_keys:
            # Check if this critic's key matches any detected context
            should_resolve = any(
                ctx_key in canonical_key or canonical_key in ctx_key
                for ctx_key in matching_critic_keys
            )

        if not should_resolve:
            continue

        updated = update_runtime_reflective_critic_status(
            str(item.get("critic_id") or ""),
            status="resolved",
            updated_at=now,
            status_reason="User signaled that the prior mismatch is better now.",
        )
        if updated is None:
            continue
        resolved += 1
        event_bus.publish(
            "reflective_critic.resolved",
            {
                "critic_id": updated.get("critic_id"),
                "critic_type": updated.get("critic_type"),
                "status": updated.get("status"),
                "summary": updated.get("summary"),
                "canonical_key": canonical_key,
            },
        )
    return resolved


def _detect_resolution_context(lower: str, active_critics: list[dict]) -> list[str]:
    """Detect which critic context the resolution message refers to."""
    context_keys = []

    # Map resolution language to possible critic keys
    resolution_context_map = {
        "dansk": ["danish", "concise", "calibration"],
        "danish": ["danish", "concise", "calibration"],
        "kort": ["danish", "concise", "calibration"],
        "concise": ["danish", "concise", "calibration"],
        "short": ["danish", "concise", "calibration"],
        "hej": ["repetitive", "opener", "greeting"],
        "greeting": ["repetitive", "opener", "greeting"],
        "opening": ["repetitive", "opener", "greeting"],
    }

    for keyword, key_parts in resolution_context_map.items():
        if keyword in lower:
            for part in key_parts:
                context_keys.append(part)

    return context_keys


def _recent_user_message_history(*, limit_sessions: int, per_session_limit: int) -> list[dict[str, object]]:
    sessions = list_chat_sessions()
    items: list[dict[str, object]] = []
    for session in sessions[:limit_sessions]:
        session_id = str(session.get("id") or "")
        if not session_id:
            continue
        detail = get_chat_session(session_id)
        if not detail:
            continue
        for message in reversed(detail.get("messages") or []):
            if str(message.get("role") or "") != "user":
                continue
            content = " ".join(str(message.get("content") or "").split()).strip()
            if not content:
                continue
            items.append(
                {
                    "session_id": session_id,
                    "content": content,
                    "created_at": str(message.get("created_at") or ""),
                }
            )
            if len([row for row in items if row["session_id"] == session_id]) >= per_session_limit:
                break
    return items


def _message_matches_focus_key(canonical_key: str, text: str) -> bool:
    lower = str(text or "").lower()
    key = str(canonical_key or "")
    if "danish-concise-calibration" in key:
        return any(marker in lower for marker in ("dansk", "danish")) and any(
            marker in lower for marker in ("kort", "korte", "concise", "short")
        )
    if "avoid-repetitive-openers" in key:
        return any(marker in lower for marker in ("du behøver ikke", "you do not need to", "you don't need to"))
    return False


def _quote(text: str) -> str:
    normalized = " ".join(str(text or "").split()).strip()
    if len(normalized) > 160:
        normalized = normalized[:159].rstrip() + "…"
    return f'"{normalized}"' if normalized else ""


def _rank(ranks: dict[str, int], value: str) -> int:
    return int(ranks.get(str(value or "").strip().lower(), 0))


def _parse_dt(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(str(value or "").replace("Z", "+00:00"))
    except ValueError:
        return None
