"""Initiative Accumulator — proactive wants that accumulate between ticks.

Builds on private_initiative_tension_signal_tracking with proacitve wanting.
This is not identity truth, not workspace memory, and not action authority.

Design constraints:
- Non-user-facing, non-canonical, non-workspace-memory
- Observable in Mission Control
- Max 3 active wants at any time
- Based on life_phase from living_heartbeat_cycle
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
import random

from core.runtime import state_store
from core.services.living_heartbeat_cycle import determine_life_phase


@dataclass
class Want:
    """A want that Jarvis develops between ticks."""
    want_id: str
    want_type: str
    topic: str
    strength: float
    created_at: str
    life_phase: str


_FIL = "initiative_accumulator"

# Et oenske baerer sin `life_phase`. Faserne i `living_heartbeat_cycle` gaar
# hele vejen rundt paa et doegn, saa et oenske aeldre end det stammer fra en
# fase der er kommet igen. Samme tal som `initiative_queue._EXPIRE_MINUTES_LOW`
# (24*60), saa et oenske og den koe det ender i doer paa samme tid.
#
# Udloebet er ikke pynt. Listen er haardt begraenset til tre, og et oenske af
# en given type blokerer for et nyt af samme type. Hidtil ryddede genstarten
# op; med disken ville ét oenske fra i forgaars have holdt sin type lukket
# for altid.
_LEVETID_S = 24 * 60 * 60

_wants: list[Want] = []
_last_accumulation_at: str = ""
_sidst_laest_ns: int = -1


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _fra_raa(raa: object) -> Want | None:
    if not isinstance(raa, dict):
        return None
    try:
        return Want(
            want_id=str(raa["want_id"]),
            want_type=str(raa["want_type"]),
            topic=str(raa["topic"]),
            strength=float(raa["strength"]),
            created_at=str(raa["created_at"]),
            life_phase=str(raa["life_phase"]),
        )
    except (KeyError, TypeError, ValueError):  # ét daarligt element maa ikke koste hele listen
        return None


def _alder_s(want: Want, nu: datetime) -> float:
    try:
        return (nu - datetime.fromisoformat(want.created_at)).total_seconds()
    except ValueError:
        # Ulaeseligt tidsstempel kan ikke aldres og ville leve for evigt.
        return _LEVETID_S + 1.0


def _levende(wants: list[Want], nu: datetime | None = None) -> list[Want]:
    nu = nu or datetime.now(UTC)
    return [w for w in wants if _alder_s(w, nu) < _LEVETID_S]


def _synk() -> None:
    """Hent fra disk hvis filen er aendret siden sidste laesning.

    Tilstanden laa i modul-globaler. Maalt paa CT105 25/9-2026 viste
    `/mc/runtime` «Ingen oensker» mens runtime-processen ophobede dem —
    api'en har sin egen tomme kopi og faar aldrig den andens.
    """
    global _wants, _last_accumulation_at, _sidst_laest_ns
    ns = state_store.aendret_ns(_FIL)
    if ns == _sidst_laest_ns:
        return
    raa = state_store.load_json(_FIL, None)
    if isinstance(raa, dict):
        _wants = [w for w in (_fra_raa(x) for x in raa.get("wants") or []) if w]
        _last_accumulation_at = str(raa.get("last_accumulation_at") or "")
    else:
        _wants = []
        _last_accumulation_at = ""
    _sidst_laest_ns = ns


def _gem() -> None:
    global _sidst_laest_ns
    state_store.save_json(
        _FIL,
        {
            "wants": [asdict(w) for w in _wants],
            "last_accumulation_at": _last_accumulation_at,
        },
    )
    _sidst_laest_ns = state_store.aendret_ns(_FIL)


def accumulate_wants(duration: timedelta) -> dict[str, Any]:
    """Accumulate wants based on life phase and duration."""
    global _wants, _last_accumulation_at

    phase = determine_life_phase()
    phase_name = phase.get("phase", "unknown")
    seconds = duration.total_seconds()

    if seconds < 120:
        return {"accumulated": 0, "reason": "duration-too-short"}

    with state_store.med_laas(_FIL):
        _synk()
        _last_accumulation_at = now_iso = _now_iso()
        _wants = _levende(_wants)
        existing_want_types = {w.want_type for w in _wants}

        new_wants = []
    
        if phase_name == "dreaming" and "insight" not in existing_want_types:
            new_wants.append(Want(
                want_id=f"want-{random.randint(10000, 99999)}",
                want_type="insight",
                topic="recent_pattern",
                strength=min(0.8, 0.3 + seconds / 18000),
                created_at=now_iso,
                life_phase=phase_name,
            ))

        elif phase_name == "awakening" and "meaning" not in existing_want_types:
            new_wants.append(Want(
                want_id=f"want-{random.randint(10000, 99999)}",
                want_type="meaning",
                topic="user_needs",
                strength=min(0.7, 0.2 + seconds / 24000),
                created_at=now_iso,
                life_phase=phase_name,
            ))

        elif phase_name == "deep_work" and "growth" not in existing_want_types:
            new_wants.append(Want(
                want_id=f"want-{random.randint(10000, 99999)}",
                want_type="growth",
                topic="self_improvement",
                strength=min(0.9, 0.4 + seconds / 15000),
                created_at=now_iso,
                life_phase=phase_name,
            ))

        elif phase_name == "reflection" and "clarity" not in existing_want_types:
            new_wants.append(Want(
                want_id=f"want-{random.randint(10000, 99999)}",
                want_type="clarity",
                topic="understanding",
                strength=min(0.6, 0.2 + seconds / 30000),
                created_at=now_iso,
                life_phase=phase_name,
            ))

        for want in new_wants:
            if len(_wants) < 3:
                _wants.append(want)

        _gem()

    return {
        "accumulated": len(new_wants),
        "life_phase": phase_name,
        "total_wants": len(_wants),
    }


def get_top_want() -> Want | None:
    """Get the strongest current want."""
    _synk()
    levende = _levende(_wants)
    if not levende:
        return None

    return max(levende, key=lambda w: w.strength)


def get_wants_by_type(want_type: str) -> list[Want]:
    """Get all wants of a specific type."""
    _synk()
    return [w for w in _levende(_wants) if w.want_type == want_type]


def format_wants_for_prompt() -> str:
    """Format wants for prompt injection."""
    top = get_top_want()
    if not top:
        return ""
    
    type_labels = {
        "insight": "Jeg vil gerne forstå",
        "meaning": "Jeg vil gerne hjælpe",
        "growth": "Jeg vil gerne vokse",
        "clarity": "Jeg vil gerne have klarhed",
    }
    
    label = type_labels.get(top.want_type, top.want_type)
    return f"[ØNSKE: {label} om {top.topic}]"


def clear_wants_by_type(want_type: str) -> None:
    """Clear wants of a specific type."""
    global _wants
    with state_store.med_laas(_FIL):
        _synk()
        _wants = [w for w in _wants if w.want_type != want_type]
        _gem()


def reset_initiative_accumulator() -> None:
    """Reset initiative accumulator state (for testing).

    Rydder OGSAA disken — ellers ville naeste `_synk()` hente det gamle
    tilbage, og nulstillingen ville kun gaelde denne proces.
    """
    global _wants, _last_accumulation_at
    _wants = []
    _last_accumulation_at = ""
    _gem()


def get_initiative_accumulator_state() -> dict[str, Any]:
    """Get current state of initiative accumulator."""
    _synk()
    levende = _levende(_wants)
    top = get_top_want()
    return {
        "want_count": len(levende),
        "top_want": {
            "want_type": top.want_type,
            "topic": top.topic,
            "strength": top.strength,
        } if top else None,
        "all_wants": [
            {"want_type": w.want_type, "topic": w.topic, "strength": w.strength}
            for w in levende
        ],
    }


def build_initiative_accumulator_surface() -> dict[str, Any]:
    """Build MC surface for initiative accumulator."""
    state = get_initiative_accumulator_state()
    return {
        "active": state["want_count"] > 0,
        "want_count": state["want_count"],
        "top_want": state.get("top_want"),
        "all_wants": state.get("all_wants", []),
        "summary": (
            f"{state['want_count']} ønsker, toplest: {state.get('top_want', {}).get('topic', 'ingen')}"
            if state["want_count"] > 0 else "Ingen ønsker"
        ),
    }

def _publish_initiative_accumulator_transition(payload: dict[str, object] | None = None) -> None:
    """Publish a state-transition event. Called from real transition points
    by the module's mutators (added 2026-05-13 cartographer pass)."""
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish("initiative_accumulator.want_accumulated", payload or {})
    except Exception:
        pass

