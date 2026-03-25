from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from apps.api.jarvis_api.services.heartbeat_runtime import heartbeat_runtime_surface
from apps.api.jarvis_api.services.non_visible_lane_execution import (
    local_lane_execution_truth,
)
from apps.api.jarvis_api.services.visible_model import visible_execution_readiness
from core.eventbus.bus import event_bus
from core.runtime.db import (
    list_runtime_awareness_signals,
    supersede_runtime_awareness_signals,
    update_runtime_awareness_signal_status,
    upsert_runtime_awareness_signal,
)

_STALE_AFTER_DAYS = 7


def track_runtime_awareness_signals_for_visible_turn(
    *,
    session_id: str | None,
    run_id: str,
) -> dict[str, object]:
    normalized_session_id = str(session_id or "").strip()
    signals = _extract_runtime_awareness_candidates()
    items = _persist_runtime_awareness_signals(
        signals=signals,
        session_id=normalized_session_id,
        run_id=run_id,
    )
    return {
        "created": len([item for item in items if item.get("was_created")]),
        "updated": len([item for item in items if item.get("was_updated")]),
        "items": items,
        "summary": (
            f"Tracked {len(items)} bounded runtime-awareness signals."
            if items
            else "No bounded hardware/runtime awareness signal warranted tracking."
        ),
    }


def refresh_runtime_awareness_signal_statuses() -> dict[str, int]:
    now = datetime.now(UTC)
    refreshed = 0
    for item in list_runtime_awareness_signals(limit=40):
        if str(item.get("status") or "") not in {"active", "constrained", "recovered"}:
            continue
        updated_at = _parse_dt(str(item.get("updated_at") or item.get("created_at") or ""))
        if updated_at is None or updated_at > now - timedelta(days=_STALE_AFTER_DAYS):
            continue
        refreshed_item = update_runtime_awareness_signal_status(
            str(item.get("signal_id") or ""),
            status="stale",
            updated_at=now.isoformat(),
            status_reason="Marked stale after bounded runtime-situation inactivity window.",
        )
        if refreshed_item is not None:
            refreshed += 1
            event_bus.publish(
                "runtime_awareness_signal.stale",
                {
                    "signal_id": refreshed_item.get("signal_id"),
                    "signal_type": refreshed_item.get("signal_type"),
                    "status": refreshed_item.get("status"),
                    "summary": refreshed_item.get("summary"),
                },
            )
    return {"stale_marked": refreshed}


def build_runtime_awareness_signal_surface(*, limit: int = 8) -> dict[str, object]:
    refresh_runtime_awareness_signal_statuses()
    items = list_runtime_awareness_signals(limit=max(limit, 1))
    active = [item for item in items if str(item.get("status") or "") == "active"]
    constrained = [item for item in items if str(item.get("status") or "") == "constrained"]
    recovered = [item for item in items if str(item.get("status") or "") == "recovered"]
    stale = [item for item in items if str(item.get("status") or "") == "stale"]
    superseded = [item for item in items if str(item.get("status") or "") == "superseded"]
    ordered = [*constrained, *active, *recovered, *stale, *superseded]
    latest = next(iter(constrained or active or recovered or stale or superseded), None)
    machine_state = _machine_state_summary(
        constrained=constrained,
        active=active,
        recovered=recovered,
    )
    return {
        "active": bool(active or constrained or recovered),
        "items": ordered,
        "recent_history": [_history_item_from_signal(item) for item in items[: min(max(limit, 1), 5)]],
        "summary": {
            "active_count": len(active),
            "constrained_count": len(constrained),
            "recovered_count": len(recovered),
            "stale_count": len(stale),
            "superseded_count": len(superseded),
            "current_signal": str((latest or {}).get("title") or "No active runtime-awareness signal"),
            "current_status": str((latest or {}).get("status") or "none"),
            "machine_state": machine_state["label"],
            "machine_detail": machine_state["detail"],
        },
    }


