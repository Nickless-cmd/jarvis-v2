"""Koerslens run-id og origin — sat af koerslen selv, ikke gaettet globalt.

15/9-2026: `skill_invoked` stod med tomt run_id paa hans synlige tur, fordi
den eneste kilde (run_closure_gate) kun kender autonome koersler. Hver test
koerer i sin egen kontekst, saa en ContextVar ikke kan lække mellem tests.
"""
from __future__ import annotations

import contextvars

import pytest

import core.services.run_closure_gate as gate
from core.services import run_autonomy_context as A
from core.services import skill_relevance_surface as S
from core.services.session_context_resolve import aktivt_run_id


def _i_ren_kontekst(fn):
    return contextvars.Context().run(fn)


@pytest.fixture(autouse=True)
def _ren_gate():
    gate._set_current_run("")
    gate._set_current_origin("")
    yield
    gate._set_current_run("")
    gate._set_current_origin("")


def test_synlig_tur_faar_sit_run_id_uden_gaten():
    # Praecis situationen fra 16:29: gaten ved intet, koerslen har sat sit id.
    def tur():
        A.set_run_identity("visible-abc", "")
        return aktivt_run_id("")
    assert _i_ren_kontekst(tur) == "visible-abc"


def test_koerslens_id_vinder_over_gatens_globale():
    gate._set_current_run("autonomous-gammel")
    def tur():
        A.set_run_identity("visible-ny", "")
        return aktivt_run_id("")
    assert _i_ren_kontekst(tur) == "visible-ny"


def test_uden_koerselsidentitet_bruges_gaten_stadig():
    gate._set_current_run("autonomous-xyz")
    assert _i_ren_kontekst(lambda: aktivt_run_id("")) == "autonomous-xyz"


def test_to_samtidige_koersler_ser_hver_sit_id():
    def tur(rid):
        A.set_run_identity(rid, "")
        return aktivt_run_id("")
    assert _i_ren_kontekst(lambda: tur("a")) == "a"
    assert _i_ren_kontekst(lambda: tur("b")) == "b"
    # …og ingen af dem har lækket ud hertil.
    assert A.current_run_id() == ""


@pytest.mark.parametrize("origin,undtaget", [
    ("heartbeat", True), ("recurring", True), ("dream", True),
    ("autonomous", False), ("wakeup", False), ("", False),
])
def test_koerslens_origin_afgoer_undtagelsen(origin, undtaget):
    def tur():
        A.set_run_identity("run-1", origin)
        return S._er_selvstartet_tur()
    assert _i_ren_kontekst(tur) is undtaget


def test_brugertur_arver_IKKE_en_tidligere_hjerteslags_origin():
    """Faelden i fallbacken: gaten husker den SENESTE autonome koersel. En tom
    origin paa hans egen tur maa ikke falde igennem til «heartbeat»."""
    gate._set_current_origin("heartbeat")
    def hans_tur():
        A.set_run_identity("visible-bjorn", "")
        return S._er_selvstartet_tur()
    assert _i_ren_kontekst(hans_tur) is False


def test_uden_koerselsidentitet_falder_origin_tilbage_til_gaten():
    gate._set_current_origin("dream")
    assert _i_ren_kontekst(S._er_selvstartet_tur) is True
