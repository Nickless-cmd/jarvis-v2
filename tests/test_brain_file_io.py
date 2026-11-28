"""Tests for brain_file_io — frontmatter-parsing og atomisk skrivning.

Udskilt fra jarvis_brain.py 24/11-2026 saa `rebuild_index_from_files` kan skelne
en fil UDEN frontmatter (legacy/manuel skrivning) fra en fil der er korrupt.
Før kastede begge en ValueError, og opstartsloggen fik en traceback pr. fil.
"""
from __future__ import annotations

import os
import stat
import threading

import pytest

from core.services.brain_file_io import (
    MissingFrontmatterError,
    atomic_write,
    parse_frontmatter,
)


def test_manglende_frontmatter_faar_sin_egen_fejltype(tmp_path) -> None:
    """Den skal kunne skelnes fra en korrupt fil — derfor egen type."""
    p = tmp_path / "uden.md"
    p.write_text("# Legacy\n\nIngen frontmatter.\n", encoding="utf-8")

    with pytest.raises(MissingFrontmatterError):
        parse_frontmatter(p)


def test_fejltypen_arver_valueerror(tmp_path) -> None:
    """Bagudkompatibel: eksisterende kaldere fanger ValueError og skal virke."""
    p = tmp_path / "uden.md"
    p.write_text("ingen frontmatter\n", encoding="utf-8")

    assert issubclass(MissingFrontmatterError, ValueError)
    with pytest.raises(ValueError):
        parse_frontmatter(p)


def test_gyldig_frontmatter_parses(tmp_path) -> None:
    p = tmp_path / "med.md"
    p.write_text("---\nid: abc\nkind: fakta\n---\n\nbrødtekst\n", encoding="utf-8")

    fm, body = parse_frontmatter(p)

    assert fm["id"] == "abc"
    assert fm["kind"] == "fakta"
    assert body.strip() == "brødtekst"


def test_uafsluttet_frontmatter_er_en_valueerror(tmp_path) -> None:
    """Uafsluttet frontmatter er korrupt — ikke «mangler»."""
    p = tmp_path / "brudt.md"
    p.write_text("---\nid: abc\n\nbrødtekst uden afslutning\n", encoding="utf-8")

    with pytest.raises(ValueError) as exc:
        parse_frontmatter(p)
    assert not isinstance(exc.value, MissingFrontmatterError)


def test_atomisk_skrivning_opretter_mapper_og_indhold(tmp_path) -> None:
    p = tmp_path / "dyb" / "mappe" / "fil.md"

    atomic_write(p, "indhold")

    assert p.read_text(encoding="utf-8") == "indhold"
    assert not (tmp_path / "dyb" / "mappe" / "fil.md.tmp").exists()


def test_skrivningen_fsyncer_baade_fil_og_mappe(tmp_path, monkeypatch) -> None:
    """Uden fsync på mappen er rename ikke holdbar — målt 28/11-2026: to
    entries stod på 0 byte efter et nedbrud, mens indekset meldte 928."""
    ramte: list[bool] = []
    aegte = os.fsync

    def _fang(fd: int) -> None:
        ramte.append(stat.S_ISDIR(os.fstat(fd).st_mode))
        aegte(fd)

    monkeypatch.setattr(os, "fsync", _fang)

    atomic_write(tmp_path / "fil.md", "indhold")

    assert ramte.count(True) == 1, f"mappen blev ikke fsynket: {ramte}"
    assert ramte.count(False) == 1, f"filen blev ikke fsynket: {ramte}"


def test_samtidige_skrivninger_til_samme_sti_kaster_ikke(tmp_path) -> None:
    """Det faste ``path + ".tmp"``-navn er i sig selv en race: målt 275
    FileNotFoundError ud af 300 runder med to tråde, fordi den ene tråds
    rename stjæler den andens temp-fil."""
    p = tmp_path / "delt.md"
    fejl: list[BaseException] = []

    def _skriv(tekst: str) -> None:
        try:
            for _ in range(40):
                atomic_write(p, tekst)
        except BaseException as exc:  # noqa: BLE001 — fejlen rapporteres nedenfor
            fejl.append(exc)

    traade = [
        threading.Thread(target=_skriv, args=(tekst,))
        for tekst in ("a" * 200, "b" * 200)
    ]
    for traad in traade:
        traad.start()
    for traad in traade:
        traad.join()

    assert not fejl, f"skrivning kastede under samtidighed: {fejl!r}"
    assert p.read_text(encoding="utf-8") in {"a" * 200, "b" * 200}
    assert not list(tmp_path.glob("*.tmp")), "temp-fil efterladt på disken"
