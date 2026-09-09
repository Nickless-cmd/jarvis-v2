"""Et doedt run maa efterlade den AERLIGE forskel — Fase 3, K6.

«disconnect tests distinguish `aborted_before_dispatch` from
`outcome_unknown`.»

Broen kunne skelne fra dag ét. Men INGEN kaldte `abandon()` — maalt 9/9-2026:
nul kaldere i hele repoet. En skelnen der aldrig foretages, er ikke en
skelnen; posten blev liggende som `dispatching` for evigt, og saa betyder
«udfald ukendt» ingenting.

Forskellen er ikke akademisk:

    prepared/approved → handlingen skete ALDRIG. Sikkert at proeve igen.
    dispatching       → vi afsendte og saa aldrig udfaldet. K7 forbyder et
                        automatisk genforsoeg, fordi et gentaget
                        ikke-idempotent kald kan goere skaden to gange.
"""
from __future__ import annotations

import logging
from types import SimpleNamespace

import pytest

from core.runtime import db_approval_bridge as B
from core.services import visible_run_abandonment as A


@pytest.fixture
def run(isolated_runtime):
    return SimpleNamespace(run_id="run-doed", session_id="s1", provider="p",
                           model="m", autonomous=False)


# ── selve skelnen ────────────────────────────────────────────────────────

def test_afbrudt_FOER_afsendelsen_er_aldrig_sket(run):
    """Godkendt, men klienten forsvandt inden kaldet krydsede graensen."""
    B.request("a1", tool_name="bash", arguments={"command": "ls"},
              run_id="run-doed")
    B.decide("a1", approved=True)

    ud = A.abandon_bridge_records(run)
    assert ud == {B.ABORTED_BEFORE_DISPATCH: 1}
    assert B.state("a1")["state"] == B.ABORTED_BEFORE_DISPATCH


def test_afbrudt_UNDER_afsendelsen_er_UKENDT(run):
    """Vi naaede at afsende. Om vaerktoejet naaede at goere det, ved ingen."""
    B.request("a2", tool_name="bash", arguments={"command": "ls"},
              run_id="run-doed")
    B.decide("a2", approved=True)
    B.claim("a2", tool_name="bash", arguments={"command": "ls"})

    ud = A.abandon_bridge_records(run)
    assert ud == {B.OUTCOME_UNKNOWN: 1}
    assert B.state("a2")["state"] == B.OUTCOME_UNKNOWN


def test_en_auto_registreret_der_aldrig_blev_afsendt(run):
    """K3-posterne foelger samme skelnen — ingen bliver spurgt om dem, men de
    aendrer noget."""
    B.prepare("i1", tool_name="write_file", arguments={"path": "/w/x"},
              run_id="run-doed")
    assert A.abandon_bridge_records(run) == {B.ABORTED_BEFORE_DISPATCH: 1}


def test_BEGGE_slags_i_samme_doede_run(run):
    """Det virkelige tilfaelde: et run naaede at afsende ét kald og havde et
    andet klar. De to maa ikke faa samme udfald."""
    for aid in ("b1", "b2"):
        B.request(aid, tool_name="bash", arguments={"command": aid},
                  run_id="run-doed")
        B.decide(aid, approved=True)
    B.claim("b1", tool_name="bash", arguments={"command": "b1"})

    ud = A.abandon_bridge_records(run)
    assert ud == {B.OUTCOME_UNKNOWN: 1, B.ABORTED_BEFORE_DISPATCH: 1}
    assert B.state("b1")["state"] == B.OUTCOME_UNKNOWN
    assert B.state("b2")["state"] == B.ABORTED_BEFORE_DISPATCH


def test_et_AFSLUTTET_kald_roeres_ikke(run):
    """Runnet doede bagefter. Handlingen naaede sin beslutning og beholder den."""
    B.request("c1", tool_name="bash", arguments={"command": "ls"},
              run_id="run-doed")
    B.decide("c1", approved=True)
    B.claim("c1", tool_name="bash", arguments={"command": "ls"})
    B.settle("c1", ok=True)

    assert A.abandon_bridge_records(run) == {}
    assert B.state("c1")["state"] == B.COMPLETED


def test_et_ANDET_runs_poster_roeres_ikke(run):
    B.request("d1", tool_name="bash", arguments={"command": "ls"},
              run_id="et-andet-run")
    B.decide("d1", approved=True)

    assert A.abandon_bridge_records(run) == {}
    assert B.state("d1")["state"] == B.APPROVED


# ── det alvorlige siges hoejt ────────────────────────────────────────────

def test_UKENDT_udfald_logges_som_advarsel(run, caplog):
    """«Vi afsendte og saa aldrig udfaldet» er den tilstand nogen skal kigge
    paa — ikke én der forsvinder i en taeller."""
    B.request("e1", tool_name="gmail_send", arguments={"to": "x"},
              run_id="run-doed")
    B.decide("e1", approved=True)
    B.claim("e1", tool_name="gmail_send", arguments={"to": "x"})

    with caplog.at_level(logging.WARNING):
        A.abandon_bridge_records(run)
    assert "UKENDT udfald" in caplog.text and "run-doed" in caplog.text


def test_intet_at_opgive_er_tavst(run, caplog):
    with caplog.at_level(logging.WARNING):
        assert A.abandon_bridge_records(run) == {}
    assert "UKENDT" not in caplog.text


# ── den maa ikke lade runnet doe én gang til ─────────────────────────────

def test_en_kollapset_bro_vaelter_ikke_oprydningen(run, monkeypatch, caplog):
    monkeypatch.setattr(B, "abandon_run",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("nede")))
    with caplog.at_level(logging.WARNING):
        assert A.abandon_bridge_records(run) == {}
    assert "kunne ikke opgive" in caplog.text


def test_rapporten_kaster_aldrig(run, monkeypatch):
    """Alle fire ting i rapporten sidder paa veje der kan fejle."""
    import core.services.central_core as CC
    monkeypatch.setattr(CC, "central",
                        lambda: (_ for _ in ()).throw(RuntimeError("nede")))
    A.report_abandoned_run(run, abort_kind="GeneratorExit", run_stage="stream",
                           visible_len=0)


def test_rapporten_opgiver_broens_poster(run):
    """Koblingen: hvis rapporten ikke kalder den, er skelnen stadig teoretisk."""
    B.prepare("f1", tool_name="write_file", arguments={"path": "/w/x"},
              run_id="run-doed")
    A.report_abandoned_run(run, abort_kind="GeneratorExit", run_stage="stream",
                           visible_len=0)
    assert B.state("f1")["state"] == B.ABORTED_BEFORE_DISPATCH


def test_visible_runs_kalder_rapporten():
    """Og at DEN bliver kaldt fra det ene sted hvert run passerer."""
    import inspect
    import core.services.visible_runs as VR
    kilde = inspect.getsource(VR)
    assert "report_abandoned_run(run, abort_kind=" in kilde
