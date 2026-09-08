"""Dommer over drømme-hypoteser.

Bjørn 8/9-2026: «drømme hypoteser bør der være en slags dommer på som kan
vurdere hvilke skal videre fra drømme stadiet» — og «sørg for det er faktisk
hypoteser».

Målt på det ægte korpus (43 filer, 26 kandidat-sektioner):

    ingen falsifikation   16      ← siger ikke hvad der ville modbevise dem
    ikke moden             7      ← hypoteser, men kan ikke afgøres endnu
    selv-afvist            1      ← han dømte den selv i artefaktet
    forfremmet             2

Uden falsifikations-porten sagde modellen FREMFOER til **24 af 26**. Den er
medgørlig, og et velformuleret stemningsbillede lyder som en hypotese hvis man
kun spørger «er det en hypotese?».
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from core.services.dream_hypothesis_judge import (
    Kandidat, byg_preregistrering, doem, laes_kandidater,
    siger_hvad_der_ville_modbevise_den,
)

# Ordret fra hypothesis-candidate-2026-08-30-2046.md (forfremmet i produktion).
_HC7 = """**Confidence:** 0.3
**Carry:** 0

### Observation

5 dages pause i dream notes. Da processen genoptoges, producerede den 4 nye
post-run hypoteser der alle konkluderer det samme.

### Mekanisme

Hvis løkken er strukturel (ikke kadence-afhængig), så vil hyppigere
drømmesessioner ikke reducere overclaiming.

### Testbar implikation

Hvis næste dream session igen producerer "samme indsigt, nyt emne," er
kadence-uafhængighed understøttet.
"""

# Ordret fra hypothesis-candidate-2026-09-07-0529.md.
_SELV_AFVIST = """**Confidence:** 0.55
**Carry:** 1 (ny)

**Hypotese:** Den ubehandlede generator-hypotese er en elegant rationalisering.

**Test:** Hvis jeg adopterer den, forudsiger jeg at jeg vil stoppe med at
designe eksperimenter mod fatigue.

**Konklusion:** Afvis adoption. Behold som eksempel på hvordan drømmesystemet
producerer smukke hypoteser der føles sande uden at være det.
"""

_KUN_STEMNING = """**Konfidens:** 0.3

