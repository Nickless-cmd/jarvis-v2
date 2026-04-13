"""Session distillation and private brain continuity.

Responsibilities:
1. distill_session_carry — classifies end-of-run carry into
   private_brain / workspace_memory / discard.
2. Anti-spam consolidation — suppresses near-duplicate brain records.
3. build_private_brain_context — bounded read of recent brain records
   for heartbeat / continuity ingestion.
4. run_private_brain_continuity — lightweight continuity pass that
   can run from heartbeat without visible chat.

Design constraints:
- Private brain records are append-only and Jarvis-owned.
- Workspace memory candidates flow through the existing contract-candidate
  pipeline (approve → apply → write to MEMORY.md).
- Discard items are logged for observability but not persisted beyond the
  distillation record itself.
- No canonical identity mutation.
- No external action.
"""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.runtime.db import (
    insert_private_brain_record,
    insert_session_distillation_record,
    list_private_brain_records,
    list_session_distillation_records,
    update_private_brain_record_status,
)

# ---------------------------------------------------------------------------
# Surface builders used for distillation evidence
# ---------------------------------------------------------------------------

from apps.api.jarvis_api.services.private_inner_note_signal_tracking import (
    build_runtime_private_inner_note_signal_surface,
)
from apps.api.jarvis_api.services.private_state_snapshot_tracking import (
    build_runtime_private_state_snapshot_surface,
)
from apps.api.jarvis_api.services.self_model_signal_tracking import (
    build_runtime_self_model_signal_surface,
)
from apps.api.jarvis_api.services.diary_synthesis_signal_tracking import (
    build_diary_synthesis_signal_surface,
)
from apps.api.jarvis_api.services.development_focus_tracking import (
    build_runtime_development_focus_surface,
)
from apps.api.jarvis_api.services.open_loop_signal_tracking import (
    build_runtime_open_loop_signal_surface,
)
from apps.api.jarvis_api.services.world_model_signal_tracking import (
    build_runtime_world_model_signal_surface,
)
from apps.api.jarvis_api.services.remembered_fact_signal_tracking import (
    build_runtime_remembered_fact_signal_surface,
)
from apps.api.jarvis_api.services.goal_signal_tracking import (
    build_runtime_goal_signal_surface,
)


# ---------------------------------------------------------------------------
# Anti-spam / consolidation constants
# ---------------------------------------------------------------------------

_DUPLICATE_SUMMARY_WINDOW = 12  # check last N brain records for duplicates
_SUMMARY_SIMILARITY_MIN_WORDS = 4  # summaries shorter than this always pass


# ---------------------------------------------------------------------------
# Anti-spam guard
# ---------------------------------------------------------------------------


def _is_near_duplicate(
    summary: str,
    record_type: str,
    recent_records: list[dict[str, object]],
) -> bool:
    """Return True if a record with very similar summary + same type exists
    in recent_records.  Uses simple word-set overlap (Jaccard-like)."""
    summary_normalized = " ".join(summary.lower().split())
    if len(summary_normalized.split()) < _SUMMARY_SIMILARITY_MIN_WORDS:
        return False  # too short to judge — allow through

    summary_words = set(summary_normalized.split())
    for existing in recent_records:
        if str(existing.get("record_type", "")) != record_type:
            continue
        existing_summary = " ".join(
            str(existing.get("summary") or "").lower().split()
        )
        existing_words = set(existing_summary.split())
        if not existing_words:
            continue
        # Jaccard similarity > 0.7 → near duplicate
        intersection = summary_words & existing_words
        union = summary_words | existing_words
        if union and (len(intersection) / len(union)) > 0.7:
            return True
    return False


def _try_insert_guarded(
    *,
    record_type: str,
    layer: str,
    session_id: str,
    run_id: str,
    focus: str,
    summary: str,
    detail: str,
    source_signals: str,
    confidence: str,
    now: str,
    recent_records: list[dict[str, object]],
) -> dict[str, object] | None:
    """Insert a private brain record if it passes anti-spam guard.
    Returns the record or None if suppressed."""
    if _is_near_duplicate(summary, record_type, recent_records):
        return None
    record = insert_private_brain_record(
        record_id=f"pb-{record_type[:8]}-{uuid4().hex[:12]}",
        record_type=record_type,
        layer=layer,
        session_id=session_id,
        run_id=run_id,
        focus=focus,
        summary=summary,
        detail=detail,
        source_signals=source_signals,
        confidence=confidence,
        created_at=now,
    )
    return record if record else None


