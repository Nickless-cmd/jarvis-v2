from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from apps.api.jarvis_api.services.attachment_topology_signal_tracking import (
    build_runtime_attachment_topology_signal_surface,
)
from apps.api.jarvis_api.services.autonomy_pressure_signal_tracking import (
    build_runtime_autonomy_pressure_signal_surface,
)
from apps.api.jarvis_api.services.chronicle_consolidation_brief_tracking import (
    build_runtime_chronicle_consolidation_brief_surface,
)
from apps.api.jarvis_api.services.loyalty_gradient_signal_tracking import (
    build_runtime_loyalty_gradient_signal_surface,
)
from apps.api.jarvis_api.services.meaning_significance_signal_tracking import (
    build_runtime_meaning_significance_signal_surface,
)
from apps.api.jarvis_api.services.proactive_loop_lifecycle_tracking import (
    build_runtime_proactive_loop_lifecycle_surface,
)
from apps.api.jarvis_api.services.regulation_homeostasis_signal_tracking import (
    build_runtime_regulation_homeostasis_signal_surface,
)
from apps.api.jarvis_api.services.release_marker_signal_tracking import (
    build_runtime_release_marker_signal_surface,
)
from apps.api.jarvis_api.services.relation_continuity_signal_tracking import (
    build_runtime_relation_continuity_signal_surface,
)
from apps.api.jarvis_api.services.runtime_awareness_signal_tracking import (
    build_runtime_awareness_signal_surface,
)
from apps.api.jarvis_api.services.witness_signal_tracking import (
    build_runtime_witness_signal_surface,
)
from core.eventbus.bus import event_bus
from core.runtime.db import (
    list_runtime_proactive_question_gates,
    supersede_runtime_proactive_question_gates_for_kind,
    update_runtime_proactive_question_gate_status,
    upsert_runtime_proactive_question_gate,
)

_STALE_AFTER_DAYS = 7
_CONFIDENCE_RANKS = {"low": 0, "medium": 1, "high": 2}
_WEIGHT_RANKS = {"low": 0, "medium": 1, "high": 2}


def track_runtime_proactive_question_gates_for_visible_turn(
    *,
    session_id: str | None,
    run_id: str,
) -> dict[str, object]:
    normalized_session_id = str(session_id or "").strip()
    items = _persist_proactive_question_gates(
        signals=_extract_proactive_question_gate_candidates(),
        session_id=normalized_session_id,
        run_id=run_id,
    )
    return {
        "created": len([item for item in items if item.get("was_created")]),
        "updated": len([item for item in items if item.get("was_updated")]),
        "items": items,
        "summary": (
            f"Tracked {len(items)} bounded proactive-question gate signals."
            if items
            else "No bounded proactive-question gate signal warranted tracking."
        ),
    }


def refresh_runtime_proactive_question_gate_statuses() -> dict[str, int]:
    now = datetime.now(UTC)
    refreshed = 0
    for item in list_runtime_proactive_question_gates(limit=40):
        if str(item.get("status") or "") not in {"active", "softening"}:
            continue
        updated_at = _parse_dt(str(item.get("updated_at") or item.get("created_at") or ""))
        if updated_at is None or updated_at > now - timedelta(days=_STALE_AFTER_DAYS):
            continue
        refreshed_item = update_runtime_proactive_question_gate_status(
            str(item.get("gate_id") or ""),
            status="stale",
            updated_at=now.isoformat(),
            status_reason="Marked stale after bounded proactive-question gate inactivity window.",
        )
        if refreshed_item is None:
            continue
        refreshed += 1
        event_bus.publish(
            "proactive_question_gate.stale",
            {
                "gate_id": refreshed_item.get("gate_id"),
                "gate_type": refreshed_item.get("gate_type"),
                "status": refreshed_item.get("status"),
                "summary": refreshed_item.get("summary"),
            },
        )
    return {"stale_marked": refreshed}


