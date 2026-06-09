"""skill_chain tool — Lag #4 sequential skill composition.

Synchronous tool. Accepts a plan (ordered list of 2-5 skill names),
pre-validates atomically that all named skills exist, then builds a
C-format combined instructions package: step-numbered headers + verbatim
SKILL.md instructions + closing line that binds steps.

No DB writes, no daemon, no runtime-state. Pure validation + lookup +
string assembly.

Discovery: skill_gate's chain_candidates/chain_hint fields surface
viable chains. Tool description guides Jarvis when to chain vs invoke.
"""
from __future__ import annotations

import logging
from typing import Any

from core.eventbus.bus import event_bus
from core.runtime.settings import load_settings
from core.services import skill_engine

logger = logging.getLogger(__name__)


# Soft cap on combined instructions (chars). Above this we emit a warning
# but still execute. ~8k tokens worth — well under model context window
# but heavy enough to warrant attention.
_SOFT_INSTRUCTIONS_CAP = 32000


def _validate_plan_existence(plan: list[str]) -> list[str]:
    """Return list of missing skill names (empty list if all exist)."""
    return [name for name in plan if not skill_engine.skill_exists(name)]


def _build_combined_instructions(plan: list[str]) -> str:
    """Header-format combination — instructions verbatim, step-headers added."""
    n = len(plan)
    parts = [f"[skill_chain — {n} steps]\n"]
    for i, name in enumerate(plan, start=1):
        skill_data = skill_engine.get_skill_instructions(name)
        if skill_data.get("status") != "ok":
            # Defensive — pre-validation should have caught this
            parts.append(f"\n## Step {i} of {n}: {name} (UNAVAILABLE)\n")
            continue
        instructions = str(skill_data.get("instructions") or "").strip()
        parts.append(f"\n## Step {i} of {n}: {name}\n")
        parts.append(instructions)
    parts.append(
        "\n\nWhen you finish step 1, continue to step 2 using your step-1 "
        "output as context. Each subsequent step builds on prior output."
    )
    return "\n".join(parts)


def _build_note(plan: list[str], instructions: str) -> str:
    """Build the user-visible note. Warns when over soft cap."""
    if len(instructions) > _SOFT_INSTRUCTIONS_CAP:
        return (
            f"⚠ Combined instructions are {len(instructions)} chars "
            f"(soft cap {_SOFT_INSTRUCTIONS_CAP}). Consider shorter chain. "
            "Execute step 1 first, then continue to step 2 using your "
            "step-1 output as context."
        )
    return (
        f"Skills loaded in chain: {len(plan)} steps. Execute step 1 first, "
        "then continue to step 2 using your step-1 output as context. "
        "Each skill's instructions are below."
    )


def _publish_chain_event(
    *,
    plan: list[str],
    instructions_length: int,
    rationale_provided: bool,
    status: str,
) -> None:
    """Publish to eventbus. Metadata only — NO rationale text."""
    try:
        event_bus.publish(
            "cognitive_skill_chain.executed",
            {
                "plan": plan,
                "step_count": len(plan),
                "instructions_length": instructions_length,
                "rationale_provided": rationale_provided,
                "status": status,
            },
        )
    except Exception as exc:
        logger.debug("skill_chain: publish failed: %s", exc)


def _exec_skill_chain(args: dict[str, Any]) -> dict[str, Any]:
    """Validate plan, build combined instructions, return.

    All-or-nothing pre-validation: if any skill in plan is missing, the
    whole call is rejected with the missing list (no partial execution).
    """
    # 1. Kill-switch
    try:
        if not load_settings().skill_chain_enabled:
            return {
                "status": "disabled",
                "note": "skill_chain is disabled in runtime settings",
            }
    except Exception:
        pass

    # 2. Required arg + type
    plan = args.get("plan")
    if not isinstance(plan, list):
        return {"status": "rejected", "reason": "plan must be a list"}

    # 3. Length bounds
    if len(plan) < 2:
        return {
            "status": "rejected",
            "reason": "plan must have at least 2 skills",
        }
    if len(plan) > 5:
        return {"status": "rejected", "reason": "plan exceeds max length of 5"}

    # 4. Type check entries
    if not all(isinstance(s, str) and s.strip() for s in plan):
        return {
            "status": "rejected",
            "reason": "all plan entries must be non-empty strings",
        }

    # 5. Normalize names (strip whitespace)
    normalized_plan = [s.strip() for s in plan]

    # 6. Pre-validate ALL skills exist (atomic — alt-eller-intet)
    missing = _validate_plan_existence(normalized_plan)
    if missing:
        try:
            available = [s["name"] for s in skill_engine.list_skills()]
        except Exception:
            available = []
        return {
            "status": "rejected",
            "reason": "unknown skills in plan",
            "missing": missing,
            "available": available,
        }

    # 7. Build combined instructions
    instructions = _build_combined_instructions(normalized_plan)

    # 8. Record usage for each skill in chain (C4 auto-learning)
    for skill_name in normalized_plan:
        try:
            skill_engine.record_skill_usage(
                skill_name,
                source="skill_chain",
                success=True,
                query="",
                context_tags="",
                score=1.0,
            )
        except Exception as exc:
            logger.warning("skill_chain: record_skill_usage failed for %s: %s", skill_name, exc)

    # 9. Publish event (metadata only — no rationale text)
    _publish_chain_event(
        plan=normalized_plan,
        instructions_length=len(instructions),
        rationale_provided=bool(args.get("rationale")),
        status="ok",
    )

    # 10. Return success
    return {
        "status": "ok",
        "chain": normalized_plan,
        "step_count": len(normalized_plan),
        "instructions": instructions,
        "instructions_full_length": len(instructions),
        "note": _build_note(normalized_plan, instructions),
    }


SKILL_CHAIN_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "skill_chain",
            "description": (
                "Chain multiple skills in sequence for tasks that require "
                "more than one skill (e.g. fact-check then summarize, "
                "research then format). Each step's instructions are loaded "
                "into context in order, with clear step-headers. You execute "
                "step 1, then continue to step 2 using your step-1 output as "
                "context, and so on. Use when skill_gate returns multiple "
                "close-matching candidates, or when the task naturally has "
                "multiple phases. For single-skill tasks, use skill_invoke "
                "instead."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "plan": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "Ordered list of skill names. Min 2, max 5. "
                            "Each name must exist (verified before execution)."
                        ),
                        "minItems": 2,
                        "maxItems": 5,
                    },
                    "rationale": {
                        "type": "string",
                        "description": (
                            "Optional: short note on why this chain. "
                            "Logged in tool-call but not persisted to events."
                        ),
                    },
                },
                "required": ["plan"],
            },
        },
    },
]


SKILL_CHAIN_TOOL_HANDLERS: dict[str, Any] = {
    "skill_chain": _exec_skill_chain,
}
