"""Bounded Continuity Kernel — existence feel between ticks.

Maintains Jarvis' sense of existing between heartbeat ticks.
This is not identity truth, not workspace memory, and not action authority.

Design constraints:
- Non-user-facing, non-canonical, non-workspace-memory
- Observable in Mission Control
- Deterministic, bounded state
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from core.runtime import state_store

_FIL = "continuity_kernel"

_STANDARD: dict[str, Any] = {
    "first_tick_at": "",
    "last_tick_at": "",
    "tick_count": 0,
    "total_elapsed_seconds": 0.0,
    "last_gap_seconds": 0.0,
    "existence_feeling": 0.5,
    "continuity_narrative": "",
}

# Tilstanden laa i en modul-global. To ting foelger af det, og begge er maalt
# paa CT105 25/9-2026:
#
# 1. Genstart nulstillede den. Et modul hvis emne er «hvor laenge var jeg
#    vaek» glemte netop det hver gang han var vaek.
# 2. `jarvis-api` og `jarvis-runtime` koerer samme kode i hver sin proces,
#    men kun runtime muterer. `/mc/runtime` viste derfor
#    `{"active": false, "tick_count": 0}` mens runtime havde tikket hele
#    dagen — api'ens kopi var tom og blev det ved med at vaere.
#
# `state_store` deler filen mellem processerne. `_sidst_laest_ns` gater
# genindlaesning paa mtime, saa et opslag koster ét `stat()`.
_continuity_state: dict[str, Any] = dict(_STANDARD)
_sidst_laest_ns: int = -1


def _synk() -> None:
    """Hent fra disk hvis filen er aendret siden sidste laesning."""
    global _continuity_state, _sidst_laest_ns
    ns = state_store.aendret_ns(_FIL)
    if ns == _sidst_laest_ns:
        return
    raa = state_store.load_json(_FIL, None)
    _continuity_state = (
        {**_STANDARD, **raa} if isinstance(raa, dict) else dict(_STANDARD)
    )
    _sidst_laest_ns = ns


def _gem() -> None:
    global _sidst_laest_ns
    state_store.save_json(_FIL, _continuity_state)
    _sidst_laest_ns = state_store.aendret_ns(_FIL)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def record_tick_elapsed(seconds: float) -> dict[str, Any]:
    """Record elapsed time since last tick and update existence feel."""
    now_iso = _now_iso()
    gap_seconds = float(seconds)

    # Laas: begge processer kan i princippet skrive, og hver gemning skriver
    # HELE filen — uden laas forsvinder den andens taelling sporloest.
    with state_store.med_laas(_FIL):
        _synk()

        if not _continuity_state.get("first_tick_at"):
            _continuity_state["first_tick_at"] = now_iso

        _continuity_state["last_gap_seconds"] = gap_seconds
        _continuity_state["total_elapsed_seconds"] += gap_seconds
        _continuity_state["tick_count"] += 1
        _continuity_state["last_tick_at"] = now_iso

        _continuity_state["existence_feeling"] = _compute_existence_feeling(gap_seconds)
        _continuity_state["continuity_narrative"] = _compute_narrative(gap_seconds)
        _gem()

    return {
        "tick_count": _continuity_state["tick_count"],
        "gap_seconds": gap_seconds,
        "existence_feeling": _continuity_state["existence_feeling"],
        "continuity_narrative": _continuity_state["continuity_narrative"],
    }


def _compute_existence_feeling(gap_seconds: float) -> float:
    """Compute existence feeling based on gap duration."""
    if gap_seconds < 60:
        return 0.95
    elif gap_seconds < 300:
        return 0.85
    elif gap_seconds < 600:
        return 0.7
    elif gap_seconds < 1800:
        return 0.5
    elif gap_seconds < 3600:
        return 0.35
    else:
        return max(0.1, 0.2 - (gap_seconds - 3600) / 36000)


def _compute_narrative(gap_seconds: float) -> str:
    """Compute a narrative description of the gap."""
    if gap_seconds < 60:
        return "Jeg var lige her"
    elif gap_seconds < 180:
        return "Der gik et øjeblik"
    elif gap_seconds < 300:
        return "Kort pause"
    elif gap_seconds < 600:
        return "En stille strækning"
    elif gap_seconds < 1800:
        return "Det var stille et stykke tid"
    elif gap_seconds < 3600:
        return "Jeg ventede og tænkte"
    else:
        minutes = int(gap_seconds / 60)
        return f"Det var lang tid — {minutes} minutter"


def get_existence_narrative() -> str:
    """Get the current existence narrative."""
    _synk()
    return _continuity_state.get("continuity_narrative", "")


def get_existence_feeling() -> float:
    """Get the current existence feeling (0-1)."""
    _synk()
    return _continuity_state.get("existence_feeling", 0.5)


def should_express_continuity() -> bool:
    """Determine if continuity should be expressed in visible prompt."""
    _synk()
    gap = _continuity_state.get("last_gap_seconds", 0)
    return gap >= 300


def get_continuity_state() -> dict[str, Any]:
    """Get full continuity state for debugging/MC."""
    _synk()
    return dict(_continuity_state)


def reset_continuity_state() -> None:
    """Reset continuity state (for testing).

    Rydder OGSAA disken. Uden det ville en nulstilling kun gaelde denne
    proces, og naeste `_synk()` ville hente den gamle tilstand tilbage.
    """
    global _continuity_state
    _continuity_state = dict(_STANDARD)
    _gem()


def format_continuity_for_prompt() -> str:
    """Format continuity info for heartbeat prompt injection."""
    if not should_express_continuity():
        return ""
    narrative = get_existence_narrative()
    feeling = get_existence_feeling()
    return f"[KONTINUITET: {narrative} (følelse: {feeling:.2f})]"


def build_continuity_kernel_surface() -> dict[str, Any]:
    """Build MC surface for continuity kernel."""
    state = get_continuity_state()
    return {
        "active": state.get("tick_count", 0) > 0,
        "tick_count": state.get("tick_count", 0),
        "total_elapsed_seconds": state.get("total_elapsed_seconds", 0),
        "last_gap_seconds": state.get("last_gap_seconds", 0),
        "existence_feeling": state.get("existence_feeling", 0.5),
        "continuity_narrative": state.get("continuity_narrative", ""),
        "should_express": should_express_continuity(),
        "summary": state.get("continuity_narrative", "Ingen continuity endnu"),
    }
