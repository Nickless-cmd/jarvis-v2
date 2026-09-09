"""Afregningstabellen — én test pr. række.

Fase 2's første udgangskriterium: «every row in the settlement table has a
test». Rækkefølgen her følger spec'ens §2, og hver test bærer sin rækkes
kolonner: hvad udbyderen gav, hvad UI skal gøre, hvad der afregnes, om det
kommer i model-historikken, og hvad der bør ske bagefter.
"""
from __future__ import annotations

import pytest

from core.services import stream_settlement as S
from core.services.stream_settlement import Attempt, classify


# ── række 1: vellykket tekst ─────────────────────────────────────────────

def test_tekstsvar():
    s = classify(Attempt(terminal=S.OK, text_blocks=("hej",), emitted_prefix="hej"))
    assert s.event == S.ASSISTANT_MESSAGE and s.ui == S.FINALIZE
    assert s.in_model_surface is True and s.next_action == S.CONTINUE
    assert s.interrupted is False


# ── række 2: vellykkede værktøjskald, med eller uden tekst ───────────────

@pytest.mark.parametrize("tekst", [(), ("jeg slår det op",)])
def test_vaerktoejskald(tekst):
    s = classify(Attempt(terminal=S.OK, text_blocks=tekst,
                         tool_calls=({"name": "grep"},)))
    assert s.event == S.ASSISTANT_MESSAGE and s.next_action == S.EXECUTE_TOOLS
    assert s.in_model_surface is True


# ── række 3: vellykket TOMT svar ─────────────────────────────────────────

def test_tomt_svar_er_et_MISLYKKET_forsoeg():
    """Bevidst strengere end DeepSeek: et indholdsløst svar må ikke blive til
    en synlig assistent-besked. Det er husets no-empty-visible-completion."""
    s = classify(Attempt(terminal=S.OK))
    assert s.event == S.ASSISTANT_ATTEMPT and s.reason == S.EMPTY_RESPONSE
    assert s.in_model_surface is False and s.ui == S.TERMINAL_STATUS
    assert s.next_action == S.RETRY_WITHIN_POLICY


# ── række 4: kun privat ræsonnement ──────────────────────────────────────

def test_kun_raesonnement_er_ikke_et_svar():
    s = classify(Attempt(terminal=S.OK, reasoning_blocks=("hmm...",)))
    assert s.event == S.ASSISTANT_ATTEMPT and s.reason == S.EMPTY_RESPONSE
    assert s.in_model_surface is False


# ── række 5: svarbærende thinking med tomt normalt indhold ───────────────

def test_svarbaerende_thinking_forfremmes():
    s = classify(Attempt(terminal=S.OK, reasoning_blocks=("hmm",),
                         promotable_answer="svaret er 42"))
    assert s.event == S.ASSISTANT_MESSAGE and s.in_model_surface is True
    assert s.next_action == S.CONTINUE


def test_forfremmelse_gaelder_KUN_naar_normalt_indhold_er_tomt():
    s = classify(Attempt(terminal=S.OK, text_blocks=("rigtigt svar",),
                         promotable_answer="tankespor"))
    assert "tekstsvar" in s.rule


# ── række 6: max_tokens med gyldige blokke ───────────────────────────────

def test_max_tokens_er_et_AFKORTET_svar_ikke_en_fejl():
    """ALDRIG stille genforsøg: svaret er ægte, bare afkortet. Et genforsøg
    ville kaste et gyldigt svar væk og betale for det samme igen."""
    s = classify(Attempt(terminal=S.MAX_TOKENS, text_blocks=("halvt sva",),
                         emitted_prefix="halvt sva"))
    assert s.event == S.ASSISTANT_MESSAGE and s.interrupted is True
    assert s.in_model_surface is True
    assert s.next_action == S.STOP_OR_CONTINUATION
    assert s.next_action != S.RETRY_WITHIN_POLICY


def test_max_tokens_UDEN_indhold_er_et_tomt_svar():
    s = classify(Attempt(terminal=S.MAX_TOKENS))
    assert s.event == S.ASSISTANT_ATTEMPT and s.reason == S.EMPTY_RESPONSE


# ── række 7: annullering FØR nogen sendt delta ───────────────────────────

def test_annulleret_foer_noget_naaede_ud():
    s = classify(Attempt(terminal=S.CANCELLED, text_blocks=("foreløbigt",)))
    assert s.event == S.ASSISTANT_ATTEMPT and s.reason == S.CANCELLED_REASON
    assert s.ui == S.CLEAR and s.in_model_surface is False
    assert s.next_action == S.END_INTERRUPTED


# ── række 8: annullering EFTER sendte deltaer ────────────────────────────

