from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from core.services.attachment_topology_signal_tracking import (
    build_runtime_attachment_topology_signal_surface,
)
from core.services.chronicle_consolidation_brief_tracking import (
    build_runtime_chronicle_consolidation_brief_surface,
)
from core.services.loyalty_gradient_signal_tracking import (
    build_runtime_loyalty_gradient_signal_surface,
)
from core.services.meaning_significance_signal_tracking import (
    build_runtime_meaning_significance_signal_surface,
)
from core.services.metabolism_state_signal_tracking import (
    build_runtime_metabolism_state_signal_surface,
)
from core.services.open_loop_closure_proposal_tracking import (
    build_runtime_open_loop_closure_proposal_surface,
)
from core.services.open_loop_signal_tracking import (
    build_runtime_open_loop_signal_surface,
)
from core.services.private_initiative_tension_signal_tracking import (
    build_runtime_private_initiative_tension_signal_surface,
)
from core.services.regulation_homeostasis_signal_tracking import (
    build_runtime_regulation_homeostasis_signal_surface,
)
from core.services.release_marker_signal_tracking import (
    build_runtime_release_marker_signal_surface,
)
from core.services.relation_continuity_signal_tracking import (
    build_runtime_relation_continuity_signal_surface,
)
from core.services.runtime_awareness_signal_tracking import (
    build_runtime_awareness_signal_surface,
)
from core.services.witness_signal_tracking import (
    build_runtime_witness_signal_surface,
)
from core.eventbus.bus import event_bus
from core.runtime.db import (
    list_runtime_autonomy_pressure_signals,
    supersede_runtime_autonomy_pressure_signals_for_type,
    update_runtime_autonomy_pressure_signal_status,
    upsert_runtime_autonomy_pressure_signal,
)

_STALE_AFTER_DAYS = 7
_STALE_AFTER_CREATION_DAYS = 14  # Hard cap: stale if created > 14 days ago
_MAX_MERGES_BEFORE_STALE = 30    # Zombie detection: >30 merges = keepalive artifact
_CONFIDENCE_RANKS = {"low": 0, "medium": 1, "high": 2}
_WEIGHT_RANKS = {"low": 0, "medium": 1, "high": 2}


def track_runtime_autonomy_pressure_signals_for_visible_turn(
    *,
    session_id: str | None,
    run_id: str,
) -> dict[str, object]:
    normalized_session_id = str(session_id or "").strip()
    items = _persist_autonomy_pressure_signals(
        signals=_extract_autonomy_pressure_candidates(),
        session_id=normalized_session_id,
        run_id=run_id,
    )
    return {
        "created": len([item for item in items if item.get("was_created")]),
        "updated": len([item for item in items if item.get("was_updated")]),
        "items": items,
        "summary": (
            f"Tracked {len(items)} bounded autonomy-pressure signals."
            if items
            else "No bounded autonomy-pressure signal warranted tracking."
        ),
    }


def refresh_runtime_autonomy_pressure_signal_statuses() -> dict[str, int]:
    """Mark signals as stale based on multiple criteria.

    A signal goes stale if ANY of these are true:
    1. updated_at > 7 days old (original check — but defeated by merge keepalive)
    2. created_at > 14 days old (hard cap — merges can't keep a signal alive forever)
    3. merge_count > 30 (zombie detection — real signals don't need 30+ merges)
    """
    now = datetime.now(UTC)
    refreshed = 0
    for item in list_runtime_autonomy_pressure_signals(limit=40):
        if str(item.get("status") or "") not in {"active", "softening"}:
            continue

        updated_at = _parse_dt(str(item.get("updated_at") or item.get("created_at") or ""))
        created_at = _parse_dt(str(item.get("created_at") or ""))
        merge_count = int(item.get("merge_count") or 0)

        # Check all three stale conditions
        stale_reason = None
        if updated_at is not None and updated_at <= now - timedelta(days=_STALE_AFTER_DAYS):
            stale_reason = "Marked stale after bounded autonomy-pressure inactivity window."
        elif created_at is not None and created_at <= now - timedelta(days=_STALE_AFTER_CREATION_DAYS):
            stale_reason = (
                f"Marked stale: signal created {_STALE_AFTER_CREATION_DAYS}+ days ago "
                f"(created_at={item.get('created_at')}). "
                "Merge keepalive cannot prevent natural retirement."
            )
        elif merge_count > _MAX_MERGES_BEFORE_STALE:
            stale_reason = (
                f"Marked stale: merge_count={merge_count} exceeds threshold "
                f"({_MAX_MERGES_BEFORE_STALE}). Signal is being kept alive "
                "by automatic merges, not genuine new observations."
            )

        if not stale_reason:
            continue

        refreshed_item = update_runtime_autonomy_pressure_signal_status(
            str(item.get("signal_id") or ""),
            status="stale",
            updated_at=now.isoformat(),
            status_reason=stale_reason,
        )
        if refreshed_item is None:
            continue
        refreshed += 1
        event_bus.publish(
            "autonomy_pressure_signal.stale",
            {
                "signal_id": refreshed_item.get("signal_id"),
                "signal_type": refreshed_item.get("signal_type"),
                "status": refreshed_item.get("status"),
                "summary": refreshed_item.get("summary"),
                "status_reason": refreshed_item.get("status_reason"),
            },
        )
    return {"stale_marked": refreshed}


