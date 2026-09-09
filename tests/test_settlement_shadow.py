"""Skygge-sammenligningen — er den nye afregning enig med den kørende kode?

Samme mønster som ledger-skyggen, af samme grund: en ny kontrakt er ikke
bevist ved at bestå sine egne tests. Den er bevist når den siger det SAMME som
den kode der har kørt i produktion.

Og den sidder på den SYNLIGE svarvej. En måling der kan vælte et svar, er ikke
en måling værd at have.
"""
from __future__ import annotations

import pytest

from core.services import settlement_shadow as SH


@pytest.fixture(autouse=True)
def _rene_taellere():
    SH._nulstil_for_tests()
    yield
    SH._nulstil_for_tests()


@pytest.fixture
def taendt(monkeypatch):
    monkeypatch.setattr(SH, "live", lambda: True)


def _obs(**kw):
    kw.setdefault("run_id", "r1")
    kw.setdefault("legacy_status", "completed")
    kw.setdefault("legacy_error", None)
    kw.setdefault("text", "et svar")
    kw.setdefault("emitted_prefix", "et svar")
    kw.setdefault("cancelled", False)
    return SH.observe(**kw)


# ── afbryderen ───────────────────────────────────────────────────────────

def test_slukket_som_STANDARD():
    """Husets `is_enabled` er fail-OPEN og ville svare True for en nøgle ingen
    har sat. En måling der tænder sig selv, er ikke noget nogen har besluttet."""
    assert SH.live() is False


def test_en_cache_der_fejler_regnes_som_SLUKKET(monkeypatch):
    import core.services.central_switches as CS
    monkeypatch.setattr(CS.shared_cache, "get",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("nede")))
    assert SH.live() is False


@pytest.mark.parametrize("v", [None, {}, {"enabled": False}, {"enabled": "ja"}, "sludder"])
def test_kun_et_EKSPLICIT_true_taender(monkeypatch, v):
    import core.services.central_switches as CS
    monkeypatch.setattr(CS.shared_cache, "get", lambda *a, **k: v)
    assert SH.live() is False


def test_et_eksplicit_true_taender(monkeypatch):
    import core.services.central_switches as CS
    monkeypatch.setattr(CS.shared_cache, "get", lambda *a, **k: {"enabled": True})
    assert SH.live() is True


def test_slukket_maaler_ingenting():
    _obs()
    assert SH.taellere() == {"enige": 0, "uenige": 0, "fejl": 0, "sprunget_over": 1}


# ── enighed ──────────────────────────────────────────────────────────────

def test_et_helt_svar_er_enigt(taendt):
    _obs(legacy_status="completed", text="svar", emitted_prefix="svar")
    assert SH.taellere()["enige"] == 1


def test_en_annullering_er_enig(taendt):
    _obs(legacy_status="cancelled", text="halvt", emitted_prefix="halvt", cancelled=True)
    assert SH.taellere()["enige"] == 1


def test_cancelled_og_interrupted_er_IKKE_en_uenighed(taendt):
    """Den gamle kode skelner mellem «cancelled» og «interrupted»; den nye har
    ét ord for begge, fordi forskellen er HVORFOR turen stoppede, ikke hvordan
    den endte."""
    _obs(legacy_status="interrupted", text="halvt", emitted_prefix="halvt", cancelled=True)
    assert SH.taellere()["enige"] == 1 and SH.taellere()["uenige"] == 0


def test_en_fejl_er_enig(taendt):
    _obs(legacy_status="failed", text="", emitted_prefix="", transport_error=True)
    assert SH.taellere()["enige"] == 1


# ── uenighed ─────────────────────────────────────────────────────────────

def test_uenighed_taelles_og_LOGGES(taendt, caplog):
    import logging
    with caplog.at_level(logging.WARNING):
        _obs(legacy_status="completed", text="", emitted_prefix="", transport_error=True)
    assert SH.taellere()["uenige"] == 1
    assert "UENIGE" in caplog.text


def test_loggen_baerer_BEGGE_svar_og_kendsgerningerne(taendt, caplog):
    """Uenighed betyder ikke nødvendigvis at den nye kode tager fejl. Derfor
    skal den kunne AFGØRES frem for at skulle gættes."""
    import logging
    with caplog.at_level(logging.WARNING):
        _obs(run_id="r-42", legacy_status="completed", text="",
             emitted_prefix="", transport_error=True)
    t = caplog.text
    assert "r-42" in t and "gammel=completed" in t and "ny=failed" in t
    assert "regel=" in t and "praefiks=0" in t


# ── den må aldrig kunne vælte et svar ────────────────────────────────────

def test_en_fejl_i_maalingen_kaster_ALDRIG(taendt, monkeypatch):
    import core.services.stream_settlement as S
    monkeypatch.setattr(S, "classify",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("i stykker")))
    _obs()                       # kaster ikke
    assert SH.taellere()["fejl"] == 1


def test_maalingen_har_ingen_returvaerdi_nogen_kan_handle_paa(taendt):
    assert _obs() is None


def test_selvmodsigende_input_vaelter_ikke_maalingen(taendt):
    """Et sendt præfiks uden tekst er en selvmodsigelse for klassifikatoren.
    Den kaster — og skyggen skal fange det, ikke sende det videre."""
    _obs(legacy_status="completed", text="", emitted_prefix="brugeren så det her")
    assert SH.taellere()["fejl"] == 1


# ── tavshed skal kunne skelnes fra fravær ────────────────────────────────

def test_enigheden_siges_HOEJT_med_jaevne_mellemrum(taendt, caplog):
    """En måling der kun logger ved uenighed, kan ikke skelne «alt passer» fra
    «fyrede aldrig»."""
    import logging
    with caplog.at_level(logging.INFO):
        for _ in range(SH.PULS_HVER):
            _obs()
    assert "settlement-shadow puls" in caplog.text
    assert SH.taellere()["enige"] == SH.PULS_HVER


def test_pulsen_kommer_ikke_ved_HVER_observation(taendt, caplog):
    import logging
    _obs()                       # den første siges altid højt
    caplog.clear()
    with caplog.at_level(logging.INFO):
        for _ in range(SH.PULS_HVER - 2):
            _obs()
    assert "puls" not in caplog.text


def test_den_FOERSTE_observation_siges_hoejt(taendt, caplog):
    """Beviset for at koblingen overhovedet fyrer. Uden den skal man vente på
    den 20. for at vide om målingen er i live."""
    import logging
    with caplog.at_level(logging.INFO):
        _obs()
    assert "settlement-shadow puls" in caplog.text