def test_annulleret_efter_at_bytes_naaede_ud():
    """Præfikset er sandheden om hvad der nåede ud, og det gemmes nøjagtigt —
    ellers ville UI og model-historik kunne skilles ad."""
    s = classify(Attempt(terminal=S.CANCELLED, text_blocks=("halvt",),
                         emitted_prefix="halvt"))
    assert s.event == S.ASSISTANT_MESSAGE and s.interrupted is True
    assert s.in_model_surface is True and s.ui == S.FINALIZE


# ── række 9: transport-fejl FØR nogen delta ──────────────────────────────

def test_transportfejl_foer_levering():
    s = classify(Attempt(terminal=S.TRANSPORT_ERROR, failure="forbindelsen brast"))
    assert s.event == S.ASSISTANT_ATTEMPT and s.reason == S.FAILURE
    assert s.ui == S.TERMINAL_STATUS and s.in_model_surface is False
    assert s.next_action == S.RETRY_WITHIN_POLICY


# ── række 10: transport-fejl EFTER delvise deltaer ───────────────────────

def test_transportfejl_efter_delvis_levering_kraever_ERSTATNING():
    """UI skal have en erstatning FØR næste forsøg må streame, ellers blander
    to svar sig i hinanden på skærmen."""
    s = classify(Attempt(terminal=S.TRANSPORT_ERROR, text_blocks=("halvt",),
                         emitted_prefix="halvt", failure="brast"))
    assert s.event == S.ASSISTANT_ATTEMPT and s.ui == S.RESET
    assert s.in_model_surface is False


# ── række 11: misdannet kald FØR beskeden blev accepteret ────────────────

def test_misdannet_kald_foer_accept():
    s = classify(Attempt(terminal=S.OK, malformed_tool_call=True))
    assert s.event == S.ASSISTANT_ATTEMPT and s.reason == S.MALFORMED_TOOL_CALL
    assert s.in_model_surface is False and s.next_action == S.NO_SIDE_EFFECT


# ── række 12: misdannet kald EFTER gyldig besked ─────────────────────────

def test_misdannet_kald_efter_gyldig_besked_BEVARER_beskeden():
    """At kassere de gyldige blokke fordi et kald var forkert, ville slette et
    svar brugeren har set."""
    s = classify(Attempt(terminal=S.OK, text_blocks=("her er svaret",),
                         malformed_tool_call=True, message_committed=True))
    assert s.event == S.ASSISTANT_MESSAGE and s.ui == S.RETAIN_WITH_TOOL_ERROR
    assert s.in_model_surface is True and s.next_action == S.NO_SIDE_EFFECT


# ── række 13: fejl EFTER at et værktøjskald blev sendt ───────────────────

def test_fejl_efter_sendt_vaerktoejskald_proever_ALDRIG_blindt_igen():
    s = classify(Attempt(terminal=S.TRANSPORT_ERROR, text_blocks=("jeg slår op",),
                         tool_calls=({"name": "bash"},), tool_dispatched=True,
                         message_committed=True))
    assert s.event == S.ASSISTANT_MESSAGE
    assert s.next_action == S.RECONCILE_INVOCATION
    assert s.next_action != S.RETRY_WITHIN_POLICY


# ── den hårde invariant ──────────────────────────────────────────────────

def test_TOMT_med_et_sendt_praefiks_er_en_selvmodsigelse():
    """`visible_runs.py` bærer to advarsler om samme fejl: en falsk
    empty_completion får fallback'en til at «wipe det streamede svar». Altså —
    systemet konkluderede at der ikke kom noget svar, mens brugeren sad og så
    på det. Reglen håndhæves i funktionen, ikke kun her."""
    with pytest.raises(AssertionError, match="EMPTY_RESPONSE"):
        classify(Attempt(terminal=S.OK, emitted_prefix="brugeren SÅ det her"))


def test_intet_sendt_praefiks_kan_godt_vaere_tomt():
    assert classify(Attempt(terminal=S.OK)).reason == S.EMPTY_RESPONSE


# ── egenskaber der gælder på tværs ───────────────────────────────────────

ALLE = [
    Attempt(terminal=S.OK, text_blocks=("x",), emitted_prefix="x"),
    Attempt(terminal=S.OK, tool_calls=({"name": "t"},)),
    Attempt(terminal=S.OK),
    Attempt(terminal=S.OK, reasoning_blocks=("r",)),
    Attempt(terminal=S.OK, promotable_answer="a"),
    Attempt(terminal=S.MAX_TOKENS, text_blocks=("x",), emitted_prefix="x"),
    Attempt(terminal=S.CANCELLED),
    Attempt(terminal=S.CANCELLED, text_blocks=("x",), emitted_prefix="x"),
    Attempt(terminal=S.TRANSPORT_ERROR),
    Attempt(terminal=S.TRANSPORT_ERROR, emitted_prefix="x", text_blocks=("x",)),
    Attempt(terminal=S.OK, malformed_tool_call=True),
    Attempt(terminal=S.OK, text_blocks=("x",), malformed_tool_call=True,
            message_committed=True),
    Attempt(terminal=S.TRANSPORT_ERROR, tool_dispatched=True, message_committed=True),
]


