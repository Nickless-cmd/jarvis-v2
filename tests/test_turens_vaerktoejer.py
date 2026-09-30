"""Ét værktøjssæt for hele turen — begge trin ser det samme.

Målt 30/9-2026: første pas havde 48 værktøjer, de agentiske runder ~119, og
sættene var ikke indlejrede — 77 kunne kun kaldes i runderne, 6 kun i første
pas (heriblandt `read_tool_result`, som læser resultater fra andre værktøjer og
manglede i de runder hvor resultater læses). 95 % af alle ture har mere end én
runde, så den lille første kasse tvang en omvej i næsten alle ture.
"""
from __future__ import annotations

import types

import core.tools.copilot_tool_pruning as ctp
from core.services.session_tool_pin import clear, get_pinned, resolve
from core.services.turens_vaerktoejer import vaerktoejer_for_turen
from core.tools.simple_tools import get_tool_definitions


def _navne(defs) -> set[str]:
    return {(d.get("function") or d).get("name") for d in defs}


def test_begge_trin_faar_SAMME_saet():
    alle = get_tool_definitions()
    kendte = _navne(alle) | {"call_loaded_tool"}
    clear("tv-forening")
    try:
        foerste = _navne(vaerktoejer_for_turen(
            alle, user_message="hej", session_id="tv-forening"))
        agentisk = {n for n in resolve("tv-forening", list(get_pinned("tv-forening")))[0]
                    if n in kendte}
        assert foerste == agentisk, (
            f"kun i foerste pas: {sorted(foerste - agentisk)[:6]}; "
            f"kun i runderne: {sorted(agentisk - foerste)[:6]}")
    finally:
        clear("tv-forening")


def test_foreningen_gaar_mod_ROUTEREN_ikke_mod_de_48():
    """RETNINGEN er hele pointen. Gik den omvendt, satte foerste pas laasen til
    sine 48, og saa fik de agentiske runder ogsaa kun 48 i stedet for ~119 — en
    tavs kapabilitets-nedskaering."""
    clear("tv-retning")
    try:
        egne = _navne(ctp.select_tools_for_visible(
            get_tool_definitions(), user_message="hej", session_id=None))
        vaerktoejer_for_turen(get_tool_definitions(),
                              user_message="hej", session_id="tv-retning")
        laast = set(get_pinned("tv-retning"))
        assert laast, "laasen blev ikke sat"
        assert laast != egne, (
            "laasen bar foerste pas' eget 48-valg — foreningen gaar forkert vej")
    finally:
        clear("tv-retning")


def test_dispatcheren_overlever_foreningen():
    """`call_loaded_tool` har ingen definition i katalogets liste — pruneren
    injicerer den. Tabte foreningen den, kunne et hentet vaerktoej ikke kaldes."""
    clear("tv-disp")
    try:
        n = _navne(vaerktoejer_for_turen(
            get_tool_definitions(), user_message="hej", session_id="tv-disp"))
        assert "call_loaded_tool" in n
    finally:
        clear("tv-disp")


def test_uden_session_er_adfaerden_UAENDRET():
    """Cache-warmeren kalder uden session. Den maa ikke aendre sig."""
    v = vaerktoejer_for_turen(get_tool_definitions(), user_message="", session_id=None)
    assert len(v) == ctp.VISIBLE_MAX_TOOLS


def test_killswitchen_virker_UDEN_genstart(monkeypatch):
    """`load_settings()` laeser filen ved hvert kald. Uden det var en fejlslagen
    forening kun rettelig med en genstart — og det er praecis naar man har
    mindst brug for det."""
    monkeypatch.setattr("core.runtime.settings.load_settings",
                        lambda: types.SimpleNamespace(visible_tools_unified=False))
    clear("tv-ks")
    try:
        v = vaerktoejer_for_turen(
            get_tool_definitions(), user_message="hej", session_id="tv-ks")
        assert len(v) == ctp.VISIBLE_MAX_TOOLS, "killswitchen slukkede ikke foreningen"
    finally:
        clear("tv-ks")


def test_en_fejl_koster_ikke_turen_dens_vaerktoejer(monkeypatch):
    """Self-sikkerhed: enhver fejl -> prunerens valg. En forening der kaster
    ville braekke hver eneste tur."""
    monkeypatch.setattr("core.services.tool_router.select_tools",
                        lambda **kw: (_ for _ in ()).throw(RuntimeError("nede")))
    clear("tv-fejl")
    try:
        v = vaerktoejer_for_turen(
            get_tool_definitions(), user_message="hej", session_id="tv-fejl")
        assert len(v) == ctp.VISIBLE_MAX_TOOLS
    finally:
        clear("tv-fejl")
