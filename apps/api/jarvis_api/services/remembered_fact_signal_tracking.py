from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from apps.api.jarvis_api.services.chat_sessions import get_chat_session
from core.eventbus.bus import event_bus
from core.runtime.db import (
    list_runtime_remembered_fact_signals,
    supersede_runtime_remembered_fact_signals_for_dimension,
    update_runtime_remembered_fact_signal_status,
    upsert_runtime_remembered_fact_signal,
)

_CONFIDENCE_RANKS = {"low": 1, "medium": 2, "high": 3}
_STALE_AFTER_DAYS = 14
_NAME_PATTERNS = (
    re.compile(r"\bmit navn er ([A-Za-zÆØÅæøå][A-Za-zÆØÅæøå' -]{0,40})", re.IGNORECASE),
    re.compile(r"\bjeg hedder ([A-Za-zÆØÅæøå][A-Za-zÆØÅæøå' -]{0,40})", re.IGNORECASE),
    re.compile(r"\bmy name is ([A-Za-z][A-Za-z' -]{0,40})", re.IGNORECASE),
    re.compile(r"\bi am called ([A-Za-z][A-Za-z' -]{0,40})", re.IGNORECASE),
)


def track_runtime_remembered_fact_signals_for_visible_turn(
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
            "items": [],
            "summary": "No bounded remembered-fact evidence was available.",
        }

    items = _persist_remembered_fact_signals(
        signals=_extract_remembered_fact_candidates(
            user_message=normalized_message,
            session_id=normalized_session_id,
        ),
        session_id=normalized_session_id,
        run_id=run_id,
    )
    return {
        "created": len([item for item in items if item.get("was_created")]),
        "updated": len([item for item in items if item.get("was_updated")]),
        "items": items,
        "summary": (
            f"Tracked {len(items)} bounded remembered-fact signals."
            if items
            else "No bounded remembered-fact signal warranted tracking."
        ),
    }


def refresh_runtime_remembered_fact_signal_statuses() -> dict[str, int]:
    now = datetime.now(UTC)
    refreshed = 0
    for item in list_runtime_remembered_fact_signals(limit=40):
        if str(item.get("status") or "") not in {"active", "softening"}:
            continue
        updated_at = _parse_dt(str(item.get("updated_at") or item.get("created_at") or ""))
        if updated_at is None or updated_at > now - timedelta(days=_STALE_AFTER_DAYS):
            continue
        refreshed_item = update_runtime_remembered_fact_signal_status(
            str(item.get("signal_id") or ""),
            status="stale",
            updated_at=now.isoformat(),
            status_reason="Marked stale after bounded remembered-fact inactivity window.",
        )
        if refreshed_item is None:
            continue
        refreshed += 1
        event_bus.publish(
            "remembered_fact_signal.stale",
            {
                "signal_id": refreshed_item.get("signal_id"),
                "signal_type": refreshed_item.get("signal_type"),
                "status": refreshed_item.get("status"),
                "summary": refreshed_item.get("summary"),
                "status_reason": refreshed_item.get("status_reason"),
            },
        )
    return {"stale_marked": refreshed}


def build_runtime_remembered_fact_signal_surface(*, limit: int = 8) -> dict[str, object]:
    refresh_runtime_remembered_fact_signal_statuses()
    items = list_runtime_remembered_fact_signals(limit=max(limit, 1))
    enriched_items = [_with_surface_view(item) for item in items]
    active = [item for item in enriched_items if str(item.get("status") or "") == "active"]
    softening = [item for item in enriched_items if str(item.get("status") or "") == "softening"]
    stale = [item for item in enriched_items if str(item.get("status") or "") == "stale"]
    superseded = [item for item in enriched_items if str(item.get("status") or "") == "superseded"]
    ordered = [*active, *softening, *stale, *superseded]
    latest = next(iter(active or softening or stale or superseded), None)
    return {
        "active": bool(active or softening),
        "items": ordered,
        "summary": {
            "active_count": len(active),
            "softening_count": len(softening),
            "stale_count": len(stale),
            "superseded_count": len(superseded),
            "current_signal": str((latest or {}).get("title") or "No active remembered-fact signal"),
            "current_status": str((latest or {}).get("status") or "none"),
            "current_signal_type": str((latest or {}).get("signal_type") or "none"),
            "current_signal_confidence": str((latest or {}).get("signal_confidence") or "low"),
        },
    }


def _extract_remembered_fact_candidates(
    *,
    user_message: str,
    session_id: str,
) -> list[dict[str, object]]:
    messages = _recent_user_messages(session_id=session_id, current_message=user_message)
    if not messages:
        return []

    signals = [
        _explicit_user_name_fact(messages),
        _explicit_project_anchor_fact(messages),
        _explicit_working_context_fact(messages),
    ]

    deduped: dict[str, dict[str, object]] = {}
    for signal in signals:
        if not signal:
            continue
        canonical_key = str(signal.get("canonical_key") or "")
        if not canonical_key:
            continue
        current = deduped.get(canonical_key)
        if current is None:
            deduped[canonical_key] = signal
            continue
        if _rank_confidence(str(signal.get("confidence") or "")) >= _rank_confidence(
            str(current.get("confidence") or "")
        ):
            deduped[canonical_key] = signal
    return list(deduped.values())[:4]