def retire_autonomy_pressure_signal(signal_id: str, *, reason: str = "") -> dict[str, object] | None:
    """Explicitly retire/close an autonomy pressure signal.

    Use when the underlying loop or pressure has been resolved.
    This bridges the gap between MEMORY.md (where loops are marked closed)
    and the signal database (where they otherwise live forever).
    """
    now = datetime.now(UTC).isoformat()
    status_reason = reason or "Explicitly retired — underlying pressure resolved."
    result = update_runtime_autonomy_pressure_signal_status(
        signal_id,
        status="stale",
        updated_at=now,
        status_reason=status_reason,
    )
    if result:
        event_bus.publish(
            "autonomy_pressure_signal.retired",
            {
                "signal_id": signal_id,
                "status": "stale",
                "status_reason": status_reason,
            },
        )
    return result


def build_runtime_autonomy_pressure_signal_surface(*, limit: int = 8) -> dict[str, object]:
    refresh_runtime_autonomy_pressure_signal_statuses()
    items = list_runtime_autonomy_pressure_signals(limit=max(limit, 1))
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
            "current_signal": str((latest or {}).get("title") or "No active autonomy-pressure support"),
            "current_status": str((latest or {}).get("status") or "none"),
            "current_state": str((latest or {}).get("autonomy_pressure_state") or "none"),
            "current_type": str((latest or {}).get("autonomy_pressure_type") or "none"),
            "current_weight": str((latest or {}).get("autonomy_pressure_weight") or "low"),
            "current_confidence": str((latest or {}).get("autonomy_pressure_confidence") or "low"),
            "current_continuity_mode": str((latest or {}).get("autonomy_pressure_continuity_mode") or "none"),
            "authority": "non-authoritative",
            "layer_role": "runtime-support",
            "planner_authority_state": "not-planner-authority",
            "proactive_execution_state": "not-proactive-execution",
            "canonical_intention_state": "not-canonical-intention-truth",
            "prompt_inclusion_state": "not-prompt-included",
            "workflow_bridge_state": "not-workflow-bridge",
        },
    }


