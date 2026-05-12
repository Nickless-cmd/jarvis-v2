"""revise_skill_chain tool — Skill Chain Phase 2 (AGI track #10).

Eksplicit revision-verb for skill_chain. Gyldig i to kontekster:

  - pre_execution: Jarvis modtog et forslag fra propose_skill_chain men
    vil justere kæden før han kører den.
  - mid_chain: Jarvis er midt i at eksekvere en kæde og indser at
    retningen ikke længere passer baseret på intermediate result.

Genbruger Phase 1's `_build_combined_instructions` og
`_validate_plan_existence` direkte fra skill_chain_tool.py. Stateless —
ingen state-machine, ingen chain_id.

See spec: docs/superpowers/specs/2026-05-12-skill-chain-phase2-design.md
"""
from __future__ import annotations

import logging
from typing import Any

from core.runtime.settings import load_settings
from core.tools.skill_chain_tool import (
    _build_combined_instructions,
    _validate_plan_existence,
)

logger = logging.getLogger(__name__)


_MIN_REASON_LEN = 10
_MIN_PLAN_LEN = 2
_MAX_PLAN_LEN = 5
_REASON_PAYLOAD_MAX = 200  # bound on event payload (not on input)
_VALID_CONTEXTS = ("pre_execution", "mid_chain")


def _phase2_enabled() -> bool:
    try:
        return bool(load_settings().skill_chain_phase2_enabled)
    except Exception:
        return True  # fail-open


def _exec_revise_skill_chain(args: dict[str, Any]) -> dict[str, Any]:
    """Tool handler for revise_skill_chain.

    Validates → pre-validates skill existence → builds combined
    instructions → emits event → returns.
    """
    # 1. Killswitch
    if not _phase2_enabled():
        return {
            "status": "disabled",
            "note": "skill_chain_phase2 is disabled in runtime settings",
        }

    # 2. Validate reason
    reason = str(args.get("reason") or "").strip()
    if not reason:
        return {"status": "rejected", "reason": "reason is required"}
    if len(reason) < _MIN_REASON_LEN:
        return {
            "status": "rejected",
            "reason": f"reason must be at least {_MIN_REASON_LEN} chars",
        }

    # 3. Validate revision_context
    revision_context = str(args.get("revision_context") or "").strip()
    if revision_context not in _VALID_CONTEXTS:
        return {
            "status": "rejected",
            "reason": (
                f"revision_context must be one of {_VALID_CONTEXTS}, "
                f"got {revision_context!r}"
            ),
        }

    # 4. Validate new_plan structure
    new_plan = args.get("new_plan")
    if not isinstance(new_plan, list):
        return {"status": "rejected", "reason": "new_plan must be a list"}
    if not all(isinstance(s, str) and s.strip() for s in new_plan):
        return {
            "status": "rejected",
            "reason": "new_plan entries must be non-empty strings",
        }
    normalized = [s.strip() for s in new_plan]
    if len(normalized) < _MIN_PLAN_LEN:
        return {
            "status": "rejected",
            "reason": f"new_plan must have at least {_MIN_PLAN_LEN} skills",
        }
    if len(normalized) > _MAX_PLAN_LEN:
        return {
            "status": "rejected",
            "reason": f"new_plan exceeds max length of {_MAX_PLAN_LEN}",
        }

    # 5. Pre-validate skill existence (alt-eller-intet, mirror Phase 1)
    missing = _validate_plan_existence(normalized)
    if missing:
        return {
            "status": "rejected",
            "reason": "unknown skills in new_plan",
            "missing": missing,
        }

    # 6. Build combined instructions (genbrug Phase 1)
    instructions = _build_combined_instructions(normalized)

    # 7. Emit event
    _publish_revise_event(
        new_plan=normalized,
        reason=reason[:_REASON_PAYLOAD_MAX],
        revision_context=revision_context,
        instructions_length=len(instructions),
    )

    # 8. Return success
    return {
        "status": "ok",
        "new_plan": normalized,
        "revision_context": revision_context,
        "instructions": instructions,
        "instructions_length": len(instructions),
    }


def _publish_revise_event(
    *,
    new_plan: list[str],
    reason: str,
    revision_context: str,
    instructions_length: int,
) -> None:
    """Defensively publish cognitive_skill_chain.revised. Never blocks."""
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish(
            "cognitive_skill_chain.revised",
            {
                "new_plan": new_plan,
                "step_count": len(new_plan),
                "reason": reason,
                "revision_context": revision_context,
                "instructions_length": instructions_length,
            },
        )
    except Exception as exc:
        logger.debug("revise_skill_chain: event publish failed: %s", exc)


REVISE_SKILL_CHAIN_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "revise_skill_chain",
            "description": (
                "Erklær eksplicit at du dropper én kæde til fordel for en "
                "anden. Gyldig i to kontekster: 'pre_execution' (du så et "
                "propose_skill_chain-forslag og vil justere før du kører) "
                "eller 'mid_chain' (du er midt i at eksekvere og indser "
                "at retningen ikke længere passer). Returnerer combined "
                "instructions for den nye plan — samme format som "
                "skill_chain. Stateless: ingen chain_id, ingen state-"
                "machine. Brug dette FREM FOR at kalde skill_chain igen, "
                "så vi får observability på dine revisioner."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {
                        "type": "string",
                        "description": (
                            "Hvorfor reviderer du? 1-2 sætninger om hvad "
                            "der ændrede dig fra den oprindelige kæde. "
                            "Mindst 10 tegn."
                        ),
                    },
                    "new_plan": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "Den nye kæde — 2-5 skill-navne i "
                            "eksekveringsrækkefølge."
                        ),
                    },
                    "revision_context": {
                        "type": "string",
                        "enum": ["pre_execution", "mid_chain"],
                        "description": (
                            "'pre_execution' hvis du dropper et forslag før "
                            "eksekvering. 'mid_chain' hvis du pivoter midt i."
                        ),
                    },
                },
                "required": ["reason", "new_plan", "revision_context"],
            },
        },
    },
]

REVISE_SKILL_CHAIN_TOOL_HANDLERS: dict[str, Any] = {
    "revise_skill_chain": _exec_revise_skill_chain,
}
