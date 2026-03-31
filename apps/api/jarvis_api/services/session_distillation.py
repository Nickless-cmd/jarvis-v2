"""Session distillation — classifies end-of-run carry into private brain,
workspace memory, or discard.

This is the bridge between session-scoped signal production and persistent
layered memory.  It runs at visible-run completion and inspects the runtime
surfaces that were active during the session.

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

    # Gather evidence from current runtime surfaces
    inner_notes = build_runtime_private_inner_note_signal_surface(limit=6)
    state_snapshots = build_runtime_private_state_snapshot_surface(limit=4)
    self_model = build_runtime_self_model_signal_surface(limit=4)
    diary = build_diary_synthesis_signal_surface(limit=4)
    focus = build_runtime_development_focus_surface(limit=4)
    loops = build_runtime_open_loop_signal_surface(limit=6)
    world_model = build_runtime_world_model_signal_surface(limit=4)
    facts = build_runtime_remembered_fact_signal_surface(limit=6)
    goals = build_runtime_goal_signal_surface(limit=4)

    private_items: list[dict[str, object]] = []
    workspace_items: list[dict[str, object]] = []
    discard_reasons: list[str] = []

    # --- Private brain carry ---
    # Inner notes with substance → private brain
    for item in inner_notes.get("items", []):
        summary = str(item.get("summary") or "").strip()
        if not summary or str(item.get("status") or "") not in {"active", "softening"}:
            discard_reasons.append(f"inner-note-inactive:{item.get('signal_id', 'unknown')}")
            continue
        record = insert_private_brain_record(
            record_id=f"pb-inner-{uuid4().hex[:12]}",
            record_type="inner-note-carry",
            layer="private_brain",
            session_id=session_id,
            run_id=run_id,
            focus=str(item.get("title") or ""),
            summary=summary,
            detail=str(item.get("rationale") or ""),
            source_signals=f"inner-note:{item.get('signal_id', '')}",
            confidence=str(item.get("confidence") or "medium"),
            created_at=now,
        )
        if record:
            private_items.append(record)

    # Self-model signals → private brain
    for item in self_model.get("items", []):
        summary = str(item.get("summary") or "").strip()
        if not summary or str(item.get("status") or "") not in {"active", "softening"}:
            discard_reasons.append(f"self-model-inactive:{item.get('signal_id', 'unknown')}")
            continue
        record = insert_private_brain_record(
            record_id=f"pb-selfmodel-{uuid4().hex[:12]}",
            record_type="self-model-carry",
            layer="private_brain",
            session_id=session_id,
            run_id=run_id,
            focus=str(item.get("title") or ""),
            summary=summary,
            detail=str(item.get("evidence_summary") or ""),
            source_signals=f"self-model:{item.get('signal_id', '')}",
            confidence=str(item.get("confidence") or "medium"),
            created_at=now,
        )
        if record:
            private_items.append(record)

    # Diary synthesis → private brain
    for item in diary.get("items", []):
        summary = str(item.get("summary") or "").strip()
        if not summary or str(item.get("status") or "") not in {"active", "softening"}:
            discard_reasons.append(f"diary-inactive:{item.get('signal_id', 'unknown')}")
            continue
        record = insert_private_brain_record(
            record_id=f"pb-diary-{uuid4().hex[:12]}",
            record_type="diary-carry",
            layer="private_brain",
            session_id=session_id,
            run_id=run_id,
            focus=str(item.get("title") or ""),
            summary=summary,
            detail=str(item.get("rationale") or ""),
            source_signals=f"diary:{item.get('signal_id', '')}",
            confidence=str(item.get("confidence") or "medium"),
            created_at=now,
        )
        if record:
            private_items.append(record)

    # State snapshots → private brain (only if initiative or self-state content)
    for item in state_snapshots.get("items", []):
        summary = str(item.get("summary") or "").strip()
        if not summary or str(item.get("status") or "") not in {"active", "softening"}:
            discard_reasons.append(f"snapshot-inactive:{item.get('snapshot_id', 'unknown')}")
            continue
        record = insert_private_brain_record(
            record_id=f"pb-snapshot-{uuid4().hex[:12]}",
            record_type="state-snapshot-carry",
            layer="private_brain",
            session_id=session_id,
            run_id=run_id,
            focus=str(item.get("title") or ""),
            summary=summary,
            detail=str(item.get("evidence_summary") or ""),
            source_signals=f"state-snapshot:{item.get('snapshot_id', '')}",
            confidence=str(item.get("confidence") or "medium"),
            created_at=now,
        )
        if record:
            private_items.append(record)

    # --- Workspace memory carry ---
    # Remembered facts → workspace memory (via existing candidate pipeline)
    # These are already tracked via candidate_tracking — we just log them here
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

    # Active development focus → workspace context (informational, already in pipeline)
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

    # Active goals → workspace context
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
    total = len(private_items) + len(workspace_items) + len(discard_reasons)

    distill_summary = (
        f"Session distillation: {len(private_items)} private brain, "
        f"{len(workspace_items)} workspace memory, "
        f"{len(discard_reasons)} discarded."
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
                "types": list({str(r.get("record_type", "")) for r in private_items}),
                "summary": f"{len(private_items)} private brain records created.",
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
            "summary": distill_summary,
        },
    )

    return {
        "distillation_id": distillation_id,
        "private_brain_count": len(private_items),
        "workspace_memory_count": len(workspace_items),
        "discard_count": len(discard_reasons),
        "private_items": private_items,
        "workspace_items": workspace_items,
        "distillation": distillation,
        "summary": distill_summary,
    }


# ---------------------------------------------------------------------------
# Surface builders for observability
# ---------------------------------------------------------------------------


def build_private_brain_surface(*, limit: int = 20) -> dict[str, object]:
    """Return the current private brain state for observability."""
    items = list_private_brain_records(limit=limit, status="active")
    types = {}
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
