from __future__ import annotations

from apps.api.jarvis_api.services.runtime_surface_cache import (
    get_cached_runtime_surface,
)

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
from apps.api.jarvis_api.services.metabolism_state_signal_tracking import (
    build_runtime_metabolism_state_signal_surface,
)
from apps.api.jarvis_api.services.open_loop_closure_proposal_tracking import (
    build_runtime_open_loop_closure_proposal_surface,
)
from apps.api.jarvis_api.services.open_loop_signal_tracking import (
    build_runtime_open_loop_signal_surface,
)
from apps.api.jarvis_api.services.private_initiative_tension_signal_tracking import (
    build_runtime_private_initiative_tension_signal_surface,
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
from apps.api.jarvis_api.services.witness_signal_tracking import (
    build_runtime_witness_signal_surface,
)
from core.eventbus.bus import event_bus
from core.runtime.db import (
    list_runtime_proactive_loop_lifecycle_signals,
    supersede_runtime_proactive_loop_lifecycle_signals_for_kind,
    update_runtime_proactive_loop_lifecycle_signal_status,
    upsert_runtime_proactive_loop_lifecycle_signal,
)

_STALE_AFTER_DAYS = 7
_CONFIDENCE_RANKS = {"low": 0, "medium": 1, "high": 2}
_WEIGHT_RANKS = {"low": 0, "medium": 1, "high": 2}
_STATE_RANKS = {
    "loop-emerging": 0,
    "loop-carried": 1,
    "loop-question-worthy": 2,
    "loop-closure-worthy": 3,
}


def track_runtime_proactive_loop_lifecycle_signals_for_visible_turn(
    *,
    session_id: str | None,
    run_id: str,
) -> dict[str, object]:
    normalized_session_id = str(session_id or "").strip()
    items = _persist_proactive_loop_lifecycle_signals(
        signals=_extract_proactive_loop_lifecycle_candidates(),
        session_id=normalized_session_id,
        run_id=run_id,
    )
    return {
        "created": len([item for item in items if item.get("was_created")]),
        "updated": len([item for item in items if item.get("was_updated")]),
        "items": items,
        "summary": (
            f"Tracked {len(items)} bounded proactive-loop lifecycle signals."
            if items
            else "No bounded proactive-loop lifecycle signal warranted tracking."
        ),
    }


def refresh_runtime_proactive_loop_lifecycle_signal_statuses() -> dict[str, int]:
    now = datetime.now(UTC)
    refreshed = 0
    for item in list_runtime_proactive_loop_lifecycle_signals(limit=40):
        if str(item.get("status") or "") not in {"active", "softening"}:
            continue
        updated_at = _parse_dt(str(item.get("updated_at") or item.get("created_at") or ""))
        if updated_at is None or updated_at > now - timedelta(days=_STALE_AFTER_DAYS):
            continue
        refreshed_item = update_runtime_proactive_loop_lifecycle_signal_status(
            str(item.get("signal_id") or ""),
            status="stale",
            updated_at=now.isoformat(),
            status_reason="Marked stale after bounded proactive-loop inactivity window.",
        )
        if refreshed_item is None:
            continue
        refreshed += 1
        event_bus.publish(
            "proactive_loop_lifecycle.stale",
            {
                "signal_id": refreshed_item.get("signal_id"),
                "signal_type": refreshed_item.get("signal_type"),
                "status": refreshed_item.get("status"),
                "summary": refreshed_item.get("summary"),
                "status_reason": refreshed_item.get("status_reason"),
            },
        )
    return {"stale_marked": refreshed}


def build_runtime_proactive_loop_lifecycle_surface(*, limit: int = 8) -> dict[str, object]:
    return get_cached_runtime_surface(
        ("runtime_proactive_loop_lifecycle_surface", max(limit, 1)),
        lambda: _build_runtime_proactive_loop_lifecycle_surface_uncached(
            limit=max(limit, 1)
        ),
    )


def _build_runtime_proactive_loop_lifecycle_surface_uncached(
    *, limit: int = 8
) -> dict[str, object]:
    refresh_runtime_proactive_loop_lifecycle_signal_statuses()
    items = list_runtime_proactive_loop_lifecycle_signals(limit=limit)
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
            "current_signal": str((latest or {}).get("title") or "No active proactive-loop lifecycle support"),
            "current_status": str((latest or {}).get("status") or "none"),
            "current_state": str((latest or {}).get("loop_state") or "none"),
            "current_kind": str((latest or {}).get("loop_kind") or "none"),
            "current_focus": str((latest or {}).get("loop_focus") or "none"),
            "current_weight": str((latest or {}).get("loop_weight") or "low"),
            "current_confidence": str((latest or {}).get("loop_confidence") or "low"),
            "current_question_readiness": str((latest or {}).get("question_readiness") or "low"),
            "current_closure_readiness": str((latest or {}).get("closure_readiness") or "low"),
            "authority": "non-authoritative",
            "layer_role": "runtime-support",
            "planner_authority_state": "not-planner-authority",
            "proactive_execution_state": "not-proactive-execution",
            "canonical_intention_state": "not-canonical-intention-truth",
            "prompt_inclusion_state": "not-prompt-included",
            "workflow_bridge_state": "not-workflow-bridge",
        },
    }


