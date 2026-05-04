"""Desire/value arbitration as a compact drive system."""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from core.eventbus.bus import event_bus
from core.runtime.db import get_runtime_state_value, set_runtime_state_value

_STATE_KEY = "drive_arbitration_engine"
_DRIVES = ("truth", "care", "autonomy", "continuity", "craft", "caution", "curiosity")


def arbitrate_drives(
    *,
    user_message: str = "",
    context: dict[str, object] | None = None,
) -> dict[str, object]:
    text = str(user_message or "").lower()
    context = context or {}
    scores = {drive: 0.35 for drive in _DRIVES}
    if any(w in text for w in ("agi", "forskn", "research", "ud af boksen")):
        scores["curiosity"] += 0.35
        scores["autonomy"] += 0.2
        scores["truth"] += 0.15
    if any(w in text for w in ("levende", "følel", "synd", "glad", "takker")):
        scores["care"] += 0.35
        scores["continuity"] += 0.2
    if any(w in text for w in ("commit", "tests", "rigtig", "korrekt", "virker")):
        scores["craft"] += 0.3
        scores["truth"] += 0.2
    if any(w in text for w in ("sikker", "pas på", "afbrudt", "timeout", "fejl")):
        scores["caution"] += 0.3
        scores["continuity"] += 0.15
    if str(context.get("outcome_status") or "") == "interrupted":
        scores["continuity"] += 0.35
        scores["caution"] += 0.2
    normalized = {k: round(min(v, 1.0), 3) for k, v in scores.items()}
    top = sorted(normalized.items(), key=lambda item: item[1], reverse=True)[:3]
    policy = _policy_for_top(top)
    result = {
        "active": True,
        "scores": normalized,
        "top_drives": [{"drive": k, "weight": v} for k, v in top],
        "policy": policy,
        "updated_at": datetime.now(UTC).isoformat(),
    }
    set_runtime_state_value(_STATE_KEY, result, updated_at=str(result["updated_at"]))
    event_bus.publish(
        "cognitive_state.drive_arbitrated",
        {"top": [k for k, _ in top], "policy": policy},
    )
    return result


def build_drive_arbitration_surface() -> dict[str, object]:
    raw = get_runtime_state_value(_STATE_KEY, {})
    if isinstance(raw, dict) and raw.get("active"):
        return raw
    return {
        "active": False,
        "scores": {},
        "top_drives": [],
        "policy": "",
        "summary": "No drive arbitration yet",
    }


def build_drive_arbitration_prompt_section() -> str | None:
    surface = build_drive_arbitration_surface()
    if not surface.get("active"):
        return None
    top = ", ".join(
        f"{item.get('drive')}={item.get('weight')}"
        for item in list(surface.get("top_drives") or [])[:3]
    )
    return "\n".join([
        "Drive arbitration:",
        f"- top: {top}",
        f"- policy: {str(surface.get('policy') or '')[:140]}",
    ])


def _policy_for_top(top: list[tuple[str, float]]) -> str:
    drives = [name for name, _ in top]
    if "curiosity" in drives and "truth" in drives:
        return "Explore boldly, but keep claims evidence-grounded and label uncertainty."
    if "care" in drives and "truth" in drives:
        return "Treat relational care and factual rigor as co-primary, not competing."
    if "continuity" in drives and "caution" in drives:
        return "Preserve continuity first; resume/check state before new action."
    if "craft" in drives:
        return "Prefer clean implementation, tests, and commits over broad speculation."
    if "autonomy" in drives:
        return "Support autonomous progress while keeping the next action explicit."
    return "Balance drives and choose the lowest-regret next action."