def _extract_runtime_awareness_candidates() -> list[dict[str, object]]:
    readiness = visible_execution_readiness()
    local_lane = local_lane_execution_truth()
    heartbeat = heartbeat_runtime_surface().get("state") or {}
    signals: list[dict[str, object]] = []

    visible_signal = _visible_runtime_signal(readiness=readiness)
    if visible_signal:
        signals.append(visible_signal)

    local_signal = _local_lane_signal(local_lane=local_lane)
    if local_signal:
        signals.append(local_signal)

    heartbeat_signal = _heartbeat_runtime_signal(heartbeat=heartbeat, readiness=readiness)
    if heartbeat_signal:
        signals.append(heartbeat_signal)

    return signals


def _visible_runtime_signal(*, readiness: dict[str, object]) -> dict[str, object] | None:
    provider = str(readiness.get("provider") or "").strip()
    provider_status = str(readiness.get("provider_status") or "unknown").strip()
    model = str(readiness.get("model") or "").strip() or "unknown-model"
    reachable = bool(readiness.get("provider_reachable"))
    live_verified = bool(readiness.get("live_verified"))
    if provider not in {"ollama", "phase1-runtime"}:
        return None

    if provider == "phase1-runtime":
        return {
            "signal_type": "visible-runtime-situation",
            "canonical_key": "runtime-awareness:visible-runtime",
            "status": "active",
            "title": "Visible runtime is operating in local fallback mode",
            "summary": "Jarvis is currently using the local fallback visible runtime instead of a live provider-backed lane.",
            "rationale": "This bounded signal captures a meaningful local runtime situation without creating a broader monitoring layer.",
            "source_kind": "runtime-health",
            "confidence": "medium",
            "evidence_summary": f"provider={provider} provider_status={provider_status or 'local-fallback'} model={model}",
            "support_summary": "Visible execution is local fallback backed.",
            "support_count": 1,
            "session_count": 1,
            "status_reason": "Local fallback mode is currently active.",
        }

    if reachable and provider_status == "ready":
        status = "active"
        title = "Visible local model lane is ready"
        summary = "Jarvis is currently running against a reachable local visible-model runtime."
        if not live_verified:
            summary = "Jarvis is currently pointed at a reachable local visible-model runtime, but it has only bounded readiness evidence."
        return {
            "signal_type": "visible-local-runtime",
            "canonical_key": "runtime-awareness:visible-local-runtime",
            "status": status,
            "title": title,
            "summary": summary,
            "rationale": "This keeps Jarvis' situated awareness of his visible local runtime available in a bounded, operator-readable form.",
            "source_kind": "runtime-health",
            "confidence": "high" if live_verified else "medium",
            "evidence_summary": f"provider={provider} model={model} status={provider_status} live_verified={str(live_verified).lower()}",
            "support_summary": "Visible local runtime probe succeeded.",
            "support_count": 1,
            "session_count": 1,
            "status_reason": "Visible local runtime is currently reachable and ready.",
        }

    return {
        "signal_type": "visible-local-runtime",
        "canonical_key": "runtime-awareness:visible-local-runtime",
        "status": "constrained",
        "title": "Visible local model lane is constrained",
        "summary": "Jarvis is currently carrying a bounded signal that the visible local-model path is constrained or unavailable.",
        "rationale": "Visible local runtime friction materially affects Jarvis' situated behavior and should stay observable as a bounded signal.",
        "source_kind": "runtime-health",
        "confidence": "high",
        "evidence_summary": f"provider={provider} model={model} reachable={str(reachable).lower()} status={provider_status}",
        "support_summary": "Visible local runtime probe did not return ready.",
        "support_count": 1,
        "session_count": 1,
        "status_reason": f"Visible local runtime status is {provider_status or 'unknown'}.",
    }