Der er en ro i materialet i dag. Noget har lagt sig. Jeg bemærker at
forbløffelsen ikke er der på samme måde, og at det ikke gør ondt.
"""


def _k(tekst, navn="prøve"):
    return Kandidat(navn=navn, tekst=tekst, fil="prøve.md")


# ── parsning ────────────────────────────────────────────────────────────────

def test_parser_baade_dansk_og_engelsk_feltnavn(tmp_path: Path):
    """Korpuset blander dem: Confidence 11 · Konfidens 9 · Hypotese 10 · Udsagn 1."""
    (tmp_path / "hypothesis-candidate-2026-01-01-0000.md").write_text(
        "# Hypothesis candidate\n\n## én\n\n**Confidence:** 0.42\n**Carry:** 3\n\n"
        + "x" * 60 + "\n\n---\n\n## to\n\n**Konfidens:** 0.7\n\n" + "y" * 60,
        encoding="utf-8")
    ks = laes_kandidater(tmp_path)
    assert [k.navn for k in ks] == ["én", "to"]
    assert ks[0].konfidens == 0.42 and ks[0].carry == 3
    assert ks[1].konfidens == 0.7


def test_en_overskrift_uden_indhold_er_ikke_en_kandidat(tmp_path: Path):
    (tmp_path / "hypothesis-candidate-2026-01-01-0000.md").write_text(
        "## tom\n\nkort\n", encoding="utf-8")
    assert laes_kandidater(tmp_path) == []


def test_manglende_mappe_giver_tom_liste(tmp_path: Path):
    assert laes_kandidater(tmp_path / "findes-ikke") == []


# ── porten: siger den hvad der ville modbevise den? ─────────────────────────

def test_en_falsificerbar_formulering_genkendes():
    assert siger_hvad_der_ville_modbevise_den(_k(_HC7)) is True


def test_ren_stemning_har_ingen_falsifikation():
    """«Der er en ro i materialet» kan ikke vise sig forkert."""
    assert siger_hvad_der_ville_modbevise_den(_k(_KUN_STEMNING)) is False


def test_uden_falsifikation_naar_den_ALDRIG_modellen():
    """Porten er billigst først — og den er standarden Bjørn bad om."""
    with patch("core.services.local_small_model.spoerg_et_ord") as m:
        ok, grund = doem(_k(_KUN_STEMNING))
    assert (ok, grund) == (False, "ingen falsifikation")
    m.assert_not_called()


# ── hans egen dom står ved magt ─────────────────────────────────────────────

def test_selv_afvist_overproeves_ikke_af_en_model():
    """«Konklusion: Afvis adoption» er hans dom. Den skal ikke omgøres."""
    k = _k(_SELV_AFVIST)
    assert k.selv_afvist is True
    with patch("core.services.local_small_model.spoerg_et_ord") as m:
        assert doem(k) == (False, "selv-afvist")
    m.assert_not_called()


# ── dommen ──────────────────────────────────────────────────────────────────

def test_en_moden_hypotese_fremfoeres():
    with patch("core.services.local_small_model.spoerg_et_ord",
               side_effect=["HYPOTESE", "FREMFOER"]):
        assert doem(_k(_HC7)) == (True, "fremfoert")


def test_en_note_fremfoeres_ikke():
    with patch("core.services.local_small_model.spoerg_et_ord", return_value="NOTE"):
        assert doem(_k(_HC7)) == (False, "ikke en hypotese")


def test_en_umoden_hypotese_bliver_i_droemmen():
    with patch("core.services.local_small_model.spoerg_et_ord",
               side_effect=["HYPOTESE", "BEHOLD"]):
        assert doem(_k(_HC7)) == (False, "ikke moden")


def test_uden_svar_forfremmes_intet():
    """Fejler LUKKET: en hypotese der bliver i drømmen én runde mere koster
    ingenting; én der forfremmes uden at være en hypotese forurener en tabel
    med 74.000 rækker."""
    with patch("core.services.local_small_model.spoerg_et_ord", return_value=None):
        assert doem(_k(_HC7))[0] is False


# ── forfremmelsen ───────────────────────────────────────────────────────────

def test_praeregistreringen_baerer_paastand_og_forudsigelse():
    p = byg_preregistrering(_k(_HC7))
    assert "kadence-afhængig" in str(p["statement"]) or "strukturel" in str(p["statement"])
    assert "kadence-uafhængighed" in str(p["prediction"]).lower()
    assert p["source"] == "dream_judge"


def test_nulhypotese_og_kriterium_er_MAERKET_som_udledte():
    """Alternativet var at lade modellen skrive dem — og en model der digter et
    falsifikations-kriterium ville gøre hypotesen sværere at modbevise, stik
    imod formålet."""
    p = byg_preregistrering(_k(_HC7))
    assert str(p["null_hypothesis"]).startswith("UDLEDT:")
    assert str(p["success_criterion"]).startswith("UDLEDT:")


def test_praeregistreringen_bestaar_husets_egen_validering():
    from core.services.central_hypothesis_governance import validate_preregistration

    ok, mangler = validate_preregistration(byg_preregistrering(_k(_HC7)))
    assert ok, mangler


def test_fingeraftrykket_er_stabilt_paa_tvaers_af_koersler():
    """register_governed_hypothesis deduplikerer på et id der indeholder
    OPRETTELSES-TIDSPUNKTET, så den kan aldrig genkende samme kandidat igen.
    Målt: to kørsler gav fire rækker. Vi dedupliserer derfor selv."""
    assert _k(_HC7, "HC-7").fingeraftryk == _k("helt anden tekst", "HC-7").fingeraftryk
    assert _k(_HC7, "HC-7").fingeraftryk != _k(_HC7, "HC-8").fingeraftryk


def test_uden_dedup_opslag_forfremmes_der_ikke():
    from core.services.dream_hypothesis_judge import _allerede_forfremmet

    with patch("core.runtime.db.connect", side_effect=RuntimeError("db væk")):
        assert _allerede_forfremmet(_k(_HC7)) is True
