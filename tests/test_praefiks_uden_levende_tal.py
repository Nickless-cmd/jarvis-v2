"""Den CACHEBARE praefiks maa ikke baere levende tal.

## Hvorfor vagten findes

Samme fejl er rettet TRE gange:

  * 2026-05-22 — CONTINUITY-mood ved byte 78.924 var «den primaere
    cache-draeber». Rettet ved at afrunde mood til 0,1. Halvdelen af
    problemet; gap-strengen skiftede stadig.
  * 2026-07-16 — `_dyn_tail` blev initialiseret UNDER fem tail-maerkede
    sektioner, saa de med live decimaler (tick-kvalitet, vaekstpuls) endte i
    HOVEDET. Visible ramte 35,9 % cache-hit.
  * 2026-09-28 — vaekke-blokken, kroeniken og droemmeresten laa stadig i
    praefikset. Foerste kald i et run ramte 50,3 % mod opfoelgningernes
    84,9 %; den foerste systembesked havde tre hashes med naesten samme
    laengde. Blok 26 af 33 (79 % inde) var den foerste der afveg.
  * 2026-09-30 — TOOL-KATALOGET («KERNE-VAERKTOEJER») laa som den SIDSTE
    sektion i praefikset. Dets laengde er et fingeraftryk af tool-scopet
    (1.728/2.479/4.231 tegn), og byggede man praefikset med to scopes afveg
    de foerst paa tegn 30.441 — inde i kataloget, med alt foer byte-identisk.
    31 af 54 nye aabner-praefikser havde et system der aldrig var sendt foer:
    9,8 % hit, 2,70 mio miss. Flyttet til halen; praefikset er nu identisk
    paa tvaers af alle fire scopes (30.206 tegn, samme sha).

Hver gang blev det fundet ved at maale en regning, ikke ved at laese koden.
Derfor den her: en sektion med et tal der aendrer sig hoerer i halen, og det
kan efterproeves uden at vente paa en faktura.

## Hvad den IKKE paastaar

Den siger ikke at praefikset skal vaere tomt for tal. Modelnavn, versioner og
faste taerskler staar der med rette. Den leder efter de MOENSTRE der beviseligt
har brudt cachen: minut-/dag-taellere og mood-decimaler.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from core.services.prompt_contract import DYNAMIC_TAIL_SENTINEL

#: Moenstre der beviseligt har brudt cachen. Hver har en sag bag sig.
LEVENDE = [
    ("gap-streng («0 min since last session»)", re.compile(r"\d+\s*min since last session")),
    ("dagtaeller («(3 dage siden)»)", re.compile(r"\(\d+ dage siden\)")),
    ("mood-decimal («curiosity=0.9»)", re.compile(r"(curiosity|fatigue|frustration|confidence)=\d")),
]


def _praefiks(tekst: str) -> str:
    """Alt FOER tail-markoeren — det er dét DeepSeek kan cache."""
    return tekst.partition(DYNAMIC_TAIL_SENTINEL)[0]


def test_markoeren_findes_overhovedet():
    """Uden markoer er der ingen grænse at maale paa, og vagten ville vaere
    tavst virkningsloes."""
    assert DYNAMIC_TAIL_SENTINEL.strip()


@pytest.mark.parametrize("navn,moenster", LEVENDE, ids=[n for n, _ in LEVENDE])
def test_moensteret_fanges_hvis_det_staar_i_praefikset(navn, moenster):
    """Selve vagten, proevet paa en konstrueret samling — saa testen ikke
    afhaenger af hvad maskinens tilstand tilfaeldigvis indeholder lige nu."""
    daarlig = f"stabil identitet\n▲ CONTINUITY — Quick return (0 min since last session)\n" \
              f"  Mood: curiosity=0.9\n### 2026-W40 (0 dage siden)\n" \
              f"{DYNAMIC_TAIL_SENTINEL}\nhalen"
    assert moenster.search(_praefiks(daarlig)), f"{navn}: vagten ser ikke moensteret"

    god = f"stabil identitet\n{DYNAMIC_TAIL_SENTINEL}\n" \
          f"▲ CONTINUITY — Quick return (0 min since last session)\n" \
          f"  Mood: curiosity=0.9\n### 2026-W40 (0 dage siden)"
    assert not moenster.search(_praefiks(god)), f"{navn}: falsk alarm naar den ligger i halen"


def test_vaekke_blokken_bygges_ind_i_halen_og_ikke_i_praefikset():
    """AST paa kildeteksten: hvor appendes vaekke-blokken?

    Ikke en grep — `parts.append` staar hundredvis af steder i filen. Her
    findes de konkrete kald og deres modtager.
    """
    import ast
    import inspect
    import core.services.prompt_contract as pc

    kilde = inspect.getsource(pc)
    traeet = ast.parse(kilde)
    modtagere: list[str] = []
    for node in ast.walk(traeet):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == "append"):
            continue
        if not isinstance(node.func.value, ast.Name):
            continue
        for arg in node.args:
            if isinstance(arg, ast.Name) and arg.id in {
                "wake_block", "chronicle_section", "dream_residue_section",
                "_catalog_text",
            }:
                modtagere.append(f"{node.func.value.id}:{arg.id}")

    assert modtagere, "fandt ingen af de tre sektioner — er de omdoebt?"
    for m in modtagere:
        assert m.startswith("_dyn_tail:"), (
            f"{m} appendes til praefikset. Sektionen baerer levende tal og "
            f"bryder DeepSeeks cache — den hoerer i _dyn_tail.")


def test_tool_kataloget_ligger_i_halen_og_ikke_i_praefikset():
    """Fjerde sag (30/9-2026): katalogets laengde ER tool-scopet.

    Maalt FOER flytningen: praefiks 34.439 / 31.936 / 32.687 / 34.439 tegn for
    ''/chat/code/cowork — fire forskellige hashes, og den foerste afvigelse
    mellem to af dem laa paa tegn 30.441, inde i kataloget. EFTER: 30.206 tegn
    og samme sha for alle fire.

    Testen laaser begge halvdele: kataloget skal BLIVE i prompten (modellen skal
    stadig kunne se hvad der findes og kan hentes), men ligge EFTER markoeren.
    """
    from core.services.prompt_contract import build_visible_chat_prompt_assembly

    a = build_visible_chat_prompt_assembly(
        provider="deepseek", model="deepseek-v4-flash",
        user_message="hej", session_id=None,
    )
    tekst = a.text or ""
    assert "KERNE-VÆRKTØJER" in tekst, "kataloget forsvandt helt fra prompten"
    assert "KERNE-VÆRKTØJER" not in _praefiks(tekst), (
        "kataloget staar i praefikset igen — dets laengde foelger tool-scopet, "
        "saa et scope-skift braekker hele vaerktoejs-arrayet + samtalen")