def _local_lane_signal(*, local_lane: dict[str, object]) -> dict[str, object] | None:
    provider = str((local_lane.get("target") or {}).get("provider") or "").strip()
    status = str(local_lane.get("status") or "").strip()
    provider_status = str(local_lane.get("provider_status") or "").strip()
    model = str((local_lane.get("target") or {}).get("model") or "").strip() or "unknown-model"
    can_execute = bool(local_lane.get("can_execute"))
    if provider not in {"ollama", "phase1-runtime"}:
        return None
    if can_execute and status in {"ready", "local-fallback"}:
        return {
            "signal_type": "local-execution-lane",
            "canonical_key": "runtime-awareness:local-execution-lane",
            "status": "active",
            "title": "Local execution lane is ready",
            "summary": "Jarvis currently has a usable local execution lane available for bounded internal runtime work.",
            "rationale": "Local execution readiness is part of Jarvis' situated machine awareness and should be visible without becoming a control plane.",
            "source_kind": "lane-readiness",
            "confidence": "medium",
            "evidence_summary": f"provider={provider} model={model} status={status} provider_status={provider_status}",
            "support_summary": "Local execution lane reports can_execute=true.",
            "support_count": 1,
            "session_count": 1,
            "status_reason": "Local execution lane is currently ready.",
        }
    return {
        "signal_type": "local-execution-lane",
        "canonical_key": "runtime-awareness:local-execution-lane",
        "status": "constrained",
        "title": "Local execution lane is constrained",
        "summary": "Jarvis is currently carrying a bounded signal that the local execution lane is not ready for normal internal local work.",
        "rationale": "Local execution-lane friction matters to Jarvis' situated behavior and should remain visible as derived runtime truth.",
        "source_kind": "lane-readiness",
        "confidence": "high",
        "evidence_summary": f"provider={provider} model={model} status={status or 'unknown'} provider_status={provider_status or 'unknown'} can_execute={str(can_execute).lower()}",
        "support_summary": "Local execution lane reports can_execute=false or non-ready status.",
        "support_count": 1,
        "session_count": 1,
        "status_reason": f"Local execution lane status is {status or provider_status or 'unknown'}.",
    }


def _heartbeat_runtime_signal(*, heartbeat: dict[str, object], readiness: dict[str, object]) -> dict[str, object] | None:
    last_blocked_reason = str(heartbeat.get("last_blocked_reason") or "").strip()
    lane = str(heartbeat.get("lane") or "").strip()
    provider = str(heartbeat.get("provider") or "").strip()
    if not last_blocked_reason:
        return None
    if lane not in {"local", "visible"} and provider not in {"ollama", "phase1-runtime"}:
        return None
    if last_blocked_reason in {"disabled", "kill-switch"}:
        return None
    return {
        "signal_type": "heartbeat-runtime-friction",
        "canonical_key": "runtime-awareness:heartbeat-runtime-friction",
        "status": "constrained",
        "title": "Heartbeat is carrying local runtime friction",
        "summary": "Jarvis is currently carrying a bounded awareness signal that heartbeat work is encountering runtime friction.",
        "rationale": "Heartbeat friction is part of Jarvis' situated machine/runtime condition and is useful as a bounded internal awareness signal.",
        "source_kind": "heartbeat-runtime",
        "confidence": "medium",
        "evidence_summary": f"heartbeat_provider={provider or readiness.get('provider') or 'unknown'} lane={lane or 'unknown'} blocked_reason={last_blocked_reason}",
        "support_summary": "Recent heartbeat runtime state reports a non-policy blocked reason.",
        "support_count": 1,
        "session_count": 1,
        "status_reason": f"Recent heartbeat blocked reason: {last_blocked_reason}.",
    }


