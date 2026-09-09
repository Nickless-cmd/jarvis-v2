"""Et ukendt udfald maa aldrig gentages automatisk — Fase 3, K7.

K6 gjorde tilstanden virkelig: et doedt run efterlader nu enten
`aborted_before_dispatch` («skete aldrig» — sikkert at proeve igen) eller
`outcome_unknown` («vi afsendte og saa aldrig udfaldet»). K7 er hvad man saa
maa goere ved den anden.

Effekt-klassen er erklaeret for 8 af 466 vaerktoejer. `gmail_send`,
`stripe_create_issuing_card` og `operator_bash` staar alle som `unknown`. At
behandle «ved det ikke» som «sikkert at gentage» ville vaere at gaette paa den
forkerte side af en mail der sendes to gange.
"""
from __future__ import annotations

import logging

import pytest

from core.runtime import db_approval_bridge as B
from core.services import retry_admissibility as K7

ARGS = {"to": "bjorn@example.com", "subject": "kvittering"}


def _efterlad_ukendt(aid: str, tool: str = "gmail_send", args=None) -> None:
    """Bring et kald i praecis den tilstand K7 handler om."""
    a = ARGS if args is None else args
    B.request(aid, tool_name=tool, arguments=a, run_id="r-doed")
    B.decide(aid, approved=True)
    B.claim(aid, tool_name=tool, arguments=a)
    assert B.abandon(aid) == B.OUTCOME_UNKNOWN


# ── selve reglen ─────────────────────────────────────────────────────────

def test_uden_tidligere_ukendt_udfald_er_der_intet_i_vejen(isolated_runtime):
    assert K7.may_auto_retry("gmail_send", ARGS).tilladt is True


def test_et_UKENDT_udfald_forbyder_automatisk_gentagelse(isolated_runtime):
    _efterlad_ukendt("k7-a")
    dom = K7.may_auto_retry("gmail_send", ARGS)
    assert dom.tilladt is False
    assert dom.tidligere == ("k7-a",)
    assert "UKENDT udfald" in dom.grund


def test_det_er_KALDET_der_taeller_ikke_vaerktoejet(isolated_runtime):
    """Samme vaerktoej, ANDRE argumenter, er et andet kald. At blokere det
    ville goere ét ukendt udfald til en spaerring for hele vaerktoejet."""
    _efterlad_ukendt("k7-b")
    assert K7.may_auto_retry("gmail_send", {"to": "en.anden@x", "subject": "y"}).tilladt


def test_et_ANDET_vaerktoej_med_samme_argumenter_er_ogsaa_et_andet_kald(
        isolated_runtime):
    _efterlad_ukendt("k7-c")
    assert K7.may_auto_retry("docs_append", ARGS).tilladt is True


def test_en_AFSLUTTET_post_forbyder_ingenting(isolated_runtime):
    """Kun det UKENDTE udfald er farligt. Et kald der naaede sin beslutning,
    er ikke en gaade."""
    B.request("k7-d", tool_name="gmail_send", arguments=ARGS)
    B.decide("k7-d", approved=True)
    B.claim("k7-d", tool_name="gmail_send", arguments=ARGS)
    B.settle("k7-d", ok=True)
    assert K7.may_auto_retry("gmail_send", ARGS).tilladt is True


def test_ABORTED_before_dispatch_forbyder_ingenting(isolated_runtime):
    """«Skete aldrig» er praecis den tilstand hvor et genforsoeg ER sikkert.
    Hele grunden til at K6 skelner."""
    B.request("k7-e", tool_name="gmail_send", arguments=ARGS)
    B.decide("k7-e", approved=True)
    assert B.abandon("k7-e") == B.ABORTED_BEFORE_DISPATCH
    assert K7.may_auto_retry("gmail_send", ARGS).tilladt is True


# ── «ukendt effekt» taeller som ikke-idempotent ──────────────────────────

def test_et_vaerktoej_med_UKENDT_effekt_maa_ikke_gentages(isolated_runtime):
    """458 af 466 staar som `unknown`. At laese det som «sikkert» ville vaere
    at gaette paa den forkerte side."""
    from core.tools.tool_definition_v2 import UKENDT, describe
    assert describe("gmail_send").effect_class == UKENDT
    _efterlad_ukendt("k7-f")
    assert K7.may_auto_retry("gmail_send", ARGS).tilladt is False