@pytest.mark.parametrize("a", ALLE)
def test_hver_raekke_giver_NOEJAGTIG_en_afregning(a):
    s = classify(a)
    assert s.event in (S.ASSISTANT_MESSAGE, S.ASSISTANT_ATTEMPT)
    assert s.rule, "afregningen skal sige HVILKEN regel der afgjorde den"


@pytest.mark.parametrize("a", ALLE)
def test_kun_en_assistant_message_kommer_i_model_historikken(a):
    """Et mislykket forsøg må aldrig ende i den historik næste runde ser."""
    s = classify(a)
    if s.event == S.ASSISTANT_ATTEMPT:
        assert s.in_model_surface is False


@pytest.mark.parametrize("a", ALLE)
def test_klassifikationen_er_DETERMINISTISK(a):
    assert classify(a) == classify(a)


@pytest.mark.parametrize("a", ALLE)
def test_klassifikatoren_aendrer_ikke_sit_input(a):
    import dataclasses
    foer = dataclasses.asdict(a)
    classify(a)
    assert dataclasses.asdict(a) == foer


def test_hver_tabelraekke_har_sin_EGEN_regel():
    """Falder to rækker sammen i samme regel, er tabellen ikke implementeret —
    så er der bare noget der ligner.

    Kravet er én regel pr. post, ikke et bestemt tal: bliver tabellen udvidet,
    skal denne test fange en ny række der smutter ind under en gammel regel."""
    regler = [classify(a).rule for a in ALLE]
    dubletter = {r for r in regler if regler.count(r) > 1}
    assert not dubletter, f"disse regler dækker mere end én tabelrække: {dubletter}"
    assert len(set(regler)) == len(ALLE)


# ── nøjagtig én afregning, og ingen forsinkede pumper ───────────────────

from core.services.stream_settlement import (          # noqa: E402
    AlreadySettled, AttemptLedger, StaleAttempt,
)


@pytest.fixture
def bog():
    return AttemptLedger()


def _ok():
    return classify(Attempt(terminal=S.OK, text_blocks=("x",), emitted_prefix="x"))


def test_et_forsoeg_afregnes_EN_gang(bog):
    bog.settle("a1", _ok())
    with pytest.raises(AlreadySettled):
        bog.settle("a1", _ok())


def test_afregningen_kan_laeses_tilbage(bog):
    s = bog.settle("a1", _ok())
    assert bog.settled("a1") == s and bog.is_settled("a1") is True


def test_to_FORSKELLIGE_forsoeg_er_uafhaengige(bog):
    bog.settle("a1", _ok())
    bog.settle("a2", _ok())
    assert bog.is_settled("a1") and bog.is_settled("a2")


def test_en_forsinket_pumpe_kan_ikke_sende_flere_rammer(bog):
    """En pumpe der læser videre efter en annullering, ved det ikke. Uden
    denne vagt ville dens næste delta skrive ind i en historik der allerede er
    afsluttet — og der ville stå to halve svar oven i hinanden uden at noget
    havde fejlet."""
    bog.next_frame("a1")
    bog.next_frame("a1")
    bog.settle("a1", _ok())
    with pytest.raises(StaleAttempt, match="afregnet"):
        bog.next_frame("a1")


def test_guard_afviser_en_afregnet_pumpe(bog):
    bog.settle("a1", _ok())
    with pytest.raises(StaleAttempt):
        bog.guard("a1")


def test_guard_slipper_et_AABENT_forsoeg_igennem(bog):
    bog.next_frame("a1")
    bog.guard("a1")          # kaster ikke


def test_rammesekvensen_er_monotont_stigende_pr_forsoeg(bog):
    assert [bog.next_frame("a1") for _ in range(4)] == [1, 2, 3, 4]


def test_hvert_forsoeg_har_sin_EGEN_rammesekvens(bog):
    bog.next_frame("a1"); bog.next_frame("a1")
    assert bog.next_frame("a2") == 1
    assert bog.frames("a1") == 2 and bog.frames("a2") == 1


def test_et_ukendt_forsoeg_er_hverken_afregnet_eller_i_gang(bog):
    assert bog.is_settled("findes-ikke") is False
    assert bog.settled("findes-ikke") is None
    assert bog.frames("findes-ikke") == 0
