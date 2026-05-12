"""Plan revision tool — revise_plan.

Phase 2 of Multi-step Planner (2026-05-12). Closes the destination gap on
Bjørn's replan_signal: stale-signal fires but Jarvis has no clean tool to
revise. This tool proposes a revision via plan_proposals.revise_plan, which
goes through the standard approval flow.

Approval semantics:
  - Revision starts as awaiting_approval (NOT auto-approved)
  - Original plan stays approved until revision is approved
  - On approval, the original plan transitions to "superseded"
  - On dismissal, the original plan continues unchanged

Mirror the world_model_tools.py pattern.
"""
from __future__ import annotations

import logging
from typing import Any

from core.runtime.settings import load_settings
from core.services.plan_proposals import revise_plan

logger = logging.getLogger(__name__)


def _exec_revise_plan(args: dict[str, Any]) -> dict[str, Any]:
    """Tool handler for revise_plan."""
    try:
        if not bool(load_settings().plan_revision_enabled):
            return {"status": "error", "error": "plan_revision disabled (killswitch)"}
    except Exception:
        pass  # fail-open

    plan_id = str(args.get("plan_id") or "").strip()
    session_id = args.get("session_id")
    reason = str(args.get("reason") or "").strip()
    new_steps = args.get("new_steps") or []
    if not isinstance(new_steps, list):
        new_steps = [str(new_steps)]

    if not plan_id:
        return {"status": "error", "error": "plan_id is required"}
    if not reason:
        return {"status": "error", "error": "reason is required"}
    if not new_steps:
        return {"status": "error", "error": "new_steps is required"}

    return revise_plan(
        plan_id=plan_id,
        session_id=session_id,
        reason=reason,
        new_steps=[str(s) for s in new_steps],
    )


PLAN_REVISE_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "revise_plan",
            "description": (
                "Foreslå en revision af en eksisterende approved plan. Bruges når "
                "planen er blevet stale, konteksten har ændret sig, eller du har "
                "lært noget der ændrer hvad næste skridt bør være. Ny plan venter "
                "på godkendelse — godkendelse markerer den gamle plan som "
                "superseded. Progress nulstilles (revision = ny plan = ny progress)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "plan_id": {
                        "type": "string",
                        "description": "ID på den eksisterende approved plan der reviseres",
                    },
                    "reason": {
                        "type": "string",
                        "description": "Hvorfor reviderer du? Hvad har ændret sig?",
                    },
                    "new_steps": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "Den reviderede step-liste. Inkluder allerede-"
                            "fuldførte steps hvis de stadig er relevante "
                            "(progress nulstilles)."
                        ),
                    },
                },
                "required": ["plan_id", "reason", "new_steps"],
            },
        },
    },
]


PLAN_REVISE_TOOL_HANDLERS: dict[str, Any] = {
    "revise_plan": _exec_revise_plan,
}
