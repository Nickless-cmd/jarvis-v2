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

    # Build a consolidation summary from excerpts
    focus_parts = [e["focus"] for e in excerpts[:3] if e.get("focus")]
    summary_parts = [e["summary"] for e in excerpts[:3] if e.get("summary")]
    consolidated_focus = " + ".join(focus_parts[:3]) if focus_parts else "private continuity"
    consolidated_summary = (
        f"Consolidation across {total} brain records ({type_count} types). "
        f"Key threads: {'; '.join(s[:60] for s in summary_parts[:3])}"
    )

    # Anti-spam: check if we already have a very similar consolidation
    recent_records = list_private_brain_records(limit=_DUPLICATE_SUMMARY_WINDOW)
    if _is_near_duplicate(consolidated_summary, "continuity-consolidation", recent_records):
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
        record_id=f"pb-consolidation-{uuid4().hex[:12]}",
        record_type="continuity-consolidation",
        layer="private_brain",
        session_id="",  # continuity motor runs between sessions
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
            "record_count_input": total,
            "type_count_input": type_count,
            "summary": consolidated_summary[:200],
        },
    )

    return {
        "action": "consolidated",
        "trigger": trigger,
        "brain_record_count": total,
        "record": record,
        "summary": consolidated_summary,
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