def build_runtime_proactive_question_gate_surface(*, limit: int = 8) -> dict[str, object]:
    refresh_runtime_proactive_question_gate_statuses()
    items = list_runtime_proactive_question_gates(limit=max(limit, 1))
    enriched_items = [_with_surface_view(item) for item in items]
    active = [item for item in enriched_items if str(item.get("status") or "") == "active"]
    softening = [item for item in enriched_items if str(item.get("status") or "") == "softening"]
    stale = [item for item in enriched_items if str(item.get("status") or "") == "stale"]
    superseded = [item for item in enriched_items if str(item.get("status") or "") == "superseded"]
    ordered = [*active, *softening, *stale, *superseded]
    latest = next(iter(active or softening or stale or superseded), None)
    return {
        "active": bool(active or softening),
        "authority": "non-authoritative",
        "layer_role": "runtime-support",
        "planner_authority_state": "not-planner-authority",
        "proactive_execution_state": "not-proactive-execution",
        "canonical_intention_state": "not-canonical-intention-truth",
        "prompt_inclusion_state": "not-prompt-included",
        "workflow_bridge_state": "not-workflow-bridge",
        "items": ordered,
        "summary": {
            "active_count": len(active),
            "softening_count": len(softening),
            "stale_count": len(stale),
            "superseded_count": len(superseded),
            "current_gate": str((latest or {}).get("title") or "No active proactive-question gate support"),
            "current_status": str((latest or {}).get("status") or "none"),
            "current_state": str((latest or {}).get("question_gate_state") or "none"),
            "current_reason": str((latest or {}).get("question_gate_reason") or "none"),
            "current_weight": str((latest or {}).get("question_gate_weight") or "low"),
            "current_confidence": str((latest or {}).get("question_gate_confidence") or "low"),
            "current_send_permission_state": str((latest or {}).get("send_permission_state") or "not-granted"),
            "authority": "non-authoritative",
            "layer_role": "runtime-support",
            "planner_authority_state": "not-planner-authority",
            "proactive_execution_state": "not-proactive-execution",
            "canonical_intention_state": "not-canonical-intention-truth",
            "prompt_inclusion_state": "not-prompt-included",
            "workflow_bridge_state": "not-workflow-bridge",
        },
    }


