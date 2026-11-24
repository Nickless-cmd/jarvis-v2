"""End-to-end: pensionering af personligheds-poster gennem værktøjs-laget.

`retire_mistake` / `retire_strength` fandtes som service-funktioner 24/11-2026,
men **ingen kaldte dem** — den eneste vej til at fjerne en post var dommerens
eget skøn. Disse tests går gennem `_TOOL_HANDLERS`, altså den dispatch-dict
modellen faktisk rammer, og læser listen fra "disken" bagefter.

Det er forskellen på «funktionen virker» og «døren har et håndtag».
"""
from __future__ import annotations

import json

import pytest

from core.tools.simple_tools import _TOOL_HANDLERS
from core.tools.simple_tools_definitions import TOOL_DEFINITIONS


def _fake_db(monkeypatch, mistakes, strengths=None):
    """Samme fixture-form som `test_personality_vector._fake_db`.

    Patcher DB-laget, ikke service-funktionen: handleren skal ramme den ægte
    `retire_mistake`, ellers måler testen sin egen mock.
    """
    import core.services.personality_vector as pv

    state = {
        "row": {
            "recurring_mistakes": json.dumps(mistakes, ensure_ascii=False),
            "strengths_discovered": json.dumps(strengths or [], ensure_ascii=False),
            "current_bearing": "b",
        },
        "writes": 0,
    }

    def _get():
        return dict(state["row"])

    def _upsert(**kw):
        state["row"] = dict(kw)
        state["writes"] += 1
        return {"version": state["writes"]}

    monkeypatch.setattr(pv, "get_latest_cognitive_personality_vector", _get)
    monkeypatch.setattr(pv, "upsert_cognitive_personality_vector", _upsert)
    monkeypatch.setattr(pv.event_bus, "publish", lambda *a, **k: None)
    return state


def _liste(state, felt="recurring_mistakes"):
    return json.loads(state["row"][felt])


# ── koblingen: er værktøjet nåbart? ────────────────────────────────────────

@pytest.mark.parametrize("navn", ["retire_mistake", "retire_strength"])
def test_vaerktoejet_er_i_dispatch_dicten(navn):
    """Annonceret uden handler = «Unknown tool» ved kald. Det skete før."""
    assert navn in _TOOL_HANDLERS


@pytest.mark.parametrize("navn", ["retire_mistake", "retire_strength"])
def test_vaerktoejet_er_annonceret_til_modellen(navn):
    """En handler modellen ikke kan se, bliver aldrig kaldt."""
    navne = [t["function"]["name"] for t in TOOL_DEFINITIONS]
    assert navn in navne


def test_kataloget_naevner_dem():
    """`explore` blev bygget, testet og registreret — og brugt nul gange, fordi
    kerne-kataloget ikke nævnte den. Inventaret skal stemme med virkeligheden."""
    from core.services.tool_catalog import _CORE_TOOL_GROUPS

    navne = [t for _g, tools in _CORE_TOOL_GROUPS for t in tools]
    assert "retire_mistake" in navne and "retire_strength" in navne


# ── den ægte rejse: værktøj → service → skrivning → disk ───────────────────

def test_pension_fjerner_posten_gennem_vaerktoejet(monkeypatch):
    state = _fake_db(monkeypatch, ["falsk post", "ægte post"])

    svar = _TOOL_HANDLERS["retire_mistake"](
        {"post": "falsk post", "bevis": "chat_messages viser at svaret er komplet"}
    )

    assert svar["status"] == "ok"
    # Læst fra disken EFTER skrivningen — ikke fra returværdien.
    assert _liste(state) == ["ægte post"]
    assert state["writes"] == 1


def test_sporet_er_med_i_svaret(monkeypatch):
    """Uden `bevis` og `retired_at` kan pensionen ikke efterprøves bagefter."""
    _fake_db(monkeypatch, ["falsk post"])

    svar = _TOOL_HANDLERS["retire_mistake"](
        {"post": "falsk post", "bevis": "modbevist i chat_messages"}
    )

    assert svar["post"] == "falsk post"
    assert svar["bevis"] == "modbevist i chat_messages"
    assert svar["retired_at"]
    assert svar["remaining"] == 0
    assert svar["field"] == "recurring_mistakes"


def test_ukendt_post_afvises_uden_skrivning(monkeypatch):
    state = _fake_db(monkeypatch, ["falsk post", "ægte post"])

    svar = _TOOL_HANDLERS["retire_mistake"]({"post": "slet ikke til", "bevis": "bevis"})

    assert svar["status"] == "error"
    assert "findes ikke ordret" in svar["error"]
    assert _liste(state) == ["falsk post", "ægte post"]
    assert state["writes"] == 0


@pytest.mark.parametrize("naer", ["falsk pos", "falsk post.", "Falsk post", " falsk post"])
def test_naer_match_afvises_gennem_vaerktoejet(monkeypatch, naer):
    """Et næsten-match er den farligste form: den ser rigtig ud og rammer
    naboposten. Ordret betyder ordret."""
    state = _fake_db(monkeypatch, ["falsk post", "ægte post"])

    svar = _TOOL_HANDLERS["retire_mistake"]({"post": naer, "bevis": "bevis"})

    assert svar["status"] == "error"
    assert state["writes"] == 0


@pytest.mark.parametrize("bevis", ["", "   ", None])
def test_bevis_er_paakraevet(monkeypatch, bevis):
    """En pension uden bevis efterlader ingen grund til at posten forsvandt."""
    state = _fake_db(monkeypatch, ["falsk post"])

    svar = _TOOL_HANDLERS["retire_mistake"]({"post": "falsk post", "bevis": bevis})

    assert svar["status"] == "error"
    assert "bevis" in svar["error"]
    assert state["writes"] == 0


@pytest.mark.parametrize("post", ["", "   ", None])
def test_tom_post_afvises(monkeypatch, post):
    state = _fake_db(monkeypatch, ["falsk post"])

    svar = _TOOL_HANDLERS["retire_mistake"]({"post": post, "bevis": "bevis"})

    assert svar["status"] == "error"
    assert state["writes"] == 0


def test_retire_strength_roerer_ikke_mistakes(monkeypatch):
    """To lister, to værktøjer. En styrke-pension må ikke ramme fejllisten."""
    state = _fake_db(monkeypatch, ["m1", "m2"], ["s1", "s2"])

    svar = _TOOL_HANDLERS["retire_strength"]({"post": "s1", "bevis": "holdt ikke"})

    assert svar["status"] == "ok"
    assert _liste(state, "strengths_discovered") == ["s2"]
    assert _liste(state) == ["m1", "m2"]