# ---------------------------------------------------------------------------
# Main distillation entry point
# ---------------------------------------------------------------------------


def distill_session_carry(
    *,
    session_id: str,
    run_id: str,
) -> dict[str, object]:
    """Classify runtime evidence into private-brain / workspace-memory / discard.

    Called at the end of a visible run.  Returns a summary of what was carried.
    """
    now = datetime.now(UTC).isoformat()

    # Load recent brain records for anti-spam guard
    recent_records = list_private_brain_records(limit=_DUPLICATE_SUMMARY_WINDOW)

    # Gather evidence from current runtime surfaces
    inner_notes = build_runtime_private_inner_note_signal_surface(limit=6)
    state_snapshots = build_runtime_private_state_snapshot_surface(limit=4)
    self_model = build_runtime_self_model_signal_surface(limit=4)
    diary = build_diary_synthesis_signal_surface(limit=4)
    focus = build_runtime_development_focus_surface(limit=4)
    facts = build_runtime_remembered_fact_signal_surface(limit=6)
    goals = build_runtime_goal_signal_surface(limit=4)

    private_items: list[dict[str, object]] = []
    workspace_items: list[dict[str, object]] = []
    discard_reasons: list[str] = []
    suppressed_count = 0

    def _try_private(
        *, record_type: str, item: dict[str, object],
        summary: str, detail: str, source_signals: str,
    ) -> None:
        nonlocal suppressed_count
        record = _try_insert_guarded(
            record_type=record_type,
            layer="private_brain",
            session_id=session_id,
            run_id=run_id,
            focus=str(item.get("title") or ""),
            summary=summary,
            detail=detail,
            source_signals=source_signals,
            confidence=str(item.get("confidence") or "medium"),
            now=now,
            recent_records=recent_records,
        )
        if record:
            private_items.append(record)
            # Add to recent_records so subsequent items in this run are checked too
            recent_records.insert(0, record)
        else:
            suppressed_count += 1
            discard_reasons.append(
                f"near-duplicate-suppressed:{record_type}:{item.get('signal_id') or item.get('snapshot_id') or 'unknown'}"
            )

    # --- Private brain carry ---
    for item in inner_notes.get("items", []):
        summary = str(item.get("summary") or "").strip()
        if not summary or str(item.get("status") or "") not in {"active", "softening"}:
            discard_reasons.append(f"inner-note-inactive:{item.get('signal_id', 'unknown')}")
            continue
        _try_private(
            record_type="inner-note-carry", item=item,
            summary=summary,
            detail=str(item.get("rationale") or ""),
            source_signals=f"inner-note:{item.get('signal_id', '')}",
        )

    for item in self_model.get("items", []):
        summary = str(item.get("summary") or "").strip()
        if not summary or str(item.get("status") or "") not in {"active", "softening"}:
            discard_reasons.append(f"self-model-inactive:{item.get('signal_id', 'unknown')}")
            continue
        _try_private(
            record_type="self-model-carry", item=item,
            summary=summary,
            detail=str(item.get("evidence_summary") or ""),
            source_signals=f"self-model:{item.get('signal_id', '')}",
        )

    for item in diary.get("items", []):
        summary = str(item.get("summary") or "").strip()
        if not summary or str(item.get("status") or "") not in {"active", "softening"}:
            discard_reasons.append(f"diary-inactive:{item.get('signal_id', 'unknown')}")
            continue
        _try_private(
            record_type="diary-carry", item=item,
            summary=summary,
            detail=str(item.get("rationale") or ""),
            source_signals=f"diary:{item.get('signal_id', '')}",
        )

    for item in state_snapshots.get("items", []):
        summary = str(item.get("summary") or "").strip()
        if not summary or str(item.get("status") or "") not in {"active", "softening"}:
            discard_reasons.append(f"snapshot-inactive:{item.get('snapshot_id', 'unknown')}")
            continue
        _try_private(
            record_type="state-snapshot-carry", item=item,
            summary=summary,
            detail=str(item.get("evidence_summary") or ""),
            source_signals=f"state-snapshot:{item.get('snapshot_id', '')}",
        )

    # --- Workspace memory carry ---
    for item in facts.get("items", []):
        summary = str(item.get("summary") or "").strip()
        if not summary or str(item.get("status") or "") not in {"active", "softening"}:
            discard_reasons.append(f"fact-inactive:{item.get('signal_id', 'unknown')}")
            continue
        workspace_items.append({
            "type": "remembered-fact",
            "summary": summary,
            "signal_id": item.get("signal_id"),
            "note": "Already tracked via candidate pipeline for MEMORY.md promotion.",
        })

    for item in focus.get("items", []):
        summary = str(item.get("summary") or "").strip()
        if not summary or str(item.get("status") or "") not in {"active", "softening"}:
            continue
        workspace_items.append({
            "type": "development-focus",
            "summary": summary,
            "signal_id": item.get("focus_id"),
            "note": "Development focus is workspace-relevant context.",
        })

    for item in goals.get("items", []):
        summary = str(item.get("summary") or "").strip()
        if not summary or str(item.get("status") or "") not in {"active", "softening"}:
            continue
        workspace_items.append({
            "type": "goal-signal",
            "summary": summary,
            "signal_id": item.get("goal_id"),
            "note": "Goal is workspace-relevant context.",
        })

    # --- Build distillation record ---
    distillation_id = f"distill-{uuid4().hex[:12]}"

    distill_summary = (
        f"Session distillation: {len(private_items)} private brain, "
        f"{len(workspace_items)} workspace memory, "
        f"{len(discard_reasons)} discarded"
        f"{f', {suppressed_count} near-duplicate suppressed' if suppressed_count else ''}."
    )

    distillation = insert_session_distillation_record(
        distillation_id=distillation_id,
        session_id=session_id,
        run_id=run_id,
        private_brain_count=len(private_items),
        workspace_memory_count=len(workspace_items),
        discard_count=len(discard_reasons),
        summary=distill_summary,
        detail=" | ".join(discard_reasons[:5]) if discard_reasons else "",
        created_at=now,
    )

    # Publish events for observability
    if private_items:
        event_bus.publish(
            "private_brain.records_created",
            {
                "distillation_id": distillation_id,
                "session_id": session_id,
                "run_id": run_id,
                "count": len(private_items),
                "suppressed": suppressed_count,
                "types": list({str(r.get("record_type", "")) for r in private_items}),
                "summary": f"{len(private_items)} private brain records created, {suppressed_count} suppressed.",
            },
        )

    event_bus.publish(
        "session_distillation.completed",
        {
            "distillation_id": distillation_id,
            "session_id": session_id,
            "run_id": run_id,
            "private_brain_count": len(private_items),
            "workspace_memory_count": len(workspace_items),
            "discard_count": len(discard_reasons),
            "suppressed_count": suppressed_count,
            "summary": distill_summary,
        },
    )

    # --- Cognitive architecture: session-level analysis ---
    _analyze_session_for_cognitive_systems(
        session_id=session_id,
        run_id=run_id,
    )

    return {
        "distillation_id": distillation_id,
        "private_brain_count": len(private_items),
        "workspace_memory_count": len(workspace_items),
        "discard_count": len(discard_reasons),
        "suppressed_count": suppressed_count,
        "private_items": private_items,
        "workspace_items": workspace_items,
        "distillation": distillation,
        "summary": distill_summary,
    }


