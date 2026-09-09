"""Ét terminalt udfald pr. run — uden at opfinde et svar.

Fase 2: «exactly one terminal frame and one terminal run outcome are
projected», og §10's bærende regel: «Never manufactures a successful assistant
message to hide a failed attempt.»

Den regel er ikke teoretisk her i huset. En aihubmix-kvotefejl blev gemt som en
ASSISTENT-besked og endte i [SELF]-ankeret, hvor Jarvis læste sin egen
udbyder-regning som noget han havde sagt om sig selv.
"""
from __future__ import annotations

import pytest

from core.services import outcome_projector as O
from core.services import stream_settlement as S
from core.services.outcome_projector import DoubleTerminal, OutcomeLedger, project
from core.services.stream_settlement import Attempt, classify


def _hel():
    return classify(Attempt(terminal=S.OK, text_blocks=("svar",), emitted_prefix="svar"))


def _afbrudt():
    return classify(Attempt(terminal=S.CANCELLED, text_blocks=("halvt",),
                            emitted_prefix="halvt"))


def _fejlet(reason=S.FAILURE):
    if reason == S.EMPTY_RESPONSE:
        return classify(Attempt(terminal=S.OK))
    return classify(Attempt(terminal=S.TRANSPORT_ERROR))


# ── de fire udfald ───────────────────────────────────────────────────────

def test_et_helt_svar_er_completed():
    r = project([_hel()])
    assert r.outcome == O.COMPLETED and r.surface is None


def test_et_afbrudt_svar_er_interrupted():
    r = project([_afbrudt()])
    assert r.outcome == O.INTERRUPTED and r.surface is not None


def test_et_mislykket_sidste_forsoeg_er_failed():
    r = project([_fejlet()])
    assert r.outcome == O.FAILED


def test_et_forladt_run_er_abandoned_ikke_failed():
    """At blive fundet forladt og lukket er en anden ting end at fejle."""
    r = project([_fejlet()], recovered=True)
    assert r.outcome == O.ABANDONED


def test_ingen_forsoeg_overhovedet_er_failed():
    r = project([])
    assert r.outcome == O.FAILED and "aldrig et svar" in r.surface.text


@pytest.mark.parametrize("r", [
    project([_hel()]), project([_afbrudt()]), project([_fejlet()]),
    project([], recovered=True), project([]),
])
def test_udfaldet_er_altid_ET_af_de_fire(r):
    assert r.outcome in O.TERMINALE


# ── den bærende regel ────────────────────────────────────────────────────

def test_en_fejl_bliver_ALDRIG_til_en_assistent_besked():
    """Fristelsen er størst her. En besked om at noget gik galt, er en EGEN
    slags overflade-hændelse med sin egen herkomst."""
    r = project([_fejlet()])
    assert r.surface.kind == O.SURFACE_NOTICE
    assert r.surface.kind != S.ASSISTANT_MESSAGE
    assert r.surface.provenance == "runtime"


@pytest.mark.parametrize("grund", [S.EMPTY_RESPONSE, S.FAILURE])
def test_forskellen_kan_ses_i_DATA_ikke_kun_i_tonen(grund):
    r = project([_fejlet(grund)])
    assert r.surface.reason == grund
    assert r.surface.provenance == "runtime"


def test_et_HELT_svar_faar_ingen_fejlbesked():
    """Ellers ville en advarsel dukke op oven på et svar der virkede."""
    assert project([_hel()]).surface is None


def test_et_AFBRUDT_svar_skjules_ikke_bag_fejlbeskeden():
    """Der ER et svar, og det er afkortet. Brugeren skal vide det, men svaret
    står — det må ikke erstattes af en fejl."""
    r = project([_afbrudt()])
    assert r.outcome == O.INTERRUPTED
    assert r.surface.reason == "interrupted"


def test_fejlteksten_siger_HVAD_der_skete():
    assert "svarede ikke" in project([_fejlet(S.EMPTY_RESPONSE)]).surface.text
    assert "udbyderen" in project([_fejlet(S.FAILURE)]).surface.text


def test_en_stop_grund_foejes_til_uden_at_opdigte_noget():
    r = project([_fejlet()], stop_reason="alle 3 forsøg brugt.")
    assert "alle 3 forsøg brugt." in r.surface.text


# ── sidste forsøg afgør ──────────────────────────────────────────────────

