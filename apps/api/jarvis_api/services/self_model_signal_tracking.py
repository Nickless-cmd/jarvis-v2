from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from apps.api.jarvis_api.services.chat_sessions import get_chat_session, list_chat_sessions
from core.eventbus.bus import event_bus
from core.runtime.db import (
    list_runtime_reflective_critics,
    list_runtime_self_model_signals,
    update_runtime_self_model_signal_status,
    upsert_runtime_self_model_signal,
)

_CONFIDENCE_RANKS = {"low": 1, "medium": 2, "high": 3}
_SOURCE_KIND_RANKS = {
    "runtime-derived-support": 1,
    "critic-supported": 2,
    "user-explicit": 3,
    "repeated-user-feedback": 4,
}
_STALE_AFTER_DAYS = 10


def track_runtime_self_model_signals_for_visible_turn(
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
            "summary": "No self-model evidence was available.",
        }

    corrected = _apply_correction_signals(user_message=normalized_message)
    signals = _extract_self_model_candidates(
        user_message=normalized_message,
        session_id=normalized_session_id,
    )
    items = _persist_self_model_signals(
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
            f"Tracked {len(items)} bounded self-model signals and corrected {corrected}."
            if items or corrected
            else "No bounded self-model assessment warranted tracking."
        ),
    }


def refresh_runtime_self_model_signal_statuses() -> dict[str, int]:
    now = datetime.now(UTC)
    refreshed = 0
    for item in list_runtime_self_model_signals(limit=40):
        if str(item.get("status") or "") not in {"active", "uncertain"}:
            continue
        updated_at = _parse_dt(str(item.get("updated_at") or item.get("created_at") or ""))
        if updated_at is None or updated_at > now - timedelta(days=_STALE_AFTER_DAYS):
            continue
        refreshed_item = update_runtime_self_model_signal_status(
            str(item.get("signal_id") or ""),
            status="stale",
            updated_at=now.isoformat(),
            status_reason="Marked stale after bounded inactivity window.",
        )
        if refreshed_item is not None:
            refreshed += 1
            event_bus.publish(
                "self_model_signal.stale",
                {
                    "signal_id": refreshed_item.get("signal_id"),
                    "signal_type": refreshed_item.get("signal_type"),
                    "status": refreshed_item.get("status"),
                    "summary": refreshed_item.get("summary"),
                },
            )
    return {"stale_marked": refreshed}


def build_runtime_self_model_signal_surface(*, limit: int = 8) -> dict[str, object]:
    refresh_runtime_self_model_signal_statuses()
    items = list_runtime_self_model_signals(limit=max(limit, 1))
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
            "current_signal": str((latest or {}).get("title") or "No active self-model signal"),
            "current_status": str((latest or {}).get("status") or "none"),
        },
    }


def _extract_self_model_candidates(*, user_message: str, session_id: str) -> list[dict[str, object]]:
    signals: list[dict[str, object]] = []

    limitation = _current_limitation_signal(user_message, session_id=session_id)
    if limitation:
        signals.append(limitation)

    improvement = _improving_edge_signal(user_message)
    if improvement:
        signals.append(improvement)

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


def _current_limitation_signal(message: str, *, session_id: str) -> dict[str, object] | None:
    text = (message or "").strip()
    matched_critic = _matching_active_critic(text)
    if matched_critic is None:
        return None
    if int(matched_critic.get("support_count") or 0) < 2:
        return None
    limitation_key = _critic_limitation_key(str(matched_critic.get("canonical_key") or ""))
    limitation_label = _limitation_label(limitation_key)
    sessions = _supporting_sessions_for_limitation(limitation_key)
    if session_id:
        sessions.add(session_id)
    support_count = max(int(matched_critic.get("support_count") or 0), len(sessions), 1)
    return {
        "signal_type": "current-limitation",
        "canonical_key": f"self-model:limitation:{limitation_key}",
        "status": "active",
        "title": f"Current limitation: {limitation_label}",
        "summary": f"Jarvis is carrying a bounded self-assessment that {limitation_label}.",
        "rationale": "Repeated correction pressure backed by an active reflective critic suggests this remains a current limitation rather than a one-off slip.",
        "source_kind": "critic-supported",
        "confidence": "high" if len(sessions) > 1 else str(matched_critic.get("confidence") or "medium"),
        "evidence_summary": str(matched_critic.get("evidence_summary") or _quote(text)),
        "support_summary": f"{support_count} corrective signals backing an active reflective critic across {max(len(sessions), 1)} session(s).",
        "support_count": support_count,
        "session_count": max(len(sessions), 1),
        "status_reason": "Active reflective mismatch still supports this limitation assessment.",
    }


