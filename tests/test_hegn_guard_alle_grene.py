"""Hegn-guarden skal sætte ``` om en bar `jarvis-ui {…}` — på ALLE grene.

Målt 25/10-2026 (Bjørn): en bar blok slap igennem til klienten og fejlede i
renderen. Guarden fandtes, men blev kun kaldt i first-pass-grenen og kun når
`fejl_i_flader` havde fundet en JSON-fejl. En bar form er ikke en JSON-fejl,
så den blev aldrig set.

Disse tests værner to ting:
1. Den mekaniske reparation sætter hegn på den bare form (indhold urørt).
2. Den rører IKKE prosa-omtaler — en sætning der nævner `jarvis-ui {…}` skal
   ikke forvandles til en flade.
"""

from __future__ import annotations

import ast
from pathlib import Path

from core.services.flade_korrektion import _mekanisk_reparation

VISIBLE_RUNS = Path(__file__).resolve().parents[1] / "core" / "services" / "visible_runs.py"

FENCE = "`" * 3


def test_bar_blok_faar_hegn() -> None:
    """Den form Bjørn så: `jarvis-ui {…}` uden hegn foran."""
    raa = 'Her er fladen:\n\njarvis-ui {"type":"timeline","title":"Test"}\n\nOg lidt prosa.'
    rettet = _mekanisk_reparation(raa)
    assert f"{FENCE}jarvis-ui" in rettet, "hegnet blev ikke sat"
    assert '{"type":"timeline","title":"Test"}' in rettet, "indholdet blev ændret"
    assert rettet.count(FENCE) == 2, "der skal være præcis ét åbnings- og ét lukke-hegn"


def test_indholdet_er_byte_identisk() -> None:
    """Reparationen må kun tilføje hegn — aldrig røre JSON'en."""
    json_del = '{"type":"comparison","title":"T","columns":["a","b"],"rows":[]}'
    rettet = _mekanisk_reparation(f"jarvis-ui {json_del}")
    assert json_del in rettet


def test_prosa_omtale_roeres_ikke() -> None:
    """En sætning der NÆVNER formen er ikke en blok."""
    prosa = "Jeg skrev `jarvis-ui {…}` i svaret, men det virkede ikke."
    assert _mekanisk_reparation(prosa) == prosa


def test_allerede_hegnet_blok_roeres_ikke() -> None:
    """En korrekt blok skal stå urørt — ellers ville vi ødelægge det der virker."""
    korrekt = f'{FENCE}jarvis-ui\n{{"type":"timeline"}}\n{FENCE}'
    assert _mekanisk_reparation(korrekt) == korrekt


def test_hegn_indeni_hegn_roeres_ikke() -> None:
    """En linje inde i et eksisterende hegn er kode, ikke en bar blok."""
    tekst = f'{FENCE}python\njarvis-ui {{"type":"x"}}\n{FENCE}'
    assert _mekanisk_reparation(tekst) == tekst


def test_begge_grene_kalder_hegn_reparationen() -> None:
    """Source-regression: guarden skal stå på BEGGE udgange.

    Målt 25/10: den blev kun kaldt i first-pass. Et værn på én gren er ikke et
    værn — samme fejlform som normaliseringen tidligere samme dag.
    """
    kilde = VISIBLE_RUNS.read_text(encoding="utf-8")
    trae = ast.parse(kilde)

    fundet: list[str] = []
    for node in ast.walk(trae):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if node.name not in ("_stream_visible_run", "_complete_visible_run_from_fallback"):
            continue
        krop = ast.get_source_segment(kilde, node) or ""
        if "_hegn_mekanisk" in krop:
            fundet.append(node.name)

    assert "_stream_visible_run" in fundet, "hovedgrenen kalder ikke hegn-reparationen"
    # To kald inde i _stream_visible_run: agentisk gren + first-pass.
    kilde_stream = next(
        ast.get_source_segment(kilde, n)
        for n in ast.walk(trae)
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == "_stream_visible_run"
    )
    assert kilde_stream.count("_hegn_mekanisk(") >= 2, (
        "kun én gren kalder hegn-reparationen — den anden kan stadig sende rå kode"
    )
