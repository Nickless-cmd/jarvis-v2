"""Reasoning escalation — compose tier + gate signals into a council recommendation.

R3 of the reasoning-layer rollout. Combines two upstream signals to decide
whether the situation warrants escalation to a council / sub-agent:

- **tier** (from reasoning_classifier): fast / reasoning / deep
- **gate** (from verification_gate): how many mutations are unverified,
  how many verify_* calls failed

Escalation triggers (any of):
  - tier=deep AND any failed verify_* in recent window
  - tier=deep AND ≥3 unverified mutations (claiming work without proof)
  - tier=reasoning AND ≥2 failed verify_* (lots of broken claims)

When triggered, the section names a specific escalation path that
already exists in Jarvis' tool registry:

  - convene_council(topic) — full deliberation across roles
  - spawn_agent_task(role=critic, goal=...) — independent review
  - spawn_agent_task(role=researcher, goal=...) — verification at scale

Adfærds-sikker: surfaces awareness only. Does NOT auto-spawn agents
(would surprise the user, cost tokens, and tie up GPU). The model
decides whether to act on the recommendation.

This is the *thinnest* useful R3 — it makes the deep-tier signal
actionable without changing Jarvis' autonomy. R3.5 / future work could
make escalation auto-trigger for very-high-confidence cases (multiple
failed verifies on production paths), but that's a separate decision.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def _safe_tier(message: str) -> dict[str, Any]:
    try:
        from core.services.reasoning_classifier import classify_reasoning_tier
        return classify_reasoning_tier(message)
    except Exception as exc:
        logger.debug("tier import failed: %s", exc)
        return {"tier": "fast", "score": 0, "signals": []}


def _safe_gate() -> dict[str, Any]:
    try:
        from core.services.verification_gate import evaluate_verification_gate
        return evaluate_verification_gate()
    except Exception as exc:
        logger.debug("gate import failed: %s", exc)
        return {
            "mutation_count": 0,
            "verify_count": 0,
            "failed_verify_count": 0,
            "unverified_count": 0,
            "failed_verifies": [],
        }


def _recommend_path(tier: str, failed: int, unverified: int, signals: list[str]) -> dict[str, Any]:
    """Pick the escalation path that fits the situation."""
    # Heavy verify failures → critic agent for independent review
    if failed >= 2:
        return {
            "path": "spawn_agent_task",
            "role": "critic",
            "reason": (
                f"{failed} verify_* fejlede — bed en critic-agent gennemgå "
                "påstandene uafhængigt før du fortsætter."
            ),
        }
    # Deep tier + risk markers → full council
    risk_markers = [s for s in signals if "destructive" in s or "production" in s or "secrets" in s or "migration" in s]
    if tier == "deep" and risk_markers:
        return {
            "path": "convene_council",
            "topic_hint": "; ".join(risk_markers[:2]),
            "reason": (
                "Deep tier med risikomarkører — convene_council for "
                "deliberation før destruktive skridt."
            ),
        }
    # Lots of unverified mutations → researcher to verify at scale
    if unverified >= 3:
        return {
            "path": "spawn_agent_task",
            "role": "researcher",
            "reason": (
                f"{unverified} mutations uden verify — bed en researcher-agent "
                "gennemgå hvad der faktisk landede."
            ),
        }
    # Deep tier without specific failure pattern → planner for sequencing
    if tier == "deep":
        return {
            "path": "spawn_agent_task",
            "role": "planner",
            "reason": (
                "Deep tier — bed en planner-agent skitsere sekvensering før "
                "udførelse."
            ),
        }
    return {"path": None, "reason": ""}


def evaluate_escalation(message: str = "") -> dict[str, Any]:
    """Compose tier + gate into an escalation recommendation."""
    tier_info = _safe_tier(message)
    gate_info = _safe_gate()

    tier = str(tier_info.get("tier") or "fast")
    failed = int(gate_info.get("failed_verify_count") or 0)
    unverified = int(gate_info.get("unverified_count") or 0)
    signals = list(tier_info.get("signals") or [])

    # Trigger logic
    triggered = False
    triggers: list[str] = []
    if tier == "deep" and failed > 0:
        triggered = True
        triggers.append(f"deep tier + {failed} failed verify(s)")
    if tier == "deep" and unverified >= 3:
        triggered = True
        triggers.append(f"deep tier + {unverified} unverified mutations")
    if tier == "reasoning" and failed >= 2:
        triggered = True
        triggers.append(f"reasoning tier + {failed} failed verify(s)")

    if not triggered:
        return {
            "status": "ok",
            "escalate": False,
            "tier": tier,
            "triggers": [],
            "recommendation": None,
        }

    rec = _recommend_path(tier, failed, unverified, signals)
    return {
        "status": "ok",
        "escalate": True,
        "tier": tier,
        "triggers": triggers,
        "tier_signals": signals[:5],
        "gate": {
            "failed_verifies": failed,
            "unverified_mutations": unverified,
            "mutation_count": gate_info.get("mutation_count", 0),
            "verify_count": gate_info.get("verify_count", 0),
        },
        "recommendation": rec,
    }


def escalation_section(message: str = "") -> str | None:
    """Format escalation recommendation as a prompt-awareness section, or None."""
    result = evaluate_escalation(message)
    if not result.get("escalate"):
        return None
    rec = result.get("recommendation") or {}
    path = rec.get("path")
    if not path:
        return None
    triggers = result.get("triggers") or []
    trigger_text = "; ".join(triggers)
    if path == "convene_council":
        topic_hint = rec.get("topic_hint") or "(skitsér selv et kort topic)"
        action = f"Brug `convene_council(topic=\"{topic_hint}\")`."
    else:
        role = rec.get("role", "critic")
        action = f"Brug `spawn_agent_task(role=\"{role}\", goal=...)` med en konkret opgave."
    return (
        f"🚨 Reasoning-eskalation anbefalet ({trigger_text}).\n"
        f"{rec.get('reason', '')}\n"
        f"{action} Det er stadig dit valg — eskalering er rådgivende, ikke "
        "tvungen."
    )


def _exec_recommend_escalation(args: dict[str, Any]) -> dict[str, Any]:
    return evaluate_escalation(str(args.get("message") or ""))


REASONING_ESCALATION_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "recommend_escalation",
            "description": (
                "Compose reasoning tier + verification gate signals into one "
                "escalation recommendation: should you spawn a critic / "
                "researcher / planner subagent, or convene the council? "
                "Returns escalate=true/false plus a specific path with role "
                "and reason. Advisory — does not auto-spawn anything."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "Optional task/message for tier classification.",
                    },
                },
                "required": [],
            },
        },
    },
]
