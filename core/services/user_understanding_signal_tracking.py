from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from core.services.chat_sessions import get_chat_session
from core.eventbus.bus import event_bus
from core.runtime.db import (
    list_runtime_user_understanding_signals,
    supersede_runtime_user_understanding_signals_for_dimension,
    update_runtime_user_understanding_signal_status,
    upsert_runtime_user_understanding_signal,
)

_CONFIDENCE_RANKS = {"low": 1, "medium": 2, "high": 3}
_STALE_AFTER_DAYS = 14


def track_runtime_user_understanding_signals_for_visible_turn(
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
            "summary": "No bounded user-understanding evidence was available.",
        }

    items = _persist_user_understanding_signals(
        signals=_extract_user_understanding_candidates(
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
            f"Tracked {len(items)} bounded user-understanding signals."
            if items
            else "No bounded user-understanding signal warranted tracking."
        ),
    }


def refresh_runtime_user_understanding_signal_statuses() -> dict[str, int]:
    now = datetime.now(UTC)
    refreshed = 0
    for item in list_runtime_user_understanding_signals(limit=40):
        if str(item.get("status") or "") not in {"active", "softening"}:
            continue
        updated_at = _parse_dt(str(item.get("updated_at") or item.get("created_at") or ""))
        if updated_at is None or updated_at > now - timedelta(days=_STALE_AFTER_DAYS):
            continue
        refreshed_item = update_runtime_user_understanding_signal_status(
            str(item.get("signal_id") or ""),
            status="stale",
            updated_at=now.isoformat(),
            status_reason="Marked stale after bounded user-understanding inactivity window.",
        )
        if refreshed_item is None:
            continue
        refreshed += 1
        event_bus.publish(
            "user_understanding_signal.stale",
            {
                "signal_id": refreshed_item.get("signal_id"),
                "signal_type": refreshed_item.get("signal_type"),
                "status": refreshed_item.get("status"),
                "summary": refreshed_item.get("summary"),
                "status_reason": refreshed_item.get("status_reason"),
            },
        )
    return {"stale_marked": refreshed}


def build_runtime_user_understanding_signal_surface(*, limit: int = 8) -> dict[str, object]:
    refresh_runtime_user_understanding_signal_statuses()
    items = list_runtime_user_understanding_signals(limit=max(limit, 1))
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
            "current_signal": str((latest or {}).get("title") or "No active user-understanding signal"),
            "current_status": str((latest or {}).get("status") or "none"),
            "current_signal_type": str((latest or {}).get("signal_type") or "none"),
            "current_signal_confidence": str((latest or {}).get("signal_confidence") or "low"),
        },
    }