def _extract_autonomy_pressure_candidates() -> list[dict[str, object]]:
    initiative = build_runtime_private_initiative_tension_signal_surface(limit=6)
    open_loops = build_runtime_open_loop_signal_surface(limit=6)
    regulation = build_runtime_regulation_homeostasis_signal_surface(limit=6)
    relation = build_runtime_relation_continuity_signal_surface(limit=6)
    meaning = build_runtime_meaning_significance_signal_surface(limit=6)
    witness = build_runtime_witness_signal_surface(limit=6)
    chronicle = build_runtime_chronicle_consolidation_brief_surface(limit=6)
    metabolism = build_runtime_metabolism_state_signal_surface(limit=6)
    release = build_runtime_release_marker_signal_surface(limit=6)
    attachment = build_runtime_attachment_topology_signal_surface(limit=6)
    loyalty = build_runtime_loyalty_gradient_signal_surface(limit=6)
    closure = build_runtime_open_loop_closure_proposal_surface(limit=6)
    awareness = build_runtime_awareness_signal_surface(limit=6)

    candidates: list[dict[str, object]] = []

    initiative_summary = initiative.get("summary") or {}
    open_summary = open_loops.get("summary") or {}
    regulation_summary = regulation.get("summary") or {}
    tension_intensity = str(initiative_summary.get("current_intensity") or "low")
    regulation_pressure = str(regulation_summary.get("current_pressure") or "low")
    initiative_anchor = _source_anchor(initiative, fallback="initiative-tension")
    if (
        int(initiative_summary.get("active_count") or 0) > 0
        and (
            int(open_summary.get("open_count") or 0) > 0
            or regulation_pressure in {"medium", "high"}
        )
    ):
        weight = "high" if tension_intensity == "medium" or int(open_summary.get("open_count") or 0) > 1 else "medium"
        confidence = _stronger_confidence(
            str(initiative_summary.get("current_confidence") or "low"),
            str(regulation_summary.get("current_confidence") or "low"),
        )
        candidates.append(
            _candidate(
                pressure_type="initiative-pressure",
                pressure_state="initiative-held" if weight == "high" else "initiative-rising",
                weight=weight,
                confidence=confidence,
                title="Autonomy pressure: initiative carry",
                summary=(
                    "Bounded autonomy pressure is observing carried initiative around current open loops and regulation pressure. "
                    "This is runtime support only, not planner authority or proactive execution."
                ),
                rationale="Initiative pressure is grounded in private initiative tension plus bounded open-loop or regulation carry.",
                source_anchor=initiative_anchor,
                evidence_summary=_merge_fragments(
                    str(initiative_summary.get("current_signal") or ""),
                    str(open_summary.get("current_signal") or ""),
                    str(regulation_summary.get("current_signal") or ""),
                ),
                support_summary=_merge_fragments(
                    f"autonomy-pressure-state={'initiative-held' if weight == 'high' else 'initiative-rising'}",
                    "autonomy-pressure-type=initiative-pressure",
                    f"autonomy-pressure-weight={weight}",
                    f"autonomy-pressure-confidence={confidence}",
                    f"source-anchor={initiative_anchor}",
                    f"tension-intensity={tension_intensity}",
                ),
                support_count=max(int(initiative_summary.get("active_count") or 0), 1),
                session_count=max(int(open_summary.get("open_count") or 0), 1),
                status_reason="Bounded initiative carry remains visible without execution authority.",
            )
        )

    relation_summary = relation.get("summary") or {}
    meaning_summary = meaning.get("summary") or {}
    witness_summary = witness.get("summary") or {}
    attachment_summary = attachment.get("summary") or {}
    loyalty_summary = loyalty.get("summary") or {}
    relation_weight = str(relation_summary.get("current_weight") or "low")
    meaning_weight = str(meaning_summary.get("current_weight") or "low")
    chronicle_weight = str(chronicle.get("summary", {}).get("current_weight") or "low")
    loyalty_weight = str(loyalty_summary.get("current_weight") or "low")
    attachment_weight = str(attachment_summary.get("current_weight") or "low")
    witness_persistence = str(witness_summary.get("current_persistence_state") or "none")
    continuity = _question_continuity_support(
        relation=relation,
        meaning=meaning,
        witness=witness,
        chronicle=chronicle,
        attachment=attachment,
        loyalty=loyalty,
    )
    loop_continuity = _initiative_loop_question_support(
        open_loops=open_loops,
        initiative=initiative,
        regulation=regulation,
        awareness=awareness,
        witness=witness,
        chronicle=chronicle,
        attachment=attachment,
        loyalty=loyalty,
    )
    if continuity["supported"]:
        weight = (
            "high"
            if (
                meaning_weight == "high"
                or relation_weight == "high"
                or loyalty_weight == "high"
                or attachment_weight == "high"
                or witness_persistence in {"carried-forward", "persistent"}
                or chronicle_weight == "high"
            )
            else "medium"
        )
        confidence = _stronger_confidence(
            str(relation_summary.get("current_confidence") or "low"),
            str(meaning_summary.get("current_confidence") or "low"),
            str(chronicle.get("summary", {}).get("current_confidence") or "low"),
            str(loyalty_summary.get("current_confidence") or "low"),
            str(attachment_summary.get("current_confidence") or "low"),
            str(witness_summary.get("current_witness_confidence") or witness_summary.get("current_confidence") or "low"),
        )
        question_anchor = _merge_fragments(
            _source_anchor(relation, fallback="relation-continuity"),
            _source_anchor(meaning, fallback="meaning-significance"),
            _source_anchor(witness, fallback="witness"),
            _source_anchor(chronicle, fallback="chronicle-brief"),
            _source_anchor(attachment, fallback="attachment-topology"),
            _source_anchor(loyalty, fallback="loyalty-gradient"),
        )
        candidates.append(
            _candidate(
                pressure_type="question-pressure",
                pressure_state="question-worthy" if weight == "high" else "question-emerging",
                weight=weight,
                confidence=confidence,
                title="Autonomy pressure: question carry",
                summary=(
                    "Bounded autonomy pressure is observing question-worthy carry from relation continuity, meaning significance, and carried continuity substrate. "
                    "This is not send permission and not proactive execution."
                ),
                rationale="Question pressure is grounded in existing continuity substrate, where carried witness or chronicle support may legitimately reinforce relation/meaning through attachment or loyalty hold.",
                source_anchor=question_anchor,
                evidence_summary=_merge_fragments(
                    str(relation_summary.get("current_signal") or ""),
                    str(meaning_summary.get("current_signal") or ""),
                    str(witness_summary.get("current_signal") or ""),
                    str(chronicle.get("summary", {}).get("current_brief") or ""),
                    str(attachment_summary.get("current_signal") or ""),
                    str(loyalty_summary.get("current_signal") or ""),
                ),
                support_summary=_merge_fragments(
                    f"autonomy-pressure-state={'question-worthy' if weight == 'high' else 'question-emerging'}",
                    "autonomy-pressure-type=question-pressure",
                    f"autonomy-pressure-weight={weight}",
                    f"autonomy-pressure-confidence={confidence}",
                    f"autonomy-pressure-continuity-mode={continuity['mode']}",
                    f"source-anchor={question_anchor}",
                    f"relation-weight={relation_weight}",
                    f"meaning-weight={meaning_weight}",
                    f"chronicle-weight={chronicle_weight}",
                    f"witness-persistence={witness_persistence}",
                    f"attachment-weight={attachment_weight}",
                    f"loyalty-weight={loyalty_weight}",
                ),
                support_count=max(
                    int(relation_summary.get("active_count") or 0) + int(meaning_summary.get("active_count") or 0),
                    2,
                ),
                session_count=max(
                    int(witness_summary.get("carried_count") or 0),
                    int(attachment_summary.get("active_count") or 0),
                    int(loyalty_summary.get("active_count") or 0),
                    1,
                ),
                status_reason="Bounded question pressure is present, but messaging remains explicitly gated.",
            )
        )
    elif loop_continuity["supported"]:
        weight = str(loop_continuity["weight"] or "medium")
        confidence = _stronger_confidence(
            str(initiative_summary.get("current_confidence") or "low"),
            str(regulation_summary.get("current_confidence") or "low"),
            str(witness_summary.get("current_witness_confidence") or witness_summary.get("current_confidence") or "low"),
            str(chronicle.get("summary", {}).get("current_confidence") or "low"),
            str(attachment_summary.get("current_confidence") or "low"),
            str(loyalty_summary.get("current_confidence") or "low"),
        )
        question_anchor = str(loop_continuity["source_anchor"] or "")
        candidates.append(
            _candidate(
                pressure_type="question-pressure",
                pressure_state="question-worthy" if weight == "high" else "question-emerging",
                weight=weight,
                confidence=confidence,
                title="Autonomy pressure: carried loop question",
                summary=(
                    "Bounded autonomy pressure is observing question-worthy carry from open-loop continuity, initiative carry, regulation support, and situated runtime readiness. "
                    "This is not send permission and not proactive execution."
                ),
                rationale=(
                    "Question pressure may be carried by an already-lived initiative loop when open-loop continuity, initiative tension, regulation support, "
                    "and a usable runtime are concurrently present, even before stricter relation/meaning substrate has materialized."
                ),
                source_anchor=question_anchor,
                evidence_summary=_merge_fragments(
                    str(open_summary.get("current_signal") or ""),
                    str(initiative_summary.get("current_signal") or ""),
                    str(regulation_summary.get("current_signal") or ""),
                    str(awareness.get("summary", {}).get("current_signal") or ""),
                    str(witness_summary.get("current_signal") or ""),
                    str(chronicle.get("summary", {}).get("current_brief") or ""),
                ),
                support_summary=_merge_fragments(
                    f"autonomy-pressure-state={'question-worthy' if weight == 'high' else 'question-emerging'}",
                    "autonomy-pressure-type=question-pressure",
                    f"autonomy-pressure-weight={weight}",
                    f"autonomy-pressure-confidence={confidence}",
                    f"autonomy-pressure-continuity-mode={loop_continuity['mode']}",
                    f"source-anchor={question_anchor}",
                    f"open-loop-count={int(open_summary.get('open_count') or 0)}",
                    f"tension-intensity={tension_intensity}",
                    f"regulation-pressure={regulation_pressure}",
                    f"runtime-awareness-state={loop_continuity['awareness_state']}",
                ),
                support_count=max(
                    int(initiative_summary.get("active_count") or 0),
                    int(open_summary.get("open_count") or 0),
                    2,
                ),
                session_count=max(
                    int(open_summary.get("open_count") or 0),
                    int(attachment_summary.get("active_count") or 0),
                    int(loyalty_summary.get("active_count") or 0),
                    1,
                ),
                status_reason="Bounded question pressure is present through carried initiative-loop continuity, but messaging remains explicitly gated.",
            )
        )

    awareness_summary = awareness.get("summary") or {}
    if int(awareness_summary.get("constrained_count") or 0) > 0:
        awareness_anchor = _source_anchor(awareness, fallback="runtime-awareness")
        confidence = "high"
        weight = "high" if int(awareness_summary.get("constrained_count") or 0) > 1 else "medium"
        candidates.append(
            _candidate(
                pressure_type="anomaly-report-pressure",
                pressure_state="anomaly-held" if weight == "high" else "anomaly-emerging",
                weight=weight,
                confidence=confidence,
                title="Autonomy pressure: anomaly/report carry",
                summary=(
                    "Bounded autonomy pressure is observing a runtime anomaly or constrained machine-state worth keeping reportable. "
                    "This is not automatic reporting execution."
                ),
                rationale="Anomaly/report pressure is grounded in explicit runtime-awareness constraints rather than hidden monitoring logic.",
                source_anchor=awareness_anchor,
                evidence_summary=_merge_fragments(
                    str(awareness_summary.get("current_signal") or ""),
                    str(awareness_summary.get("machine_detail") or ""),
                ),
                support_summary=_merge_fragments(
                    f"autonomy-pressure-state={'anomaly-held' if weight == 'high' else 'anomaly-emerging'}",
                    "autonomy-pressure-type=anomaly-report-pressure",
                    f"autonomy-pressure-weight={weight}",
                    f"autonomy-pressure-confidence={confidence}",
                    f"source-anchor={awareness_anchor}",
                ),
                support_count=max(int(awareness_summary.get("constrained_count") or 0), 1),
                session_count=1,
                status_reason="Runtime-awareness constraints are currently visible and report-worthy, but not self-report execution.",
            )
        )

    closure_summary = closure.get("summary") or {}
    release_summary = release.get("summary") or {}
    chronicle_summary = chronicle.get("summary") or {}
    metabolism_summary = metabolism.get("summary") or {}
    closure_count = (
        int(closure_summary.get("fresh_count") or 0)
        + int(closure_summary.get("active_count") or 0)
        + int(closure_summary.get("fading_count") or 0)
    )
    if closure_count > 0 or (
        int(open_summary.get("softening_count") or 0) > 0
        and str(release_summary.get("current_state") or "none") in {"release-ready", "release-leaning"}
    ):
        weight = "high" if closure_count > 0 else "medium"
        confidence = _stronger_confidence(
            str(closure_summary.get("current_closure_confidence") or "low"),
            str(release_summary.get("current_confidence") or "low"),
            str(chronicle_summary.get("current_confidence") or "low"),
            str(metabolism_summary.get("current_confidence") or "low"),
        )
        closure_anchor = _merge_fragments(
            _source_anchor(closure, fallback="open-loop-closure-proposal"),
            _source_anchor(release, fallback="release-marker"),
            _source_anchor(chronicle, fallback="chronicle-brief"),
        )
        candidates.append(
            _candidate(
                pressure_type="closure-pressure",
                pressure_state="closure-ready" if weight == "high" else "closure-emerging",
                weight=weight,
                confidence=confidence,
                title="Autonomy pressure: loop closure carry",
                summary=(
                    "Bounded autonomy pressure is observing closure-ready loop carry. "
                    "This remains governance-facing runtime support, not workflow/apply execution."
                ),
                rationale="Closure pressure is grounded in existing open-loop closure proposals, softening loops, and release-aware support.",
                source_anchor=closure_anchor,
                evidence_summary=_merge_fragments(
                    str(closure_summary.get("current_proposal") or ""),
                    str(release_summary.get("current_signal") or ""),
                    str(open_summary.get("current_signal") or ""),
                ),
                support_summary=_merge_fragments(
                    f"autonomy-pressure-state={'closure-ready' if weight == 'high' else 'closure-emerging'}",
                    "autonomy-pressure-type=closure-pressure",
                    f"autonomy-pressure-weight={weight}",
                    f"autonomy-pressure-confidence={confidence}",
                    f"source-anchor={closure_anchor}",
                ),
                support_count=max(closure_count, 1),
                session_count=max(int(open_summary.get("softening_count") or 0), 1),
                status_reason="Closure pressure is present, but closure still requires governed proposal handling.",
            )
        )

    candidates.sort(
        key=lambda item: (
            _WEIGHT_RANKS.get(str(item.get("autonomy_pressure_weight") or "low"), 0),
            _CONFIDENCE_RANKS.get(str(item.get("autonomy_pressure_confidence") or "low"), 0),
        ),
        reverse=True,
    )
    return candidates[:4]


