"""Hvad nåede FAKTISK ud, før turen blev afbrudt?

Spec: «The authoritative cancellation boundary is the highest contiguous frame
sequence appended to the server-owned resumable run buffer before SSE emission.
Ordinary SSE client acknowledgement is neither required nor inferred.»

En klient kan påstå hvad som helst om hvad den nåede at se, og en klient der er
væk kan slet ingenting påstå. Sandheden ligger i serverens buffer.
"""
from __future__ import annotations

import json

import pytest

from core.services import run_event_log as REL
from core.services.emitted_prefix import Prefix, emitted_prefix


def _delta(t: str) -> str:
    return 'event: delta\ndata: ' + json.dumps({"type": "delta", "delta": t})


def _v2delta(t: str) -> str:
    return 'event: content_block_delta\ndata: ' + json.dumps(
        {"type": "content_block_delta", "delta": {"type": "text_delta", "text": t}})


@pytest.fixture
def run():
    rid = "run-praefiks-test"
    REL._RUNS.pop(rid, None)
    REL.create(rid, "sess-x")
    yield rid
    REL._RUNS.pop(rid, None)


# ── præfikset er det der nåede bufferen ──────────────────────────────────

def test_praefikset_er_det_udsendte_i_raekkefoelge(run):
    for t in ("Hej ", "Bjørn", "!"):
        REL.append(run, _delta(t))
    p = emitted_prefix(run)
    assert p.text == "Hej Bjørn!" and p.complete is True


def test_v2_rammer_laeses_ogsaa(run):
    REL.append(run, _v2delta("halvt "))
    REL.append(run, _v2delta("svar"))
    assert emitted_prefix(run).text == "halvt svar"


def test_ikke_tekst_rammer_taeller_ikke_med(run):
    REL.append(run, _delta("svar"))
    REL.append(run, 'event: working_step\ndata: {"type": "working_step"}')
    REL.append(run, 'event: heartbeat\ndata: {"type": "heartbeat"}')
    assert emitted_prefix(run).text == "svar"


def test_et_run_uden_udsendte_bytes_er_TOMT_men_HELT(run):
    p = emitted_prefix(run)
    assert p.text == "" and p.complete is True and not p


def test_et_UKENDT_run_er_tomt_men_helt():
    """Der er ikke noget vi har mistet."""
    p = emitted_prefix("findes-ikke")
    assert p.text == "" and p.complete is True and p.problem == ""


def test_uden_run_id_er_det_et_problem():
    p = emitted_prefix("")
    assert p.problem == "intet run_id" and p.text == ""


# ── fuldstændigheden skal siges HØJT ─────────────────────────────────────

def test_en_udrullet_begyndelse_meldes_som_UFULDSTAENDIG(run, monkeypatch):
    """Bufferen er en ring. Et afkortet præfiks der PÅSTOD at være helt, ville
    gemme et halvt svar som om det var hele det leverede."""
    monkeypatch.setattr(REL, "read_from",
                        lambda r, i: ([REL.GAP_FRAME, _delta("resten")], False, 2))
    p = emitted_prefix(run)
    assert p.complete is False and p.text == "resten"


def test_gap_genkendes_paa_KONSTANTEN_ikke_paa_ordet(run):
    """En tekst-delta der indeholder ordet «gap» er ikke et hul."""
    REL.append(run, _delta("der er et gap i logikken"))
    p = emitted_prefix(run)
    assert p.complete is True and "gap" in p.text


def test_fuldstaendigheden_kan_ikke_overses():
    """Den ligger ved siden af teksten, ikke i en flag-parameter man glemmer."""
    import dataclasses
    felter = {f.name for f in dataclasses.fields(Prefix)}
    assert "complete" in felter and "text" in felter


# ── den kaster aldrig, og gætter aldrig ──────────────────────────────────

def test_en_ulaeselig_log_giver_et_PROBLEM_ikke_et_gaet(run, monkeypatch):
    monkeypatch.setattr(REL, "read_from",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("nede")))
    p = emitted_prefix(run)
    assert p.text == "" and p.problem and p.complete is False


def test_en_oedelagt_ramme_springes_over_frem_for_at_vaelte(run):
    REL.append(run, _delta("god "))
    REL.append(run, "event: delta\ndata: { ødelagt json")
    REL.append(run, _delta("igen"))
    assert emitted_prefix(run).text == "god igen"


def test_praefikset_er_sandt_ogsaa_naar_klienten_er_VAEK(run):
    """Ingen klient-kvittering kræves eller udledes — bufferen er sandheden."""
    for t in ("a", "b", "c"):
        REL.append(run, _delta(t))
    REL.mark_done(run)
    assert emitted_prefix(run).text == "abc"
