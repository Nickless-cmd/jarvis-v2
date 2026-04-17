from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.services.signal_noise_guard import is_noisy_signal_text
from core.runtime.db import (
    list_runtime_development_focuses,
    list_runtime_goal_signals,
    list_runtime_reflective_critics,
    list_runtime_self_model_signals,
    update_runtime_goal_signal_status,
    upsert_runtime_goal_signal,
)

_STALE_AFTER_DAYS = 10
_EARLY_RETIRE_DAYS = 2
_CONFIDENCE_RANKS = {"low": 1, "medium": 2, "high": 3}
_REFRESH_SCAN_LIMIT = 2000


def track_runtime_goal_signals_for_visible_turn(
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
            "summary": "No goal-signal evidence was available.",
        }

    completed_domains = _completed_goal_domains(normalized_message)
    completed = _apply_completion_signals(completed_domains)
    goals = _extract_goal_candidates(
        user_message=normalized_message,
        completed_domains=completed_domains,
    )
    items = _persist_goal_signals(
        goals=goals,
        session_id=normalized_session_id,
        run_id=run_id,
    )
    return {
        "created": len([item for item in items if item.get("was_created")]),
        "updated": len([item for item in items if item.get("was_updated")]),
        "completed": completed,
        "items": items,
        "summary": (
            f"Tracked {len(items)} bounded goal signals and completed {completed}."
            if items or completed
            else "No bounded goal signal warranted tracking."
        ),
    }


def refresh_runtime_goal_signal_statuses() -> dict[str, int]:
    now = datetime.now(UTC)
    refreshed = 0
    for item in list_runtime_goal_signals(limit=_REFRESH_SCAN_LIMIT):
        if str(item.get("status") or "") not in {"active", "blocked"}:
            continue
        updated_at = _parse_dt(str(item.get("updated_at") or item.get("created_at") or ""))
        if updated_at is None:
            continue
        retire_early = (
            str(item.get("confidence") or "") == "low"
            or int(item.get("support_count") or 0) <= 1
            or is_noisy_signal_text(str(item.get("title") or "") + " " + str(item.get("summary") or ""))
        )
        stale_after = _EARLY_RETIRE_DAYS if retire_early else _STALE_AFTER_DAYS
        if updated_at > now - timedelta(days=stale_after):
            continue
        refreshed_item = update_runtime_goal_signal_status(
            str(item.get("goal_id") or ""),
            status="stale",
            updated_at=now.isoformat(),
            status_reason="Marked stale after bounded inactivity window.",
        )
        if refreshed_item is not None:
            refreshed += 1
            event_bus.publish(
                "goal_signal.stale",
                {
                    "goal_id": refreshed_item.get("goal_id"),
                    "goal_type": refreshed_item.get("goal_type"),
                    "status": refreshed_item.get("status"),
                    "summary": refreshed_item.get("summary"),
                },
            )
    return {"stale_marked": refreshed}


def build_runtime_goal_signal_surface(*, limit: int = 8) -> dict[str, object]:
    refresh_runtime_goal_signal_statuses()
    items = list_runtime_goal_signals(limit=max(limit, 1))
    active = [item for item in items if str(item.get("status") or "") == "active"]
    blocked = [item for item in items if str(item.get("status") or "") == "blocked"]
    stale = [item for item in items if str(item.get("status") or "") == "stale"]
    completed = [item for item in items if str(item.get("status") or "") == "completed"]
    superseded = [item for item in items if str(item.get("status") or "") == "superseded"]
    ordered_items = [*blocked, *active, *stale, *completed, *superseded]
    latest = next(iter(blocked or active or stale or completed or superseded), None)
    return {
        "active": bool(active or blocked),
        "items": ordered_items,
        "summary": {
            "active_count": len(active),
            "blocked_count": len(blocked),
            "stale_count": len(stale),
            "completed_count": len(completed),
            "superseded_count": len(superseded),
            "current_goal": str((latest or {}).get("title") or "No active goal signal"),
            "current_status": str((latest or {}).get("status") or "none"),
        },
    }


