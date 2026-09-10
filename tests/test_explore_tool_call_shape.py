"""`tool_calls` betyder TO ting — og explore laeste den forkerte.

Jarvis' fjerde koersel. Agenten gjorde alt rigtigt: rotationen skiftede model,
mistral kaldte tre aegte vaerktoejer og laeste filen. Og saa crashede kaldet:

    [Tool explore error: int() argument must be a string, a bytes-like
     object or a real number, not 'list']

AARSAGEN. `tool_calls` er et TAL i koerslens `output_payload_json` (loekkens
taelling) og en LISTE i agent-fladen (`enrich_agent_surface`), hvor tallet
hedder `tool_call_count`. Explore faar fladen og laeste navnet med payloadens
betydning.

DET HAVDE LIGGET DER HELE TIDEN og aldrig fejlet, fordi `[] or 0` er 0 — saa
laenge listen var TOM. To fixes samme dag gjorde den ikke-tom: bogfoeringen
fyldte den, og rotationen soergede for at der var noget at bogfoere.

Jo bedre agenten opfoerte sig, jo sikrere crashede det. Og fejlen blev fanget
af explores egen `except` og returneret som `status: error`, saa hverken
svaret eller dommen naaede frem — agenten havde laest filen KORREKT.
"""
from __future__ import annotations

import inspect


def _tael(result: dict) -> int:
    """Samme udtryk som i `_exec_explore`, isoleret."""
    raa = result.get("tool_call_count")
    if raa is None:
        raa = result.get("tool_calls")
    return len(raa) if isinstance(raa, (list, tuple, set)) else int(raa or 0)


def test_begge_betydninger_giver_samme_tal():
    assert _tael({"tool_calls": [1, 2, 3]}) == 3        # agent-fladen
    assert _tael({"tool_call_count": 3}) == 3           # fladen, taellingen
    assert _tael({"tool_calls": 3}) == 3                # koerslens payload
    assert _tael({}) == 0


def test_explore_laeser_efter_FORM_ikke_efter_navn():
    """Et navn der er aerligt i to sammenhaenge og loegnagtigt i den tredje
    maa ikke afgoeres af hvilken vej svaret kom."""
    from core.tools import simple_tools_explore as e

    kilde = inspect.getsource(e._exec_explore)
    assert 'result.get("tool_call_count")' in kilde, (
        "explore laeser stadig kun det tvetydige navn")
    assert "isinstance(_raa, (list, tuple, set))" in kilde, (
        "der laeses efter navn, ikke efter form — en liste vil kaste igen")
    assert 'int(result.get("tool_calls") or 0)' not in kilde


def test_en_TOM_liste_er_nul_ikke_et_crash():
    """Det var praecis derfor fejlen laa skjult: en tom liste opfoerte sig som
    nul, saa fejlen ventede paa den dag agenten begyndte at arbejde."""
    assert _tael({"tool_calls": []}) == 0


# ── noten skal foelge DOMMEN, ikke taellingen ───────────────────────────
#
# Foer forgrenede `bevis_note` kun paa `kontrolleret == 0`, saa
# `kun-eksistens` — hvor INTET indhold er bekraeftet — sagde «5 paastand(e)
# slaaet op og BEKRAEFTET». Noten lovede praecis det dommen netop siger vi
# ikke gjorde: to felter om samme sag, der kunne sige hver sit.

def test_noten_modsiger_ikke_dommen():
    from core.tools.simple_tools_explore import _bevis_note

    kun = _bevis_note("kun-eksistens", 5, 0)
    assert "bekraeftet" not in kun.lower() or "INTET" in kun, kun
    assert "ikke verificeret" in kun.lower()

    ver = _bevis_note("verificeret", 5, 3)
    assert "3" in ver and "bekraeftet" in ver.lower()

    assert "ikke bekraeftes" in _bevis_note("uenig", 5, 1).lower()
    assert "Ingen efterproevelig" in _bevis_note("intet-bevis", 0, 0)


def test_hver_dom_har_sin_EGEN_note():
    from core.tools.simple_tools_explore import _bevis_note

    noter = {_bevis_note(b, 5, 1) for b in
             ("verificeret", "kun-eksistens", "uenig", "intet-bevis")}
    assert len(noter) == 4, "to domme deler samme note — saa siger den intet"
