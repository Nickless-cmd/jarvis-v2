"""Active curiosity with hypothesis debt."""
from __future__ import annotations

import re
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
    # LivingNeuron Fase A: EGRESS-FRI liveness (prioritet + antal åbne, ALDRIG hypotese-teksten).
    try:
        from core.services.central_private_observe import observe_hub
        observe_hub("curiosity_debt", meta={"priority": item["priority"],
                    "open_count": len(state.get("items") or [])}, cluster="cognition")
    except Exception:
        pass
    return item


# Korte triggere skal matche som ORD. "agi" som substring rammer inde i almindelige
# ord og gjorde gaeldslisten til stoej; det samme for "could" i sammensaetninger.
_ORD_TRIGGERE = re.compile(r"\b(agi|perception|learning)\b", re.IGNORECASE)
_HYPOTESE_TRIGGERE = re.compile(r"(hvad hvis|\bcould\b|hypot)", re.IGNORECASE)

# En hypotese skal vaere hans EGEN tanke. Er teksten kortere end dette, er der
# ikke noget at forfoelge; er den laengere end det vi gemmer, klippes den.
_MIN_HYPOTESE_CHARS = 25


def maybe_register_from_text(*, text: str, source: str = "") -> dict[str, object] | None:
    """Registrér en aaben hypotese hvis teksten rummer en.

    2026-09-05: to fejl gjorde hele gaeldslisten ubrugelig. Kaldstedet sendte
    `user_message + summary` ind, og vi gemte `text[:180]` — altsaa HOVEDET af
    sammenskrivningen. I droemme-koersler er `user_message` selve droemme-
    prompten, saa hver eneste post blev «Du er i en droemmetilstand — dedikeret,
    uforstyrret tid til at konsolidere…». Triggeren fyrede paa hans egen summary;
    det gemte var teksten han havde faaet udleveret. Fem af fem aabne poster var
    identisk prompt-stoej.

    Og "agi" blev matchet som substring, saa den ramte inde i almindelige ord.
    """
    raw = str(text or "").strip()
    if len(raw) < _MIN_HYPOTESE_CHARS:
        return None
    lower = raw.lower()
    if _HYPOTESE_TRIGGERE.search(lower):
        return register_hypothesis_debt(
            hypothesis=raw[:180],
            why_it_matters="Unresolved counterfactual may change future policy.",
            resolving_observation="Run a small test, ask the user, or compare future outcome.",
            source=source,
            priority="medium",
        )
    if _ORD_TRIGGERE.search(lower):
        return register_hypothesis_debt(
            hypothesis=raw[:180],
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