def _extract_goal_candidates(
    *,
    user_message: str,
    completed_domains: set[str],
) -> list[dict[str, object]]:
    goals: list[dict[str, object]] = []
    for focus in list_runtime_development_focuses(limit=10):
        if str(focus.get("status") or "") != "active":
            continue
        goal = _goal_from_active_focus(focus, user_message=user_message, completed_domains=completed_domains)
        if goal:
            goals.append(goal)

    deduped: dict[str, dict[str, object]] = {}
    for item in goals:
        key = str(item.get("canonical_key") or "")
        if not key:
            continue
        current = deduped.get(key)
        if current is None or _rank(str(item.get("confidence") or "")) >= _rank(
            str(current.get("confidence") or "")
        ):
            deduped[key] = item
    return list(deduped.values())


def _goal_from_active_focus(
    focus: dict[str, object],
    *,
    user_message: str,
    completed_domains: set[str],
) -> dict[str, object] | None:
    canonical_key = str(focus.get("canonical_key") or "")
    domain_key = _domain_key_from_focus(canonical_key)
    if not domain_key:
        return None
    if is_noisy_signal_text(
        " ".join(
            part
            for part in (
                str(focus.get("title") or ""),
                str(focus.get("summary") or ""),
                domain_key,
            )
            if part
        )
    ):
        return None
    if domain_key in completed_domains:
        return None

    blocking = _blocking_state_for_domain(domain_key)
    if not blocking["blocked"] and _has_completed_goal_history(domain_key):
        return None

    status = "blocked" if blocking["blocked"] else "active"
    title = _goal_title(domain_key, str(focus.get("title") or "current development thread"))
    rationale = (
        "Jarvis is carrying a bounded practical aim derived from an active development focus."
        if not blocking["blocked"]
        else "Jarvis is carrying a bounded practical aim, but active critic/self-model tension shows the aim is not landing visibly yet."
    )
    support_bits = [
        str(focus.get("support_summary") or ""),
        str(blocking["support_summary"] or ""),
    ]
    evidence_bits = [
        str(focus.get("evidence_summary") or ""),
        str(blocking["evidence_summary"] or ""),
    ]
    return {
        "goal_type": "development-direction",
        "canonical_key": f"goal-signal:{domain_key}",
        "status": status,
        "title": title,
        "summary": title,
        "rationale": rationale,
        "source_kind": "critic-backed" if blocking["blocked"] else str(focus.get("source_kind") or "focus-derived"),
        "confidence": "high" if blocking["blocked"] else str(focus.get("confidence") or "medium"),
        "evidence_summary": _merge_fragments(*evidence_bits),
        "support_summary": _merge_fragments(*support_bits),
        "support_count": max(
            int(focus.get("support_count") or 1),
            int(blocking["support_count"] or 0),
            1,
        ),
        "session_count": max(
            int(focus.get("session_count") or 1),
            int(blocking["session_count"] or 0),
            1,
        ),
        "status_reason": (
            "Active development focus is being carried as a current practical aim."
            if status == "active"
            else str(blocking["status_reason"] or "Active tension is currently blocking this goal from landing visibly.")
        ),
    }