def _extract_proactive_loop_lifecycle_candidates() -> list[dict[str, object]]:
    autonomy = build_runtime_autonomy_pressure_signal_surface(limit=8)
    open_loops = build_runtime_open_loop_signal_surface(limit=8)
    closure = build_runtime_open_loop_closure_proposal_surface(limit=8)
    initiative = build_runtime_private_initiative_tension_signal_surface(limit=6)
    regulation = build_runtime_regulation_homeostasis_signal_surface(limit=6)
    relation = build_runtime_relation_continuity_signal_surface(limit=6)
    meaning = build_runtime_meaning_significance_signal_surface(limit=6)
    witness = build_runtime_witness_signal_surface(limit=6)
    chronicle = build_runtime_chronicle_consolidation_brief_surface(limit=6)
    metabolism = build_runtime_metabolism_state_signal_surface(limit=6)
    release = build_runtime_release_marker_signal_surface(limit=6)
    attachment = build_runtime_attachment_topology_signal_surface(limit=6)
    loyalty = build_runtime_loyalty_gradient_signal_surface(limit=6)

    autonomy_items = {
        str(item.get("autonomy_pressure_type") or ""): item
        for item in autonomy.get("items", [])
        if str(item.get("status") or "") in {"active", "softening"}
    }
    if not autonomy_items:
        return []

    open_items = [
        item
        for item in open_loops.get("items", [])
        if str(item.get("status") or "") in {"open", "softening"}
    ]

    # --- Initiative-tension-driven path (no formal open loop required) ---
    # When initiative tension is at least medium-intensity AND autonomy pressure
    # exists, allow loop materialization from tension alone. This prevents the
    # chain from being blocked when tension is real but no formal open loop has
    # been created yet.
    initiative_intensity = str(initiative.get("summary", {}).get("current_intensity") or "low")
    initiative_active = int(initiative.get("summary", {}).get("active_count") or 0) > 0
    tension_driven = (
        not open_items
        and initiative_active
        and initiative_intensity in {"medium", "high"}
        and "initiative-pressure" in autonomy_items
    )

    if not open_items and not tension_driven:
        return []

    if open_items:
        latest_loop = open_items[0]
    else:
        # Synthesize a minimal open-loop-like dict from initiative tension
        latest_loop = {
            "title": str(initiative.get("summary", {}).get("current_signal") or "initiative tension thread"),
            "status": "open",
            "confidence": initiative_intensity,
            "closure_readiness": "low",
            "source_anchor": "initiative-tension-driven",
            "support_count": 1,
            "session_count": 1,
        }

    focus = _best_loop_focus(
        latest_loop=latest_loop,
        attachment=attachment,
        loyalty=loyalty,
        relation=relation,
        meaning=meaning,
    )
    source_anchor = _merge_fragments(
        str(latest_loop.get("source_anchor") or ""),
        _source_anchor(autonomy, fallback="autonomy-pressure"),
        _source_anchor(relation, fallback="relation-continuity"),
        _source_anchor(meaning, fallback="meaning-significance"),
        _source_anchor(loyalty, fallback="loyalty-gradient"),
        _source_anchor(closure, fallback="open-loop-closure-proposal"),
    )

    candidates: list[dict[str, object]] = []

    initiative_pressure = autonomy_items.get("initiative-pressure")
    if initiative_pressure is not None:
        candidates.append(
            _build_lifecycle_candidate(
                loop_kind="initiative-loop",
                loop_focus=focus,
                open_loop=latest_loop,
                autonomy_pressure=initiative_pressure,
                source_anchor=source_anchor,
                question_readiness="low",
                closure_readiness=str(latest_loop.get("closure_readiness") or "low"),
                relation=relation,
                meaning=meaning,
                witness=witness,
                chronicle=chronicle,
                metabolism=metabolism,
                release=release,
                initiative=initiative,
                regulation=regulation,
            )
        )

    question_pressure = autonomy_items.get("question-pressure")
    if question_pressure is not None:
        candidates.append(
            _build_lifecycle_candidate(
                loop_kind="question-loop",
                loop_focus=focus,
                open_loop=latest_loop,
                autonomy_pressure=question_pressure,
                source_anchor=source_anchor,
                question_readiness=_max_ranked(
                    str(question_pressure.get("autonomy_pressure_weight") or "low"),
                    str(relation.get("summary", {}).get("current_weight") or "low"),
                    str(meaning.get("summary", {}).get("current_weight") or "low"),
                ),
                closure_readiness=str(latest_loop.get("closure_readiness") or "low"),
                relation=relation,
                meaning=meaning,
                witness=witness,
                chronicle=chronicle,
                metabolism=metabolism,
                release=release,
                initiative=initiative,
                regulation=regulation,
            )
        )

    closure_pressure = autonomy_items.get("closure-pressure")
    if closure_pressure is not None:
        candidates.append(
            _build_lifecycle_candidate(
                loop_kind="closure-loop",
                loop_focus=focus,
                open_loop=latest_loop,
                autonomy_pressure=closure_pressure,
                source_anchor=source_anchor,
                question_readiness="low",
                closure_readiness=_max_ranked(
                    str(closure_pressure.get("autonomy_pressure_weight") or "low"),
                    str(latest_loop.get("closure_readiness") or "low"),
                    str(closure.get("summary", {}).get("current_closure_confidence") or "low"),
                ),
                relation=relation,
                meaning=meaning,
                witness=witness,
                chronicle=chronicle,
                metabolism=metabolism,
                release=release,
                initiative=initiative,
                regulation=regulation,
            )
        )

    candidates.sort(
        key=lambda item: (
            _STATE_RANKS.get(str(item.get("loop_state") or ""), 0),
            _WEIGHT_RANKS.get(str(item.get("loop_weight") or "low"), 0),
            _CONFIDENCE_RANKS.get(str(item.get("loop_confidence") or "low"), 0),
        ),
        reverse=True,
    )
    return candidates[:4]


