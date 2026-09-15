"""Matcheren forstod ikke dansk — og mekanismen havde været der hele tiden.

## Målt 15/9-2026

Otte rimelige danske formuleringer; seks fandt ingenting:

    «lav et regneark»        → INTET   (excel-automation findes)
    «lav en powerpoint»      → INTET   (pptx findes)
    «lav en praesentation»   → INTET
    «skriv et word-dokument» → fact-checker, tdd
    «undersoeg det grundigt» → INTET   (deep-research findes)
    «lav en pdf»             → pdf     ✓

De to der virkede havde det danske ord i selve navnet («pdf», «youtube»). De
øvrige kræver oversættelse: regneark er ikke excel, præsentation er ikke pptx.
Embedderen (`all-MiniLM-L6-v2`) er engelsk-centreret.

## Mekanismen fandtes

Matcheren splitter tosprogede `use_when` i per-sprog-fragmenter — designet var
der. **Ingen skill havde en `DA:`-linje.** Fjerde gang på én dag at noget
findes uden nogen der bruger det.

## Hvorfor tillægget ikke bor i SKILL.md

De fleste skills er leverandør-filer (`composio-*`, dokument-bundtet) og
overskrives ved opdatering. Tillægget ligger i repoet og flettes ind som et
ekstra kandidat-fragment.
"""
from __future__ import annotations

import pytest

from core.services import skill_engine
from core.tools import skill_dansk_tillaeg as dt
from core.tools.skill_engine_tools import _suggest_skills_for_query


#: Skills der findes paa PRODUKTIONSVAERTEN men ikke i repoet eller paa en
#: vilkaarlig udviklermaskine. Verificeret 15/9-2026 paa 10.0.0.39.
#:
#: Uden denne liste ville vagten fejle paa miljoe-forskel i stedet for paa en
#: aegte fejl — og en test der fejler af den forkerte grund bliver slaaet fra.
VAERT_LOKALE = {"pfsense-api"}


@pytest.fixture(scope="module")
def kendte() -> set[str]:
    """Alt vi kan bevise findes: installeret her + det repoet selv baerer."""
    skill_engine.reload_skills()
    installeret = {s["name"] for s in skill_engine.list_skills()}
    import pathlib as _p
    i_repo = {q.parent.name for q in _p.Path(".claude/skills").rglob("SKILL.md")}
    return installeret | i_repo | VAERT_LOKALE


# ───────────────────────────────────────────── vagten mod at listen rådner

def test_tillaegget_peger_kun_paa_skills_der_FINDES(kendte):
    """En håndholdt ordliste rådner. Et navn her uden et skill ville pege
    stille på noget der er fjernet — og ingen ville opdage det.

    Første udgave fejlede på `pfsense-api`, som findes i produktion men ikke på
    min maskine. Vagten var miljø-afhængig, ikke forkert i indhold — så den
    måler nu mod alt vi kan bevise findes, og navngiver de vært-lokale.
    """
    ukendte = sorted(set(dt.DANSKE_UDTRYK) - kendte)
    assert not ukendte, f"tillaeg for skills der ikke findes: {ukendte}"


def test_ingen_tomme_linjer():
    for navn, linje in dt.DANSKE_UDTRYK.items():
        assert linje.strip(), navn


def test_opslag_paa_ukendt_navn_giver_tom_streng():
    assert dt.dansk_udtryk("findes-ikke") == ""
    assert dt.dansk_udtryk("") == ""


# ──────────────────────────────────────────── de otte, som de blev målt

@pytest.mark.parametrize("spoergsmaal,forventet", [
    ("lav et regneark", "excel-automation"),
    ("lav en powerpoint", "pptx"),
    ("lav en pdf", "pdf"),
    ("skriv et word-dokument", "docx"),
    ("lav en praesentation", "pptx"),
    ("analyser et regneark", "excel-automation"),
    ("hent en youtube-video", "youtube-downloader"),
    ("undersoeg det grundigt", "deep-research"),
])
def test_dansk_formulering_finder_det_rigtige(kendte, spoergsmaal, forventet):
    if forventet not in kendte:
        pytest.skip(f"{forventet} er ikke installeret her")
    traef = _suggest_skills_for_query(query=spoergsmaal, threshold=0.30, max_results=3) or []
    navne = [t.get("name") for t in traef]
    assert forventet in navne, f"«{spoergsmaal}» → {navne}"


def test_smaasnak_matcher_stadig_ingenting():
    """Tillægget må ikke gøre matcheren løs. Flere kandidat-fragmenter
    betyder flere chancer for et tilfældigt træf."""
    for q in ["hej", "ok tak", "ja gerne", "godmorgen"]:
        assert not (_suggest_skills_for_query(query=q, threshold=0.30, max_results=3) or []), q
