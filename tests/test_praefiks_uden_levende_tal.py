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


def test_support_signals_ligger_i_halen_og_ikke_i_praefikset(monkeypatch):
    """Femte sag (30/9-2026): sektionens indhold afgoeres af et KAPLOEB.

    Bygningen er cappet (`_HOT_RESOLVE_CAP_S`), og rammes deadline'en beholdes
    kun de under-sektioner der NAAEDE at blive faerdige — resten loeber videre i
    baggrunden. Hvilke der naaede det varierer fra tur til tur.

    Maalt paa CT105 efter katalog-flytningen: to praefiks-varianter, 30.204 og
    30.206 tegn. Foerste forskel laa i chunk 29 af 30 — 98 % inde i
    systemblokken. Alligevel overlevede kun 33 % af praefikset, og hit faldt
    89,5 % -> 79,2 %: to tegn i systemblokkens hale kostede hele
    vaerktoejsarrayet OG hele samtalen.

    Testen laaser begge halvdele: forbeholdet skal BLIVE i prompten (det er en
    guardrail modellen skal se), men ligge EFTER markoeren.
    """
    from core.services import prompt_contract as pc
    from core.services.prompt_sections.support_signals_section import SUBORDINAT

    # INDSPROEJTET, ikke haabet paa. Foerste udgave af denne test byggede
    # prompten som den var og krævede at forbeholdet stod der — den bestod
    # isoleret og FALDT i fuld suite, fordi support-byggerne intet producerer
    # under test-fixtures. En vagt der afhaenger af miljoeet maaler ikke
    # placering; den maaler held. Her tvinges sektionen frem, saa kun
    # PLACERINGEN er under maaling.
    _blok = SUBORDINAT + "\nRuntime awareness support signal: probe."

    def _fake(*, compact, include, user_message="", session_id=None, acc=None):
        if acc is not None:
            acc.append(_blok)
        return [_blok]

    monkeypatch.setattr(pc, "_visible_support_signal_sections", _fake)
    a = pc.build_visible_chat_prompt_assembly(
        provider="deepseek", model="deepseek-v4-flash",
        user_message="hej", session_id=None,
    )
    tekst = a.text or ""
    assert SUBORDINAT in tekst, "den indsproejtede sektion naaede slet ikke prompten"
    assert SUBORDINAT not in _praefiks(tekst), (
        "support_signals staar i praefikset igen — dens indhold er et "
        "tids-snapshot, saa et kaploeb afgoer praefikset og braekker "
        "vaerktoejs-arrayet + samtalen")


def test_halen_faar_den_BUDGET_klippede_support_ikke_den_raa():
    """Loftet maa ikke forsvinde med flytningen.

    `support_signals` kostede 27,4 s af en 30,8-sekunders kold opbygning foer
    den blev cappet, og attention-budgettet klipper den til sit loft. Halen skal
    derfor faa `selected[...]` — ikke `support_content`, som er det uklippede
    indhold. Forskellen er usynlig i placeringen, saa den maales paa kilden.
    """
    import ast
    from pathlib import Path

    from core.services.prompt_sections.section_placement import (
        HALE_SEKTIONER,
        PRAEFIKS_SEKTIONER,
    )

    # 1) placeringen er DATA — de to maa ikke overlappe, og de volatile skal
    #    staa i halen.
    assert not (set(HALE_SEKTIONER) & set(PRAEFIKS_SEKTIONER)), (
        "en sektion staar baade i praefikset og i halen")
    for navn in ("support_signals", "self_report"):
        assert navn in HALE_SEKTIONER, f"{navn} er ikke i halen laengere"
        assert navn not in PRAEFIKS_SEKTIONER, f"{navn} er tilbage i praefikset"

    # 2) og halen skal faa den BUDGET-klippede vaerdi. Loftet findes fordi
    #    `support_signals` kostede 27,4 s af en 31-sekunders kold opbygning;
    #    gav man halen det raa indhold, forsvandt loftet uden at noget fejlede.
    kilde = Path(
        "core/services/prompt_sections/section_placement.py"
    ).read_text(encoding="utf-8")
    traeet = ast.parse(kilde)
    hale_kilder = []
    for node in ast.walk(traeet):
        if not isinstance(node, ast.Call):
            continue
        f = node.func
        if not (isinstance(f, ast.Attribute) and f.attr == "append"):
            continue
        if not (isinstance(f.value, ast.Name) and f.value.id == "dyn_tail"):
            continue
        hale_kilder.append(ast.unparse(node.args[0]) if node.args else "")
    assert hale_kilder, "ingen dyn_tail.append i placerings-modulet"
    for udtryk in hale_kilder:
        assert udtryk == "indhold", f"halen faar {udtryk!r}, ikke den valgte vaerdi"
    assert "selected.get(navn)" in kilde, (
        "indhold hentes ikke fra `selected` — budgettets loft er omgaaet")
