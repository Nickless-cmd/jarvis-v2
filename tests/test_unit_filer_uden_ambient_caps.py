"""`AmbientCapabilities` må ikke komme tilbage i unit-filerne.

## Hvorfor en test på en systemd-fil

Linjen braekkede bash-sandkassen HELT, og fejlen var usynlig fra koden: ambient
capabilities arves ind i ETHVERT barn, ogsaa bwrap, og bubblewrap naegter
bevidst at koere med capabilities uden at vaere setuid. Hvert kald doede med

    bwrap: Unexpected capabilities but not setuid, old file caps config?

mens `status()` meldte «aktiv: True». Ingen test kunne se det, fordi problemet
ikke laa i Python — det laa i procesens capability-maske.

## Drift-faelden

Den INSTALLEREDE unit er ikke den her. Maalt 13/9-2026 koerte den installerede
`/home/bs/miniconda3/envs/ai/bin/uvicorn` mens repo-filen sagde
`/opt/conda/envs/ai/bin/uvicorn` — to forskellige Python-miljoeer — plus
afvigende `JARVIS_VOICE_ENABLED`, `MemoryMax` og `CPUQuota`.

Denne test vogter altsaa kun repo-siden. En aendring her aendrer INTET i drift
foer nogen redigerer `/etc/systemd/system/` og koerer `daemon-reload`.
"""
from __future__ import annotations

import pathlib

import pytest

UNITS = sorted(pathlib.Path("scripts").glob("jarvis-*.service"))


def test_der_ER_unit_filer_at_vogte():
    """En tom glob ville goere alle tests nedenfor groenne og tomme."""
    assert UNITS, "ingen jarvis-*.service fundet — er de flyttet?"


@pytest.mark.parametrize("unit", UNITS, ids=lambda p: p.name)
def test_ingen_AmbientCapabilities(unit: pathlib.Path):
    linjer = [l for l in unit.read_text().splitlines()
              if l.strip().startswith("AmbientCapabilities=")]
    assert linjer == [], (
        f"{unit.name} har AmbientCapabilities igen: {linjer}. "
        "Det braekker bash-sandkassen — bwrap naegter at koere med arvede "
        "capabilities uden at vaere setuid. Brug CapabilityBoundingSet i stedet; "
        "den begraenser, og arves ikke."
    )


@pytest.mark.parametrize("unit", UNITS, ids=lambda p: p.name)
def test_forklaringen_staar_i_filen(unit: pathlib.Path):
    """En fjernet linje uden en grund kommer tilbage naeste gang nogen «mangler
    rettigheder». Grunden skal staa hvor den naeste kigger."""
    tekst = unit.read_text()
    assert "INGEN AmbientCapabilities" in tekst, \
        f"{unit.name} mangler forklaringen paa hvorfor linjen ikke maa komme igen"
    assert "bubblewrap" in tekst or "bwrap" in tekst
