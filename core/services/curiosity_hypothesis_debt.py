"""Active curiosity with hypothesis debt."""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.runtime.db import get_runtime_state_value, set_runtime_state_value

_STATE_KEY = "curiosity_hypothesis_debt"
_MAX_ITEMS = 60


def register_hypothesis_debt(
    *,
    hypothesis: str,
    why_it_matters: str,
    resolving_observation: str,
    source: str = "",
    priority: str = "medium",
) -> dict[str, object]:
    now = datetime.now(UTC).isoformat()
    item = {
        "debt_id": f"chd-{uuid4().hex[:12]}",
        "hypothesis": str(hypothesis)[:240],
        "why_it_matters": str(why_it_matters)[:240],
        "resolving_observation": str(resolving_observation)[:240],
        "source": str(source)[:120],
        "priority": str(priority or "medium"),
        "status": "open",
        "created_at": now,
        "updated_at": now,
    }
    state = _load()
    state["items"] = [item, *list(state.get("items") or [])][:_MAX_ITEMS]
    state["updated_at"] = now
    _save(state)
    event_bus.publish(
        "cognitive_state.curiosity_hypothesis_debt_registered",
        {"debt_id": item["debt_id"], "priority": item["priority"], "hypothesis": item["hypothesis"]},
    )
    # LivingNeuron Fase A: egress-fri liveness (kun metadata — prioritet + antal åbne, ALDRIG hypotese-teksten).
    try:
        from core.services.central_core import central as _central
        _central().observe({"cluster": "cognition", "nerve": "curiosity_debt",
                            "priority": item["priority"], "open_count": len(state.get("items") or [])})
    except Exception:
        pass
    return item


def maybe_register_from_text(*, text: str, source: str = "") -> dict[str, object] | None:
    lower = str(text or "").lower()
    if "hvad hvis" in lower or "could" in lower or "hypot" in lower:
        return register_hypothesis_debt(
            hypothesis=str(text)[:180],
            why_it_matters="Unresolved counterfactual may change future policy.",
            resolving_observation="Run a small test, ask the user, or compare future outcome.",
            source=source,
            priority="medium",
        )
    if "agi" in lower or "perception" in lower or "learning" in lower:
        return register_hypothesis_debt(
            hypothesis=str(text)[:180],
            why_it_matters="Research thread may reveal a missing cognitive capability.",
            resolving_observation="Observe whether the new primitive changes next-run behavior.",
            source=source,
            priority="high",
        )
    return None


def build_curiosity_debt_surface(*, limit: int = 5) -> dict[str, object]:
    items = [item for item in list(_load().get("items") or []) if item.get("status") == "open"]
    if not items:
        return {"active": False, "summary": "No active hypothesis debt", "items": [], "directive": ""}
    selected = items[: max(int(limit), 1)]
    return {
        "active": True,
        "summary": f"{len(items)} open hypothesis debts; top={selected[0].get('hypothesis')}",
        "items": selected,
        "directive": f"Keep top hypothesis in view until resolving observation: {selected[0].get('resolving_observation')}",
    }


def build_curiosity_debt_prompt_section() -> str | None:
    surface = build_curiosity_debt_surface(limit=3)
    if not surface.get("active"):
        return None
    lines = ["Curiosity hypothesis debt:"]
    lines.append(f"- directive: {str(surface.get('directive') or '')[:140]}")
    for item in list(surface.get("items") or [])[:2]:
        lines.append(f"- {item.get('priority')}: {str(item.get('hypothesis') or '')[:100]}")
    return "\n".join(lines)


def _load() -> dict[str, Any]:
    raw = get_runtime_state_value(_STATE_KEY, {})
    return raw if isinstance(raw, dict) else {}


def _save(state: dict[str, Any]) -> None:
    set_runtime_state_value(_STATE_KEY, state, updated_at=str(state.get("updated_at") or datetime.now(UTC).isoformat()))