def _persist_remembered_fact_signals(
    *,
    signals: list[dict[str, object]],
    session_id: str,
    run_id: str,
) -> list[dict[str, object]]:
    now = datetime.now(UTC).isoformat()
    persisted: list[dict[str, object]] = []
    for signal in signals:
        persisted_item = upsert_runtime_remembered_fact_signal(
            signal_id=f"remembered-fact-{uuid4().hex}",
            signal_type=str(signal.get("signal_type") or "explicit-project-fact"),
            canonical_key=str(signal.get("canonical_key") or ""),
            status=str(signal.get("status") or "active"),
            title=str(signal.get("title") or ""),
            summary=str(signal.get("fact_summary") or signal.get("summary") or ""),
            rationale=str(signal.get("rationale") or ""),
            source_kind=str(signal.get("source_kind") or "user-explicit"),
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
        superseded_count = supersede_runtime_remembered_fact_signals_for_dimension(
            dimension_key=str(signal.get("dimension_key") or ""),
            exclude_signal_id=str(persisted_item.get("signal_id") or ""),
            updated_at=now,
            status_reason="Superseded by a newer bounded remembered-fact signal for the same fact dimension.",
        )
        if superseded_count > 0:
            event_bus.publish(
                "remembered_fact_signal.superseded",
                {
                    "signal_id": persisted_item.get("signal_id"),
                    "signal_type": persisted_item.get("signal_type"),
                    "superseded_count": superseded_count,
                    "summary": persisted_item.get("summary"),
                },
            )
        if persisted_item.get("was_created"):
            event_bus.publish(
                "remembered_fact_signal.created",
                {
                    "signal_id": persisted_item.get("signal_id"),
                    "signal_type": persisted_item.get("signal_type"),
                    "status": persisted_item.get("status"),
                    "summary": persisted_item.get("summary"),
                },
            )
        elif persisted_item.get("was_updated"):
            event_bus.publish(
                "remembered_fact_signal.updated",
                {
                    "signal_id": persisted_item.get("signal_id"),
                    "signal_type": persisted_item.get("signal_type"),
                    "status": persisted_item.get("status"),
                    "summary": persisted_item.get("summary"),
                },
            )
        persisted.append(_with_runtime_view(persisted_item, signal))
    return persisted


def _explicit_user_name_fact(messages: list[str]) -> dict[str, object] | None:
    for message in messages:
        fact_value = _extract_name_value(message)
        if not fact_value:
            continue
        return {
            "signal_type": "explicit-user-fact",
            "canonical_key": "remembered-fact:explicit-user-fact:user-name",
            "dimension_key": "user-name",
            "status": "active",
            "title": "Remembered fact: user name",
            "fact_summary": f"User explicitly stated their name as {fact_value}.",
            "rationale": "An explicit self-identifying name statement is a small factual memory cue, not a broad profile.",
            "source_kind": "user-explicit",
            "confidence": "high",
            "evidence_summary": _quote(message),
            "support_summary": _merge_fragments(
                "A recent user message explicitly stated the user's name.",
                _source_anchor(message),
            ),
            "support_count": 1,
            "session_count": 1,
            "status_reason": "An explicit self-identifying statement supports an active remembered-fact signal.",
            "fact_kind": "user-name",
            "source_anchor": _source_anchor(message),
            "signal_confidence": "high",
        }
    return None


def _explicit_project_anchor_fact(messages: list[str]) -> dict[str, object] | None:
    matched = [message for message in messages if _is_project_anchor_fact(message)]
    if not matched:
        return None
    source_message = matched[0]
    return {
        "signal_type": "explicit-project-fact",
        "canonical_key": "remembered-fact:explicit-project-fact:project-anchor",
        "dimension_key": "project-anchor",
        "status": "active",
        "title": "Remembered fact: shared project anchor",
        "fact_summary": "The user explicitly framed the work as building Jarvis together.",
        "rationale": "A direct project-anchor statement is a bounded factual continuity cue for workspace memory.",
        "source_kind": "user-explicit",
        "confidence": "high",
        "evidence_summary": _quote(source_message),
        "support_summary": _merge_fragments(
            f"{len(matched)} recent message(s) explicitly framed the collaboration as building Jarvis together.",
            _source_anchor(source_message),
        ),
        "support_count": len(matched),
        "session_count": 1,
        "status_reason": "An explicit shared-project statement supports an active remembered-fact signal.",
        "fact_kind": "project-anchor",
        "source_anchor": _source_anchor(source_message),
        "signal_confidence": "high",
    }


def _explicit_working_context_fact(messages: list[str]) -> dict[str, object] | None:
    matched = [message for message in messages if _is_working_context_fact(message)]
    if not matched:
        return None
    source_message = matched[0]
    confidence = "high" if len(matched) > 1 else "medium"
    return {
        "signal_type": "explicit-working-context-fact",
        "canonical_key": "remembered-fact:explicit-working-context-fact:repo-context",
        "dimension_key": "repo-context",
        "status": "active" if confidence == "high" else "softening",
        "title": "Remembered fact: working context",
        "fact_summary": "The user explicitly located the current collaboration in the Jarvis v2 repo.",
        "rationale": "A direct working-context statement is bounded memory-worthy context, not a user profile trait.",
        "source_kind": "user-explicit",
        "confidence": confidence,
        "evidence_summary": _quote(source_message),
        "support_summary": _merge_fragments(
            f"{len(matched)} recent message(s) explicitly named the Jarvis v2 repo as the current working context.",
            _source_anchor(source_message),
        ),
        "support_count": len(matched),
        "session_count": 1,
        "status_reason": "An explicit working-context statement supports a bounded remembered-fact signal.",
        "fact_kind": "repo-context",
        "source_anchor": _source_anchor(source_message),
        "signal_confidence": confidence,
    }


def _with_runtime_view(item: dict[str, object], signal: dict[str, object]) -> dict[str, object]:
    enriched = dict(item)
    enriched["fact_kind"] = str(signal.get("fact_kind") or "")
    enriched["fact_summary"] = str(signal.get("fact_summary") or item.get("summary") or "")
    enriched["signal_confidence"] = str(signal.get("signal_confidence") or signal.get("confidence") or "low")
    enriched["source_anchor"] = str(signal.get("source_anchor") or "")
    return enriched


def _with_surface_view(item: dict[str, object]) -> dict[str, object]:
    enriched = dict(item)
    enriched["fact_kind"] = _dimension_from_canonical_key(str(item.get("canonical_key") or ""))
    enriched["fact_summary"] = str(item.get("summary") or "")
    enriched["signal_confidence"] = str(item.get("confidence") or "low")
    enriched["source_anchor"] = _source_anchor_from_support_summary(str(item.get("support_summary") or ""))
    return enriched


def _recent_user_messages(*, session_id: str, current_message: str) -> list[str]:
    messages: list[str] = []
    seen: set[str] = set()

    normalized_current = " ".join(str(current_message or "").split()).strip()
    if normalized_current:
        seen.add(normalized_current)
        messages.append(normalized_current)

    if session_id:
        session = get_chat_session(session_id)
        for item in reversed((session or {}).get("messages") or []):
            if str(item.get("role") or "") != "user":
                continue
            text = " ".join(str(item.get("content") or "").split()).strip()
            if not text or text in seen:
                continue
            seen.add(text)
            messages.append(text)
            if len(messages) >= 6:
                break
    return messages[:6]


def _extract_name_value(message: str) -> str:
    text = " ".join(str(message or "").split()).strip()
    for pattern in _NAME_PATTERNS:
        match = pattern.search(text)
        if not match:
            continue
        candidate = " ".join(match.group(1).split()).strip(" .,!?:;\"'")
        if not candidate:
            continue
        return candidate[:48]
    return ""


def _is_project_anchor_fact(message: str) -> bool:
    lower = message.lower()
    return _contains_any(
        lower,
        (
            "vi bygger jarvis sammen",
            "we are building jarvis together",
            "jarvis og jeg bygger det sammen",
            "you and i are building jarvis together",
        ),
    )


def _is_working_context_fact(message: str) -> bool:
    lower = message.lower()
    if not _contains_any(
        lower,
        (
            "jarvis v2-repoet",
            "jarvis v2 repoet",
            "jarvis v2-repo",
            "jarvis v2 repo",
            "jarvis-v2",
        ),
    ):
        return False
    return _contains_any(
        lower,
        (
            "du arbejder i",
            "you are working in",
            "du arbejder på",
            "we are in",
            "repo",
            "repoet",
        ),
    )


def _dimension_from_canonical_key(canonical_key: str) -> str:
    parts = canonical_key.split(":")
    if len(parts) < 3:
        return ""
    return parts[-1]


def _source_anchor(text: str) -> str:
    quoted = _quote(text)
    return f"Visible user anchor: {quoted}" if quoted else ""


def _source_anchor_from_support_summary(summary: str) -> str:
    for fragment in str(summary or "").split(" | "):
        if fragment.startswith("Visible user anchor:"):
            return fragment
    return ""


def _quote(text: str, *, limit: int = 160) -> str:
    normalized = " ".join(str(text or "").split()).strip()
    if not normalized:
        return ""
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 1].rstrip() + "…"


def _merge_fragments(*parts: str) -> str:
    seen: set[str] = set()
    merged: list[str] = []
    for part in parts:
        normalized = " ".join(str(part or "").split()).strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        merged.append(normalized)
    return " | ".join(merged[:4])


def _contains_any(text: str, needles: tuple[str, ...]) -> bool:
    return any(needle in text for needle in needles)


def _rank_confidence(confidence: str) -> int:
    return _CONFIDENCE_RANKS.get(str(confidence or "").lower(), 0)


def _parse_dt(value: str) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None