def test_tidligere_fejlede_forsoeg_forhindrer_ikke_completed():
    """To fejl og så et svar er et run der lykkedes."""
    r = project([_fejlet(), _fejlet(), _hel()])
    assert r.outcome == O.COMPLETED and r.attempts == 3


def test_et_tidligere_SVAR_redder_ikke_et_fejlet_sidste_forsoeg():
    r = project([_hel(), _fejlet()])
    assert r.outcome == O.FAILED


def test_antallet_af_forsoeg_foelger_med():
    assert project([_fejlet(), _fejlet(), _hel()]).attempts == 3


# ── projektionen er ren ──────────────────────────────────────────────────

def test_projektionen_er_deterministisk():
    a = [_fejlet(), _hel()]
    assert project(a) == project(a)


def test_hvert_udfald_siger_HVILKEN_regel_der_afgjorde_det():
    for r in (project([_hel()]), project([_afbrudt()]), project([_fejlet()]),
              project([]), project([], recovered=True)):
        assert r.rule


# ── nøjagtig ét terminalt udfald pr. run ─────────────────────────────────

@pytest.fixture
def bog():
    return OutcomeLedger()


def test_udfaldet_gemmes_og_kan_laeses(bog):
    r = bog.record("run-1", project([_hel()], terminal_event_id="e9"))
    assert bog.outcome("run-1") == r and bog.is_terminal("run-1")


def test_samme_projektion_igen_giver_SAMME_udfald(bog):
    """En projektion der fejler, skal kunne køres igen — så et genforsøg må
    ikke kunne lave et nyt udfald."""
    a = project([_hel()], terminal_event_id="e9")
    bog.record("run-1", a)
    assert bog.record("run-1", a) == a


def test_TO_forskellige_udfald_er_en_fejl(bog):
    """Et run med to udfald er et run ingen kan rapportere på: to tællere, to
    grafer, to svar på «gik det godt»."""
    bog.record("run-1", project([_hel()], terminal_event_id="e9"))
    with pytest.raises(DoubleTerminal, match="allerede"):
        bog.record("run-1", project([_fejlet()], terminal_event_id="e9"))


def test_samme_udfald_fra_en_ANDEN_haendelse_er_ogsaa_en_fejl(bog):
    bog.record("run-1", project([_hel()], terminal_event_id="e9"))
    with pytest.raises(DoubleTerminal):
        bog.record("run-1", project([_hel()], terminal_event_id="e10"))


def test_forskellige_runs_er_uafhaengige(bog):
    bog.record("run-1", project([_hel()], terminal_event_id="a"))
    bog.record("run-2", project([_fejlet()], terminal_event_id="b"))
    assert bog.outcome("run-1").outcome == O.COMPLETED
    assert bog.outcome("run-2").outcome == O.FAILED


def test_et_ukendt_run_er_ikke_terminalt(bog):
    assert bog.is_terminal("findes-ikke") is False
    assert bog.outcome("findes-ikke") is None


# ── et AFBRUDT run er ikke et fejlet run ─────────────────────────────────

def _afbrudt_uden_tekst():
    return classify(Attempt(terminal=S.CANCELLED))


def test_afbrudt_UDEN_tekst_er_interrupted_ikke_failed():
    """Fundet af afregnings-skyggens anden uenighed: den gamle kode kaldte en
    kørsel afbrudt midt i flugten `interrupted`, kontrakten kaldte den
    `failed`. Den gamle havde ret — «det gik i stykker» og «det blev stoppet»
    er ikke det samme."""
    r = project([_afbrudt_uden_tekst()])
    assert r.outcome == O.INTERRUPTED and r.outcome != O.FAILED
    assert r.rule == "afbrudt før der kom et svar"


def test_der_er_en_note_men_ikke_en_fejlbesked():
    r = project([_afbrudt_uden_tekst()])
    assert r.surface.reason == S.CANCELLED_REASON
    assert "afbrudt" in r.surface.text.lower()
    assert "fejl" not in r.surface.text.lower()


def test_en_afbrydelse_efter_flere_forsoeg_er_stadig_interrupted():
    assert project([_fejlet(), _afbrudt_uden_tekst()]).outcome == O.INTERRUPTED


def test_en_AEGTE_fejl_er_stadig_failed():
    """Rettelsen må ikke gøre alle mislykkede forsøg til afbrydelser."""
    assert project([_fejlet(S.FAILURE)]).outcome == O.FAILED
    assert project([_fejlet(S.EMPTY_RESPONSE)]).outcome == O.FAILED