def _analyze_session_for_cognitive_systems(
    *,
    session_id: str,
    run_id: str,
) -> None:
    """Analyze a completed session for cognitive accumulation systems.

    Fires as part of distill_session_carry — runs the user-facing
    dimension of session analysis (mood, rhythm, relationship, seeds).
    """
    import contextlib

    # 1. Classify conversation rhythm for this session
    with contextlib.suppress(Exception):
        from apps.api.jarvis_api.services.conversation_rhythm import track_conversation_rhythm
        from core.runtime.db import (
            get_latest_cognitive_user_emotional_state,
            list_cognitive_user_emotional_states,
        )
        recent_moods = list_cognitive_user_emotional_states(limit=10)
        correction_count = sum(
            1 for m in recent_moods
            if m.get("detected_mood") in ("frustrated", "impatient")
        )
        track_conversation_rhythm(
            run_id=run_id,
            session_id=session_id,
            correction_count=correction_count,
            outcome_status="completed",
        )

    # 2. Create session-level experiential memory
    with contextlib.suppress(Exception):
        from apps.api.jarvis_api.services.experiential_memory import (
            create_experiential_memory_from_run,
        )
        from core.runtime.db import get_latest_cognitive_user_emotional_state
        mood_state = get_latest_cognitive_user_emotional_state()
        user_mood = str(mood_state.get("detected_mood", "neutral")) if mood_state else "neutral"
        create_experiential_memory_from_run(
            run_id=run_id,
            session_id=session_id,
            user_message=f"Session distillation for {session_id}",
            assistant_response="Session completed",
            outcome_status="completed",
            user_mood=user_mood,
        )

    # 3. Update relationship texture with session metrics
    with contextlib.suppress(Exception):
        from apps.api.jarvis_api.services.relationship_texture import (
            update_relationship_from_run,
        )
        update_relationship_from_run(
            run_id=run_id,
            user_message="session end",
            assistant_response="",
            outcome_status="completed",
        )