def _improving_edge_signal(message: str) -> dict[str, object] | None:
    text = (message or "").strip()
    lower = text.lower()
    if not any(marker in lower for marker in ("bedre nu", "that's better now", "better now", "improved now")):
        return None
    limitation_key = _message_limitation_key(text)
    if not limitation_key:
        return None
    if not _has_matching_self_model_history(limitation_key):
        return None
    limitation_label = _limitation_label(limitation_key)
    return {
        "signal_type": "improvement-edge",
        "canonical_key": f"self-model:improving:{limitation_key}",
        "status": "uncertain",
        "title": f"Emerging improvement: {limitation_label}",
        "summary": f"Jarvis is carrying a bounded self-assessment that {limitation_label} may be improving.",
        "rationale": "Explicit user feedback says a previously weak area is getting better, but the improvement should stay bounded and provisional until reinforced.",
        "source_kind": "user-explicit",
        "confidence": "medium",
        "evidence_summary": _quote(text),
        "support_summary": "Explicit visible user feedback that this area is better now.",
        "support_count": 1,
        "session_count": 1,
        "status_reason": "Explicit user feedback created a bounded replacement signal for a previously carried limitation.",
    }


def _persist_self_model_signals(
    *,
    signals: list[dict[str, object]],
    session_id: str,
    run_id: str,
) -> list[dict[str, object]]:
    now = datetime.now(UTC).isoformat()
    persisted: list[dict[str, object]] = []
    for signal in signals:
        persisted_item = upsert_runtime_self_model_signal(
            signal_id=f"selfmodel-{uuid4().hex}",
            signal_type=str(signal.get("signal_type") or "self-model-signal"),
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
        superseded_count = _supersede_replaced_self_model_signals(
            persisted_item,
            updated_at=now,
        )
        if superseded_count > 0:
            event_bus.publish(
                "self_model_signal.superseded",
                {
                    "signal_id": persisted_item.get("signal_id"),
                    "signal_type": persisted_item.get("signal_type"),
                    "superseded_count": superseded_count,
                    "summary": persisted_item.get("summary"),
                },
            )
        if persisted_item.get("was_created"):
            event_bus.publish(
                "self_model_signal.created",
                {
                    "signal_id": persisted_item.get("signal_id"),
                    "signal_type": persisted_item.get("signal_type"),
                    "status": persisted_item.get("status"),
                    "summary": persisted_item.get("summary"),
                },
            )
        elif persisted_item.get("was_updated"):
            event_bus.publish(
                "self_model_signal.updated",
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
    if not any(marker in lower for marker in ("bedre nu", "that's better now", "better now", "improved now")):
        return 0

    limitation_key = _message_limitation_key(user_message)
    if not limitation_key:
        return 0

    corrected = 0
    now = datetime.now(UTC).isoformat()
    canonical_key = f"self-model:limitation:{limitation_key}"
    for item in list_runtime_self_model_signals(limit=20):
        if str(item.get("canonical_key") or "") != canonical_key:
            continue
        if str(item.get("status") or "") not in {"active", "uncertain"}:
            continue
        updated = update_runtime_self_model_signal_status(
            str(item.get("signal_id") or ""),
            status="corrected",
            updated_at=now,
            status_reason="Explicit user feedback said this area is better now.",
        )
        if updated is None:
            continue
        corrected += 1
        event_bus.publish(
            "self_model_signal.corrected",
            {
                "signal_id": updated.get("signal_id"),
                "signal_type": updated.get("signal_type"),
                "status": updated.get("status"),
                "summary": updated.get("summary"),
            },
        )
    return corrected


def _supersede_replaced_self_model_signals(
    persisted_item: dict[str, object],
    *,
    updated_at: str,
) -> int:
    signal_id = str(persisted_item.get("signal_id") or "")
    canonical_key = str(persisted_item.get("canonical_key") or "")
    signal_type = str(persisted_item.get("signal_type") or "")
    domain_key = _self_model_domain_key(canonical_key)
    if not signal_id or not canonical_key or not domain_key:
        return 0

    superseded = 0
    for item in list_runtime_self_model_signals(limit=40):
        existing_id = str(item.get("signal_id") or "")
        if not existing_id or existing_id == signal_id:
            continue
        existing_status = str(item.get("status") or "")
        if existing_status not in {"active", "uncertain", "stale"}:
            continue
        existing_key = str(item.get("canonical_key") or "")
        if _self_model_domain_key(existing_key) != domain_key:
            continue

        should_supersede = False
        status_reason = ""
        if signal_type == "improvement-edge" and existing_key.startswith("self-model:improving:"):
            should_supersede = True
            status_reason = "Superseded by newer improvement signal for the same self-model thread."
        elif signal_type == "current-limitation" and existing_key.startswith("self-model:improving:"):
            should_supersede = True
            status_reason = "Superseded because the same self-model thread now looks like a current limitation again."

        if not should_supersede:
            continue
        updated = update_runtime_self_model_signal_status(
            existing_id,
            status="superseded",
            updated_at=updated_at,
            status_reason=status_reason,
        )
        if updated is not None:
            superseded += 1
    return superseded


def _has_matching_self_model_history(limitation_key: str) -> bool:
    if not limitation_key:
        return False
    for item in list_runtime_self_model_signals(limit=20):
        domain_key = _self_model_domain_key(str(item.get("canonical_key") or ""))
        if domain_key != limitation_key:
            continue
        if str(item.get("status") or "") in {"active", "uncertain", "corrected", "stale"}:
            return True
    return False


def _matching_active_critic(message: str) -> dict[str, object] | None:
    active_critics = [
        item for item in list_runtime_reflective_critics(limit=12)
        if str(item.get("status") or "") == "active"
    ]
    limitation_key = _message_limitation_key(message)
    for item in active_critics:
        critic_key = _critic_limitation_key(str(item.get("canonical_key") or ""))
        if limitation_key and limitation_key == critic_key:
            return item
        if _message_matches_limited_domain(critic_key, message):
            return item
    return None


def _supporting_sessions_for_limitation(limitation_key: str) -> set[str]:
    sessions: set[str] = set()
    for item in _recent_user_message_history(limit_sessions=6, per_session_limit=4):
        if _message_matches_limited_domain(limitation_key, str(item.get("content") or "")):
            session_id = str(item.get("session_id") or "")
            if session_id:
                sessions.add(session_id)
    return sessions


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


def _critic_limitation_key(canonical_key: str) -> str:
    text = str(canonical_key or "")
    if "danish-concise" in text or ("dansk" in text and "kort" in text):
        return "danish-concise-calibration"
    if "repetitive-openers" in text or "hej" in text:
        return "avoid-repetitive-openers"
    if text.startswith("reflective-critic:mismatch:"):
        return text.removeprefix("reflective-critic:mismatch:").replace("focus:", "")
    return "general-calibration"


def _message_limitation_key(message: str) -> str:
    text = str(message or "").lower()
    if ("dansk" in text or "danish" in text) and any(token in text for token in ("kort", "korte", "concise", "short")):
        return "danish-concise-calibration"
    if "hej" in text and any(token in text for token in ("hver gang", "every time", "always")):
        return "avoid-repetitive-openers"
    return ""


def _self_model_domain_key(canonical_key: str) -> str:
    text = str(canonical_key or "")
    if text.startswith("self-model:limitation:"):
        return text.removeprefix("self-model:limitation:")
    if text.startswith("self-model:improving:"):
        return text.removeprefix("self-model:improving:")
    return ""


def _limitation_label(limitation_key: str) -> str:
    labels = {
        "danish-concise-calibration": "keeping Danish replies short and well calibrated",
        "avoid-repetitive-openers": "avoiding repetitive opener habits",
        "general-calibration": "current visible calibration is still uneven",
    }
    return labels.get(limitation_key, limitation_key.replace("-", " "))


def _message_matches_limited_domain(limitation_key: str, message: str) -> bool:
    text = str(message or "").lower()
    if limitation_key == "danish-concise-calibration":
        return ("dansk" in text or "danish" in text) and any(
            token in text for token in ("kort", "korte", "concise", "short")
        )
    if limitation_key == "avoid-repetitive-openers":
        return "hej" in text or "hello" in text
    return False


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
