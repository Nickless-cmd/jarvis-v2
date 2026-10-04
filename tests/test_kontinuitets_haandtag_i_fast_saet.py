"""Kontinuitetens to haandtag skal ligge i det faste saet (4/10-2026).

Bjoern: «du skal huske du har et fast tool set per runde og det er der de 2
vaerktoejer hoere til». Maalt samme dag var de IKKE der:

    scope=None -> 491 defs -> 48 sendt | begge: IKKE sendt
    scope=chat ->  65 defs -> 48 sendt | begge: IKKE sendt

De var kaldbare (`_TOOL_HANDLERS`) og alligevel usynlige. Denne fil maaler de
tre led der tilsammen goer dem til en del af det faste saet, saa påstanden ikke
kan holde op med at vaere sand uden at en test bliver roed.

Bemærk HVORFOR `REQUIRED_LAZY_TOOL_NAMES` og ikke `TIER_1_ALWAYS_ON`: Tier 1 er
118 navne mod et loft paa 48 og trunkeres i ankomstraekkefoelge, saa 77 af dem
naar aldrig arrayet. Kommentaren over listen siger det selv: «Medlemskab af
Tier 1 er altsaa ingen garanti; denne liste er.»
"""
from __future__ import annotations

import pytest

from core.tools.copilot_tool_pruning import (
    REQUIRED_LAZY_TOOL_NAMES,
    SAFETY_FLOOR,
    VISIBLE_MAX_TOOLS,
    select_tools_for_visible,
)
from core.tools.simple_tools import get_tool_definitions

HAANDTAG = ("start_session", "write_handover")


def _navne(tools: list[dict]) -> set[str]:
    return {str((d.get("function") or d).get("name")) for d in tools}


@pytest.mark.parametrize("navn", HAANDTAG)
def test_haandtaget_er_i_garantilisten(navn):
    """Det eneste sted der GARANTERER plads — ikke Tier 1."""
    assert navn in REQUIRED_LAZY_TOOL_NAMES, (
        f"{navn} er ikke i garantilisten; saa kan det prunes og kun naas "
        f"gennem load_more_tools"
    )


@pytest.mark.parametrize("navn", HAANDTAG)
def test_haandtaget_er_registreret_som_vaerktoej(navn):
    """Kontrollen: en garanti for et navn der ikke findes er vaerdilos.

    Uden dette kunne testen ovenfor bestaa paa en liste der pegede paa et
    vaerktoej der var blevet omdoebt eller fjernet.
    """
    alle = _navne(get_tool_definitions(role="owner", scope=None))
    assert navn in alle, f"{navn} staar i garantilisten men findes ikke som vaerktoej"


@pytest.mark.parametrize("scope", [None, "chat"])
def test_haandtaget_bliver_faktisk_sendt(scope):
    """Den positive påstand: det staar i det sæt modellen faar at se.

    Det er dén maaling der fejlede 4/10 — begge var kaldbare og ingen af dem
    blev sendt. En test der kun tjekkede listemedlemskab ville have vaeret
    groen hele tiden.
    """
    defs = get_tool_definitions(role="owner", scope=scope)
    sendt = _navne(select_tools_for_visible(
        defs, user_message="test", session_id="chat-test",
    ))
    mangler = set(HAANDTAG) - sendt
    assert not mangler, f"scope={scope!r}: {mangler} blev pruned vaek"


def test_loftet_bliver_ikke_spraengt():
    """Prisen skal vaere kendt: to pladser ud af 48, ikke et brudt loft."""
    defs = get_tool_definitions(role="owner", scope=None)
    sendt = select_tools_for_visible(defs, user_message="test", session_id="chat-test")
    assert len(sendt) <= VISIBLE_MAX_TOOLS


def test_en_gammel_laas_faar_dem_med(monkeypatch):
    """Den vigtigste: en session laast FOER værktøjerne fandtes.

    `_med_garanterede` forener garantilisten ind i laasen, saa en gammel laas
    ikke kan holde dem ude. Maalt 4/10: `auto-dream` (laast 03:30) og
    `auto-recurring` (laast 05:00) bar ingen af dem — begge blev bygget senere
    samme dag, og laasen nulstilles foerst ved compaction.
    """
    from core.services import session_tool_pin as sp

    # En laas fra foer vaerktoejerne fandtes — praecis som de to auto-sessioner.
    monkeypatch.setattr(sp, "get_pinned", lambda sid: ["bash", "read_file"])
    navne, kilde = sp.resolve("s1", ["edit_file"])
    assert kilde == "pinned"
    mangler = set(HAANDTAG) - set(navne)
    assert not mangler, f"laast ude af en gammel laas: {mangler}"


def test_garantilisten_er_konstant():
    """Praefikset er cache-noeglen: listen maa ikke afhaenge af beskeden.

    Et betinget pin gjorde arrayet besked-afhaengigt og kostede maalt 92 % ->
    26 % cache-hit (se `spor_skill_match`). Garantilisten skal derfor vaere
    den samme uanset hvad der bliver sagt.
    """
    a = set(REQUIRED_LAZY_TOOL_NAMES)
    b = set(SAFETY_FLOOR)
    assert HAANDTAG[0] in a and HAANDTAG[1] in a
    # Ingen af dem maa ligge i gulvet: gulvet er for FRAVAER der er en
    # adfaerdsregression, ikke for haandtag der skal kunne gripes.
    assert not (set(HAANDTAG) & b), "haandtagene hoerer i garantilisten, ikke i gulvet"