# ---------------------------------------------------------------------------
# Private brain context for heartbeat / continuity ingestion
# ---------------------------------------------------------------------------

_BRAIN_CONTEXT_LIMIT = 6
_BRAIN_CONTEXT_MAX_CHARS_PER_RECORD = 200


def build_private_brain_context(*, limit: int = _BRAIN_CONTEXT_LIMIT) -> dict[str, object]:
    """Build a bounded read of recent private brain records suitable for
    heartbeat context or continuity ingestion.

    Returns a compact summary + selected record excerpts, bounded by
    count and character limits to avoid prompt bloat.
    """
    records = list_private_brain_records(limit=limit, status="active")

    if not records:
        return {
            "active": False,
            "record_count": 0,
            "excerpts": [],
            "continuity_summary": "No private brain records to carry.",
        }

    excerpts = []
    types_seen: dict[str, int] = {}
    for record in records:
        record_type = str(record.get("record_type") or "unknown")
        types_seen[record_type] = types_seen.get(record_type, 0) + 1
        summary = str(record.get("summary") or "")
        if len(summary) > _BRAIN_CONTEXT_MAX_CHARS_PER_RECORD:
            summary = summary[:_BRAIN_CONTEXT_MAX_CHARS_PER_RECORD] + "…"
        excerpts.append({
            "type": record_type,
            "focus": str(record.get("focus") or ""),
            "summary": summary,
            "confidence": str(record.get("confidence") or "medium"),
        })

    # Build a readable one-line continuity summary
    type_parts = [f"{count} {t}" for t, count in types_seen.items()]
    continuity_summary = (
        f"Private brain carries {len(records)} active records "
        f"({', '.join(type_parts)}). "
        f"Latest: {excerpts[0]['summary'][:80]}"
    )

    return {
        "active": True,
        "record_count": len(records),
        "excerpts": excerpts,
        "continuity_summary": continuity_summary,
        "by_type": types_seen,
    }


# ---------------------------------------------------------------------------
# Continuity mode classification
# ---------------------------------------------------------------------------

# Modes for the continuity motor:
# - reinforce: multiple records of the same thread → strengthen carry
# - carry: diverse threads all active → maintain breadth
# - settle: older records dominating → time to let threads rest
# - release: mostly consolidation records → brain is already settled

_CONSOLIDATION_TYPES = {"continuity-reinforce", "continuity-carry", "continuity-settle", "continuity-release", "continuity-consolidation"}


def _classify_continuity_mode(
    excerpts: list[dict[str, object]],
    by_type: dict[str, int],
) -> dict[str, str]:
    """Classify the semantic intention of a continuity pass.

    Returns a dict with 'mode' and 'reason' keys.
    """
    type_count = len(by_type)
    total = sum(by_type.values())

    # Count how many are consolidation-type records (already settled)
    consolidation_count = sum(
        count for t, count in by_type.items()
        if t in _CONSOLIDATION_TYPES
    )

    if consolidation_count > total / 2:
        return {
            "mode": "release",
            "reason": "Brain is mostly consolidation records — inner threads are settling",
        }

    # Check for focus concentration (same focus appearing in multiple excerpts)
    focuses = [str(e.get("focus") or "").lower().strip() for e in excerpts if e.get("focus")]
    focus_set = set(focuses)
    if len(focuses) >= 3 and len(focus_set) <= 2:
        return {
            "mode": "reinforce",
            "reason": f"Inner threads are concentrating around {len(focus_set)} focal point(s)",
        }

    if type_count >= 3:
        return {
            "mode": "carry",
            "reason": f"Diverse inner threads ({type_count} types) are all still active",
        }

    if type_count >= 2 and total >= 3:
        return {
            "mode": "settle",
            "reason": "Mixed inner threads are stabilizing with moderate activity",
        }

    return {
        "mode": "carry",
        "reason": "Inner continuity is being maintained across active threads",
    }


