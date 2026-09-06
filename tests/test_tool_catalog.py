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
    assert gruppe[0] == "explore"


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