def _persist_goal_signals(
    *,
    goals: list[dict[str, object]],
    session_id: str,
    run_id: str,
) -> list[dict[str, object]]:
    now = datetime.now(UTC).isoformat()
    persisted: list[dict[str, object]] = []
    for goal in goals:
        persisted_item = upsert_runtime_goal_signal(
            goal_id=f"goal-{uuid4().hex}",
            goal_type=str(goal.get("goal_type") or "goal-signal"),
            canonical_key=str(goal.get("canonical_key") or ""),
            status=str(goal.get("status") or "active"),
            title=str(goal.get("title") or ""),
            summary=str(goal.get("summary") or ""),
            rationale=str(goal.get("rationale") or ""),
            source_kind=str(goal.get("source_kind") or ""),
            confidence=str(goal.get("confidence") or "low"),
            evidence_summary=str(goal.get("evidence_summary") or ""),
            support_summary=str(goal.get("support_summary") or ""),
            support_count=int(goal.get("support_count") or 1),
            session_count=int(goal.get("session_count") or 1),
            created_at=now,
            updated_at=now,
            status_reason=str(goal.get("status_reason") or ""),
            run_id=run_id,
            session_id=session_id,
        )
        superseded_count = _supersede_replaced_goal_signals(
            persisted_item,
            updated_at=now,
        )
        if superseded_count > 0:
            event_bus.publish(
                "goal_signal.superseded",
                {
                    "goal_id": persisted_item.get("goal_id"),
                    "goal_type": persisted_item.get("goal_type"),
                    "superseded_count": superseded_count,
                    "summary": persisted_item.get("summary"),
                },
            )
        if persisted_item.get("was_created"):
            event_bus.publish(
                "goal_signal.created",
                {
                    "goal_id": persisted_item.get("goal_id"),
                    "goal_type": persisted_item.get("goal_type"),
                    "status": persisted_item.get("status"),
                    "summary": persisted_item.get("summary"),
                },
            )
        elif persisted_item.get("was_updated"):
            event_bus.publish(
                "goal_signal.updated",
                {
                    "goal_id": persisted_item.get("goal_id"),
                    "goal_type": persisted_item.get("goal_type"),
                    "status": persisted_item.get("status"),
                    "summary": persisted_item.get("summary"),
                },
            )
        persisted.append(persisted_item)
    return persisted


def _apply_completion_signals(domains: set[str]) -> int:
    if not domains:
        return 0
    completed = 0
    now = datetime.now(UTC).isoformat()
    for domain in domains:
        live_items = [
            item for item in list_runtime_goal_signals(limit=30)
            if _goal_domain_key(str(item.get("canonical_key") or "")) == domain
            and str(item.get("status") or "") in {"active", "blocked"}
        ]
        if not live_items:
            continue
        target = live_items[0]
        updated = update_runtime_goal_signal_status(
            str(target.get("goal_id") or ""),
            status="completed",
            updated_at=now,
            status_reason="Explicit visible feedback suggests this bounded goal has landed for now.",
        )
        if updated is None:
            continue
        completed += 1
        event_bus.publish(
            "goal_signal.completed",
            {
                "goal_id": updated.get("goal_id"),
                "goal_type": updated.get("goal_type"),
                "status": updated.get("status"),
                "summary": updated.get("summary"),
            },
        )
        superseded_count = 0
        for item in live_items[1:]:
            superseded = update_runtime_goal_signal_status(
                str(item.get("goal_id") or ""),
                status="superseded",
                updated_at=now,
                status_reason="Superseded by newer completed goal thread for the same bounded domain.",
            )
            if superseded is not None:
                superseded_count += 1
        if superseded_count > 0:
            event_bus.publish(
                "goal_signal.superseded",
                {
                    "goal_id": updated.get("goal_id"),
                    "goal_type": updated.get("goal_type"),
                    "superseded_count": superseded_count,
                    "summary": updated.get("summary"),
                },
            )
    return completed


def _supersede_replaced_goal_signals(
    persisted_item: dict[str, object],
    *,
    updated_at: str,
) -> int:
    goal_id = str(persisted_item.get("goal_id") or "")
    domain_key = _goal_domain_key(str(persisted_item.get("canonical_key") or ""))
    if not goal_id or not domain_key:
        return 0

    superseded = 0
    for item in list_runtime_goal_signals(limit=40):
        existing_id = str(item.get("goal_id") or "")
        if not existing_id or existing_id == goal_id:
            continue
        if _goal_domain_key(str(item.get("canonical_key") or "")) != domain_key:
            continue
        if str(item.get("status") or "") not in {"active", "blocked", "stale"}:
            continue
        updated = update_runtime_goal_signal_status(
            existing_id,
            status="superseded",
            updated_at=updated_at,
            status_reason="Superseded by newer bounded goal thread for the same domain.",
        )
        if updated is not None:
            superseded += 1
    return superseded


def _completed_goal_domains(message: str) -> set[str]:
    lower = str(message or "").lower()
    if not any(marker in lower for marker in ("bedre nu", "that's better now", "better now", "improved now")):
        return set()
    domain = _message_domain_key(lower)
    return {domain} if domain else set()


