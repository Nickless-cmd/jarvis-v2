"""Fail-closed indespaerring — men KUN for uovervaagede koersler. K9.

«requested confinement fails before execution when unavailable.»

Bjoern 10/9-2026: kun for autonome koersler. En uovervaaget koersel har ingen
til at redde sig hvis sandkassen mangler; hans egen sti er fail-open med
vilje, for han er der selv til at se hvad der sker — og en manglende mekanisme
maa ikke goere bagdoeren ubrugelig.
"""
from __future__ import annotations

import pytest

from core.services import bash_sandbox as SB
from core.services import run_autonomy_context as A


@pytest.fixture(autouse=True)
def _rent():
    t = A.set_autonomous(False)
    yield
    A.reset_autonomous(t)


@pytest.fixture
def sandkasse_oensket_men_umulig(monkeypatch):
    monkeypatch.setattr(SB, "is_enabled", lambda: True)
    monkeypatch.setattr(SB, "is_available", lambda: False)


def _bash(monkeypatch, cmd="echo x"):
    from core.services import operator_channel as OC
    from core.tools import simple_tools_web as W
    monkeypatch.setattr(OC, "maybe_reroute_bash", lambda *a, **k: None)
    monkeypatch.setattr(W, "_get_or_open_default_bash_session", lambda: None)
    return W._exec_bash({"command": cmd})


# ── flaget selv ──────────────────────────────────────────────────────────

def test_standard_er_IKKE_autonom():
    """Ved vi det ikke, opfoerer alt sig som foer."""
    assert A.is_autonomous() is False


def test_flaget_kan_saettes_og_nulstilles():
    t = A.set_autonomous(True)
    assert A.is_autonomous() is True
    A.reset_autonomous(t)
    assert A.is_autonomous() is False


def test_det_er_run_scopet_ikke_globalt():
    """En traad maa ikke arve en anden koersels autonomi."""
    import threading
    A.set_autonomous(True)
    set_af = []
    t = threading.Thread(target=lambda: set_af.append(A.is_autonomous()))
    t.start(); t.join()
    assert set_af == [False]


# ── og hvad det goer ved bash ────────────────────────────────────────────

def test_en_AUTONOM_koersel_naegtes_naar_indespaerring_er_umulig(
        isolated_runtime, monkeypatch, sandkasse_oensket_men_umulig):
    A.set_autonomous(True)
    svar = _bash(monkeypatch)
    assert svar["status"] == "error"
    assert "paakraevet for autonome" in svar["error"]
    assert svar["confinement"]["honored"] is False


def test_BJOERNS_egen_sti_koerer_videre_i_samme_situation(
        isolated_runtime, monkeypatch, sandkasse_oensket_men_umulig):
    """Fail-open med vilje. En manglende mekanisme maa ikke goere bagdoeren
    ubrugelig."""
    A.set_autonomous(False)
    svar = _bash(monkeypatch)
    assert svar["status"] == "ok"
    assert svar["confinement"]["honored"] is False   # men det SIGES


def test_en_autonom_koersel_med_VIRKENDE_sandkasse_koerer(
        isolated_runtime, monkeypatch):
    """Naegtelsen gaelder kun naar indespaerringen er umulig — ikke altid."""
    A.set_autonomous(True)
    svar = _bash(monkeypatch)
    assert svar["status"] == "ok"


def test_slukket_sandkasse_naegter_ikke_noget(isolated_runtime, monkeypatch):
    """Er sandkassen slukket, er der ingen indespaerring oensket — og saa er
    der intet at fejle lukket paa."""
    monkeypatch.setattr(SB, "is_enabled", lambda: False)
    monkeypatch.setattr(SB, "is_available", lambda: False)
    A.set_autonomous(True)
    assert _bash(monkeypatch)["status"] == "ok"


def test_koerslen_saetter_flaget_selv():
    """Koblingen: uden den er flaget altid False og K9 er stadig halv."""
    import inspect
    import core.services.visible_runs as VR
    assert "run_autonomy_context" in inspect.getsource(VR)
    assert "set_autonomous(bool(getattr(run" in inspect.getsource(VR)


def test_SLUKKET_sandkasse_maa_ALDRIG_naegte_en_autonom_koersel(
        isolated_runtime, monkeypatch):
    """Den fejl der naesten naaede maskinen.

    `enforcement(require=True)` kaster ogsaa paa «ikke taendt». Uden leddet
    `and is_enabled()` ville ALT autonomt bash-arbejde doe hver gang sandkassen
    var slukket — hvilket er dens normale tilstand. Er ingen indespaerring
    oensket, er der intet at fejle lukket paa.
    """
    monkeypatch.setattr(SB, "is_enabled", lambda: False)
    for tilgaengelig in (True, False):
        monkeypatch.setattr(SB, "is_available", lambda: tilgaengelig)
        A.set_autonomous(True)
        assert _bash(monkeypatch)["status"] == "ok", (
            f"naegtet med slukket sandkasse (bwrap tilgaengelig={tilgaengelig})")
