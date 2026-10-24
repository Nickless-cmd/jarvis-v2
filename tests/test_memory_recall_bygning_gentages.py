"""En fejlet md-vecs-bygning må ikke gentages ved hvert kald.

Målt 24/10-2026: `_build()`s `except` nulstillede `building=False` men satte
aldrig `mtime`. Næste kald så derfor `mtime != cached` og startede en helt ny
bygning af de samme 6.348 linjer — 195 sekunder, hver tur, i det uendelige.

Det er formen der gør en engangsomkostning kronisk: fejlen efterlader ingen
markør, så systemet kan ikke se at det allerede har prøvet.

To ting skal holde:

1. En fejlet bygning efterlader `failed_mtime`, så den ikke straks gentages.
2. Når filen ændrer sig (nyt mtime), skal den prøve IGEN — ellers ville et
   midlertidigt fejl blokere cachen for evigt.
"""

from __future__ import annotations

import time

import pytest


@pytest.fixture()
def mr(tmp_path, monkeypatch):
    """Isolerer modulet: egen MEMORY.md, tom cache, ingen rigtig embedding."""
    from core.services.prompt_sections import memory_recall as m

    md = tmp_path / "MEMORY.md"
    md.write_text("linje et\nlinje to\nlinje tre\n", encoding="utf-8")

    # `_md_line_vecs` importerer `workspace_dir` INDE i funktionen, så patchen
    # skal ramme kildemodulet — ikke dette modul.
    import core.runtime.workspace_paths as wp

    monkeypatch.setattr(wp, "workspace_dir", lambda *a, **k: tmp_path, raising=False)
    monkeypatch.setattr(m, "_memory_md_lines", lambda uid="": ["linje et", "linje to"])
    monkeypatch.setattr(m, "_load_md_vecs_from_disk", lambda uid="": {})
    with m._MD_VECS_LOCK:
        m._MD_VECS_CACHE.clear()
    return m, md


def _vent_til_bygning_faerdig(m, timeout: float = 3.0) -> None:
    slut = time.monotonic() + timeout
    while time.monotonic() < slut:
        with m._MD_VECS_LOCK:
            if not m._MD_VECS_CACHE.get("building"):
                return
        time.sleep(0.01)
    raise AssertionError("bygningen blev aldrig færdig")


def test_fejlet_bygning_gentages_ikke(mr, monkeypatch) -> None:
    """Kernen: andet kald må ikke starte en ny bygning af samme mtime."""
    m, _md = mr
    kald = {"n": 0}

    def _boom(tekster):
        kald["n"] += 1
        raise RuntimeError("embed-motoren er nede")

    import core.services.jarvis_brain as jb

    monkeypatch.setattr(jb, "_embed_texts", _boom)

    m._md_line_vecs()
    _vent_til_bygning_faerdig(m)

    with m._MD_VECS_LOCK:
        assert m._MD_VECS_CACHE.get("failed_mtime") is not None, (
            "en fejlet bygning efterlod ingen markør — så gentages den ved hvert kald"
        )
    foerste = kald["n"]
    assert foerste == 1, f"første kald skulle forsøge én gang, fik {foerste}"

    # Samme mtime, nyt kald: må IKKE forsøge igen.
    m._md_line_vecs()
    time.sleep(0.1)
    assert kald["n"] == foerste, (
        f"bygningen blev forsøgt igen for samme mtime ({kald['n']} kald i alt) — "
        "det er den kroniske form målt 24/10-2026"
    )


def test_nyt_mtime_proever_igen(mr, monkeypatch) -> None:
    """Et midlertidigt fejl må ikke blokere cachen for evigt."""
    m, md = mr
    kald = {"n": 0}

    def _boom(tekster):
        kald["n"] += 1
        raise RuntimeError("nede")

    import core.services.jarvis_brain as jb

    monkeypatch.setattr(jb, "_embed_texts", _boom)

    m._md_line_vecs()
    _vent_til_bygning_faerdig(m)
    foerste = kald["n"]

    # Filen ændrer sig → nyt mtime → den SKAL prøve igen.
    time.sleep(0.02)
    md.write_text("linje et\nlinje to\nlinje tre\nlinje fire\n", encoding="utf-8")
    m._md_line_vecs()
    _vent_til_bygning_faerdig(m)

    assert kald["n"] > foerste, (
        "et nyt mtime blev ikke forsøgt — så ville ét fejl blokere cachen permanent"
    )


def test_gemme_fejl_meldes_ikke_tavst(mr, monkeypatch) -> None:
    """En fejlende disk-gemning skal meldes, ikke sluges med `pass`."""
    m, _md = mr
    kald = []
    monkeypatch.setattr(m.logger, "warning", lambda *a, **k: kald.append(a))

    # Et objekt kan ikke pickles → _save_md_vecs_to_disk rammer sin except-gren
    # uden at vi skal efterligne filsystemet.
    m._save_md_vecs_to_disk({"a": lambda: None})

    assert kald, "en fejlet gemning blev slugt — pkl kan stå stille i dage uden spor"
    assert "gemme" in str(kald[0]), f"advarslen nævner ikke gemningen: {kald[0]}"
