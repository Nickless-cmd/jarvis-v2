"""Selvmodellets runtime-flade: rollen en producent får på skærmen.

Fladen oversætter cadence-status til en rolle. Oversættelsen har en
default — og en default er præcis dér en ny status forsvinder uden at
nogen opdager det.
"""
from __future__ import annotations

import core.services.runtime_self_model_surfaces as S


def _roller(cadence_status: str) -> str:
    """Kør fladen med én producent i den givne status og hent dens rolle."""
    import core.services.internal_cadence as ic

    tidligere = ic.get_cadence_state

    def _falsk() -> dict[str, object]:
        return {"producers": [{"name": "snegl",
                               "last_tick_status": {"status": cadence_status}}]}

    ic.get_cadence_state = _falsk  # type: ignore[assignment]
    try:
        lag = S._producer_layers()
    finally:
        ic.get_cadence_state = tidligere  # type: ignore[assignment]
    return str((lag or [{}])[0].get("role") or "")


def test_en_producent_hvis_forrige_koersel_stadig_koerer_vises_som_AKTIV():
    """`i_flugt` betyder at tråden fra sidste tik stadig arbejder.

    Uden en linje i `role_map` faldt den til default «idle». Den halve time
    26/9-2026 hvor Bjørns vært gik fra 35 til 73 grader — fordi 26 forladte
    producent-tråde kørte samtidig — ville fladen have vist ro.
    """
    assert _roller("i_flugt") == "active"


def test_de_oevrige_statusser_er_uaendrede():
    assert _roller("ran") == "active"
    assert _roller("cooling_down") == "cooling"
    assert _roller("visible_grace") == "idle"
    assert _roller("error") == "idle"


def test_en_ukendt_status_falder_stadig_til_idle():
    # Defaulten skal blive — den er rigtig for det ukendte. Den var bare
    # forkert for `i_flugt`.
    assert _roller("noget-helt-nyt") == "idle"