def _blocking_state_for_domain(domain_key: str) -> dict[str, object]:
    active_critics = [
        item for item in list_runtime_reflective_critics(limit=12)
        if str(item.get("status") or "") == "active"
    ]
    for item in active_critics:
        if _domain_key_from_critic(str(item.get("canonical_key") or "")) != domain_key:
            continue
        return {
            "blocked": True,
            "status_reason": "Active reflective critic shows this goal is still not landing visibly.",
            "support_summary": str(item.get("support_summary") or ""),
            "evidence_summary": str(item.get("evidence_summary") or ""),
            "support_count": int(item.get("support_count") or 1),
            "session_count": int(item.get("session_count") or 1),
        }

    active_self_model = [
        item for item in list_runtime_self_model_signals(limit=12)
        if str(item.get("status") or "") == "active"
    ]
    for item in active_self_model:
        if _domain_key_from_self_model(str(item.get("canonical_key") or "")) != domain_key:
            continue
        if str(item.get("signal_type") or "") != "current-limitation":
            continue
        return {
            "blocked": True,
            "status_reason": "Active self-model limitation shows this goal is still a live improvement edge.",
            "support_summary": str(item.get("support_summary") or ""),
            "evidence_summary": str(item.get("evidence_summary") or ""),
            "support_count": int(item.get("support_count") or 1),
            "session_count": int(item.get("session_count") or 1),
        }

    return {
        "blocked": False,
        "status_reason": "",
        "support_summary": "",
        "evidence_summary": "",
        "support_count": 0,
        "session_count": 0,
    }


def _has_completed_goal_history(domain_key: str) -> bool:
    for item in list_runtime_goal_signals(limit=20):
        if _goal_domain_key(str(item.get("canonical_key") or "")) != domain_key:
            continue
        if str(item.get("status") or "") == "completed":
            return True
    return False


def _domain_key_from_focus(canonical_key: str) -> str:
    text = str(canonical_key or "")
    if "danish-concise-calibration" in text:
        return "danish-concise-calibration"
    if ("dansk" in text or "danish" in text) and any(token in text for token in ("kort", "korte", "concise", "short")):
        return "danish-concise-calibration"
    if "avoid-repetitive-openers" in text:
        return "avoid-repetitive-openers"
    if "hej" in text and "hver-gang" in text:
        return "avoid-repetitive-openers"
    if text.startswith("development-focus:"):
        return text.removeprefix("development-focus:").replace(":", "-")
    return ""


def _domain_key_from_critic(canonical_key: str) -> str:
    text = str(canonical_key or "")
    if "danish-concise-calibration" in text:
        return "danish-concise-calibration"
    if "avoid-repetitive-openers" in text:
        return "avoid-repetitive-openers"
    return ""


def _domain_key_from_self_model(canonical_key: str) -> str:
    text = str(canonical_key or "")
    if text.startswith("self-model:limitation:"):
        return text.removeprefix("self-model:limitation:")
    if text.startswith("self-model:improving:"):
        return text.removeprefix("self-model:improving:")
    return ""


def _goal_domain_key(canonical_key: str) -> str:
    return str(canonical_key or "").removeprefix("goal-signal:")


def _message_domain_key(text: str) -> str:
    lower = str(text or "").lower()
    if ("dansk" in lower or "danish" in lower) and any(token in lower for token in ("kort", "korte", "concise", "short")):
        return "danish-concise-calibration"
    if "hej" in lower and "hver gang" in lower:
        return "avoid-repetitive-openers"
    return ""


def _goal_title(domain_key: str, fallback: str) -> str:
    if domain_key == "danish-concise-calibration":
        return "Current goal: make concise Danish calibration land visibly"
    if domain_key == "avoid-repetitive-openers":
        return "Current goal: eliminate repetitive opener habits"
    return f"Current goal: make {fallback.lower()} land visibly"


def _merge_fragments(*parts: str) -> str:
    seen: list[str] = []
    for part in parts:
        normalized = " ".join(str(part or "").split()).strip()
        if normalized and normalized not in seen:
            seen.append(normalized)
    return " ".join(seen)


def _rank(value: str) -> int:
    return int(_CONFIDENCE_RANKS.get(str(value or "").strip().lower(), 0))


def _parse_dt(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(str(value or "").replace("Z", "+00:00"))
    except ValueError:
        return None
