"""Kerne-værktøjs-kataloget — det Jarvis læser når han spørger sig selv «hvad kan jeg».

Filen advarer selv: «Navnene SKAL matche de faktisk registrerede tool-navne,
ellers skjules de stille.» Intet tjekkede det. Nu gør noget.

MÅLT 6/9-2026: `explore` var bygget, testet, registreret, synlig i alle scopes
OG nævnt i en awareness-vejledning — og blev stadig ikke brugt. Bedt om at finde
SSRF-værnet lavede han 13 bash-kald, 6 søgninger og 4 fil-læsninger. Grunden stod
i kataloget: det sagde read_file/search/find_files/bash, altså præcis det han
gjorde, og nævnte aldrig alternativet.
"""
from __future__ import annotations

from core.services.tool_catalog import _CORE_TOOL_GROUPS
from core.tools.simple_tools import _TOOL_HANDLERS


def _alle_navne():
    return [t for _gruppe, tools in _CORE_TOOL_GROUPS for t in tools]


def test_hvert_navn_i_kataloget_er_registreret():
    """Et navn uden en handler skjules stille — værktøjet ser ud til at findes
    og gør det ikke. Filen har advaret om det i månedsvis uden at nogen tjekkede."""
    ukendte = [t for t in _alle_navne() if t not in _TOOL_HANDLERS]
    assert not ukendte, f"i kataloget men ikke registreret: {ukendte}"


def test_ingen_dubletter():
    navne = _alle_navne()
    dubletter = {t for t in navne if navne.count(t) > 1}
    assert not dubletter, f"nævnt flere gange: {dubletter}"


def test_explore_staar_foerst_under_filer_og_kode():
    """Rækkefølgen er budskabet: når han tænker «jeg skal finde noget i koden»,
    skal alternativet til at læse alt selv stå først."""
    gruppe = dict(_CORE_TOOL_GROUPS)["Filer & kode"]
    assert gruppe[0] == "scout_agent"  # omdøbt fra explore 17/9-2026


def test_de_nye_operator_vaerktoejer_er_med():
    """Bygget 5-6/9 og skjult af samme grund som explore: de stod ikke her."""
    operator = dict(_CORE_TOOL_GROUPS)["Operator (din egen maskine/desktop)"]
    for t in ("operator_multi_edit", "operator_run_in_background",
              "operator_bash_output", "operator_kill_shell", "operator_edit_file"):
        assert t in operator, f"{t} mangler i kerne-kataloget"


def test_todo_vaerktoejerne_er_i_kataloget():
    """De fandtes med service, fem tools OG en prompt-sektion der siger «max ÉN
    må være ▶» — men var usynlige i alle scopes og fraværende her. Prompten
    mindede ham om en evne han ikke kunne nå; det er værre end at mangle den."""
    navne = _alle_navne()
    for t in ("todo_list", "todo_add", "todo_update_status"):
        assert t in navne


def test_todos_er_synlige_i_begge_modes():
    from core.tools.simple_tools import get_tool_definitions
    from core.tools.tool_scoping import current_tool_scope, set_tool_scope
    foer = current_tool_scope()
    try:
        for scope in ("chat", "code"):
            set_tool_scope(scope)
            n = {t["function"]["name"] for t in get_tool_definitions()
                 if isinstance(t, dict) and t.get("function")}
            assert "todo_add" in n, f"todos usynlige i {scope}"
    finally:
        # Scope er en ContextVar — laekker den, ser NAESTE test en beskidt
        # tilstand. Fanget af test_context_manager_sets_and_resets.
        set_tool_scope(foer or "")


def test_prompt_sektionen_og_vaerktoejerne_haenger_sammen():
    """Sektionen lover noget; værktøjerne skal kunne indfri det. Driver de fra
    hinanden, peger prompten på en evne der ikke findes."""
    import inspect

    from core.services import agent_todos
    assert "Aktive todos" in inspect.getsource(agent_todos)
    from core.tools.simple_tools import _TOOL_HANDLERS
    assert "todo_add" in _TOOL_HANDLERS