def _build_lifecycle_candidate(
    *,
    loop_kind: str,
    loop_focus: str,
    open_loop: dict[str, object],
    autonomy_pressure: dict[str, object],
    source_anchor: str,
    question_readiness: str,
    closure_readiness: str,
    relation: dict[str, object],
    meaning: dict[str, object],
    witness: dict[str, object],
    chronicle: dict[str, object],
    metabolism: dict[str, object],
    release: dict[str, object],
    initiative: dict[str, object],
    regulation: dict[str, object],
) -> dict[str, object]:
    loop_weight = _max_ranked(
        str(autonomy_pressure.get("autonomy_pressure_weight") or "low"),
        str(open_loop.get("confidence") or "low"),
        str(meaning.get("summary", {}).get("current_weight") or "low"),
    )
    loop_confidence = _stronger_confidence(
        str(autonomy_pressure.get("autonomy_pressure_confidence") or "low"),
        str(open_loop.get("confidence") or "low"),
        str(relation.get("summary", {}).get("current_confidence") or "low"),
        str(meaning.get("summary", {}).get("current_confidence") or "low"),
        str(chronicle.get("summary", {}).get("current_confidence") or "low"),
    )
    loop_state = _derive_loop_state(
        loop_kind=loop_kind,
        open_status=str(open_loop.get("status") or "open"),
        question_readiness=question_readiness,
        closure_readiness=closure_readiness,
        witness_persistence=str(witness.get("summary", {}).get("current_persistence_state") or "none"),
        release_state=str(release.get("summary", {}).get("current_state") or "none"),
    )
    lifecycle_status = (
        "softening"
        if str(open_loop.get("status") or "") == "softening" or loop_state == "loop-closure-worthy"
        else "active"
    )
    summary = _loop_summary(
        loop_kind=loop_kind,
        loop_state=loop_state,
        loop_focus=loop_focus,
        question_readiness=question_readiness,
        closure_readiness=closure_readiness,
    )
    return {
        "signal_type": "proactive-loop-lifecycle",
        "canonical_key": f"proactive-loop-lifecycle:{loop_kind}:{_slug(loop_focus)}",
        "status": lifecycle_status,
        "title": f"Proactive loop lifecycle: {loop_focus}",
        "summary": summary,
        "rationale": (
            "A proactive-loop lifecycle may return only when bounded autonomy pressure is already present on top of an existing open-loop substrate, without becoming planner authority, send permission, or proactive execution."
        ),
        "source_kind": "runtime-derived-support",
        "confidence": loop_confidence,
        "evidence_summary": _merge_fragments(
            str(open_loop.get("summary") or ""),
            str(autonomy_pressure.get("autonomy_pressure_summary") or ""),
            str(relation.get("summary", {}).get("current_signal") or ""),
            str(meaning.get("summary", {}).get("current_signal") or ""),
        ),
        "support_summary": _merge_fragments(
            f"loop-state={loop_state}",
            f"loop-kind={loop_kind}",
            f"loop-focus={loop_focus}",
            f"loop-weight={loop_weight}",
            f"loop-confidence={loop_confidence}",
            f"question-readiness={question_readiness}",
            f"closure-readiness={closure_readiness}",
            f"source-anchor={source_anchor}",
            f"witness-persistence={witness.get('summary', {}).get('current_persistence_state') or 'none'}",
            f"chronicle-weight={chronicle.get('summary', {}).get('current_weight') or 'low'}",
            f"release-state={release.get('summary', {}).get('current_state') or 'none'}",
        ),
        "support_count": max(
            int(autonomy_pressure.get("support_count") or 1),
            int(open_loop.get("support_count") or 1),
            1,
        ),
        "session_count": max(
            int(autonomy_pressure.get("session_count") or 1),
            int(open_loop.get("session_count") or 1),
            1,
        ),
        "status_reason": (
            "Bounded proactive-loop lifecycle remains descriptive runtime support only and is not send permission, planner authority, or execution authority."
        ),
        "loop_state": loop_state,
        "loop_kind": loop_kind,
        "loop_focus": loop_focus,
        "loop_weight": loop_weight,
        "loop_summary": summary,
        "loop_confidence": loop_confidence,
        "question_readiness": question_readiness,
        "closure_readiness": closure_readiness,
        "source_anchor": source_anchor,
        "planner_authority_state": "not-planner-authority",
        "proactive_execution_state": "not-proactive-execution",
        "canonical_intention_state": "not-canonical-intention-truth",
        "prompt_inclusion_state": "not-prompt-included",
        "workflow_bridge_state": "not-workflow-bridge",
        "_initiative_signal": str(initiative.get("summary", {}).get("current_signal") or ""),
        "_regulation_state": str(regulation.get("summary", {}).get("current_state") or ""),
        "_metabolism_state": str(metabolism.get("summary", {}).get("current_state") or ""),
    }


