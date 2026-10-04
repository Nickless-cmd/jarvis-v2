"""Vagten på de fire flyttede præfiks-sektioner (Bjørn 4/10-2026).

Flytningen var en nettogevinst UDELUKKENDE fordi de målte nul ændringer:

    sparer   900 tokens × 99 ture × $0,147/M  =  $0,0131
    koster   ÉN ændring: 120.064 tokens miss  =  $0,0176

Et skift sidst i præfikset invaliderer hele samtalehistorikken ovenpå, fordi
cachen matcher på længste fælles præfiks. Så én ændring per 99 ture gør
flytningen til et tab — og uden vagten ville det ske i tavshed.
"""
from __future__ import annotations

import logging

import pytest

from core.services import praefiks_stabilitet as ps


@pytest.fixture(autouse=True)
def rent():
    ps.nulstil()
    yield
    ps.nulstil()


def _felter(s: str) -> dict[str, str]:
    return dict(x.split("=", 1) for x in s.split() if "=" in x)


def test_foerste_tur_registrerer_uden_at_melde_skift():
    f = _felter(ps.tjek([("A", "x"), ("B", "y")]))
    assert f["stabile"] == "2"
    assert f["stabil_skift"] == "0"


def test_uaendret_indhold_giver_INGEN_skift():
    ps.tjek([("A", "x")])
    assert _felter(ps.tjek([("A", "x")]))["stabil_skift"] == "0"


def test_en_AENDRING_ses_og_navngives(caplog):
    ps.tjek([("A", "x"), ("B", "y")])
    with caplog.at_level(logging.WARNING):
        f = _felter(ps.tjek([("A", "NYT"), ("B", "y")]))
    assert f["stabil_skift"] == "1"
    assert f["stabil_skiftede"] == "A"
    # Navnet SKAL med i loggen — ellers ved man at noget skred, men ikke hvad.
    assert any("«A»" in r.message for r in caplog.records), \
        "loggen navngiver ikke sektionen"


def test_den_TAELLER_op_ved_gentagne_skift():
    """En sektion der skifter ÉN gang kan være tilfældig. En der skifter hver
    tur er et argument for at flytte den tilbage, og tallet er argumentet."""
    ps.tjek([("A", "1")])
    for i in range(2, 6):
        ps.tjek([("A", str(i))])
    assert _felter(ps.tjek([("A", "9")]))["stabil_skift"] == "5"


def test_skift_i_FLERE_sektioner_navngiver_dem_alle():
    ps.tjek([("A", "x"), ("B", "y")])
    f = _felter(ps.tjek([("A", "1"), ("B", "2")]))
    assert f["stabil_skift"] == "2"
    assert set(f["stabil_skiftede"].split(",")) == {"A", "B"}


def test_den_vokser_ikke_i_det_uendelige():
    """En omdøbt sektion ville ellers lægge en ny nøgle for hver tur."""
    for i in range(ps._MAKS + 20):
        ps.tjek([(f"sektion-{i}", "x")])
    assert len(ps._set) <= ps._MAKS


def test_den_kaster_ALDRIG():
    """Et instrument der kan vælte det det måler er værre end ingen måling."""
    for skrald in (None, [], [("", "")], [(None, None)], "ikke en liste"):
        ps.tjek(skrald)  # type: ignore[arg-type]


def test_vagten_er_KOBLET_paa_assemblyen():
    """Husets hyppigste fejl: koden er rigtig og ingen kalder den."""
    import ast
    import pathlib
    kilde = pathlib.Path("core/services/prompt_contract.py").read_text()
    traeet = ast.parse(kilde)
    navne = {n.name for x in ast.walk(traeet)
             if isinstance(x, ast.ImportFrom) for n in x.names}
    assert "praefiks_stabilitet" in navne, "vagten importeres ikke"
    assert "_stabil_felter" in kilde
    # Felterne faar deres EGEN linje: timing-linjen skrives ~500 linjer foer
    # partitionen i samme funktion, saa feltet ville vaere ubundet dér. Den
    # fejl ser ud som en lille omflytning og er en UnboundLocalError.
    assert "prompt-praefiks-stabilitet" in kilde, "vagten skriver ingen linje"
    i = kilde.index("prompt-praefiks-stabilitet")
    assert "{_stabil_felter}" in kilde[i:i + 120], "linjen baerer ikke felterne"


def test_den_tjekker_PRAECIS_de_flyttede_sektioner():
    """Vagten skal følge `_STABILE_I_HALEN` — ikke have sin egen liste. To
    lister ville drive fra hinanden, og så ville vagten passe på noget andet
    end det der blev flyttet."""
    import pathlib
    kilde = pathlib.Path("core/services/prompt_contract.py").read_text()
    i = kilde.index("_ps.tjek(")
    blok = kilde[i:i + 400]
    assert "_STABILE_I_HALEN" in blok, "vagten bruger ikke den flyttede liste"
    assert "_stabile" in blok, "vagten tjekker ikke de faktisk flyttede tekster"
