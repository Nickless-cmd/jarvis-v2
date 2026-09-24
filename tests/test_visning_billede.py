"""Tests for /visning/billede — billeder fra Jarvis' egen maskine til desk.

Ruten er broens modstykke på serveren: desk kan læse lokale filer gennem
`electron/billede.ts`, men Jarvis' egne skærmbilleder ligger i temp-mappen på
SERVEREN. Uden den kunne man ikke se det samme som Jarvis.

Testen holder især hvidlisten fast: ruten må ikke blive en fil-browser.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from apps.api.jarvis_api.routes import visning

app = FastAPI()
app.include_router(visning.router)
client = TestClient(app)

PNG = b"\x89PNG\r\n\x1a\n" + b"x" * 64


@pytest.fixture(autouse=True)
def hjem_og_temp(tmp_path, monkeypatch):
    """Flyt BEGGE rødder ned i tmp_path, så testen ikke rører de rigtige."""
    hjem = tmp_path / "hjem"
    temp = tmp_path / "temp"
    hjem.mkdir()
    temp.mkdir()
    monkeypatch.setattr(visning, "JARVIS_HOME", hjem)
    monkeypatch.setattr(visning.tempfile, "gettempdir", lambda: str(temp))
    return hjem, temp


def _skriv(sti: Path, data: bytes = PNG) -> Path:
    sti.parent.mkdir(parents=True, exist_ok=True)
    sti.write_bytes(data)
    return sti


def _hent(sti: Path):
    return client.get("/visning/billede", params={"sti": str(sti)})


# ── Det der skal virke ────────────────────────────────────────────────────

def test_billede_i_jarvis_hjem(hjem_og_temp):
    hjem, _ = hjem_og_temp
    fil = _skriv(hjem / "uploads" / "skarm.png")
    r = _hent(fil)
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/png"
    assert r.content == PNG


def test_tempfil_med_jarvis_prefix(hjem_og_temp):
    # Præcis det mønster operator_tools.py bruger til skærmbilleder.
    _, temp = hjem_og_temp
    fil = _skriv(temp / "jarvisx-window-1790265530568.png")
    assert _hent(fil).status_code == 200


def test_alle_billed_endelser_godtages(hjem_og_temp):
    hjem, _ = hjem_og_temp
    for navn in ("a.png", "b.jpg", "c.jpeg", "d.webp", "e.gif", "f.avif"):
        assert _hent(_skriv(hjem / navn)).status_code == 200, navn


# ── Det der skal afvises ──────────────────────────────────────────────────

def test_tempfil_uden_jarvis_prefix_afvises(hjem_og_temp):
    # Ellers kunne enhver fil i en delt temp-mappe hentes gennem API'et.
    _, temp = hjem_og_temp
    fil = _skriv(temp / "fremmed.png")
    assert _hent(fil).status_code == 403


def test_udenfor_roedderne_afvises(hjem_og_temp, tmp_path):
    fil = _skriv(tmp_path / "udenfor" / "billede.png")
    assert _hent(fil).status_code == 403


def test_ikke_billed_endelse_afvises(hjem_og_temp):
    hjem, _ = hjem_og_temp
    fil = hjem / "hemmelig.txt"
    fil.write_text("nej")
    assert _hent(fil).status_code == 403


def test_path_traversal_afvises(hjem_og_temp):
    # Stien SER ud som om den ligger i hjem, men peger ud af det.
    hjem, _ = hjem_og_temp
    udenfor = _skriv(hjem.parent / "hemmelig.png")
    assert udenfor.exists()
    assert _hent(hjem / ".." / "hemmelig.png").status_code == 403


def test_relativ_sti_afvises():
    assert client.get("/visning/billede", params={"sti": "uploads/x.png"}).status_code == 403


def test_tom_sti_afvises():
    assert client.get("/visning/billede", params={"sti": ""}).status_code == 403


def test_findes_ikke_giver_404(hjem_og_temp):
    hjem, _ = hjem_og_temp
    assert _hent(hjem / "vaek.png").status_code == 404


def test_for_stort_afvises(hjem_og_temp, monkeypatch):
    hjem, _ = hjem_og_temp
    monkeypatch.setattr(visning, "_LOFT", 10)
    assert _hent(_skriv(hjem / "stor.png")).status_code == 413


# ── Reglen som ren funktion ───────────────────────────────────────────────

def test_tilladt_sti_er_ren(hjem_og_temp):
    hjem, _ = hjem_og_temp
    fil = _skriv(hjem / "x.png")
    assert visning.tilladt_sti(str(fil)) == fil.resolve()
    assert visning.tilladt_sti("/etc/passwd") is None
    assert visning.tilladt_sti("") is None
