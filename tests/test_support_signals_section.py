"""Forbeholdet hoistes ÉN gang — og kroppen beholder resten.

Sektionen blev udskilt fra `prompt_contract.py` 30/9-2026 da den blev flyttet
fra prompt-præfikset til halen. Hoisting-logikken er den del der let går tavst
i stykker: står forbeholdet i hver blok, klipper attention-budgettet det af
sammen med resten, og så står guardrailen NUL steder mens dataen bliver.
Det skete én gang og blev rettet 8/9-2026; disse tests holder det fast.
"""
from __future__ import annotations

from core.services.prompt_sections.support_signals_section import (
    SUBORDINAT,
    byg_support_indhold,
)


def test_ingen_blokke_giver_ingen_sektion():
    """Tomt skal give None, ikke et forbehold uden data.

    Budgettet udelader `None`; en streng med kun forbeholdet ville optage en
    sektionsplads for at sige ingenting."""
    assert byg_support_indhold(None) is None
    assert byg_support_indhold([]) is None


def test_forbeholdet_staar_foerst_og_kun_en_gang():
    ud = byg_support_indhold(["krop A", "krop B"])
    assert ud is not None
    assert ud.startswith(SUBORDINAT), ud[:80]
    assert ud.count(SUBORDINAT) == 1, f"forbeholdet gentages: {ud.count(SUBORDINAT)}x"
    assert "krop A" in ud and "krop B" in ud


def test_forbeholdet_fjernes_FRA_blokkene_naar_det_hoistes():
    """Kernen: hver bygger slutter selv med sætningen, og den må ikke blive
    liggende nede i kroppen hvor budgettet klipper den af."""
    ud = byg_support_indhold([f"krop A\n{SUBORDINAT}", f"{SUBORDINAT}\nkrop B"])
    assert ud is not None
    assert ud.count(SUBORDINAT) == 1, (
        f"forbeholdet blev ikke fjernet fra blokkene — {ud.count(SUBORDINAT)} forekomster")
    assert "krop A" in ud and "krop B" in ud, "kroppen forsvandt med forbeholdet"
    # og det skal staa OEVERST, ikke der hvor den foerste blok havde det
    assert ud.index(SUBORDINAT) == 0


def test_blokkenes_raekkefoelge_bevares():
    """Rækkefølgen er byggernes, ikke alfabetisk — en omrokering ville ændre
    præfikset for de sektioner der står efter i halen."""
    ud = byg_support_indhold(["foerst", "dernaest", "sidst"])
    assert ud is not None
    assert ud.index("foerst") < ud.index("dernaest") < ud.index("sidst")
