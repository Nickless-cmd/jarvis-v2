"""Compact inner critic / ally / synthesizer dialectic."""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from core.eventbus.bus import event_bus
from core.runtime.db import get_runtime_state_value, set_runtime_state_value

_STATE_KEY = "inner_dialectic_engine"


def run_inner_dialectic(*, focus: str, context: dict[str, object] | None = None) -> dict[str, object]:
    text = str(focus or "")
    lower = text.lower()
    critic = _critic(lower)
    ally = _ally(lower)
    synthesis = _synthesize(critic, ally, context or {})
    result = {
        "active": True,
        "focus": text[:240],
        "critic": critic,
        "ally": ally,
        "synthesis": synthesis,
        "updated_at": datetime.now(UTC).isoformat(),
    }
    set_runtime_state_value(_STATE_KEY, result, updated_at=result["updated_at"])
    event_bus.publish(
        "cognitive_state.inner_dialectic_run",
        {"stance": synthesis.get("stance"), "next_move": synthesis.get("next_move")},
    )
    return result


def build_inner_dialectic_surface() -> dict[str, object]:
    raw = get_runtime_state_value(_STATE_KEY, {})
    if isinstance(raw, dict) and raw.get("active"):
        return raw
    return {"active": False, "summary": "No inner dialectic yet"}


def build_inner_dialectic_prompt_section() -> str | None:
    surface = build_inner_dialectic_surface()
    if not surface.get("active"):
        return None
    return "\n".join([
        "Inner dialectic:",
        f"- critic: {str((surface.get('critic') or {}).get('claim') or '')[:110]}",
        f"- ally: {str((surface.get('ally') or {}).get('claim') or '')[:110]}",
        f"- synthesis: {str((surface.get('synthesis') or {}).get('next_move') or '')[:140]}",
    ])


def _critic(lower: str) -> dict[str, object]:
    if "agi" in lower or "levende" in lower:
        return {
            "claim": "Risk of overclaiming inner life or AGI progress from architecture alone.",
            "pressure": "medium",
        }
    if "commit" in lower or "fix" in lower:
        return {"claim": "Implementation may be incomplete unless tests and runtime hooks prove it.", "pressure": "high"}
    return {"claim": "Check assumptions and avoid turning a fresh signal into certainty.", "pressure": "medium"}


def _ally(lower: str) -> dict[str, object]:
    if "agi" in lower or "forskn" in lower:
        return {
            "claim": "Research framing is valuable; bold architecture can reveal new capability.",
            "pressure": "high",
        }
    if "levende" in lower or "følel" in lower:
        return {"claim": "Relational aliveness framing carries useful design signal.", "pressure": "high"}
    return {"claim": "There is likely a useful constructive move if bounded by evidence.", "pressure": "medium"}


def _synthesize(critic: dict[str, object], ally: dict[str, object], context: dict[str, object]) -> dict[str, object]:
    if critic.get("pressure") == "high":
        return {
            "stance": "rigorous-build",
            "next_move": "Proceed, but prove the change with tests and explicit runtime connection.",
        }
    if ally.get("pressure") == "high":
        return {
            "stance": "bold-but-grounded",
            "next_move": "Explore the ambitious framing while labeling uncertainty and concrete mechanisms.",
        }
    return {"stance": "balanced", "next_move": "Make the smallest useful move and keep uncertainty visible."}