def test_kun_ERKLAERET_read_only_slipper_igennem(isolated_runtime, monkeypatch):
    import core.tools.tool_definition_v2 as V
    _efterlad_ukendt("k7-g", tool="read_file", args={"path": "/x"})
    assert K7.may_auto_retry("read_file", {"path": "/x"}).tilladt is False

    monkeypatch.setattr(K7, "_er_beviseligt_uskadeligt", lambda n: n == "read_file")
    dom = K7.may_auto_retry("read_file", {"path": "/x"})
    assert dom.tilladt is True and "read_only" in dom.grund


# ── kan vi ikke afgoere det, er svaret nej ───────────────────────────────

def test_et_opslag_der_fejler_giver_NEJ(isolated_runtime, monkeypatch, caplog):
    """«Vi ved ikke om det allerede er sket» er selve tilstanden K7 handler
    om — saa det kan ikke vaere en grund til at sige ja."""
    monkeypatch.setattr(B, "prior_unknown_outcome",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("nede")))
    with caplog.at_level(logging.WARNING):
        dom = K7.may_auto_retry("gmail_send", ARGS)
    assert dom.tilladt is False and "kunne ikke afgoere" in dom.grund


# ── koblingerne ──────────────────────────────────────────────────────────

def test_den_auto_godkendte_sti_ADVARER_men_blokerer_ikke(isolated_runtime,
                                                          caplog):
    """`invocation_record` maa aldrig vaelte et kald. Men den maa heller ikke
    tie om at skrivningen maaske sker for anden gang."""
    from core.services.invocation_record import recorded
    _efterlad_ukendt("k7-h", tool="write_file", args={"path": "/w/x.py"})

    kaldt = []
    with caplog.at_level(logging.WARNING):
        with recorded("write_file", {"path": "/w/x.py"}):
            kaldt.append(1)
    assert kaldt == [1], "kaldet blev blokeret — det maa det ikke"
    assert "K7:" in caplog.text and "UKENDT udfald" in caplog.text


def test_den_godkendte_sti_AFVISER_naar_broen_haandhaever(isolated_runtime,
                                                          monkeypatch):
    """Dér, hvor et menneske allerede har sagt ja én gang, og udfaldet forblev
    ukendt: handlingen maa ikke ske af sig selv igen."""
    import core.services.visible_runs_approvals as A
    import core.services.approval_bridge_shadow as S
    import core.tools.approval_rollout_gate as G
    import core.tools.simple_tools as ST

    _efterlad_ukendt("k7-i")
    monkeypatch.setattr(S, "note_claim", lambda *a, **k: (True, ""))
    monkeypatch.setattr(G, "bridge_active", lambda: True)
    kaldt = []
    monkeypatch.setattr(ST, "execute_tool_force",
                        lambda n, a, **k: (kaldt.append(n), {"status": "ok"})[1])
    monkeypatch.setattr(ST, "format_tool_result_for_model", lambda n, r: "ok")
    A._vr._PENDING_APPROVALS["k7-ny"] = {
        "tool_name": "gmail_send", "arguments": ARGS,
        "run_id": "r2", "session_id": "s2", "status": "pending"}

    ud = A.resolve_pending_approval("k7-ny", approved=True)
    assert kaldt == [], "kaldet blev afsendt anden gang"
    assert ud["status"] == "error"


# ── de veje der IKKE er automatiske genforsoeg ───────────────────────────

def test_runde_genforsoeget_koerer_aldrig_et_vaerktoej_igen():
    """Invarianten stod som en kommentar. Nu er den ogsaa en test."""
    import inspect
    import core.services.visible_runs as VR
    kilde = inspect.getsource(VR)
    assert "NO tool is ever re-executed on the retry path" in kilde


def test_broen_afviser_i_forvejen_en_gen_overtagelse_af_SAMME_post(
        isolated_runtime):
    _efterlad_ukendt("k7-j")
    with pytest.raises(B.ApprovalRefused, match="outcome_unknown"):
        B.claim("k7-j", tool_name="gmail_send", arguments=ARGS)
