"""`call_loaded_tool` er en transport — og den må ALDRIG skjule det ægte navn.

Værktøjsarrayet ligger før samtalen i DeepSeeks præfiks, så én ny definition
kasserer historikken. Målt tre gange 30/9-2026: 8.704 tokens mod deres API,
88,0 % → 17,9 % ved katalog-dommen, og 419 tegn → 62.672 miss i produktion.
Dispatcheren gør en hentning til et almindeligt værktøjskald i beskederne, så
arrayet aldrig behøver ændre sig.

Prisen for at gøre det forkert er værre end gevinsten: hver eneste gate nøgles
på navnet i kaldet. Udførte dispatcheren selv — eller pakkede vi ud EFTER
gaten — var den en universel gate-omgåelse for alle ~370 værktøjer.
"""
from __future__ import annotations

import pytest

from core.tools.kaldt_vaerktoej import DEFINITION, KALD_NAVN, pak_ud


def test_almindelige_kald_gaar_uroert_igennem():
    assert pak_ud("read_file", {"path": "/x"}) == ("read_file", {"path": "/x"})
    assert pak_ud("bash", {}) == ("bash", {})


def test_dispatcheren_oversaettes_til_det_aegte_kald():
    assert pak_ud(KALD_NAVN, {"navn": "delete_file", "argumenter": {"path": "/x"}}) == (
        "delete_file", {"path": "/x"})


def test_manglende_argumenter_giver_tomt_objekt_ikke_None():
    """Et vaerktoej uden argumenter skal kaldes med {}, ikke med None."""
    assert pak_ud(KALD_NAVN, {"navn": "todo_list"}) == ("todo_list", {})
    assert pak_ud(KALD_NAVN, {"navn": "todo_list", "argumenter": "ikke-et-objekt"}) == (
        "todo_list", {})


def test_uden_navn_fejler_den_HOEJLYDT():
    """Uden brugbart navn skal dispatcher-navnet blive staaende, saa kaldet
    falder som «ukendt vaerktoej» i stedet for at udfoere ingenting i stilhed."""
    assert pak_ud(KALD_NAVN, {}) == (KALD_NAVN, {})
    assert pak_ud(KALD_NAVN, {"navn": "  "}) == (KALD_NAVN, {"navn": "  "})
    assert pak_ud(KALD_NAVN, {"navn": KALD_NAVN}) == (KALD_NAVN, {"navn": KALD_NAVN})


def test_definitionen_er_konstant_og_uden_levende_tal():
    """Hele pointen: arrayet maa ikke aendre sig. En definition med et tal der
    bevaeger sig ville braekke praefikset praecis som det den skal loese."""
    import json
    a = json.dumps(DEFINITION, sort_keys=True)
    b = json.dumps(DEFINITION, sort_keys=True)
    assert a == b
    assert DEFINITION["function"]["name"] == KALD_NAVN
    assert "navn" in DEFINITION["function"]["parameters"]["required"]


def test_dispatcheren_staar_altid_i_det_synlige_saet():
    """Uden den i arrayet kan modellen ikke kalde den — DeepSeek afviser et
    vaerktoej der ikke er deklareret (maalt mod deres API 30/9-2026)."""
    from core.tools.copilot_tool_pruning import select_tools_for_visible

    valgt = select_tools_for_visible([], user_message="", session_id=None)
    navne = [(d.get("function") or d).get("name") for d in valgt]
    assert KALD_NAVN in navne, navne[:10]
    assert navne.count(KALD_NAVN) == 1, "dispatcheren staar dobbelt"


def test_GATEN_SER_DET_AEGTE_NAVN(monkeypatch):
    """Sikkerhedstesten. Alle gates noegles paa `name`; ser de dispatcherens
    navn, er den en universel omgaaelse for alle vaerktoejer."""
    from core.services import commit_gate_arbiter as cga
    from core.services import simple_tool_executor as ste

    set_navne: list[str] = []

    class _Verdict:
        blocked = True
        reason = "test"
        gate_type = "decision_gate"

    def _fake(*, name, arguments, **kw):
        set_navne.append(name)
        return _Verdict()

    monkeypatch.setattr(cga, "evaluate_commit_gates", _fake)
    ste._prepare_call(
        {"function": {"name": KALD_NAVN,
                      "arguments": {"navn": "delete_file", "argumenter": {"path": "/x"}}}},
        force=False, run_id=None, session_id=None, user_message="",
        controller=None, round_seen=set(),
    )
    assert set_navne == ["delete_file"], (
        f"gaten fik {set_navne!r} — dispatcheren skjuler det aegte navn")


def test_dispatcheren_har_INGEN_executor():
    """Den maa ikke kunne udfoere noget selv. Kan den det, findes der en vej
    udenom udpakningen — og dermed udenom alle gates."""
    from core.tools.simple_tools import _TOOL_HANDLERS  # type: ignore[attr-defined]

    assert KALD_NAVN not in _TOOL_HANDLERS, (
        "dispatcheren har faaet en executor — saa findes der en vej udenom "
        "udpakningen, og dermed udenom alle gates")
    # Kontrollen: registret er ikke bare tomt.
    assert "read_file" in _TOOL_HANDLERS
