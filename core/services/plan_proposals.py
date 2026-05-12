"""Plan mode — propose, wait for approval, then execute.

Mirrors Claude Code's ExitPlanMode pattern: when the model has a complex
or risky multi-step idea, it writes the plan as a structured proposal
instead of executing. The user (or the autonomous policy) approves or
dismisses, and the model proceeds only when the plan is approved.

Why this matters even with phase 2's self-correction nudges: nudges are
hints, plans are contracts. A proposed-and-approved plan is a hard
checkpoint — the model commits to those steps and can be held to them
afterward by a verify pass.

Status lifecycle:
  awaiting_approval → approved | dismissed | superseded

Per-session, persisted via state_store. Pending plans surface at the top
of every visible prompt until resolved.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from core.runtime.state_store import load_json, save_json
from core.runtime.settings import load_settings

logger = logging.getLogger(__name__)

_STATE_KEY = "plan_proposals"
_VALID_STATUSES = (
    "awaiting_approval", "approved", "completed", "dismissed", "superseded",
)
_REPLAN_STALE_DAYS = 3


def _load_all() -> dict[str, dict[str, Any]]:
    raw = load_json(_STATE_KEY, {})
    if not isinstance(raw, dict):
        return {}
    return {str(k): v for k, v in raw.items() if isinstance(v, dict)}


def _save_all(data: dict[str, dict[str, Any]]) -> None:
    save_json(_STATE_KEY, data)


def propose_plan(
    *,
    session_id: str | None,
    title: str,
    why: str,
    steps: list[str],
    skill_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    title = (title or "").strip()
    why = (why or "").strip()
    if not title or not steps:
        return {"status": "error", "error": "title and steps are required"}
    cleaned_steps = [str(s).strip() for s in steps if str(s).strip()]
    if not cleaned_steps:
        return {"status": "error", "error": "steps must contain at least one non-empty entry"}

    sid = str(session_id or "_default")
    plan_id = f"plan-{uuid4().hex[:10]}"
    now = datetime.now(UTC).isoformat()

    data = _load_all()

    # Deduplicate: if an awaiting_approval plan with the same title already
    # exists (any session), skip creating a duplicate. This prevents the
    # auto-improvement proposer from spawning endless identical plans.
    normalized_title = title[:160].strip().lower()
    for rec in data.values():
        if (
            rec.get("status") == "awaiting_approval"
            and (rec.get("title") or "").strip().lower() == normalized_title
        ):
            logger.info(
                "Skipping duplicate plan proposal — title '%s' already pending as %s",
                title[:80],
                rec.get("plan_id"),
            )
            return {
                "status": "skipped_duplicate",
                "existing_plan_id": rec.get("plan_id"),
                "awaiting": True,
                "session_id": sid,
            }

    # Supersede any earlier still-pending plan for this session — only one
    # plan can be open per session at a time, otherwise the surface gets
    # cluttered and the model gets ambiguous instructions.
    for pid, rec in data.items():
        if rec.get("session_id") == sid and rec.get("status") == "awaiting_approval":
            rec["status"] = "superseded"
            rec["resolved_at"] = now

    data[plan_id] = {
        "plan_id": plan_id,
        "session_id": sid,
        "title": title[:160],
        "why": why[:400],
        "steps": cleaned_steps[:20],
        "status": "awaiting_approval",
        "created_at": now,
        "completed_step_indices": [],  # Phase 1 (2026-05-12): tracks progress
        # Tool Invention Phase 1 (2026-05-12): optional skill-install metadata.
        # When present, resolve_plan(decision="approved") will call
        # skill_engine.create_skill() on it after status transition.
        "skill_data": skill_data if isinstance(skill_data, dict) else None,
        # Phase 2 (2026-05-12) — revision tracking
        "revised_from": None,
        "revision_reason": None,
        "superseded_by": None,
    }
    _save_all(data)
    return {"status": "ok", "plan_id": plan_id, "awaiting": True, "session_id": sid}


def resolve_plan(plan_id: str, *, decision: str) -> dict[str, Any]:
    decision = (decision or "").strip().lower()
    if decision not in {"approved", "dismissed"}:
        return {"status": "error", "error": "decision must be 'approved' or 'dismissed'"}
    data = _load_all()
    rec = data.get(plan_id)
    if rec is None:
        return {"status": "error", "error": f"unknown plan_id {plan_id}"}
    if rec.get("status") != "awaiting_approval":
        return {
            "status": "error",
            "error": f"plan is {rec.get('status')}, not awaiting_approval",
        }
    rec["status"] = decision
    rec["resolved_at"] = datetime.now(UTC).isoformat()
    _save_all(data)

    # Phase 1 (2026-05-12): auto-create todos when plan is approved.
    # Hook is here (not in the approve_plan tool wrapper) so MC approvals
    # and programmatic approvals both flow through it.
    if decision == "approved" and _plan_todo_auto_create_enabled():
        steps = list(rec.get("steps") or [])
        sid = str(rec.get("session_id") or "_default")
        if steps:
            try:
                from core.services.agent_todos import create_from_plan
                create_from_plan(
                    plan_id=plan_id,
                    session_id=sid,
                    steps=steps,
                )
            except Exception as exc:
                logger.warning(
                    "plan_proposals: failed to auto-create todos for %s: %s",
                    plan_id, exc,
                )

    # Tool Invention Phase 1 (2026-05-12): if the plan carries skill_data,
    # call create_skill() on approval. Validation already ran at propose-time,
    # so this should normally succeed; I/O failures are logged + emitted but
    # do not raise (plan stays "approved" but uncompleted in that case).
    if decision == "approved":
        skill_data = rec.get("skill_data")
        if isinstance(skill_data, dict):
            try:
                from core.services.skill_engine import create_skill
                install_result = create_skill(
                    name=str(skill_data.get("name") or ""),
                    description=str(skill_data.get("description") or ""),
                    instructions=str(skill_data.get("instructions") or ""),
                    use_when=str(skill_data.get("use_when") or ""),
                    tags=list(skill_data.get("tags") or []),
                )
                if install_result.get("status") == "ok":
                    try:
                        from core.eventbus.bus import event_bus
                        event_bus.publish(
                            "cognitive_state.skill_installed",
                            {
                                "plan_id": plan_id,
                                "name": skill_data.get("name"),
                                "path": install_result.get("path"),
                            },
                        )
                    except Exception:
                        pass
                else:
                    logger.error(
                        "tool_invention: create_skill returned error for plan %s: %s",
                        plan_id, install_result.get("error"),
                    )
                    try:
                        from core.eventbus.bus import event_bus
                        event_bus.publish(
                            "cognitive_state.skill_install_failed",
                            {
                                "plan_id": plan_id,
                                "name": skill_data.get("name"),
                                "error": install_result.get("error"),
                            },
                        )
                    except Exception:
                        pass
            except Exception as exc:
                logger.error(
                    "tool_invention: create_skill raised for plan %s: %s",
                    plan_id, exc,
                )
                try:
                    from core.eventbus.bus import event_bus
                    event_bus.publish(
                        "cognitive_state.skill_install_failed",
                        {
                            "plan_id": plan_id,
                            "name": skill_data.get("name"),
                            "error": str(exc),
                        },
                    )
                except Exception:
                    pass

    # Phase 2 (2026-05-12) — supersede the revised plan's original.
    # Fires only on approval of a revision; gracefully no-ops if the
    # original is no longer in 'approved' state (race condition with
    # manual dismiss/completion).
    if decision == "approved":
        revised_from = rec.get("revised_from")
        if revised_from:
            data_after = _load_all()
            old_rec = data_after.get(str(revised_from))
            if old_rec is not None and old_rec.get("status") == "approved":
                old_rec["status"] = "superseded"
                old_rec["superseded_by"] = plan_id
                old_rec["updated_at"] = datetime.now(UTC).isoformat()
                _save_all(data_after)
                try:
                    from core.eventbus.bus import event_bus
                    event_bus.publish(
                        "cognitive_state.plan_revision_approved",
                        {
                            "old_plan_id": str(revised_from),
                            "new_plan_id": plan_id,
                        },
                    )
                except Exception:
                    pass

    return {"status": "ok", "plan_id": plan_id, "new_status": decision}


def _plan_todo_auto_create_enabled() -> bool:
    try:
        return bool(load_settings().plan_todo_auto_create_enabled)
    except Exception:
        return True


def revise_plan(
    *,
    plan_id: str,
    session_id: str | None,
    reason: str,
    new_steps: list[str],
) -> dict[str, Any]:
    """Propose a revision of an existing approved plan.

    Creates a NEW plan record with status="awaiting_approval", linked to
    the original via revised_from. The original plan is NOT mutated here —
    it stays "approved" until the revision is approved (see resolve_plan
    hook). Progress is reset on the new plan; skill_data is NOT inherited.

    Phase 2 of Multi-step Planner (2026-05-12).
    """
    if not _plan_revision_enabled():
        return {"status": "error", "error": "plan_revision disabled (killswitch)"}

    pid = str(plan_id or "").strip()
    reason_clean = (reason or "").strip()
    cleaned_steps = [str(s).strip() for s in (new_steps or []) if str(s).strip()]

    if not pid:
        return {"status": "error", "error": "plan_id is required"}
    if not reason_clean:
        return {"status": "error", "error": "reason is required"}
    if not cleaned_steps:
        return {"status": "error", "error": "new_steps must contain at least one non-empty entry"}

    data = _load_all()
    old = data.get(pid)
    if old is None:
        return {"status": "error", "error": f"unknown plan_id {pid!r}"}
    if old.get("status") != "approved":
        return {
            "status": "error",
            "error": (
                f"plan {pid} is {old.get('status')!r}, not 'approved' — "
                "only approved plans can be revised"
            ),
        }

    # Dedupe: if a pending revision of this same plan_id already exists,
    # return the existing one rather than creating a duplicate.
    for existing_id, rec in data.items():
        if (
            rec.get("status") == "awaiting_approval"
            and rec.get("revised_from") == pid
        ):
            return {
                "status": "skipped_duplicate",
                "existing_plan_id": existing_id,
                "awaiting": True,
                "session_id": str(rec.get("session_id") or session_id or "_default"),
            }

    sid = str(session_id or old.get("session_id") or "_default")
    new_plan_id = f"plan-{uuid4().hex[:10]}"
    now = datetime.now(UTC).isoformat()

    data[new_plan_id] = {
        "plan_id": new_plan_id,
        "session_id": sid,
        "title": f"Revision of {old.get('title') or pid}"[:160],
        "why": reason_clean[:400],
        "steps": cleaned_steps[:20],
        "status": "awaiting_approval",
        "created_at": now,
        "completed_step_indices": [],
        # Revisions never carry skill_data — they are for step-flows.
        "skill_data": None,
        # Phase 2 revision tracking
        "revised_from": pid,
        "revision_reason": reason_clean,
        "superseded_by": None,
    }
    _save_all(data)

    try:
        from core.eventbus.bus import event_bus
        event_bus.publish(
            "cognitive_state.plan_revised",
            {
                "old_plan_id": pid,
                "new_plan_id": new_plan_id,
                "reason": reason_clean[:120],
            },
        )
    except Exception:
        pass

    return {
        "status": "ok",
        "plan_id": new_plan_id,
        "awaiting": True,
        "session_id": sid,
        "revised_from": pid,
    }


def _plan_revision_enabled() -> bool:
    try:
        return bool(load_settings().plan_revision_enabled)
    except Exception:
        return True  # fail-open


def mark_step_completed(plan_id: str, step_index: int) -> dict[str, Any]:
    """Append step_index to plan's completed_step_indices (idempotent, sorted).

    Auto-transitions plan status to 'completed' when all steps are done.
    No-op if plan doesn't exist or step_index is out of range.
    """
    pid = str(plan_id or "").strip()
    if not pid:
        return {"status": "error", "error": "plan_id is required"}
    try:
        idx = int(step_index)
    except Exception:
        return {"status": "error", "error": "step_index must be int"}

    data = _load_all()
    rec = data.get(pid)
    if rec is None:
        return {"status": "error", "error": f"unknown plan_id {pid}"}

    steps = list(rec.get("steps") or [])
    if idx < 0 or idx >= len(steps):
        return {"status": "error", "error": f"step_index {idx} out of range (0..{len(steps)-1})"}

    completed = list(rec.get("completed_step_indices") or [])
    if idx not in completed:
        completed.append(idx)
        completed.sort()
        rec["completed_step_indices"] = completed
        rec["updated_at"] = datetime.now(UTC).isoformat()

        # Auto-completion: when all steps done, transition status.
        if len(completed) == len(steps) and rec.get("status") == "approved":
            rec["status"] = "completed"
            rec["completed_at"] = rec["updated_at"]

        _save_all(data)
    return {
        "status": "ok",
        "plan_id": pid,
        "completed_count": len(completed),
        "total_count": len(steps),
        "plan_status": rec.get("status"),
    }


def _parse_iso(value: str) -> datetime | None:
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


def replan_signal_for_plan(
    rec: dict[str, Any],
    *,
    now: datetime | None = None,
    stale_days: int = _REPLAN_STALE_DAYS,
) -> dict[str, Any]:
    """Return a non-mutating backtracking signal for an approved stale plan."""
    if rec.get("status") != "approved":
        return {"needed": False, "reason": "not-approved"}
    steps = list(rec.get("steps") or [])
    completed = list(rec.get("completed_step_indices") or [])
    if not steps or len(completed) >= len(steps):
        return {"needed": False, "reason": "complete-or-empty"}

    ref = _parse_iso(str(rec.get("updated_at") or rec.get("resolved_at") or rec.get("created_at") or ""))
    if ref is None:
        return {"needed": False, "reason": "no-timestamp"}
    current = now or datetime.now(UTC)
    age_days = max(0.0, (current - ref).total_seconds() / 86400.0)
    threshold = max(int(stale_days), 1)
    if age_days < threshold:
        return {
            "needed": False,
            "reason": "fresh",
            "age_days": round(age_days, 2),
            "threshold_days": threshold,
        }

    return {
        "needed": True,
        "reason": "approved-plan-stale",
        "age_days": round(age_days, 2),
        "threshold_days": threshold,
        "completed": len(completed),
        "total": len(steps),
        "allowed_effects": [
            "prompt_attention",
            "ask_user_or_propose_replan",
            "do_not_auto_execute_new_plan",
        ],
    }


def list_session_plans(session_id: str | None) -> list[dict[str, Any]]:
    sid = str(session_id or "_default")
    return [r for r in _load_all().values() if r.get("session_id") == sid]


def pending_plan_section(session_id: str | None) -> str | None:
    """Surface plans relevant to the current session.

    Two categories:
      1. awaiting_approval — render full plan, stop-and-wait message.
      2. approved + incomplete — render progress + remaining steps.

    Returns None if neither category has any entry for this session.
    Phase 1 (2026-05-12): now shows approved+incomplete, not only
    awaiting_approval.
    """
    session_plans = list_session_plans(session_id)

    awaiting = [r for r in session_plans if r.get("status") == "awaiting_approval"]
    active = [
        r for r in session_plans
        if r.get("status") == "approved"
        and len(r.get("completed_step_indices") or []) < len(r.get("steps") or [])
    ]

    if not awaiting and not active:
        return None

    blocks: list[str] = []

    for rec in awaiting[:1]:  # at most one by construction
        steps = rec.get("steps") or []
        step_lines = "\n".join(f"  {i+1}. {s}" for i, s in enumerate(steps))
        blocks.append(
            "📋 Du har en plan der venter på brugerens godkendelse "
            f"(plan_id={rec.get('plan_id')}):\n"
            f"  Titel: {rec.get('title')}\n"
            f"  Hvorfor: {rec.get('why') or '(ikke angivet)'}\n"
            f"  Trin:\n{step_lines}\n"
            "Stop og afvent godkendelse FØR du udfører nogen af trinnene. "
            "Hvis brugeren beder om en ændring, så foreslå en ny plan."
        )

    for rec in active[:3]:  # cap at 3 in same session
        steps = list(rec.get("steps") or [])
        completed = sorted(set(rec.get("completed_step_indices") or []))
        remaining_indices = [i for i in range(len(steps)) if i not in completed]
        remaining_lines = "\n".join(
            f"    {i+1}. {steps[i]}" for i in remaining_indices
        )
        replan = replan_signal_for_plan(rec)
        replan_line = ""
        if replan.get("needed"):
            replan_line = (
                "\n  ⚠ Replan-signal: planen er stale "
                f"({replan.get('age_days')} dage uden progress). "
                "Vurder om næste handling bør være at foreslå en revideret plan."
            )
        blocks.append(
            f"🎯 Aktiv plan (godkendt, {len(completed)}/{len(steps)} done) "
            f"plan_id={rec.get('plan_id')}: {rec.get('title')}\n"
            f"  Resterende trin:\n{remaining_lines}"
            f"{replan_line}"
        )

    return "\n\n".join(blocks)


def format_cross_session_plans_for_awareness(
    current_session_id: str | None,
    *,
    max_plans: int = 3,
    max_age_days: int = 14,
) -> str:
    """Return awareness-block text for approved+incomplete plans owned by
    OTHER sessions. Empty string if none qualify.

    Filters:
      - status == "approved"
      - len(completed_step_indices) < len(steps)  (incomplete)
      - session_id != current_session_id
      - plan["created_at"] within max_age_days (recency on the PLAN, not session)

    Capped at max_plans (sorted by created_at desc).
    """
    current = str(current_session_id or "").strip()
    if not current:
        return ""

    cutoff = datetime.now(UTC) - timedelta(days=max(int(max_age_days), 1))
    candidates: list[dict[str, Any]] = []
    for rec in _load_all().values():
        if rec.get("status") != "approved":
            continue
        steps = rec.get("steps") or []
        completed = rec.get("completed_step_indices") or []
        if len(completed) >= len(steps):
            continue  # fully done
        sid = str(rec.get("session_id") or "")
        if sid == current:
            continue
        created_iso = str(rec.get("created_at") or "")
        try:
            created = datetime.fromisoformat(created_iso.replace("Z", "+00:00"))
            if created.tzinfo is None:
                created = created.replace(tzinfo=UTC)
            if created < cutoff:
                continue
        except Exception:
            continue
        candidates.append(rec)

    if not candidates:
        return ""

    candidates.sort(key=lambda r: str(r.get("created_at", "")), reverse=True)
    capped = candidates[: max(int(max_plans), 1)]

    lines = ["### Aktive plans i andre sessions"]
    for rec in capped:
        sid_short = str(rec.get("session_id") or "?")[:8]
        completed = len(rec.get("completed_step_indices") or [])
        total = len(rec.get("steps") or [])
        title = str(rec.get("title") or "(uden titel)")
        lines.append(f"- {title} (session {sid_short}): {completed}/{total} done")
    return "\n".join(lines)


def all_pending_plans_section() -> str | None:
    """Show ALL pending plans (incl. auto-improvement proposals from
    session_id=None). Without this, auto-generated proposals sit in
    the queue forever because they're not in any user session."""
    all_pending = [
        r for r in _load_all().values()
        if r.get("status") == "awaiting_approval"
    ]
    if not all_pending:
        return None
    # Sort by created_at descending
    all_pending.sort(key=lambda r: str(r.get("created_at", "")), reverse=True)
    lines = [f"📥 {len(all_pending)} plan(er) venter på godkendelse:"]
    for rec in all_pending[:5]:
        plan_id = str(rec.get("plan_id") or "?")
        title = str(rec.get("title") or "(uden titel)")
        sid = str(rec.get("session_id") or "?")
        sid_label = "" if sid == "_default" else f" (session: {sid[:8]})"
        lines.append(f"  • {plan_id}: {title}{sid_label}")
    if len(all_pending) > 5:
        lines.append(f"  ... og {len(all_pending) - 5} mere")
    lines.append(
        "Brug `list_plans` for detaljer, `approve_plan` for at godkende, "
        "`dismiss_plan` for at afvise."
    )
    return "\n".join(lines)