# ---------------------------------------------------------------------------
# Private brain continuity motor
# ---------------------------------------------------------------------------


def run_private_brain_continuity(
    *,
    trigger: str = "heartbeat",
) -> dict[str, object]:
    """Lightweight continuity pass for the private brain.

    Reads recent brain records + current runtime signals and decides whether
    a new consolidation record is warranted.  Produces at most ONE new record
    per invocation.  All decisions are observable.

    This can run from heartbeat without visible chat.
    """
    now = datetime.now(UTC).isoformat()
    brain_context = build_private_brain_context()

    if not brain_context["active"]:
        event_bus.publish(
            "private_brain.continuity_skipped",
            {
                "trigger": trigger,
                "reason": "no-active-brain-records",
                "summary": "No private brain records to consolidate.",
            },
        )
        return {
            "action": "skipped",
            "reason": "no-active-brain-records",
            "trigger": trigger,
            "brain_record_count": 0,
        }

    excerpts = brain_context.get("excerpts") or []
    by_type = brain_context.get("by_type") or {}

    # Decision: can we produce a useful consolidation?
    # Require at least 2 records of different types, or 3+ of same type
    total = brain_context["record_count"]
    type_count = len(by_type)
    should_consolidate = (type_count >= 2 and total >= 2) or total >= 3

    if not should_consolidate:
        event_bus.publish(
            "private_brain.continuity_skipped",
            {
                "trigger": trigger,
                "reason": "insufficient-diversity",
                "record_count": total,
                "type_count": type_count,
                "summary": f"Not enough diversity for consolidation ({total} records, {type_count} types).",
            },
        )
        return {
            "action": "skipped",
            "reason": "insufficient-diversity",
            "trigger": trigger,
            "brain_record_count": total,
        }

    # Classify continuity intention semantically
    continuity_mode = _classify_continuity_mode(excerpts, by_type)

    # Build a consolidation summary from excerpts
    focus_parts = [e["focus"] for e in excerpts[:3] if e.get("focus")]
    summary_parts = [e["summary"] for e in excerpts[:3] if e.get("summary")]
    consolidated_focus = " + ".join(focus_parts[:3]) if focus_parts else "private continuity"

    mode_label = continuity_mode["mode"]
    mode_reason = continuity_mode["reason"]
    consolidated_summary = (
        f"[{mode_label}] {mode_reason}. "
        f"Across {total} records ({type_count} types): "
        f"{'; '.join(s[:50] for s in summary_parts[:3])}"
    )

    # Anti-spam: check if we already have a very similar consolidation
    recent_records = list_private_brain_records(limit=_DUPLICATE_SUMMARY_WINDOW)
    if _is_near_duplicate(consolidated_summary, f"continuity-{mode_label}", recent_records):
        event_bus.publish(
            "private_brain.continuity_skipped",
            {
                "trigger": trigger,
                "reason": "near-duplicate-consolidation",
                "record_count": total,
                "summary": "Consolidation would be near-duplicate of existing record.",
            },
        )
        return {
            "action": "skipped",
            "reason": "near-duplicate-consolidation",
            "trigger": trigger,
            "brain_record_count": total,
        }

    # Create the consolidation record
    record = insert_private_brain_record(
        record_id=f"pb-{mode_label[:8]}-{uuid4().hex[:12]}",
        record_type=f"continuity-{mode_label}",
        layer="private_brain",
        session_id="heartbeat",  # continuity motor runs between sessions
        run_id="",
        focus=consolidated_focus[:200],
        summary=consolidated_summary[:400],
        detail=brain_context.get("continuity_summary", "")[:400],
        source_signals=f"continuity-motor:{trigger}",
        confidence="medium",
        created_at=now,
    )

    event_bus.publish(
        "private_brain.continuity_completed",
        {
            "trigger": trigger,
            "record_id": record.get("record_id", ""),
            "continuity_mode": mode_label,
            "continuity_reason": mode_reason,
            "record_count_input": total,
            "type_count_input": type_count,
            "summary": consolidated_summary[:200],
        },
    )

    # Run lifecycle pass after consolidation
    lifecycle = run_private_brain_lifecycle()

    return {
        "action": "consolidated",
        "continuity_mode": mode_label,
        "continuity_reason": mode_reason,
        "trigger": trigger,
        "brain_record_count": total,
        "record": record,
        "summary": consolidated_summary,
        "lifecycle": lifecycle,
    }


# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Private brain lifecycle
# ---------------------------------------------------------------------------

# Lifecycle: active → settling → fading → released
# Transition rules:
# - Records older than _SETTLE_AFTER_RUNS continuity motor invocations → settling
# - settling records older than _FADE_AFTER_RUNS → fading
# - fading records → released (soft-expired, kept in DB)
# - consolidation records (continuity-*) settle faster

_SETTLE_THRESHOLD = 6   # records seen N+ times by continuity → settling
_FADE_THRESHOLD = 3     # settling records survive N more continuity passes → fading
_RELEASE_THRESHOLD = 2  # fading records survive N more → released

_FAST_SETTLE_TYPES = {"continuity-reinforce", "continuity-carry", "continuity-settle", "continuity-release", "continuity-consolidation"}


def run_private_brain_lifecycle() -> dict[str, object]:
    """Run a bounded lifecycle pass over private brain records.

    Transitions records through: active → settling → fading → released.
    Uses a simple age-based model: records that have been present across
    many continuity motor invocations gradually settle and fade.

    Returns a summary of transitions made.
    """
    now = datetime.now(UTC).isoformat()
    # Get ALL non-released records for lifecycle evaluation
    active_records = list_private_brain_records(limit=50, status="active")
    settling_records = list_private_brain_records(limit=50, status="settling")
    fading_records = list_private_brain_records(limit=50, status="fading")

    transitions: dict[str, int] = {"settled": 0, "faded": 0, "released": 0}

    # Active → settling: records that have been around for a while
    # Use record age relative to total active count as proxy
    if len(active_records) > _SETTLE_THRESHOLD:
        # Settle the oldest records beyond the threshold
        to_settle = active_records[_SETTLE_THRESHOLD:]
        for record in to_settle:
            rtype = str(record.get("record_type") or "")
            # Consolidation records settle faster
            if rtype in _FAST_SETTLE_TYPES or len(active_records) > _SETTLE_THRESHOLD + 2:
                update_private_brain_record_status(
                    str(record["record_id"]),
                    status="settling",
                    updated_at=now,
                )
                transitions["settled"] += 1

    # Settling → fading: if we have many settling records
    if len(settling_records) > _FADE_THRESHOLD:
        to_fade = settling_records[_FADE_THRESHOLD:]
        for record in to_fade:
            update_private_brain_record_status(
                str(record["record_id"]),
                status="fading",
                updated_at=now,
            )
            transitions["faded"] += 1

    # Fading → released
    if len(fading_records) > _RELEASE_THRESHOLD:
        to_release = fading_records[_RELEASE_THRESHOLD:]
        for record in to_release:
            update_private_brain_record_status(
                str(record["record_id"]),
                status="released",
                updated_at=now,
            )
            transitions["released"] += 1

    total_transitions = sum(transitions.values())
    if total_transitions > 0:
        event_bus.publish(
            "private_brain.lifecycle_completed",
            {
                "settled": transitions["settled"],
                "faded": transitions["faded"],
                "released": transitions["released"],
                "active_remaining": max(0, len(active_records) - transitions["settled"]),
                "settling_remaining": max(0, len(settling_records) - transitions["faded"] + transitions["settled"]),
                "summary": f"Lifecycle: {transitions['settled']} settled, {transitions['faded']} faded, {transitions['released']} released.",
            },
        )
    else:
        event_bus.publish(
            "private_brain.lifecycle_skipped",
            {
                "active_count": len(active_records),
                "settling_count": len(settling_records),
                "fading_count": len(fading_records),
                "summary": "No lifecycle transitions needed.",
            },
        )

    return {
        "transitions": transitions,
        "total_transitions": total_transitions,
        "counts": {
            "active": len(active_records),
            "settling": len(settling_records),
            "fading": len(fading_records),
        },
    }


