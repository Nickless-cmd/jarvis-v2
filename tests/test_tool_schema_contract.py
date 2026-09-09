"""Kanoniske argumenter mod versionerede skemaer — Fase 3, K2.

Maalingen der drev designet: 20.170 aegte kald, 132 aegte brud. 104 blev
allerede afvist hoejlydt af vaerktoejernes egne vagter. 28 fik et 'vellykket'
svar — og den stoerste gruppe dér skrev **14 tomme hukommelsesfiler** og
meldte dem gemt.

Men samme maaling fandt det modsatte: kald hvor SKEMAET var for snaevert og
vaerktoejet havde ret. Derfor skelner kontrakten paa brud-art, og derfor er
den skelnen det vigtigste denne fil vogter.
"""
from __future__ import annotations

import pytest

from core.tools import tool_schema_contract as K


@pytest.fixture(autouse=True)
def _rene():
    K._nulstil_for_tests()
    yield
    K._nulstil_for_tests()


# ── den fejl der kostede 14 tomme filer ──────────────────────────────────

def test_write_memory_topic_uden_body_er_et_HAARDT_brud():
    """Det aegte kald: `content` i stedet for `body`, og ingen `title`.
    Vaerktoejet skrev en tom fil og svarede `confirmed: true` 17 gange."""
    b = K.violations("write_memory_topic", {"slug": "x", "content": "# hej"})
    assert [x.art for x in b] == ["required", "required"]
    assert all(x.haard for x in b)
    assert {"'title' is a required property",
            "'body' is a required property"} == {x.besked for x in b}


def test_et_fuldt_kald_er_rent():
    assert K.violations("write_memory_topic", {
        "slug": "x", "title": "T", "hook": "h", "body": "# hej"}) == []


# ── og den fejl der ville braekke noget der virker ───────────────────────

def test_en_enum_uden_for_listen_er_BLOEDT():
    """`recall_memories` med modalities=['somatic'] gav 10 rigtige resultater:
    koden accepterer enhver streng. Dér er skemaet forkert, ikke kaldet.
    At afvise ville braekke et kald der virker."""
    b = K.violations("recall_memories", {"query": "x", "modalities": ["somatic"]})
    assert b and b[0].art == "enum"
    assert not any(x.haard for x in b)


def test_kun_required_er_haard():
    assert K.HAARDE_ARTER == frozenset({"required"})


# ── runtime-noegler er ikke modellens ────────────────────────────────────

def test_underscore_noegler_taeller_ikke_med():
    """Runtime injicerer `_runtime_session_id` og venner. De staar ikke i noget
    skema — at maale dem ville producere brud ingen har begaaet."""
    rene = K.canonical_arguments("write_file", {
        "path": "/a", "content": "x", "_runtime_session_id": "s", "_session_id": "t"})
    assert rene == {"path": "/a", "content": "x"}
    assert K.violations("write_file", {"path": "/a", "content": "x",
                                       "_runtime_session_id": "s"}) == []


# ── versioneret ──────────────────────────────────────────────────────────

def test_versionen_er_stabil_for_samme_skema():
    assert K.schema_version("write_file") == K.schema_version("write_file")
    assert K.schema_version("write_file").startswith("sha256:")


def test_versionen_aendrer_sig_naar_skemaet_goer():
    """Hele pointen: at kunne se at et skema har flyttet sig under foedderne
    paa en gemt invokation."""
    foer = K.schema_version("write_file")
    K._indlaes()["write_file"] = {"type": "object", "properties": {"andet": {}}}
    K._versioner.clear()
    assert K.schema_version("write_file") != foer


def test_ukendt_vaerktoej_giver_ingen_version_og_ingen_brud():
    assert K.schema_version("findes_ikke") == ""
    assert K.violations("findes_ikke", {"hvad": "som helst"}) == []
    assert K.kendt("findes_ikke") is False


# ── den maa ikke anklage kalderen for husets egen fejl ───────────────────

def test_et_UGYLDIGT_skema_maaler_ingenting(caplog):
    K._indlaes()["daarligt"] = {"type": "det-her-er-ikke-en-type"}
    assert K.violations("daarligt", {"x": 1}) == []


def test_validering_der_kaster_giver_tom_liste(monkeypatch):
    """Et kald maa ikke afvises fordi maaleredskabet gik i stykker."""
    class Sur:
        def iter_errors(self, _):
            raise RuntimeError("i stykker")
    monkeypatch.setitem(K._validatorer, "write_file", Sur())
    assert K.violations("write_file", {}) == []


# ── afvisningen skal kunne bruges af den der kan rette den ───────────────

def test_afvisningen_siger_hvad_der_mangler_og_paa_hvilket_skema():
    b = K.violations("write_memory_topic", {"slug": "x"})
    a = K.afvisning("write_memory_topic", b)
    assert a["status"] == "error"
    assert "title" in a["error"] and "body" in a["error"]
    assert a["schema_version"] == K.schema_version("write_memory_topic")
    assert [v["art"] for v in a["violations"]] == ["required"] * len(b)


# ── dækning: er skemaerne overhovedet der ────────────────────────────────

def test_alle_definitioner_har_et_skema_der_kan_bygges():
    """466 vaerktoejer. Et skema der ikke kan bygges maaler ingenting, tavst."""
    from core.tools.simple_tools_definitions import TOOL_DEFINITIONS
    daarlige = []
    for d in TOOL_DEFINITIONS:
        navn = d["function"]["name"]
        if K._validator(navn) is None:
            daarlige.append(navn)
    assert daarlige == [], f"skemaer der ikke kan bygges: {daarlige[:10]}"
