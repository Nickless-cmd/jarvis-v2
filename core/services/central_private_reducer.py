"""Privat-reducer for Centralens owner-surfacing (§24.4 private-layer invariant).

De private lag (inner voice, self-review, self-model, chronicle, council, dreams,
boredom/companionship) må ALDRIG række rå indhold ud til owneren. Centralen skal
kunne surface *liveness*, *tællere/magnituder* og *governance-konsekvens* — altså
HVAD det private signal fik Centralen til at beslutte — men aldrig selve det rå,
private indhold (fokus-tekst, tool-planer, memory-præcedenser, traces).

`reduce_for_owner` er den delte tragt som alle self/inner-life-endpoints kører
deres output igennem. Den er:
  - EKSPLICIT: returnerer KUN de nøgler der er nævnt i `keep` OG findes i surfacen.
  - HÅRD: en fast blokliste af rå private content-felter droppes ALTID, også hvis
    de (fejlagtigt) står i `keep`. Blokliste vinder over keep.
  - SELF-SAFE: non-dict input eller enhver fejl → `{}`. Kaster aldrig.

Samme ånd som ``visible_inner_life.build_somatic_snapshot``: overfladen viser at
noget lever og med hvilken intensitet — ikke hvad det tænker.
"""

from __future__ import annotations

from typing import Any


# Rå private content-felter der ALDRIG må nå owneren, uanset `keep`.
# Fritekst-/rå-indhold: selve tanken, planen, præcedensen, traces.
_ALWAYS_DROP: frozenset[str] = frozenset({
    "recent_traces",
    "current_focus",
    "current_tool_plan",
    "memory_precedents",
    "raw",
    "content",
    "text",
    "full",
    # yderligere åbenlyse fritekst-content-felter
    "body",
    "prompt",
    "thought",
    "thoughts",
    "narrative",
    "detail",
    "details",
    "message",
    "notes",
    "note",
    "transcript",
})


def reduce_for_owner(surface: Any, *, keep: tuple[str, ...]) -> dict:
    """Reducér en (privat) surface til kun owner-sikre meta-felter.

    Returnerer en NY dict med KUN de nøgler i ``keep`` der findes i ``surface`` og
    som ikke står på den altid-droppede blokliste. Non-dict input eller enhver
    fejl → ``{}``. Kaster aldrig (self-safe).

    Args:
        surface: producent-overfladen (forventet dict; alt andet → {}).
        keep: nøgler der ØNSKES beholdt (fx "liveness", "trace_count",
            "governance_consequence"). Blokliste-nøgler droppes selv hvis nævnt.

    Returns:
        Ny dict med kun de tilladte keep-nøgler.
    """
    try:
        if not isinstance(surface, dict):
            return {}
        out: dict = {}
        for k in keep:
            if k in _ALWAYS_DROP:
                continue
            if k in surface:
                out[k] = surface[k]
        return out
    except Exception:
        return {}