def _persist_proactive_loop_lifecycle_signals(
    *,
    signals: list[dict[str, object]],
    session_id: str,
    run_id: str,
) -> list[dict[str, object]]:
    now = datetime.now(UTC).isoformat()
    persisted: list[dict[str, object]] = []
    for signal in signals:
        persisted_item = upsert_runtime_proactive_loop_lifecycle_signal(
            signal_id=f"proactive-loop-lifecycle-signal-{uuid4().hex}",
            signal_type=str(signal.get("signal_type") or "proactive-loop-lifecycle"),
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
        superseded_count = supersede_runtime_proactive_loop_lifecycle_signals_for_kind(
            loop_kind=str(signal.get("loop_kind") or ""),
            exclude_signal_id=str(persisted_item.get("signal_id") or ""),
            updated_at=now,
            status_reason="Superseded by a newer bounded proactive-loop lifecycle signal for the same loop kind.",
        )
        view = _with_surface_view(persisted_item)
        event_bus.publish(
            "proactive_loop_lifecycle.tracked",
            {
                "signal_id": view.get("signal_id"),
                "loop_kind": view.get("loop_kind"),
                "loop_state": view.get("loop_state"),
                "status": view.get("status"),
                "superseded_count": superseded_count,
                "summary": view.get("loop_summary"),
            },
        )
        persisted.append({**view, "superseded_count": superseded_count})
    return persisted


def _with_surface_view(item: dict[str, object]) -> dict[str, object]:
    support_summary = str(item.get("support_summary") or "")
    loop_state = _find_support_value(support_summary, "loop-state", "loop-emerging")
    loop_kind = _find_support_value(support_summary, "loop-kind", "initiative-loop")
    loop_focus = _find_support_value(support_summary, "loop-focus", "bounded-loop")
    loop_weight = _find_support_value(support_summary, "loop-weight", str(item.get("confidence") or "low"))
    loop_confidence = _find_support_value(support_summary, "loop-confidence", str(item.get("confidence") or "low"))
    question_readiness = _find_support_value(support_summary, "question-readiness", "low")
    closure_readiness = _find_support_value(support_summary, "closure-readiness", "low")
    source_anchor = _find_support_value(support_summary, "source-anchor", "")
    return {
        **item,
        "source": "/mc/runtime.proactive_loop_lifecycle",
        "loop_state": loop_state,
        "loop_kind": loop_kind,
        "loop_focus": loop_focus,
        "loop_weight": loop_weight,
        "loop_summary": str(item.get("summary") or ""),
        "loop_confidence": loop_confidence,
        "question_readiness": question_readiness,
        "closure_readiness": closure_readiness,
        "source_anchor": source_anchor,
        "authority": "non-authoritative",
        "layer_role": "runtime-support",
        "planner_authority_state": "not-planner-authority",
        "proactive_execution_state": "not-proactive-execution",
        "canonical_intention_state": "not-canonical-intention-truth",
        "prompt_inclusion_state": "not-prompt-included",
        "workflow_bridge_state": "not-workflow-bridge",
    }


def _best_loop_focus(
    *,
    latest_loop: dict[str, object],
    attachment: dict[str, object],
    loyalty: dict[str, object],
    relation: dict[str, object],
    meaning: dict[str, object],
) -> str:
    for value in (
        loyalty.get("summary", {}).get("current_focus"),
        attachment.get("summary", {}).get("current_focus"),
        meaning.get("summary", {}).get("current_focus"),
        latest_loop.get("title"),
        relation.get("summary", {}).get("current_signal"),
    ):
        candidate = _normalize_focus_candidate(value)
        if candidate:
            return candidate[:96]
    return "bounded loop"


def _normalize_focus_candidate(value: object) -> str:
    candidate = str(value or "").strip()
    if not candidate:
        return ""
    lowered = candidate.lower()
    if lowered in {"none", "n/a", "null", "bounded loop", "bounded question loop", "current thread"}:
        return ""
    if lowered.startswith("no active"):
        return ""
    for prefix in (
        "Open loop: ",
        "Proactive loop lifecycle: ",
        "Relation continuity: ",
        "Meaning significance: ",
        "Attachment topology: ",
        "Loyalty gradient: ",
    ):
        if candidate.startswith(prefix):
            candidate = candidate[len(prefix):].strip()
            lowered = candidate.lower()
            break
    if not candidate or lowered in {"none", "n/a", "null"}:
        return ""
    return candidate


def _derive_loop_state(
    *,
    loop_kind: str,
    open_status: str,
    question_readiness: str,
    closure_readiness: str,
    witness_persistence: str,
    release_state: str,
) -> str:
    if loop_kind == "closure-loop" and closure_readiness == "high":
        return "loop-closure-worthy"
    if loop_kind == "question-loop" and question_readiness == "high":
        return "loop-question-worthy"
    if open_status == "softening" or release_state in {"release-leaning", "releasing"}:
        return "loop-softening"
    if witness_persistence in {"carried-forward", "persistent"}:
        return "loop-carried"
    return "loop-emerging"


def _loop_summary(
    *,
    loop_kind: str,
    loop_state: str,
    loop_focus: str,
    question_readiness: str,
    closure_readiness: str,
) -> str:
    if loop_kind == "question-loop":
        return (
            f"Bounded proactive-loop lifecycle is carrying {loop_focus.lower()} as a question-capable thread "
            f"with question-readiness {question_readiness}. This is runtime support only, not send permission."
        )
    if loop_kind == "closure-loop":
        return (
            f"Bounded proactive-loop lifecycle is carrying {loop_focus.lower()} as a closure-capable thread "
            f"with closure-readiness {closure_readiness}. This is not closure execution."
        )
    return (
        f"Bounded proactive-loop lifecycle is carrying {loop_focus.lower()} as a small initiative thread in state {loop_state}. "
        "This is descriptive runtime continuity, not proactive execution."
    )


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
    return candidate.strip("-") or "bounded-loop"


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
