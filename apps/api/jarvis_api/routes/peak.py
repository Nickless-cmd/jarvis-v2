"""Myldretids-tilstand til desk-headerens badge (30/9-2026).

Ét lille læse-endpoint: ``GET /peak/state``. Det fortæller klienten hvor
myldretiden er lige nu, hvornår næste vindue åbner, og hvor længe der er
tilbage — så desk-badgen kan tælle ned LOKALT (hvert sekund) uden at polle
hvert sekund.

Vinduet er defineret ÉT sted: ``MYLDRE_VINDUER`` i
:mod:`core.services.llm_pricing`, læst gennem :mod:`core.services.peak_hours`.
Klienten får færdige tal og skal ikke selv kende UTC-reglerne — en badge der
regner i lokal tid ville være forkert halvdelen af året (vinduet åbner 08:00
dansk om sommeren, 07:00 om vinteren).

Self-safe: enhver fejl i peak-laget giver ``in_peak: false`` frem for en 500.
En header-badge må aldrig kunne vælte desk-appen.
"""
from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.get("/peak/state")
def peak_state_endpoint() -> dict:
    """Myldretids-tilstanden lige nu — grundlaget for desk-badgen."""
    try:
        from core.services.peak_hours import peak_state

        st = peak_state()
        return {
            "ok": True,
            "in_peak": bool(st.get("in_peak")),
            "now_danish": st.get("now_danish"),
            "peak_starts_danish": st.get("peak_starts_danish"),
            "peak_ends_danish": st.get("peak_ends_danish"),
            "minutes_left": st.get("minutes_left"),
            "next_peak_danish": st.get("next_peak_danish"),
            "minutes_until_next": st.get("minutes_until_next"),
        }
    except Exception as exc:  # badge må ikke kunne vælte desk-appen
        return {
            "ok": False,
            "in_peak": False,
            "error": type(exc).__name__,
        }
