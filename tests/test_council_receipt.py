"""Indkaldelsen kvitterer — den venter ikke. Fase 6.

«start resolves on message acceptance, and send returns a message receipt
rather than a reply» og «parent can continue while an accepted continuable
child runs».

MAALT PAA LEVENDE TRAFIK 10/9-2026 kl. 08:29, mens Bjoern sad og ventede:
fire medlemmer startede inden for 5 MILLISEKUNDER af hinanden og tog 36,4 /
36,8 / 40,0 / 38,1 sekunder hver. Sekventielt: 151 sekunder. Faktisk: 38.

Parallelisering fjernede altsaa tre fjerdedele af ventetiden — men de sidste
38 sekunder froes stadig hans tur, fordi `convene_council` koerte synkront.

En kvittering uden afhentning ville vaere vaerre end at vente: saa var svaret
VAEK i stedet for forsinket. Derfor to veje tilbage, som begge fandtes i
forvejen — `council_status` direkte, og raads-hukommelsen som net.
"""
from __future__ import annotations

import pytest

from core.services import council_receipt as CR


@pytest.fixture(autouse=True)
def _rene():
    CR._nulstil_for_tests()
    yield
    CR._nulstil_for_tests()


# ── kvitteringen ─────────────────────────────────────────────────────────

def test_kvitteringen_siger_ACCEPTERET_ikke_et_svar():
    k = CR.receipt("c1", topic="skal vi", roles=["planner", "critic"], started=True)
    assert k["status"] == "accepted" and k["accepted"] is True
    assert k["council_id"] == "c1" and k["member_count"] == 2
    assert "summary" not in k, "kvitteringen indeholder et svar"


def test_kvitteringen_fortaeller_HVORDAN_man_henter():
    """En kvittering der ikke goer det, forudsaetter at laeseren kender huset."""
    k = CR.receipt("c1", topic="x", roles=["planner"], started=True)
    assert "council_status" in k["hent_resultat"]
    assert "c1" in k["hent_resultat"]
    assert "recall_council_conclusions" in k["hent_resultat"]


def test_en_MISLYKKET_start_kvitteres_ikke_som_accepteret():
    k = CR.receipt("c1", topic="x", roles=[], started=False)
    assert k["status"] == "error" and k["accepted"] is False


# ── baggrunds-runden ─────────────────────────────────────────────────────

def test_runden_startes_uden_at_der_ventes(monkeypatch):
    import core.services.agent_runtime as AR
    faerdig = []
    monkeypatch.setattr(AR, "run_council_round",
                        lambda cid: faerdig.append(cid), raising=False)
    assert CR.start_round_in_background("c1") is True
    assert CR._STARTEDE == ["c1"]


def test_tomt_id_starter_ingenting():
    assert CR.start_round_in_background("") is False
    assert CR._STARTEDE == []


def test_en_runde_der_FEJLER_i_baggrunden_siges_hoejt(monkeypatch, caplog):
    """En runde der doer stille efterlader et raad der ser ud til at vaere i
    gang for altid."""
    import logging
    import threading

    import core.services.agent_runtime as AR
    monkeypatch.setattr(AR, "run_council_round",
                        lambda cid: (_ for _ in ()).throw(RuntimeError("nede")),
                        raising=False)
    with caplog.at_level(logging.WARNING):
        CR.start_round_in_background("c1")
        for t in threading.enumerate():
            if t.name.startswith("council-"):
                t.join(timeout=5)
    assert "fejlede i baggrunden" in caplog.text


# ── afhentningen ─────────────────────────────────────────────────────────

def test_status_henter_raadet(monkeypatch):
    import core.services.agent_runtime_surfaces as S
    monkeypatch.setattr(S, "build_council_detail_surface",
                        lambda cid: {"council_id": cid, "members": []})
    ud = CR.status("c1")
    assert ud["status"] == "ok" and ud["council_id"] == "c1"


def test_status_paa_et_ukendt_raad_siger_det(monkeypatch):
    import core.services.agent_runtime_surfaces as S
    monkeypatch.setattr(S, "build_council_detail_surface", lambda cid: None)
    assert CR.status("findes-ikke")["status"] == "error"


def test_status_kraever_et_id():
    assert CR.status("")["status"] == "error"


# ── koblingen: annonceret OG kaldbar ─────────────────────────────────────

def test_council_status_er_baade_annonceret_og_kaldbar():
    """Et vaerktoej der annonceres uden executor giver «Unknown tool» — det
    hul kostede to doede vaerktoejer i K1."""
    from core.tools.simple_tools import _TOOL_HANDLERS
    from core.tools.simple_tools_definitions import TOOL_DEFINITIONS
    navne = {d["function"]["name"] for d in TOOL_DEFINITIONS}
    assert "council_status" in navne
    assert "council_status" in _TOOL_HANDLERS


def test_convene_venter_ikke_laengere():
    import inspect
    from core.tools import simple_tools_native as N
    kilde = inspect.getsource(N._exec_convene_council)
    assert "start_round_in_background" in kilde
    assert "run_council_round(" not in kilde, "indkaldelsen venter stadig"