def _persist_runtime_awareness_signals(
    *,
    signals: list[dict[str, object]],
    session_id: str,
    run_id: str,
) -> list[dict[str, object]]:
    now = datetime.now(UTC).isoformat()
    persisted: list[dict[str, object]] = []
    for signal in signals:
        existing = _latest_runtime_awareness_signal(str(signal.get("canonical_key") or ""))
        desired_status = str(signal.get("status") or "active")
        if existing and str(existing.get("status") or "") == "constrained" and desired_status == "active":
            signal["status"] = "recovered"
            signal["status_reason"] = "Previously constrained runtime thread has recovered into a ready state."
        persisted_item = upsert_runtime_awareness_signal(
            signal_id=f"runtimeaware-{uuid4().hex}",
            signal_type=str(signal.get("signal_type") or "runtime-awareness-signal"),
            canonical_key=str(signal.get("canonical_key") or ""),
            status=str(signal.get("status") or "active"),
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
                "runtime_awareness_signal.created",
                {
                    "signal_id": persisted_item.get("signal_id"),
                    "signal_type": persisted_item.get("signal_type"),
                    "status": persisted_item.get("status"),
                    "summary": persisted_item.get("summary"),
                },
            )
        elif persisted_item.get("was_updated"):
            kind = "runtime_awareness_signal.updated"
            if persisted_item.get("status") == "recovered":
                kind = "runtime_awareness_signal.recovered"
            event_bus.publish(
                kind,
                {
                    "signal_id": persisted_item.get("signal_id"),
                    "signal_type": persisted_item.get("signal_type"),
                    "status": persisted_item.get("status"),
                    "summary": persisted_item.get("summary"),
                },
            )
        superseded_count = 0
        if persisted_item.get("status") in {"constrained", "recovered"}:
            superseded_count = supersede_runtime_awareness_signals(
                signal_type=str(persisted_item.get("signal_type") or ""),
                exclude_signal_id=str(persisted_item.get("signal_id") or ""),
                updated_at=now,
                status_reason="Superseded by newer runtime-awareness state for the same bounded signal family.",
            )
        if superseded_count > 0:
            event_bus.publish(
                "runtime_awareness_signal.superseded",
                {
                    "signal_id": persisted_item.get("signal_id"),
                    "signal_type": persisted_item.get("signal_type"),
                    "superseded_count": superseded_count,
                    "summary": persisted_item.get("summary"),
                },
            )
        persisted.append(persisted_item)
    return persisted


def _latest_runtime_awareness_signal(canonical_key: str) -> dict[str, object] | None:
    for item in list_runtime_awareness_signals(limit=20):
        if str(item.get("canonical_key") or "") == canonical_key:
            return item
    return None


def _history_item_from_signal(item: dict[str, object]) -> dict[str, object]:
    return {
        "signal_id": item.get("signal_id"),
        "signal_type": item.get("signal_type"),
        "title": item.get("title"),
        "status": item.get("status"),
        "confidence": item.get("confidence"),
        "summary": item.get("summary"),
        "status_reason": item.get("status_reason"),
        "updated_at": item.get("updated_at"),
        "created_at": item.get("created_at"),
    }


def _machine_state_summary(
    *,
    constrained: list[dict[str, object]],
    active: list[dict[str, object]],
    recovered: list[dict[str, object]],
) -> dict[str, str]:
    if constrained:
        item = constrained[0]
        return {
            "label": "Constrained",
            "detail": str(item.get("title") or item.get("status_reason") or "A local runtime thread is constrained."),
        }
    if recovered:
        item = recovered[0]
        return {
            "label": "Recovering",
            "detail": str(item.get("title") or item.get("status_reason") or "A local runtime thread has recently recovered."),
        }
    if active:
        titles = [str(item.get("title") or "").strip() for item in active[:2] if str(item.get("title") or "").strip()]
        if titles:
            return {
                "label": "Local Runtime Stable",
                "detail": " · ".join(titles),
            }
    return {
        "label": "No machine signal",
        "detail": "No active bounded machine/runtime situation is being carried right now.",
    }


def _parse_dt(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None