def _persist_autonomy_pressure_signals(
    *,
    signals: list[dict[str, object]],
    session_id: str,
    run_id: str,
) -> list[dict[str, object]]:
    now = datetime.now(UTC).isoformat()
    existing_by_key = {
        str(item.get("canonical_key") or ""): item for item in list_runtime_autonomy_pressure_signals(limit=40)
    }
    persisted: list[dict[str, object]] = []
    for signal in signals:
        existing = existing_by_key.get(str(signal.get("canonical_key") or ""))
        persisted_item = upsert_runtime_autonomy_pressure_signal(
            signal_id=f"autonomy-pressure-signal-{uuid4().hex}",
            signal_type=str(signal.get("signal_type") or "autonomy-pressure"),
            canonical_key=str(signal.get("canonical_key") or ""),
            status="active" if existing and str(signal.get("status") or "") == "active" else str(signal.get("status") or "active"),
            title=str(signal.get("title") or ""),
            summary=str(signal.get("summary") or ""),
            rationale=str(signal.get("rationale") or ""),
            source_kind=str(signal.get("source_kind") or "runtime-derived-support"),
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
        superseded_count = supersede_runtime_autonomy_pressure_signals_for_type(
            pressure_type=str(signal.get("pressure_type") or ""),
            exclude_signal_id=str(persisted_item.get("signal_id") or ""),
            updated_at=now,
            status_reason="Superseded by a newer bounded autonomy-pressure signal for the same pressure type.",
        )
        persisted_item["superseded_count"] = superseded_count
        persisted.append(persisted_item)
        if persisted_item.get("was_created"):
            event_bus.publish(
                "autonomy_pressure_signal.created",
                {
                    "signal_id": persisted_item.get("signal_id"),
                    "signal_type": persisted_item.get("signal_type"),
                    "status": persisted_item.get("status"),
                    "summary": persisted_item.get("summary"),
                },
            )
        elif persisted_item.get("was_updated"):
            event_bus.publish(
                "autonomy_pressure_signal.updated",
                {
                    "signal_id": persisted_item.get("signal_id"),
                    "signal_type": persisted_item.get("signal_type"),
                    "status": persisted_item.get("status"),
                    "summary": persisted_item.get("summary"),
                },
            )
    return persisted


def _with_surface_view(item: dict[str, object]) -> dict[str, object]:
    support_summary = str(item.get("support_summary") or "")
    enriched = dict(item)
    enriched["autonomy_pressure_state"] = _find_support_value(
        support_summary, "autonomy-pressure-state", "autonomy-emerging"
    )
    enriched["autonomy_pressure_type"] = _find_support_value(
        support_summary, "autonomy-pressure-type", str(item.get("signal_type") or "autonomy-pressure")
    )
    enriched["autonomy_pressure_weight"] = _find_support_value(
        support_summary, "autonomy-pressure-weight", "low"
    )
    enriched["autonomy_pressure_confidence"] = _find_support_value(
        support_summary, "autonomy-pressure-confidence", str(item.get("confidence") or "low")
    )
    enriched["source_anchor"] = _find_support_value(
        support_summary, "source-anchor", str(item.get("title") or "autonomy-pressure")
    )
    enriched["autonomy_pressure_summary"] = str(item.get("summary") or "")
    enriched["autonomy_pressure_continuity_mode"] = _find_support_value(
        support_summary, "autonomy-pressure-continuity-mode", "relation-meaning-held"
    )
    enriched["authority"] = "non-authoritative"
    enriched["layer_role"] = "runtime-support"
    enriched["planner_authority_state"] = "not-planner-authority"
    enriched["proactive_execution_state"] = "not-proactive-execution"
    enriched["canonical_intention_state"] = "not-canonical-intention-truth"
    enriched["prompt_inclusion_state"] = "not-prompt-included"
    enriched["workflow_bridge_state"] = "not-workflow-bridge"
    return enriched


def _candidate(
    *,
    pressure_type: str,
    pressure_state: str,
    weight: str,
    confidence: str,
    title: str,
    summary: str,
    rationale: str,
    source_anchor: str,
    evidence_summary: str,
    support_summary: str,
    support_count: int,
    session_count: int,
    status_reason: str,
) -> dict[str, object]:
    return {
        "signal_type": pressure_type,
        "pressure_type": pressure_type,
        "canonical_key": f"autonomy-pressure:{pressure_type}",
        "status": "active",
        "title": title,
        "summary": summary,
        "rationale": rationale,
        "source_kind": "runtime-derived-support",
        "confidence": confidence,
        "evidence_summary": evidence_summary,
        "support_summary": support_summary,
        "support_count": max(int(support_count or 0), 1),
        "session_count": max(int(session_count or 0), 1),
        "status_reason": status_reason,
        "autonomy_pressure_state": pressure_state,
        "autonomy_pressure_type": pressure_type,
        "autonomy_pressure_weight": weight,
        "autonomy_pressure_confidence": confidence,
        "source_anchor": source_anchor,
    }


def _source_anchor(surface: dict[str, object], *, fallback: str) -> str:
    items = surface.get("items") or []
    if items:
        item = items[0] or {}
        return str(item.get("source_anchor") or item.get("title") or fallback)
    summary = surface.get("summary") or {}
    return str(summary.get("current_signal") or fallback)


def _question_continuity_support(
    *,
    relation: dict[str, object],
    meaning: dict[str, object],
    witness: dict[str, object],
    chronicle: dict[str, object],
    attachment: dict[str, object],
    loyalty: dict[str, object],
) -> dict[str, object]:
    witness_summary = witness.get("summary") or {}
    chronicle_summary = chronicle.get("summary") or {}
    attachment_summary = attachment.get("summary") or {}
    loyalty_summary = loyalty.get("summary") or {}

    witness_carried = (
        int(witness_summary.get("carried_count") or 0) > 0
        or str(witness_summary.get("current_persistence_state") or "none")
        in {"recurring", "stabilizing-over-time", "carried-forward", "persistent"}
    )
    chronicle_carried = bool(chronicle.get("active")) and str(
        chronicle_summary.get("current_weight") or "low"
    ) in {"medium", "high"}
    attachment_held = bool(attachment.get("active")) and str(
        attachment_summary.get("current_weight") or "low"
    ) in {"medium", "high"}
    loyalty_held = bool(loyalty.get("active")) and str(
        loyalty_summary.get("current_weight") or "low"
    ) in {"medium", "high"}

    same_moment = bool(relation.get("active")) and bool(meaning.get("active"))
    carried_bonded = (witness_carried or chronicle_carried) and (attachment_held or loyalty_held)

    if same_moment and carried_bonded:
        return {"supported": True, "mode": "hybrid-continuity"}
    if same_moment:
        return {"supported": True, "mode": "relation-meaning-held"}
    if carried_bonded:
        return {"supported": True, "mode": "carried-bonded-continuity"}
    return {"supported": False, "mode": "insufficient-continuity"}


def _initiative_loop_question_support(
    *,
    open_loops: dict[str, object],
    initiative: dict[str, object],
    regulation: dict[str, object],
    awareness: dict[str, object],
    witness: dict[str, object],
    chronicle: dict[str, object],
    attachment: dict[str, object],
    loyalty: dict[str, object],
) -> dict[str, object]:
    open_summary = open_loops.get("summary") or {}
    initiative_summary = initiative.get("summary") or {}
    awareness_summary = awareness.get("summary") or {}
    witness_summary = witness.get("summary") or {}
    chronicle_summary = chronicle.get("summary") or {}
    attachment_summary = attachment.get("summary") or {}
    loyalty_summary = loyalty.get("summary") or {}

    open_count = int(open_summary.get("open_count") or 0)
    initiative_active = int(initiative_summary.get("active_count") or 0) > 0
    initiative_intensity = str(initiative_summary.get("current_intensity") or "low")
    regulation_active = bool(regulation.get("active"))
    awareness_constrained = int(awareness_summary.get("constrained_count") or 0) > 0
    awareness_ready = int(awareness_summary.get("active_count") or 0) > 0 and not awareness_constrained

    # Core requirement: initiative tension must be active.
    # Then we need open loops + at least one of regulation/awareness.
    # Previously all four were required; now we accept 3-of-4 alignment
    # when initiative intensity is at least medium.
    has_runtime_support = regulation_active or awareness_ready
    has_strong_initiative = initiative_active and initiative_intensity in {"medium", "high"}
    if not initiative_active or (open_count <= 0 and not has_strong_initiative):
        return {
            "supported": False,
            "mode": "insufficient-continuity",
            "weight": "low",
            "source_anchor": "",
            "awareness_state": "not-ready",
        }
    if open_count <= 0 and not has_runtime_support:
        return {
            "supported": False,
            "mode": "insufficient-continuity",
            "weight": "low",
            "source_anchor": "",
            "awareness_state": "not-ready",
        }
    if open_count > 0 and not has_runtime_support and not has_strong_initiative:
        return {
            "supported": False,
            "mode": "insufficient-continuity",
            "weight": "low",
            "source_anchor": "",
            "awareness_state": "not-ready",
        }

    witness_carried = (
        int(witness_summary.get("carried_count") or 0) > 0
        or str(witness_summary.get("current_persistence_state") or "none")
        in {"recurring", "stabilizing-over-time", "carried-forward", "persistent"}
    )
    chronicle_carried = bool(chronicle.get("active")) and str(
        chronicle_summary.get("current_weight") or "low"
    ) in {"medium", "high"}
    attachment_held = bool(attachment.get("active")) and str(
        attachment_summary.get("current_weight") or "low"
    ) in {"medium", "high"}
    loyalty_held = bool(loyalty.get("active")) and str(
        loyalty_summary.get("current_weight") or "low"
    ) in {"medium", "high"}

    weight = "high" if (witness_carried or chronicle_carried or attachment_held or loyalty_held or open_count > 1 or initiative_intensity == "high") else "medium"
    effective_awareness = "ready" if awareness_ready else ("regulated" if regulation_active else "tension-driven")
    return {
        "supported": True,
        "mode": "initiative-loop-continuity",
        "weight": weight,
        "source_anchor": _merge_fragments(
            _source_anchor(open_loops, fallback="open-loop"),
            _source_anchor(initiative, fallback="initiative-tension"),
            _source_anchor(regulation, fallback="regulation-homeostasis"),
            _source_anchor(awareness, fallback="runtime-awareness"),
            _source_anchor(witness, fallback="witness"),
            _source_anchor(chronicle, fallback="chronicle-brief"),
            _source_anchor(attachment, fallback="attachment-topology"),
            _source_anchor(loyalty, fallback="loyalty-gradient"),
        ),
        "awareness_state": effective_awareness,
    }


def _stronger_confidence(*values: str) -> str:
    strongest = "low"
    for value in values:
        candidate = str(value or "low")
        if _CONFIDENCE_RANKS.get(candidate, 0) > _CONFIDENCE_RANKS.get(strongest, 0):
            strongest = candidate
    return strongest


def _find_support_value(support_summary: str, key: str, default: str) -> str:
    for segment in str(support_summary or "").split("|"):
        left, _, right = segment.partition("=")
        if left.strip() == key and right.strip():
            return right.strip()
    return default


def _merge_fragments(*parts: object) -> str:
    values = [str(part or "").strip() for part in parts if str(part or "").strip()]
    deduped: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        deduped.append(value)
    return " | ".join(deduped)


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