def _extract_proactive_question_gate_candidates() -> list[dict[str, object]]:
    autonomy = build_runtime_autonomy_pressure_signal_surface(limit=8)
    loops = build_runtime_proactive_loop_lifecycle_surface(limit=8)
    relation = build_runtime_relation_continuity_signal_surface(limit=6)
    meaning = build_runtime_meaning_significance_signal_surface(limit=6)
    witness = build_runtime_witness_signal_surface(limit=6)
    chronicle = build_runtime_chronicle_consolidation_brief_surface(limit=6)
    attachment = build_runtime_attachment_topology_signal_surface(limit=6)
    loyalty = build_runtime_loyalty_gradient_signal_surface(limit=6)
    awareness = build_runtime_awareness_signal_surface(limit=6)
    regulation = build_runtime_regulation_homeostasis_signal_surface(limit=6)
    release = build_runtime_release_marker_signal_surface(limit=6)

    question_pressure = next(
        (
            item
            for item in autonomy.get("items", [])
            if str(item.get("autonomy_pressure_type") or "") == "question-pressure"
            and str(item.get("status") or "") in {"active", "softening"}
        ),
        None,
    )
    question_loop = next(
        (
            item
            for item in loops.get("items", [])
            if str(item.get("loop_kind") or "") == "question-loop"
            and str(item.get("status") or "") in {"active", "softening"}
        ),
        None,
    )
    if question_pressure is None or question_loop is None:
        return []
    if not relation.get("active") or not meaning.get("active"):
        return []

    question_readiness = str(question_loop.get("question_readiness") or "low")
    relation_weight = str(relation.get("summary", {}).get("current_weight") or "low")
    meaning_weight = str(meaning.get("summary", {}).get("current_weight") or "low")
    if question_readiness == "low" and relation_weight == "low" and meaning_weight == "low":
        return []

    awareness_constrained = int(awareness.get("summary", {}).get("constrained_count") or 0) > 0
    release_state = str(release.get("summary", {}).get("current_state") or "none")
    witness_carried = int(witness.get("summary", {}).get("carried_count") or 0) > 0
    chronicle_weight = str(chronicle.get("summary", {}).get("current_weight") or "low")
    loyalty_weight = str(loyalty.get("summary", {}).get("current_weight") or "low")
    attachment_weight = str(attachment.get("summary", {}).get("current_weight") or "low")

    gate_weight = _max_ranked(
        question_readiness,
        str(question_pressure.get("autonomy_pressure_weight") or "low"),
        relation_weight,
        meaning_weight,
    )
    if release_state in {"release-leaning", "releasing"} and gate_weight == "high":
        gate_weight = "medium"
    if awareness_constrained and gate_weight == "high":
        gate_weight = "medium"

    gate_reason = _gate_reason(
        awareness_constrained=awareness_constrained,
        release_state=release_state,
        witness_carried=witness_carried,
        chronicle_weight=chronicle_weight,
        loyalty_weight=loyalty_weight,
        attachment_weight=attachment_weight,
        question_readiness=question_readiness,
    )
    gate_state = (
        "question-gated-candidate"
        if gate_weight == "high" and not awareness_constrained and release_state not in {"release-leaning", "releasing"}
        else "question-gated-hold"
    )
    status = "softening" if release_state in {"release-leaning", "releasing"} else "active"
    source_anchor = _merge_fragments(
        str(question_pressure.get("source_anchor") or ""),
        str(question_loop.get("source_anchor") or ""),
        _source_anchor(relation, fallback="relation-continuity"),
        _source_anchor(meaning, fallback="meaning-significance"),
        _source_anchor(loyalty, fallback="loyalty-gradient"),
        _source_anchor(awareness, fallback="runtime-awareness"),
    )
    confidence = _stronger_confidence(
        str(question_pressure.get("autonomy_pressure_confidence") or "low"),
        str(question_loop.get("loop_confidence") or "low"),
        str(relation.get("summary", {}).get("current_confidence") or "low"),
        str(meaning.get("summary", {}).get("current_confidence") or "low"),
        str(loyalty.get("summary", {}).get("current_confidence") or "low"),
    )

    return [
        {
            "gate_type": "proactive-question-gate",
            "canonical_key": f"proactive-question-gate:{_slug(str(question_loop.get('loop_focus') or 'bounded-question-loop'))}",
            "status": status,
            "title": f"Proactive question gate: {str(question_loop.get('loop_focus') or 'bounded question loop')[:96]}",
            "summary": (
                "Bounded proactive-question gating is surfacing a runtime question candidate only. "
                "This is not send permission and not proactive execution."
            ),
            "rationale": (
                "A proactive-question gate may return only when bounded question pressure and question-loop lifecycle already exist, "
                "with relation and meaning continuity support, without granting execution or messaging authority."
            ),
            "source_kind": "runtime-derived-support",
            "confidence": confidence,
            "evidence_summary": _merge_fragments(
                str(question_pressure.get("autonomy_pressure_summary") or ""),
                str(question_loop.get("loop_summary") or ""),
                str(relation.get("summary", {}).get("current_signal") or ""),
                str(meaning.get("summary", {}).get("current_signal") or ""),
            ),
            "support_summary": _merge_fragments(
                f"question-gate-state={gate_state}",
                f"question-gate-reason={gate_reason}",
                f"question-gate-weight={gate_weight}",
                f"question-gate-confidence={confidence}",
                "send-permission-state=gated-candidate-only" if gate_state == "question-gated-candidate" else "send-permission-state=not-granted",
                f"source-anchor={source_anchor}",
                f"question-readiness={question_readiness}",
                f"relation-weight={relation_weight}",
                f"meaning-weight={meaning_weight}",
                f"regulation-state={regulation.get('summary', {}).get('current_state') or 'none'}",
                f"release-state={release_state}",
            ),
            "support_count": max(
                int(question_pressure.get("support_count") or 1),
                int(question_loop.get("support_count") or 1),
                1,
            ),
            "session_count": max(
                int(question_pressure.get("session_count") or 1),
                int(question_loop.get("session_count") or 1),
                1,
            ),
            "status_reason": (
                "Bounded proactive-question gating remains runtime-only candidate truth and does not grant send permission, planner authority, or workflow execution."
            ),
        }
    ]