def _extract_user_understanding_candidates(
    *,
    user_message: str,
    session_id: str,
) -> list[dict[str, object]]:
    messages = _recent_user_messages(session_id=session_id, current_message=user_message)
    if not messages:
        return []

    signals = [
        _preference_signal(messages),
        _workstyle_signal(messages),
        _reminder_worthiness_signal(messages),
        _cadence_preference_signal(messages),
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


def _persist_user_understanding_signals(
    *,
    signals: list[dict[str, object]],
    session_id: str,
    run_id: str,
) -> list[dict[str, object]]:
    now = datetime.now(UTC).isoformat()
    persisted: list[dict[str, object]] = []
    for signal in signals:
        persisted_item = upsert_runtime_user_understanding_signal(
            signal_id=f"user-understanding-{uuid4().hex}",
            signal_type=str(signal.get("signal_type") or "preference-signal"),
            canonical_key=str(signal.get("canonical_key") or ""),
            status=str(signal.get("status") or "active"),
            title=str(signal.get("title") or ""),
            summary=str(signal.get("signal_summary") or signal.get("summary") or ""),
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
        superseded_count = supersede_runtime_user_understanding_signals_for_dimension(
            dimension_key=str(signal.get("dimension_key") or ""),
            exclude_signal_id=str(persisted_item.get("signal_id") or ""),
            updated_at=now,
            status_reason="Superseded by a newer bounded user-understanding signal for the same user dimension.",
        )
        if superseded_count > 0:
            event_bus.publish(
                "user_understanding_signal.superseded",
                {
                    "signal_id": persisted_item.get("signal_id"),
                    "signal_type": persisted_item.get("signal_type"),
                    "superseded_count": superseded_count,
                    "summary": persisted_item.get("summary"),
                },
            )
        if persisted_item.get("was_created"):
            event_bus.publish(
                "user_understanding_signal.created",
                {
                    "signal_id": persisted_item.get("signal_id"),
                    "signal_type": persisted_item.get("signal_type"),
                    "status": persisted_item.get("status"),
                    "summary": persisted_item.get("summary"),
                },
            )
        elif persisted_item.get("was_updated"):
            event_bus.publish(
                "user_understanding_signal.updated",
                {
                    "signal_id": persisted_item.get("signal_id"),
                    "signal_type": persisted_item.get("signal_type"),
                    "status": persisted_item.get("status"),
                    "summary": persisted_item.get("summary"),
                },
            )
        persisted.append(_with_runtime_view(persisted_item, signal))
    return persisted


def _preference_signal(messages: list[str]) -> dict[str, object] | None:
    danish_message = next((message for message in messages if _is_explicit_danish_preference(message)), "")
    if danish_message:
        matched_count = sum(1 for message in messages if _is_explicit_danish_preference(message))
        return {
            "signal_type": "preference-signal",
            "canonical_key": "user-understanding:preference-signal:language-preference",
            "dimension_key": "language-preference",
            "status": "active",
            "title": "User understanding: language preference",
            "signal_summary": "User is explicitly asking for Danish-by-default replies.",
            "rationale": "A direct user request about reply language is bounded, durable enough to observe, and low-risk to carry as collaboration truth.",
            "source_kind": "user-explicit",
            "confidence": "high",
            "evidence_summary": _quote(danish_message),
            "support_summary": _merge_fragments(
                f"{matched_count} recent message(s) explicitly asked for Danish-by-default collaboration.",
                _source_anchor(danish_message),
            ),
            "support_count": matched_count,
            "session_count": 1,
            "status_reason": "Explicit visible preference supports an active language-preference signal.",
            "user_dimension": "language-preference",
            "source_anchor": _source_anchor(danish_message),
            "signal_confidence": "high",
        }

    concise_message = next((message for message in messages if _is_explicit_concise_preference(message)), "")
    if not concise_message:
        return None
    matched_count = sum(1 for message in messages if _is_explicit_concise_preference(message))
    confidence = "high" if matched_count > 1 else "medium"
    return {
        "signal_type": "preference-signal",
        "canonical_key": "user-understanding:preference-signal:reply-style",
        "dimension_key": "reply-style",
        "status": "active" if confidence == "high" else "softening",
        "title": "User understanding: reply style",
        "signal_summary": "User is explicitly asking for concise, direct replies.",
        "rationale": "A direct reply-style request is bounded enough to observe without turning into broad profiling.",
        "source_kind": "user-explicit",
        "confidence": confidence,
        "evidence_summary": _quote(concise_message),
        "support_summary": _merge_fragments(
            f"{matched_count} recent message(s) asked for concise delivery.",
            _source_anchor(concise_message),
        ),
        "support_count": matched_count,
        "session_count": 1,
        "status_reason": "Explicit visible preference supports a bounded reply-style signal.",
        "user_dimension": "reply-style",
        "source_anchor": _source_anchor(concise_message),
        "signal_confidence": confidence,
    }


def _workstyle_signal(messages: list[str]) -> dict[str, object] | None:
    matched = [message for message in messages if _is_scoped_workstyle_signal(message)]
    if not matched:
        return None
    confidence = "high" if len(matched) > 1 else "medium"
    status = "active" if confidence == "high" or any("ingen opportunistiske refactors" in message.lower() for message in matched) else "softening"
    source_message = matched[0]
    return {
        "signal_type": "workstyle-signal",
        "canonical_key": "user-understanding:workstyle-signal:workstyle",
        "dimension_key": "workstyle",
        "status": status,
        "title": "User understanding: scoped change style",
        "signal_summary": "User is steering toward tightly scoped changes with minimal opportunistic cleanup.",
        "rationale": "Repeated requests for narrow scope and anti-cleanup posture are low-risk collaboration truth, not broad user profiling.",
        "source_kind": "user-explicit",
        "confidence": confidence,
        "evidence_summary": _quote(source_message),
        "support_summary": _merge_fragments(
            f"{len(matched)} recent message(s) steered toward small scoped implementation.",
            _source_anchor(source_message),
        ),
        "support_count": len(matched),
        "session_count": 1,
        "status_reason": "Explicit scope-guarding language supports a bounded workstyle signal.",
        "user_dimension": "workstyle",
        "source_anchor": _source_anchor(source_message),
        "signal_confidence": confidence,
    }


def _reminder_worthiness_signal(messages: list[str]) -> dict[str, object] | None:
    matched = [message for message in messages if _is_carry_forward_preference(message)]
    if not matched:
        return None
    source_message = matched[0]
    return {
        "signal_type": "reminder-worthiness-signal",
        "canonical_key": "user-understanding:reminder-worthiness-signal:reminder-worthiness",
        "dimension_key": "reminder-worthiness",
        "status": "active",
        "title": "User understanding: carry-forward preference",
        "signal_summary": "User is marking a collaboration preference as something to carry forward across turns.",
        "rationale": "This remains bounded because it only tracks whether the user framed a low-risk collaboration preference as durable.",
        "source_kind": "user-explicit",
        "confidence": "high",
        "evidence_summary": _quote(source_message),
        "support_summary": _merge_fragments(
            f"{len(matched)} recent message(s) framed a preference as something to remember across turns.",
            _source_anchor(source_message),
        ),
        "support_count": len(matched),
        "session_count": 1,
        "status_reason": "Explicit carry-forward wording supports an active reminder-worthiness signal.",
        "user_dimension": "reminder-worthiness",
        "source_anchor": _source_anchor(source_message),
        "signal_confidence": "high",
    }


def _cadence_preference_signal(messages: list[str]) -> dict[str, object] | None:
    matched = [message for message in messages if _is_reporting_cadence_preference(message)]
    if not matched:
        return None
    confidence = "high" if len(matched) > 1 else "medium"
    status = "active" if confidence == "high" else "softening"
    source_message = matched[0]
    return {
        "signal_type": "cadence-preference-signal",
        "canonical_key": "user-understanding:cadence-preference-signal:reporting-cadence",
        "dimension_key": "reporting-cadence",
        "status": status,
        "title": "User understanding: reporting cadence",
        "signal_summary": "User prefers a consistent exact reporting shape on scoped turns.",
        "rationale": "This stays bounded because it only captures a repeated preference for how turn-by-turn reporting should be structured.",
        "source_kind": "user-explicit",
        "confidence": confidence,
        "evidence_summary": _quote(source_message),
        "support_summary": _merge_fragments(
            f"{len(matched)} recent message(s) requested the same exact reporting shape.",
            _source_anchor(source_message),
        ),
        "support_count": len(matched),
        "session_count": 1,
        "status_reason": "Explicit reporting-shape language supports a bounded cadence-preference signal.",
        "user_dimension": "reporting-cadence",
        "source_anchor": _source_anchor(source_message),
        "signal_confidence": confidence,
    }


def _with_runtime_view(item: dict[str, object], signal: dict[str, object]) -> dict[str, object]:
    enriched = dict(item)
    enriched["user_dimension"] = str(signal.get("user_dimension") or "")
    enriched["signal_summary"] = str(signal.get("signal_summary") or item.get("summary") or "")
    enriched["signal_confidence"] = str(signal.get("signal_confidence") or signal.get("confidence") or "low")
    enriched["source_anchor"] = str(signal.get("source_anchor") or "")
    return enriched


def _with_surface_view(item: dict[str, object]) -> dict[str, object]:
    enriched = dict(item)
    enriched["user_dimension"] = _dimension_from_canonical_key(str(item.get("canonical_key") or ""))
    enriched["signal_summary"] = str(item.get("summary") or "")
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


def _is_explicit_danish_preference(message: str) -> bool:
    lower = message.lower()
    return _contains_any(lower, ("jeg vil gerne have", "i prefer", "please remember", "reply in", "svar på")) and _contains_any(
        lower,
        ("dansk", "danish"),
    )


def _is_explicit_concise_preference(message: str) -> bool:
    lower = message.lower()
    return _contains_any(lower, ("jeg vil gerne have", "i prefer", "concise", "short", "kort", "kortfattet")) and _contains_any(
        lower,
        ("concise", "short", "kort", "kortfattet", "direct"),
    )


def _is_scoped_workstyle_signal(message: str) -> bool:
    lower = message.lower()
    return _contains_any(
        lower,
        (
            "hold blokken lille",
            "ingen opportunistiske refactors",
            "smallest useful version",
            "small and literal",
            "no opportunistic refactors",
            "keep the block small",
            "scoped validation",
        ),
    )


def _is_carry_forward_preference(message: str) -> bool:
    lower = message.lower()
    if not _contains_any(lower, ("remember", "husk", "fremover", "from now on", "osse selv hvis", "even if i write")):
        return False
    return _contains_any(lower, ("prefer", "vil gerne have", "dansk", "danish", "reply", "svar"))


def _is_reporting_cadence_preference(message: str) -> bool:
    lower = message.lower()
    return _contains_any(
        lower,
        (
            "rapportér præcist",
            "report exact",
            "exact files inspected/changed",
            "outputformat",
            "each turn",
            "hver turn",
            "hver gang",
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
