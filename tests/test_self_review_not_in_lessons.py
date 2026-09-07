"""Selvevalueringens tilstands-tællere hører ikke i lessons-lageret.

Målt LIVE i Bjørns prompt 7/9-2026. `[HUKOMMELSE]`-blokken indeholdt præcis
dette — og intet andet:

    Lektier (det jeg har lært af fejl — brug dem, og sig det hvis en gentager sig):
    - [self_review, x1] Mangel på nylige runs indikerer en træthed eller manglende motivation.
    - [self_review, x1] 7 åbne bedre områder viser en potensiel for uopnåede mål.
    - [self_review, x1] 3 åbne rupturer kræver en dybere analyse af grundlæggende problemer.

337 tegn i HVER prompt. Ingen af dem er en lektie fra en fejl: de genereres
fra tællere (`self_review_unified.py:110-127`) og beskriver en tilstand, ikke
en årsag. En LLM omskriver dem bagefter, hvilket gjorde det værre — to af de
tre er ikke grammatisk dansk.

Værst: de var det ENESTE i blokken. Så den lærte ham ingenting, og lærte ham
samtidig at ignorere den.

R4-reparationen 4/9 flyttede dem hertil fordi deres tidligere læser aldrig
blev kaldt. Det løste synligheden og skabte støjen.
"""

from __future__ import annotations

import inspect
import re


def test_selvevalueringen_skriver_ikke_til_lessons():
    from core.services import self_review_unified as SR

    kilde = inspect.getsource(SR)
    aktive = [l for l in kilde.splitlines()
              if "record_review_lessons" in l and not l.strip().startswith("#")]
    assert not aktive, (
        "selvevalueringen skriver igen til lessons-lageret: %s" % aktive
    )


def test_dens_egen_tabel_er_uroert():
    """Lektierne forsvinder ikke — de bliver hvor de hører hjemme.

    `lessons_json` i self_reviews-tabellen er selvevalueringens eget lager.
    Fjernede man DET, ville man tabe data i stedet for at flytte støj.
    """
    from core.services import self_review_unified as SR

    kilde = inspect.getsource(SR)
    assert "lessons_json" in kilde


def test_tilstands_taellerne_producerer_stadig_deres_tekst():
    """Selve selvevalueringen skal virke som før — kun ruten er ændret."""
    from core.services import self_review_unified as SR

    kilde = inspect.getsource(SR)
    assert re.search(r"lessons\.append\(", kilde), (
        "selvevalueringen genererer ikke laengere sine observationer"
    )


def test_lessons_lageret_er_forbeholdt_fejl_og_rettelser():
    """De to kilder der er tilbage er dem der handler om FEJL.

    `record_correction` (Bjørns rettelser) og `record_tool_error` (noget gik
    galt). Det er dét overskriften «det jeg har lært af fejl» lover.
    """
    from core.services import lessons as L

    kilde = inspect.getsource(L)
    assert "def record_correction" in kilde
    assert "def record_tool_error" in kilde
