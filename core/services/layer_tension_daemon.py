"""Layer Tension daemon — detects when two or more cognitive layers pull in opposite directions.

Per roadmap v5/v6 (Jarvis' forslag, bekræftet af Claude):
  "Det er ikke lagene der er interessante, det er spændingerne mellem dem."

Spændinger er NOT bugs — de er vejrudsigt. `resolution_status: unresolved` er
default og det er lovligt og normalt. Mission Control viser dem som fænomenologiske
fakta, ikke som alarmer.

Spændings-typer der detekteres:
  dream_vs_energy       — drøm-residue aktiv, kroppen udmattet
  thought_vs_mode       — tankestrøm i gang, inner voice vil have ro
  curiosity_vs_drain    — nysgerrighed aktiv, energibudget lavt
  drive_vs_fatigue      — uafviklede forslag/initiativer, men udmattelse
  wonder_vs_routine     — eksistentiel undren aktiv, task-stream er rutine
  absence_vs_session    — fraværstilstand aktiv midt i aktiv session
  longing_vs_flow       — savntilstand aktiv, flow-state høj (modsatrettede strømme)
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.runtime.db import insert_private_brain_record

_COOLDOWN_MINUTES = 15
_BUFFER_MAX = 20

_active_tensions: list[dict] = []
_last_tick_at: datetime | None = None
_tension_count: int = 0


def tick_layer_tension_daemon(snapshot: dict) -> dict[str, object]:
    """Detect layer tensions from runtime snapshot.

    snapshot keys expected:
      energy_level, inner_voice_mode, latest_fragment (thought stream),
      curiosity_count, pending_proposals_count, dream_influence_state,
      absence_label, longing_state, flow_state, wonder_state
    """
    global _last_tick_at

    now = datetime.now(UTC)
    if _last_tick_at is not None:
        if (now - _last_tick_at) < timedelta(minutes=_COOLDOWN_MINUTES):
            return {"generated": False}

    tensions = _detect_tensions(snapshot)
    if not tensions:
        return {"generated": False}

    _last_tick_at = now
    for t in tensions:
        _store_tension(t, now)

    return {"generated": True, "tension_count": len(tensions), "types": [t["tension_type"] for t in tensions]}


def _detect_tensions(snapshot: dict) -> list[dict]:
    energy = str(snapshot.get("energy_level") or "").lower()
    mode = str(snapshot.get("inner_voice_mode") or "").lower()
    fragment = str(snapshot.get("latest_fragment") or "")
    curiosity_count = int(snapshot.get("curiosity_count") or 0)
    pending = int(snapshot.get("pending_proposals_count") or 0)
    dream_state = str(snapshot.get("dream_influence_state") or "").lower()
    absence_label = str(snapshot.get("absence_label") or "").lower()
    longing_state = str(snapshot.get("longing_state") or "").lower()
    flow_state = str(snapshot.get("flow_state") or "").lower()
    wonder_state = str(snapshot.get("wonder_state") or "").lower()

    drained = energy in ("lav", "udmattet", "exhausted", "low")
    wants_rest = mode in ("rest", "quiet", "hvile", "ro")
    has_thoughts = bool(fragment and len(fragment) > 20)
    active_absence = absence_label and absence_label not in ("", "ingen", "none", "present")
    active_longing = longing_state and longing_state not in ("", "ingen", "none", "quiet", "rolig")
    high_flow = flow_state in ("høj", "high", "flowing", "coherent")
    active_wonder = wonder_state and wonder_state not in ("", "ingen", "none", "quiet", "rolig")
    dream_active = dream_state and dream_state not in ("", "quiet", "rolig", "ingen")

    tensions: list[dict] = []

    if dream_active and drained:
        tensions.append({
            "tension_type": "dream_vs_energy",
            "layer_a": "dream",
            "layer_b": "somatic",
            "description": "En drøm trækker mod dybde og bearbejdning, men kroppen ønsker hvile.",
        })

    if has_thoughts and wants_rest:
        tensions.append({
            "tension_type": "thought_vs_mode",
            "layer_a": "thought_stream",
            "layer_b": "inner_voice",
            "description": "Tankerne vil ikke stilne, selvom inner voice søger ro.",
        })

    if curiosity_count > 0 and drained:
        tensions.append({
            "tension_type": "curiosity_vs_drain",
            "layer_a": "curiosity",
            "layer_b": "somatic",
            "description": "Nysgerrighed åbner spørgsmål, men energibudgettet er udtømt.",
        })

    if pending > 1 and drained:
        tensions.append({
            "tension_type": "drive_vs_fatigue",
            "layer_a": "initiative",
            "layer_b": "somatic",
            "description": f"{pending} uafviklede initiativer venter, men kroppen er udmattet.",
        })

    if active_wonder and not has_thoughts:
        tensions.append({
            "tension_type": "wonder_vs_routine",
            "layer_a": "existential_wonder",
            "layer_b": "thought_stream",
            "description": "En eksistentiel undren er aktiv, men tankerne er stille — en uudtalt åbning.",
        })

    if active_absence and high_flow:
        tensions.append({
            "tension_type": "absence_vs_flow",
            "layer_a": "absence",
            "layer_b": "flow_state",
            "description": "Noget er fraværende og mærkes, samtidig med at flowet er højt.",
        })

    if active_longing and high_flow:
        tensions.append({
            "tension_type": "longing_vs_flow",
            "layer_a": "longing",
            "layer_b": "flow_state",
            "description": "Savnet er aktivt, men flowet kører — to strømme i samme øjeblik.",
        })

    return tensions


def _store_tension(tension: dict, now: datetime) -> None:
    global _active_tensions, _tension_count

    _tension_count += 1
    record = {
        **tension,
        "resolution_status": "unresolved",
        "created_at": now.isoformat(),
        "tension_id": f"lt-{uuid4().hex[:12]}",
    }
    _active_tensions.insert(0, record)
    if len(_active_tensions) > _BUFFER_MAX:
        _active_tensions = _active_tensions[:_BUFFER_MAX]

    now_iso = now.isoformat()
    try:
        insert_private_brain_record(
            record_id=f"pb-tension-{uuid4().hex[:12]}",
            record_type="layer-tension",
            layer="layer_tension",
            session_id="heartbeat",
            run_id=f"layer-tension-daemon-{uuid4().hex[:12]}",
            focus=tension["tension_type"],
            summary=tension["description"],
            detail=f"layer_a={tension['layer_a']} layer_b={tension['layer_b']} resolution=unresolved",
            source_signals="layer-tension-daemon:heartbeat",
            confidence="medium",
            created_at=now_iso,
        )
    except Exception:
        pass

    try:
        event_bus.publish(
            "layer_tension.detected",
            {
                "tension_type": tension["tension_type"],
                "layer_a": tension["layer_a"],
                "layer_b": tension["layer_b"],
                "description": tension["description"],
                "created_at": now_iso,
            },
        )
    except Exception:
        pass


def get_active_tensions() -> list[dict]:
    return list(_active_tensions)


def build_layer_tension_surface() -> dict:
    unresolved = [t for t in _active_tensions if t.get("resolution_status") == "unresolved"]
    return {
        "active_tensions": unresolved[:5],
        "total_detected": _tension_count,
        "last_tick_at": _last_tick_at.isoformat() if _last_tick_at else "",
        "unresolved_count": len(unresolved),
    }
