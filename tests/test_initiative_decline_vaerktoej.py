"""`decline_initiative` skal være NÅELIG fra værktøjsfladen, ikke kun en service-funktion.

MAALT 23/11-2026: `initiatives_prompt_section` instruerede modellen: «afvis den med
`decline_initiative(id, reason=...)`». Funktionen fandtes i `initiative_queue.py` og
var testet — men der var INGEN definition, INGEN handler og ingen oppost i mappingen.
Instruktionen pegede altså på et værktøj der ikke kunne kaldes, og posten blev
liggende som `pending` indtil `_expire_stale` tavst fjernede den.

Det er samme fejlform som decline-fixet i agent-kontrakten: skrivevejen fandtes,
indgangen manglede. Testene her fælder hvis bindingen forsvinder igen — og den
første fanger selve grunden: at prompten ikke må nævne et værktøj der ikke findes.
"""
from __future__ import annotations

import re


def _definition(name: str) -> dict | None:
    from core.tools.simple_tools_definitions import TOOL_DEFINITIONS

    return next(
        (
            d
            for d in TOOL_DEFINITIONS
            if isinstance(d, dict) and d.get("function", {}).get("name") == name
        ),
        None,
    )


def test_decline_initiative_er_i_vaerktoejsfladen() -> None:
    """Uden en definition kan modellen ikke se værktøjet — så bliver den aldrig kaldt."""
    d = _definition("decline_initiative")
    assert d is not None, "decline_initiative mangler i TOOL_DEFINITIONS"
    params = d["function"]["parameters"]
    assert params["required"] == ["initiative_id", "reason"]
    assert "initiative_id" in params["properties"]
    assert "reason" in params["properties"]


def test_decline_initiative_har_en_handler() -> None:
    """En definition uden handler er et løfte runtime ikke kan indfri."""
    from core.tools.simple_tools import _TOOL_HANDLERS

    assert "decline_initiative" in _TOOL_HANDLERS


def test_prompt_linjen_peger_paa_et_vaerktoej_der_findes(isolated_runtime) -> None:
    """Den vagt der fanger fejlen fra 23/11: prompten må ikke nævne et ukendt værktøj.

    `initiatives_prompt_section` skriver værktøjsnavne i backticks som
    ``navn(...)``. Hvert sådant navn SKAL findes i fladen — ellers instruerer vi
    modellen i noget den ikke kan gøre, og posten bliver liggende uden grund.
    """
    from core.services import initiative_queue
    from core.tools.simple_tools_definitions import TOOL_DEFINITIONS

    initiative_queue.push_initiative(
        focus="En post der tvinger prompt-sektionen til at blive genereret",
        source="jarvis-tool",
        priority="high",
    )
    section = initiative_queue.initiatives_prompt_section()
    assert section, "prompt-sektionen blev ikke genereret trods en pending post"

    kendte = {
        d["function"]["name"]
        for d in TOOL_DEFINITIONS
        if isinstance(d, dict) and "function" in d
    }
    naevnte = set(re.findall(r"`([a-z_][a-z0-9_]+)\(", section))
    assert naevnte, "prompt-sektionen nævner ingen værktøjer — så er vagten blind"
    ukendte = naevnte - kendte
    assert not ukendte, f"prompten nævner værktøjer der ikke findes i fladen: {sorted(ukendte)}"


def test_vaerktoejet_afviser_og_bevarer_samtykke(isolated_runtime) -> None:
    """Kernen: afvisningen må ALDRIG ligne et samtykke.

    `reject_initiative` skriver `user_approved_at` — det er ejerens beslutning.
    Jarvis' egen afvisning må ikke røre det felt, ellers står der et samtykke
    Bjørn aldrig gav.
    """
    from core.runtime import db_runtime_initiatives as rdb
    from core.services import initiative_queue
    from core.tools.simple_tools import _TOOL_HANDLERS

    initiative_id = initiative_queue.push_initiative(
        focus="En post hvis præmis er væk",
        source="jarvis-tool",
        priority="low",
    )
    foer = rdb.get_runtime_initiative(initiative_id)
    assert foer["status"] == "pending"
    assert foer["user_approved_at"] == ""

    svar = _TOOL_HANDLERS["decline_initiative"](
        {"initiative_id": initiative_id, "reason": "Præmissen findes ikke længere."}
    )
    assert svar["status"] == "ok"

    efter = rdb.get_runtime_initiative(initiative_id)
    assert efter["status"] == "declined"
    assert efter["disposition"] == "declined"
    assert efter["disposition_reason"] == "Præmissen findes ikke længere."
    assert efter["user_approved_at"] == "", "afvisningen skrev et samtykke der aldrig blev givet"


def test_tom_grund_afvises() -> None:
    """En afvisning uden grund kan ikke efterprøves — den skal nægtes, ikke gemmes tom."""
    from core.tools.simple_tools import _TOOL_HANDLERS

    svar = _TOOL_HANDLERS["decline_initiative"](
        {"initiative_id": "init-hvad-som-helst", "reason": "   "}
    )
    assert svar["status"] == "error"
    assert "reason" in svar["error"]


def test_ukendt_id_svarer_aerligt(isolated_runtime) -> None:
    """`decline_initiative` svarer False for en post der ikke er pending — det må ikke
    ligne en succes, for så tror modellen at posten er lukket."""
    from core.tools.simple_tools import _TOOL_HANDLERS

    svar = _TOOL_HANDLERS["decline_initiative"](
        {"initiative_id": "init-findes-ikke", "reason": "test"}
    )
    assert svar["status"] == "error"
    assert "pending" in svar["error"]