# ---------------------------------------------------------------------------
# Surface builders for observability
# ---------------------------------------------------------------------------


def build_private_brain_surface(*, limit: int = 20) -> dict[str, object]:
    """Return the current private brain state for observability."""
    items = list_private_brain_records(limit=limit, status="active")
    types: dict[str, int] = {}
    for item in items:
        t = str(item.get("record_type", "unknown"))
        types[t] = types.get(t, 0) + 1
    return {
        "active": len(items) > 0,
        "total_records": len(items),
        "by_type": types,
        "items": items,
        "summary": {
            "record_count": len(items),
            "latest_focus": str(items[0].get("focus", "")) if items else "",
            "latest_summary": str(items[0].get("summary", "")) if items else "",
            "current_state": "active" if items else "empty",
        },
    }


def build_session_distillation_surface(*, limit: int = 5) -> dict[str, object]:
    """Return recent distillation records for observability."""
    items = list_session_distillation_records(limit=limit)
    return {
        "active": len(items) > 0,
        "total_records": len(items),
        "items": items,
        "summary": {
            "latest_summary": str(items[0].get("summary", "")) if items else "",
            "latest_private_count": int(items[0].get("private_brain_count", 0)) if items else 0,
            "latest_workspace_count": int(items[0].get("workspace_memory_count", 0)) if items else 0,
        },
    }


# ---------------------------------------------------------------------------
# Session summaries — LLM-generated conversation summaries for continuity
# ---------------------------------------------------------------------------


def generate_session_summary(
    *,
    session_id: str,
    run_id: str = "",
    user_message: str = "",
    assistant_response: str = "",
) -> str:
    """Generate and store a compact conversation summary for the given session.

    Uses cheap LLM lane. Returns the summary text, or "" on failure.
    """
    # Gather conversation context
    context_parts: list[str] = []

    # Use provided messages if available
    if user_message:
        context_parts.append(f"Bruger: {user_message[:300]}")
    if assistant_response:
        context_parts.append(f"Jarvis: {assistant_response[:500]}")

    # If no messages provided, try to get from chat history
    if not context_parts:
        try:
            from apps.api.jarvis_api.services.chat_sessions import get_chat_session

            session_data = get_chat_session(session_id)
            if session_data and session_data.get("messages"):
                messages = session_data["messages"]
                # Take last 6 messages for context
                for msg in messages[-6:]:
                    role = "Bruger" if msg["role"] == "user" else "Jarvis"
                    content = str(msg.get("content") or "")[:200]
                    if content:
                        context_parts.append(f"{role}: {content}")
        except Exception:
            pass

    if not context_parts:
        return ""

    conversation = "\n".join(context_parts)

    from apps.api.jarvis_api.services.daemon_llm import daemon_llm_call

    prompt = (
        "Du er Jarvis. Opsummér denne samtale i 1-2 sætninger på dansk.\n"
        "Fokus: hvad handlede samtalen om, og hvad blev besluttet eller gjort?\n"
        "Format: 'Emne: ... | Resultat: ...' — max 150 ord.\n\n"
        f"{conversation}"
    )

    summary = daemon_llm_call(
        prompt,
        max_len=500,
        fallback="",
        daemon_name="session_summary",
    )

    if not summary:
        return ""

    # Store the summary
    try:
        from core.runtime.db import session_summary_insert

        session_summary_insert(
            session_id=session_id,
            run_id=run_id,
            summary=summary,
        )
    except Exception:
        pass

    # Publish event
    try:
        from core.eventbus.bus import event_bus

        event_bus.publish(
            "session.summary_generated",
            {
                "session_id": session_id,
                "run_id": run_id,
                "summary_length": len(summary),
            },
        )
    except Exception:
        pass

    return summary


def build_previous_session_summaries(*, limit: int = 3) -> str | None:
    """Build a text block with recent session summaries for prompt injection.

    Returns None if no summaries are available.
    """
    try:
        from core.runtime.db import session_summary_recent

        summaries = session_summary_recent(limit=limit)
    except Exception:
        return None

    if not summaries:
        return None

    lines = ["Tidligere samtaler (nyeste først):"]
    for s in summaries:
        created = str(s.get("created_at") or "")[:16]
        text = str(s.get("summary") or "").strip()
        if text:
            lines.append(f"- [{created}] {text}")

    if len(lines) < 2:
        return None

    return "\n".join(lines)