def _persist_proactive_question_gates(
    *,
    signals: list[dict[str, object]],
    session_id: str,
    run_id: str,
) -> list[dict[str, object]]:
    now = datetime.now(UTC).isoformat()
    persisted: list[dict[str, object]] = []
    for signal in signals:
        persisted_item = upsert_runtime_proactive_question_gate(
            gate_id=f"proactive-question-gate-{uuid4().hex}",
            gate_type=str(signal.get("gate_type") or "proactive-question-gate"),
            canonical_key=str(signal.get("canonical_key") or ""),
            status=str(signal.get("status") or "active"),
            title=str(signal.get("title") or ""),
            summary=str(signal.get("summary") or ""),
            rationale=str(signal.get("rationale") or ""),
            source_kind=str(signal.get("source_kind") or "runtime-derived-support"),
            confidence=str(signal.get("confidence") or "low"),
            evidence_summary=str(signal.get("evidence_summary") or ""),
            support_summary=str(signal.get("support_summary") or ""),
            status_reason=str(signal.get("status_reason") or ""),
            run_id=run_id,
            session_id=session_id,
            support_count=int(signal.get("support_count") or 1),
            session_count=int(signal.get("session_count") or 1),
            created_at=now,
            updated_at=now,
        )
        superseded_count = supersede_runtime_proactive_question_gates_for_kind(
            gate_type=str(signal.get("gate_type") or ""),
            exclude_gate_id=str(persisted_item.get("gate_id") or ""),
            updated_at=now,
            status_reason="Superseded by a newer bounded proactive-question gate for the same gate type.",
        )
        view = _with_surface_view(persisted_item)
        event_bus.publish(
            "proactive_question_gate.tracked",
            {
                "gate_id": view.get("gate_id"),
                "question_gate_state": view.get("question_gate_state"),
                "question_gate_weight": view.get("question_gate_weight"),
                "status": view.get("status"),
                "superseded_count": superseded_count,
                "summary": view.get("question_gate_summary"),
            },
        )
        persisted.append({**view, "superseded_count": superseded_count})
    return persisted


def _with_surface_view(item: dict[str, object]) -> dict[str, object]:
    support_summary = str(item.get("support_summary") or "")
    return {
        **item,
        "source": "/mc/runtime.proactive_question_gate",
        "question_gate_state": _find_support_value(support_summary, "question-gate-state", "question-gated-hold"),
        "question_gate_reason": _find_support_value(support_summary, "question-gate-reason", "bounded-runtime-candidate"),
        "question_gate_weight": _find_support_value(support_summary, "question-gate-weight", "low"),
        "question_gate_summary": str(item.get("summary") or ""),
        "question_gate_confidence": _find_support_value(support_summary, "question-gate-confidence", str(item.get("confidence") or "low")),
        "send_permission_state": _find_support_value(support_summary, "send-permission-state", "not-granted"),
        "source_anchor": _find_support_value(support_summary, "source-anchor", ""),
        "authority": "non-authoritative",
        "layer_role": "runtime-support",
        "planner_authority_state": "not-planner-authority",
        "proactive_execution_state": "not-proactive-execution",
        "canonical_intention_state": "not-canonical-intention-truth",
        "prompt_inclusion_state": "not-prompt-included",
        "workflow_bridge_state": "not-workflow-bridge",
    }


def _gate_reason(
    *,
    awareness_constrained: bool,
    release_state: str,
    witness_carried: bool,
    chronicle_weight: str,
    loyalty_weight: str,
    attachment_weight: str,
    question_readiness: str,
) -> str:
    if awareness_constrained:
        return "runtime-constrained"
    if release_state in {"release-leaning", "releasing"}:
        return "release-softened"
    if question_readiness == "high" and (loyalty_weight == "high" or attachment_weight == "high"):
        return "relationally-held"
    if witness_carried or chronicle_weight in {"medium", "high"}:
        return "carried-context"
    return "bounded-question-candidate"


def _source_anchor(surface: dict[str, object], *, fallback: str) -> str:
    for item in surface.get("items", []):
        anchor = str(item.get("source_anchor") or "").strip()
        if anchor:
            return anchor
    return fallback


def _find_support_value(summary: str, key: str, default: str) -> str:
    marker = f"{key}="
    for fragment in summary.split("|"):
        fragment = fragment.strip()
        if fragment.startswith(marker):
            value = fragment[len(marker):].strip()
            if value:
                return value
    return default


def _max_ranked(*values: str) -> str:
    best = "low"
    for value in values:
        normalized = str(value or "low").strip().lower() or "low"
        if _WEIGHT_RANKS.get(normalized, 0) > _WEIGHT_RANKS.get(best, 0):
            best = normalized
    return best


def _stronger_confidence(*values: str) -> str:
    strongest = "low"
    for value in values:
        normalized = str(value or "low").strip().lower() or "low"
        if _CONFIDENCE_RANKS.get(normalized, 0) > _CONFIDENCE_RANKS.get(strongest, 0):
            strongest = normalized
    return strongest


def _merge_fragments(*values: object) -> str:
    seen: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if text and text not in seen:
            seen.append(text)
    return " | ".join(seen)


def _slug(value: str) -> str:
    candidate = "".join(char.lower() if char.isalnum() else "-" for char in str(value or ""))
    while "--" in candidate:
        candidate = candidate.replace("--", "-")
    return candidate.strip("-") or "bounded-question-loop"


def _parse_dt(value: str) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)
