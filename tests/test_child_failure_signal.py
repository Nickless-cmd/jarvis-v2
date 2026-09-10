"""Et barn der doer, skal kunne SES — Fase 5.

«provider removal/new-start rejection and child failure are observable.»

MAALT 10/9-2026: barnets skaebne blev PAENT registreret — status, `last_error`,
tidsstempel og en `agent_message`. Men i hele `agent_runtime_spawn` fandtes
NOEJAGTIG ÉN nerve (kun for udbyder-fejl, i en flygtig ring-buffer) og NUL
incidents. Udloeb, annullering og genstarts-tab blev slet ikke sagt.

Samme klasse som cut-off-signalet: registreret, aldrig set — panelet viste
derfor aldrig noget.

(Min foerste optaelling sagde «nul nerver». Den var forkert: nerven er skrevet
`_c_pe().observe(...)`, og mit greb efter `central().observe` ramte den ikke.
Endnu et for bogstaveligt navne-opslag.)
"""
from __future__ import annotations

import pytest

from core.services import child_failure_signal as CFS


@pytest.fixture
def fanget(monkeypatch):
    nerver, incidents = [], []

    class _C:
        def observe(self, p):
            nerver.append(dict(p))

    monkeypatch.setattr("core.services.central_core.central", lambda: _C())
    monkeypatch.setattr(
        "core.runtime.db_central_incidents.record_central_incident",
        lambda **kw: incidents.append(kw))
    return nerver, incidents


# ── hvad der siges ───────────────────────────────────────────────────────

@pytest.mark.parametrize("status", ["failed", "expired", "cancelled"])
def test_et_daarligt_udfald_giver_baade_nerve_og_incident(fanget, status):
    nerver, incidents = fanget
    CFS.note_child_ended("a1", status=status, role="researcher", error="x")
    assert len(nerver) == 1 and len(incidents) == 1
    assert nerver[0]["nerve"] == "child_ended" and nerver[0]["status"] == status


def test_et_VELLYKKET_barn_er_ikke_en_haendelse(fanget):
    nerver, incidents = fanget
    CFS.note_child_ended("a1", status="completed")
    CFS.note_child_ended("a2", status="")
    assert nerver == [] and incidents == []


def test_alvoren_skelner(fanget):
    """Et opbrugt budget er en graense der VIRKER; et barn der doer af en
    genstart er noget andet."""
    _, incidents = fanget
    CFS.note_child_ended("a1", status="expired")
    CFS.note_child_ended("a2", status="failed")
    assert incidents[0]["severity"] == "warning"
    assert incidents[1]["severity"] == "error"


def test_incidenten_er_DURABEL_og_dedupet(fanget):
    """observe() alene bor i en flygtig ring-buffer pr. proces og er vaek ved
    genstart — praecis derfor naaede cut-offs aldrig panelet."""
    _, incidents = fanget
    CFS.note_child_ended("a1", status="failed", error="noget")
    assert incidents[0]["dedup"] is True
    assert incidents[0]["cluster"] == "agents"


def test_herkomsten_foelger_med_saa_barnet_kan_findes_under_sin_tur(fanget):
    nerver, incidents = fanget
    CFS.note_child_ended("a1", status="failed", parent_run_id="run-7")
    assert nerver[0]["parent_run_id"] == "run-7"
    assert incidents[0]["run_id"] == "run-7"


# ── den maa aldrig vaelte det den rapporterer ────────────────────────────

def test_den_kaster_aldrig(monkeypatch):
    monkeypatch.setattr("core.services.central_core.central",
                        lambda: (_ for _ in ()).throw(RuntimeError("nede")))
    monkeypatch.setattr(
        "core.runtime.db_central_incidents.record_central_incident",
        lambda **kw: (_ for _ in ()).throw(RuntimeError("ogsaa nede")))
    CFS.note_child_ended("a1", status="failed")


def test_registry_indgangen_taaler_vroevl(fanget):
    for arg in (None, "ikke en dict", {}, {"status": "completed"}):
        CFS.note_from_registry(arg)
    assert fanget[0] == []


# ── koblingen ────────────────────────────────────────────────────────────

def test_alle_tre_doeds_steder_siger_det():
    """Ét sted der glemmer det, er en hel udfalds-klasse der forbliver usynlig."""
    import inspect
    from core.services import agent_runtime_spawn as S
    kilde = inspect.getsource(S)
    assert kilde.count("note_child_ended(") == 3, (
        "et doeds-sted mangler signalet")
    for st in ('status="failed"', 'status="expired"', 'status="cancelled"'):
        assert st in kilde
