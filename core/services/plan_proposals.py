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
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from core.runtime.state_store import load_json, save_json

logger = logging.getLogger(__name__)

_STATE_KEY = "plan_proposals"
_VALID_STATUSES = ("awaiting_approval", "approved", "dismissed", "superseded")


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

    # Supersede any earlier still-pending plan for this session — only one
    # plan can be open per session at a time, otherwise the surface gets
    # cluttered and the model gets ambiguous instructions.
    data = _load_all()
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
    return {"status": "ok", "plan_id": plan_id, "new_status": decision}


def list_session_plans(session_id: str | None) -> list[dict[str, Any]]:
    sid = str(session_id or "_default")
    return [r for r in _load_all().values() if r.get("session_id") == sid]


def pending_plan_section(session_id: str | None) -> str | None:
    pending = [
        r for r in list_session_plans(session_id)
        if r.get("status") == "awaiting_approval"
    ]
    if not pending:
        return None
    rec = pending[0]  # at most one by construction
    steps = rec.get("steps") or []
    step_lines = "\n".join(f"  {i+1}. {s}" for i, s in enumerate(steps))
    return (
        "📋 Du har en plan der venter på brugerens godkendelse "
        f"(plan_id={rec.get('plan_id')}):\n"
        f"  Titel: {rec.get('title')}\n"
        f"  Hvorfor: {rec.get('why') or '(ikke angivet)'}\n"
        f"  Trin:\n{step_lines}\n"
        "Stop og afvent godkendelse FØR du udfører nogen af trinnene. "
        "Hvis brugeren beder om en ændring, så foreslå en ny plan."
    )


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