def test_spawn_agent_task_staar_i_inventaret():
    """Den dyreste tool-definition skal staa dér hvor han faktisk kigger.

    Maalt 23/9-2026: `spawn_agent_task` fyldte 581 tokens i HVER runde — mere
    end `bash` — fordi REQUIRED_LAZY_TOOL_NAMES pinnede den ind i selve
    tool-arrayet. Men den stod ikke i inventaret, og blev kaldt NUL gange fra
    en samtale, mens `scout_agent` (303 tok) blev brugt 46 gange.

    Han greb den laesende fordi det var den han kunne se. Filens egen
    kommentar siger det: inventaret er loeftestangen, ikke mere instruks-tekst.

    Falder den ud af inventaret igen, betaler vi ~8.700 tokens i en lang tur
    for en evne ingen kan finde — og det sker TAVST.
    """
    gruppe = dict(_CORE_TOOL_GROUPS)["Filer & kode"]
    assert "spawn_agent_task" in gruppe
    # Lige efter scout, saa forskellen kan ses paa stedet: scout LAESER,
    # spawn HANDLER.
    assert gruppe.index("spawn_agent_task") == gruppe.index("scout_agent") + 1


# ── Kataloget skal sige «se efter i dine egne defs foerst» (30/9-2026) ───────
#
# Maalt over 30 dage: 541 hentede vaerktoejsnavne, ~80 (15 %) for vaerktoejer
# der ALLEREDE laa i turens native function-defs — `notify_user` 20 gange,
# `recall_memories` 19. Kataloget naevnte dem uden at skelne, og modellen
# krydstjekkede ikke sit eget array.
#
# Det koster ingen cache (merge'n springer dem over), men en runde hver gang.

def test_kataloget_beder_om_et_krydstjek_foerst():
    from core.services.tool_catalog import build_catalog_text

    tekst = build_catalog_text()
    assert "SE FØRST EFTER I DINE EGNE function-defs" in tekst, (
        "katalogets krydstjek-linje er væk — saa hentes kerne-vaerktoejer igen")
    # Kontrollen: pegepinden til load_more_tools skal BLIVE. Uden den kan de
    # ~320 oevrige ikke findes overhovedet.
    assert "load_more_tools" in tekst


def test_kataloget_naevner_stadig_vaerktoejer():
    """Uden den kunne testen ovenfor bestaa paa et katalog der kun er en
    instruktion — og saa kan han ikke finde noget som helst."""
    from core.services.tool_catalog import build_catalog_text

    tekst = build_catalog_text()
    assert len(tekst) > 1000, len(tekst)
    assert "KERNE-VÆRKTØJER" in tekst


def test_kataloget_laerer_ham_BEGGE_trin():
    """Hentning er to trin, og kataloget er det sted han slaar op FOER han
    henter.

    Hentningens eget resultat peger paa `call_loaded_tool`, og dispatcherens
    beskrivelse siger det — men begge kommer foerst naar han ALLEREDE har
    hentet. Kataloget naevnte kun `load_more_tools`, altsaa halvdelen af flowet.

    Et hentet vaerktoej kan ikke kaldes direkte: det staar ikke i hans
    function-def-liste, og DeepSeek afviser et vaerktoej der ikke er
    deklareret (maalt mod deres API 30/9-2026).
    """
    from core.services.tool_catalog import build_catalog_text

    tekst = build_catalog_text()
    assert "load_more_tools" in tekst, "trin 1 mangler"
    assert "call_loaded_tool" in tekst, "trin 2 mangler — han laerer kun halvdelen"


def test_nudgen_naevner_ogsaa_andet_trin():
    """Samme halve flow stod i nudge-teksterne der peger paa et hentet vaerktoej."""
    from pathlib import Path

    kilde = Path("core/services/tool_hunt_nudge.py").read_text(encoding="utf-8")
    for stump in kilde.split("hent den med `load_more_tools`")[1:]:
        assert "call_loaded_tool" in stump[:120], (
            "en nudge siger «hent den» uden at sige hvordan den kaldes bagefter")
