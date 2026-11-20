"""`bundt_soeg` skal oversætte et byte-offset til en MODULSTI.

MÅLT 20/11-2026: reverse-engineering af GPT-appen gav et byte-offset fra
`grep -abo`, og svaret på «hvilket modul er det?» kom fra en node-parser der
blev skrevet ind i `/tmp/asar-x.js` og forsvandt med `/tmp`. Uden mappingen er
et offset ikke et svar — man ved ikke om man kigger på `dil_text` eller på en
tilfældig base64-streng.

Testen bygger en asar med kendt indhold, så mappingen kan måles i containeren
uden broen til Bjørns maskine. Layoutet er det samme som den ægte parser brugte
(se modulets docstring), så en grøn test her betyder at offset-regnestykket
stemmer — ikke at filen på hans maskine er læst.
"""

from __future__ import annotations

import json
import struct
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import bundt_soeg  # noqa: E402


def _byg_asar(sti: Path, filer: dict[str, bytes]) -> Path:
    """Skriv en minimal asar med samme layout som den ægte."""
    trae: dict = {"files": {}}
    poster: list[tuple[str, bytes, int]] = []
    offset = 0
    for navn in sorted(filer):
        poster.append((navn, filer[navn], offset))
        offset += len(filer[navn])
    for navn, data, off in poster:
        knude = trae
        dele = navn.split("/")
        for del_ in dele[:-1]:
            knude = knude["files"].setdefault(del_, {"files": {}})
        knude["files"][dele[-1]] = {"size": len(data), "offset": off}

    tekst = json.dumps(trae).encode("utf-8")
    header_stoerrelse = 8 + len(tekst)
    blob = (
        struct.pack("<I", 4)
        + struct.pack("<I", header_stoerrelse)
        + struct.pack("<I", 4)
        + struct.pack("<I", len(tekst))
        + tekst
    )
    sti.write_bytes(blob + b"".join(d for _, d, _ in poster))
    return sti


def test_offset_bilver_modulsti(tmp_path):
    """Et træf i den anden fil skal hedde den anden fils modulsti — ikke den første."""
    fil = _byg_asar(tmp_path / "app.asar", {
        "chatgpt_finance/src/FinanceDilWidget.js": b"const x = 'finance-widget';",
        "dil_text/src/rendering/DILStreamingText.js": b"const p = {duration:800, snappy:1};",
    })

    traef = bundt_soeg.soeg(fil, b"duration:800", kontekst=20, maks=5)

    assert len(traef) == 1
    assert traef[0]["modul"] == "dil_text/src/rendering/DILStreamingText.js"


def test_negativ_kontrol_tomt_svar_er_tomt(tmp_path):
    """En streng der ikke findes må give nul træf — ellers er et fund værdiløst."""
    fil = _byg_asar(tmp_path / "app.asar", {
        "dil_text/src/rendering/DILStreamingText.js": b"const p = {duration:800};",
    })

    assert bundt_soeg.soeg(fil, b"findes-ikke-nogensinde", kontekst=10, maks=5) == []


def test_modulstien_i_headeren_tildeles_ikke_et_modul(tmp_path):
    """Modulnavnet selv står i headeren, ikke i data. Det skal ikke pege på en fil."""
    fil = _byg_asar(tmp_path / "app.asar", {
        "dil_text/src/rendering/DILStreamingText.js": b"const p = 1;",
    })

    traef = bundt_soeg.soeg(fil, b"DILStreamingText", kontekst=10, maks=5)

    assert len(traef) >= 1
    assert traef[0]["modul"] == "", "et header-træf blev tilskrevet et modul"
    assert traef[0]["modul_offset"] < 0, "header-træffet ligger før data-start"


def test_raa_fil_uden_asar_header_soeges_stadig(tmp_path, capsys):
    """En almindelig tekstfil må ikke give nul træf — kun nul modulstier."""
    fil = tmp_path / "bundle.js"
    fil.write_text("var a=1; DILStreamingAnimation.Snappy;", encoding="utf-8")

    traef = bundt_soeg.soeg(fil, b"Snappy", kontekst=12, maks=5)

    assert len(traef) == 1
    assert traef[0]["modul"] == ""
    assert "ikke en asar" in capsys.readouterr().err


def test_liste_viser_moduler_og_deres_offsets(tmp_path, capsys):
    """`--liste` skal vise hver fils data-offset, så et offset kan slås op i hånden."""
    fil = _byg_asar(tmp_path / "app.asar", {
        "a/foerste.js": b"AAAA",
        "b/anden.js": b"BBBBBB",
    })

    kode = bundt_soeg._hoved(["--fil", str(fil), "--liste"])

    assert kode == 0
    ud = capsys.readouterr().out
    assert "a/foerste.js" in ud and "b/anden.js" in ud
    assert "2 filer" in ud


def test_soeg_fra_kommandolinjen_skriver_modulstien(tmp_path, capsys):
    """Kommandolinjen er den vej jeg faktisk bruger — den skal vise modulstien."""
    fil = _byg_asar(tmp_path / "app.asar", {
        "dil_text/src/rendering/DILStreamingText.js": b"snappyStreamingAnimations===!0",
    })

    kode = bundt_soeg._hoved(["--fil", str(fil), "--soeg", "snappyStreamingAnimations"])

    assert kode == 0
    ud = capsys.readouterr().out
    assert "dil_text/src/rendering/DILStreamingText.js" in ud
    assert "1 træf" in ud


def test_ugyldig_header_giver_ikke_modulstier(tmp_path, capsys):
    """En fil der ligner en asar men har ødelagt header må ikke give falske moduler."""
    fil = tmp_path / "oedelagt.asar"
    blob = struct.pack("<I", 4) + struct.pack("<I", 32) + b"x" * 32 + b"markoer"
    fil.write_bytes(blob)

    traef = bundt_soeg.soeg(fil, b"markoer", kontekst=5, maks=3)

    assert len(traef) == 1
    assert traef[0]["modul"] == ""
    assert "ikke en asar" in capsys.readouterr().err
