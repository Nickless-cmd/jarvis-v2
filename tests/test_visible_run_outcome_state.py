"""Et synligt runs terminale beslutning, og vagten mod en optimistisk standard.

Udskilt fra `visible_runs.py` efter Boy Scout-reglen. Adfærden er den samme som
de tre lokale variable havde — testene her er den beskrivelse den aldrig fik.

Roden: standarden er `completed`, så et run der bliver AFBRUDT undervejs arver
«completed» hvis ingen når at sige noget andet. Bjørn sporede den 4. juli.
"""
from __future__ import annotations

import pytest

from core.services import visible_run_outcome_state as V
from core.services.visible_run_outcome_state import RunOutcomeState


def test_standarden_er_optimistisk():
    """De fleste runs lykkes. Prisen for det valg er vagten nedenfor."""
    s = RunOutcomeState()
    assert s.status == V.COMPLETED and s.is_default and not s.finalized


# ── vagten ───────────────────────────────────────────────────────────────

def test_en_ALDRIG_NAAET_standard_nedgraderes():
    """Klienten dropper forbindelsen, GeneratorExit rejses, eller en
    BaseException river funktionen op midtvejs. Uden vagten står der
    «completed» på en samtale der aldrig fik et svar."""
    s = RunOutcomeState()
    assert s.downgrade_if_abandoned("GeneratorExit") is True
    assert s.status == V.INTERRUPTED
    assert "GeneratorExit" in s.error


def test_et_EKSPLICIT_completed_roeres_ikke():
    """Det NÅEDE sin beslutning."""
    s = RunOutcomeState()
    s.mark(V.COMPLETED)
    assert s.downgrade_if_abandoned("GeneratorExit") is False
    assert s.status == V.COMPLETED


@pytest.mark.parametrize("status", [V.FAILED, V.CANCELLED, V.INTERRUPTED])
def test_en_anden_status_nedgraderes_ikke(status):
    s = RunOutcomeState()
    s.mark(status, error="noget gik galt")
    assert s.downgrade_if_abandoned() is False
    assert s.status == status


def test_begge_betingelser_skal_holde():
    """Standarden urørt OG intet terminalt punkt nået."""
    a = RunOutcomeState(); a.reach_finalization()
    assert a.downgrade_if_abandoned() is False      # nået, men standard

    b = RunOutcomeState(); b.mark(V.FAILED, finalized=False)
    assert b.downgrade_if_abandoned() is False      # ikke nået, men ikke standard


def test_nedgraderingen_overskriver_ikke_en_eksisterende_fejltekst():
    s = RunOutcomeState()
    s.set_error("den ægte årsag")
    s.downgrade_if_abandoned("CancelledError")
    assert s.error == "den ægte årsag"


def test_nedgraderingen_kan_ikke_ske_to_gange():
    s = RunOutcomeState()
    assert s.downgrade_if_abandoned() is True
    assert s.downgrade_if_abandoned() is False


# ── at træffe beslutningen ER at nå den ──────────────────────────────────

def test_mark_saetter_vagten_som_standard():
    """Tre løse variable kunne komme ud af trit: man kunne sætte status uden
    at sætte vagten, og så var nedgraderingen forkert."""
    s = RunOutcomeState()
    s.mark(V.FAILED, error="x")
    assert s.finalized is True


def test_en_status_undervejs_kan_saette_vagten_FRA():
    s = RunOutcomeState()
    s.mark(V.INTERRUPTED, error="midt i løkken", finalized=False)
    assert s.status == V.INTERRUPTED and s.finalized is False


def test_reach_finalization_aendrer_ikke_status():
    s = RunOutcomeState()
    s.mark(V.FAILED, error="x", finalized=False)
    s.reach_finalization()
    assert s.status == V.FAILED and s.finalized is True


def test_fejlteksten_kan_saettes_uden_at_aendre_status():
    s = RunOutcomeState()
    s.set_error("noget")
    assert s.status == V.COMPLETED and s.error == "noget"


def test_mark_uden_fejl_beholder_den_gamle():
    s = RunOutcomeState()
    s.set_error("første")
    s.mark(V.FAILED)
    assert s.error == "første"


def test_repr_viser_hele_tilstanden():
    s = RunOutcomeState()
    s.mark(V.FAILED, error="x")
    r = repr(s)
    assert "failed" in r and "finalized=True" in r
