"""Vagten der ser om den serverende vært faktisk KAN det den serverer.

## Hvorfor den findes (7/10-2026)

`tests/test_mermaid_render.py` havde `assert find_chrome() is not None` — et
deploy-krav forklædt som unittest. Den fejlede i hver kørsel på
udviklermaskinen, og otte faste røde gjorde suiten ubrugelig som vagt dér:
samme dag lå 16 ægte fejl usete blandt dem.

Testene springer nu over hvor binæren mangler. Kravet flyttede hertil — men et
flyttet krav der ikke bliver håndhævet er bare et tabt krav, og derfor skal
denne vagt kunne SES afvise.
"""
from __future__ import annotations

import socket

import pytest

from scripts import verify_vaert_evner as v


@pytest.fixture(autouse=True)
def _ren_liste(monkeypatch):
    """Rør ikke den rigtige EVNER-liste — testene skriver i den."""
    monkeypatch.setattr(v, "EVNER", [])
    yield


# ── vagten afviser ──────────────────────────────────────────────────────────

def test_en_evne_der_er_NEDE_giver_exit_1(capsys):
    v.EVNER.append(("mermaid", lambda: (False, "ingen chromium-binaer"),
                    "diagrammer kan ikke tegnes"))
    assert v.main([]) == 1
    ud = capsys.readouterr().out
    assert "ingen chromium-binaer" in ud
    assert "diagrammer kan ikke tegnes" in ud, "konsekvensen skal staa der"


def test_en_evne_der_er_oppe_giver_exit_0():
    v.EVNER.append(("mermaid", lambda: (True, "klar"), "ligegyldigt her"))
    assert v.main([]) == 0


def test_et_tjek_der_KASTER_taeller_som_nede(capsys):
    """En vagt der falder paa sin egen fejl siger ingenting. Den skal sige
    hvad der skete."""
    def _sprael() -> tuple[bool, str]:
        raise RuntimeError("importen fejlede")

    v.EVNER.append(("mermaid", _sprael, "diagrammer doer"))
    assert v.main([]) == 1
    assert "importen fejlede" in capsys.readouterr().out


def test_én_evne_der_kaster_skygger_ikke_for_de_andre():
    """En vagt der stopper ved foerste fejl fortaeller kun om én ting."""
    def _sprael() -> tuple[bool, str]:
        raise RuntimeError("boom")

    v.EVNER.append(("foerste", _sprael, "x"))
    v.EVNER.append(("anden", lambda: (True, "klar"), "y"))
    navne = [r[0] for r in v.tjek()]
    assert navne == ["foerste", "anden"]
    assert v.tjek()[1][1] is True


# ── vaert-afgraensningen ────────────────────────────────────────────────────

def test_springes_over_paa_en_ANDEN_vaert(capsys):
    v.EVNER.append(("mermaid", lambda: (False, "ingen chromium"), "x"))
    assert v.main(["--only-host", "en-vaert-der-ikke-findes"]) == 0
    assert "sprunget over" in capsys.readouterr().out


def test_haandhaeves_paa_den_RIGTIGE_vaert():
    """Uden dette ville `--only-host` kunne springe over ALTID — og vagten
    ville aldrig afvise noget nogen steder."""
    v.EVNER.append(("mermaid", lambda: (False, "ingen chromium"), "x"))
    assert v.main(["--only-host", socket.gethostname()]) == 1


def test_uden_only_host_haandhaeves_der_altid():
    v.EVNER.append(("mermaid", lambda: (False, "ingen chromium"), "x"))
    assert v.main([]) == 1


# ── den rigtige evne er hægtet på ───────────────────────────────────────────

def test_mermaid_er_FAKTISK_registreret(monkeypatch):
    """Vagten uden evner afviser aldrig noget. Her maales listen som den er i
    kilden — ikke den tomme fixture-liste."""
    monkeypatch.undo()
    navne = [navn for navn, _, _ in v.EVNER]
    assert "mermaid" in navne, navne
    for _, fn, konsekvens in v.EVNER:
        assert callable(fn)
        assert konsekvens.strip(), "en evne uden konsekvens bliver slaaet fra"


def test_mermaid_tjekket_spoerger_KODEN_ikke_sin_egen_kopi(monkeypatch):
    """Et andet sti-opslag her ville vaere samme regel to steder."""
    import core.services.mermaid_render as mr

    monkeypatch.setattr(mr, "tilgaengelig", lambda: (False, "paastand fra koden"))
    assert v._mermaid() == (False, "paastand fra koden")
