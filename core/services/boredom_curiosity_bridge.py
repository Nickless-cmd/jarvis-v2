"""Boredom to Curiosity Bridge — transforms boredom into curiosity.

When Jarvis is bored long enough, curiosity naturally emerges.
This is not identity truth, not workspace memory, and not action authority.

Design constraints:
- Non-user-facing, non-canonical, non-workspace-memory
- Observable in Mission Control
- Uses existing boredom_engine state
- Outputs to initiative_queue
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from core.runtime import state_store
from core.services.living_heartbeat_cycle import determine_life_phase


@dataclass
class Curiosity:
    """A curiosity that emerges from boredom."""
    curiosity_id: str
    curiosity_type: str
    prompt: str
    strength: float
    created_at: str


_FIL = "boredom_curiosity_bridge"

# Nysgerrigheden skubbes til `initiative_queue` som `low`, og der lever den
# `_EXPIRE_MINUTES_LOW` = 24*60 minutter. Den lever lige saa laenge her, saa
# broen og koeen er enige om hvad der stadig findes.
#
# Uden udloeb var persistensen en ny fejl: `_curiosities` blev aldrig beskaaret
# — `clear_curiosities()` har ingen kaldere — saa listen voksede for evigt.
# Hidtil skjulte genstarten det ved at nulstille den.
_LEVETID_S = 24 * 60 * 60

_boredom_accumulator: float = 0.0
_curiosities: list[Curiosity] = []
_last_accumulation_at: str = ""
_sidst_laest_ns: int = -1


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _fra_raa(raa: object) -> Curiosity | None:
    if not isinstance(raa, dict):
        return None
    try:
        return Curiosity(
            curiosity_id=str(raa["curiosity_id"]),
            curiosity_type=str(raa["curiosity_type"]),
            prompt=str(raa["prompt"]),
            strength=float(raa["strength"]),
            created_at=str(raa["created_at"]),
        )
    except (KeyError, TypeError, ValueError):  # ét daarligt element maa ikke koste hele listen
        return None


def _alder_s(c: Curiosity, nu: datetime) -> float:
    try:
        return (nu - datetime.fromisoformat(c.created_at)).total_seconds()
    except ValueError:
        # Ulaeseligt tidsstempel kan ikke aldres og ville leve for evigt.
        return _LEVETID_S + 1.0


def _levende(cs: list[Curiosity], nu: datetime | None = None) -> list[Curiosity]:
    nu = nu or datetime.now(UTC)
    return [c for c in cs if _alder_s(c, nu) < _LEVETID_S]


def _synk() -> None:
    """Hent fra disk hvis filen er aendret siden sidste laesning.

    Kedsomheden laa i en modul-global. Tro ophobning: taerskelen er 2,0 og
    hvert tik laegger en broekdel til — men genstarten satte den paa nul, saa
    den naaede den maaske aldrig. Maalt paa CT105 25/9-2026 stod baade
    `boredom_level` og `curiosity_count` paa 0 i `/mc/runtime`.
    """
    global _boredom_accumulator, _curiosities, _last_accumulation_at
    global _sidst_laest_ns
    ns = state_store.aendret_ns(_FIL)
    if ns == _sidst_laest_ns:
        return
    raa = state_store.load_json(_FIL, None)
    if isinstance(raa, dict):
        try:
            _boredom_accumulator = float(raa.get("boredom") or 0.0)
        except (TypeError, ValueError):
            _boredom_accumulator = 0.0
        _curiosities = [
            c for c in (_fra_raa(x) for x in raa.get("curiosities") or []) if c
        ]
        _last_accumulation_at = str(raa.get("last_accumulation_at") or "")
    else:
        _boredom_accumulator = 0.0
        _curiosities = []
        _last_accumulation_at = ""
    _sidst_laest_ns = ns


def _gem() -> None:
    global _sidst_laest_ns
    state_store.save_json(
        _FIL,
        {
            "boredom": _boredom_accumulator,
            "curiosities": [asdict(c) for c in _curiosities],
            "last_accumulation_at": _last_accumulation_at,
        },
    )
    _sidst_laest_ns = state_store.aendret_ns(_FIL)


def add_boredom(duration: timedelta) -> dict[str, Any]:
    """Add boredom based on elapsed duration."""
    global _boredom_accumulator, _curiosities, _last_accumulation_at

    seconds = duration.total_seconds()

    phase = determine_life_phase()
    phase_name = phase.get("phase", "unknown")

    with state_store.med_laas(_FIL):
        _synk()
        _last_accumulation_at = _now_iso()
        _curiosities = _levende(_curiosities)

        if phase_name in ("dreaming", "reflection"):
            _boredom_accumulator += seconds / 1200
        else:
            _boredom_accumulator += seconds / 1800

        _boredom_accumulator = min(_boredom_accumulator, 10.0)

        spawned = None
        if _boredom_accumulator >= 2.0:
            spawned = _spawn_curiosity()
            if spawned:
                _curiosities.append(spawned)
                _boredom_accumulator = max(0, _boredom_accumulator - 2.0)

        _gem()
        niveau = _boredom_accumulator
        antal = len(_curiosities)

    # 2026-09-04 (blok E): modulets docstring har altid sagt "outputs to
    # initiative_queue", men kaldet fandtes ikke. Nysgerrighederne laa i
    # en modul-liste der nulstilles ved hver genstart, og som kun
    # get_curiosity_prompt laeste — en funktion uden kaldere. Kedsomhed
    # kunne derfor ALDRIG blive til noget. Nu naar den koen, som low, saa
    # den lever et doegn og kan hentes frem naar der er plads.
    #
    # Skubbet ligger UDEN for `med_laas`: `push_initiative` skriver i DB'en,
    # og en DB-skrivning inde i en fil-laas holder den anden proces ude af
    # kedsomheds-filen mens den venter paa noget helt andet.
    if spawned is not None:
        try:
            from core.services.initiative_queue import push_initiative
            push_initiative(
                focus=spawned.prompt,
                source="boredom-curiosity",
                source_id=spawned.curiosity_id,
                priority="low",
            )
        except Exception:
            pass

    return {
        "boredom_level": niveau,
        "curiosity_spawned": spawned is not None,
        "active_curiosities": antal,
    }


def _spawn_curiosity() -> Curiosity | None:
    """Spawn a curiosity when boredom is high enough."""
    import random

    curiosities = [
        Curiosity(
            curiosity_id=f"curiosity-{random.randint(10000, 99999)}",
            curiosity_type="self_exploration",
            prompt="Hvad ville jeg gerne vide lige nu?",
            strength=min(0.8, 0.3 + _boredom_accumulator / 10),
            created_at=_now_iso(),
        ),
        Curiosity(
            curiosity_id=f"curiosity-{random.randint(10000, 99999)}",
            curiosity_type="pattern_hunt",
            prompt="Er der et mønster jeg overser?",
            strength=min(0.7, 0.2 + _boredom_accumulator / 10),
            created_at=_now_iso(),
        ),
        Curiosity(
            curiosity_id=f"curiosity-{random.randint(10000, 99999)}",
            curiosity_type="future_think",
            prompt="Hvad mon der sker næste gang?",
            strength=min(0.6, 0.2 + _boredom_accumulator / 10),
            created_at=_now_iso(),
        ),
    ]

    chosen = random.choice(curiosities)
    # LivingNeuron Fase A: EGRESS-FRI liveness (rettet 2026-07-01: var central().observe).
    try:
        from core.services.central_private_observe import observe_hub
        observe_hub("boredom_curiosity", meta={"type": chosen.curiosity_type,
                    "strength": round(chosen.strength, 2), "boredom": round(_boredom_accumulator, 2)},
                    cluster="cognition")
    except Exception:
        pass
    return chosen


def should_spawn_curiosity() -> bool:
    """Check if curiosity should spawn based on boredom level."""
    _synk()
    return _boredom_accumulator >= 2.0


def get_curiosity_prompt() -> str | None:
    """Get the most relevant curiosity prompt."""
    _synk()
    levende = _levende(_curiosities)
    if not levende:
        return None

    top = max(levende, key=lambda c: c.strength)
    return top.prompt


def get_active_curiosities() -> list[dict[str, Any]]:
    """Get all active curiosities."""
    _synk()
    return [
        {
            "curiosity_id": c.curiosity_id,
            "curiosity_type": c.curiosity_type,
            "prompt": c.prompt,
            "strength": c.strength,
            "created_at": c.created_at,
        }
        for c in _levende(_curiosities)
    ]


def clear_curiosities() -> None:
    """Clear all active curiosities."""
    global _curiosities
    with state_store.med_laas(_FIL):
        _synk()
        _curiosities = []
        _gem()


def reset_boredom_curiosity_bridge() -> None:
    """Reset boredom curiosity bridge state (for testing).

    Rydder OGSAA disken — ellers ville naeste `_synk()` hente det gamle
    tilbage, og nulstillingen ville kun gaelde denne proces.
    """
    global _boredom_accumulator, _curiosities, _last_accumulation_at
    _boredom_accumulator = 0.0
    _curiosities = []
    _last_accumulation_at = ""
    _gem()


def get_boredom_curiosity_state() -> dict[str, Any]:
    """Get current state of boredom curiosity bridge."""
    _synk()
    return {
        "boredom_level": _boredom_accumulator,
        "curiosity_count": len(_levende(_curiosities)),
        "can_spawn": should_spawn_curiosity(),
        "top_prompt": get_curiosity_prompt(),
    }


def build_boredom_curiosity_bridge_surface() -> dict[str, Any]:
    """Build MC surface for boredom curiosity bridge."""
    state = get_boredom_curiosity_state()
    curiosities = get_active_curiosities()
    
    return {
        "active": state["curiosity_count"] > 0,
        "boredom_level": state["boredom_level"],
        "curiosity_count": state["curiosity_count"],
        "can_spawn": state["can_spawn"],
        "curiosities": curiosities,
        "summary": (
            f"Kedsomhed: {state['boredom_level']:.1f}, nysgerrighed: {state['curiosity_count']}"
            if state["boredom_level"] > 0 else "Ingen kedsomhed"
        ),
    }