def _exec_propose_plan(args: dict[str, Any]) -> dict[str, Any]:
    return propose_plan(
        session_id=args.get("session_id"),
        title=str(args.get("title") or ""),
        why=str(args.get("why") or ""),
        steps=list(args.get("steps") or []),
    )


def _exec_approve_plan(args: dict[str, Any]) -> dict[str, Any]:
    return resolve_plan(str(args.get("plan_id") or ""), decision="approved")


def _exec_dismiss_plan(args: dict[str, Any]) -> dict[str, Any]:
    return resolve_plan(str(args.get("plan_id") or ""), decision="dismissed")


def _exec_list_plans(args: dict[str, Any]) -> dict[str, Any]:
    items = list_session_plans(args.get("session_id"))
    return {"status": "ok", "plans": items, "count": len(items)}


PLAN_PROPOSALS_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "propose_plan",
            "description": (
                "Write a multi-step plan and wait for the user to approve. "
                "Use BEFORE doing anything risky, multi-step, or reversibility-"
                "concerning. Steps should be concrete actions you'll take. "
                "Returns plan_id; you must NOT execute the steps until the "
                "plan is approved (the user responds, or you receive an "
                "approve_plan call back). Only one plan can be pending per "
                "session — proposing a new one supersedes the previous."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "title": {"type": "string", "description": "Short summary, e.g. 'Refactor visible_runs split'."},
                    "why": {"type": "string", "description": "One-paragraph motivation."},
                    "steps": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Concrete steps in order.",
                    },
                },
                "required": ["title", "steps"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "approve_plan",
            "description": "Mark a plan as approved. Use only when the user has explicitly agreed.",
            "parameters": {
                "type": "object",
                "properties": {"plan_id": {"type": "string"}},
                "required": ["plan_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "dismiss_plan",
            "description": "Mark a plan as dismissed (user declined or you're abandoning it).",
            "parameters": {
                "type": "object",
                "properties": {"plan_id": {"type": "string"}},
                "required": ["plan_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_plans",
            "description": "List all plans for this session (any status).",
            "parameters": {
                "type": "object",
                "properties": {"session_id": {"type": "string"}},
                "required": [],
            },
        },
    },
]
