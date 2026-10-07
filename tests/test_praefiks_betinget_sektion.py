"""Betingede sektioner hører i HALEN, ikke i præfikset (målt 4/10-2026).

Fire hale-sektioner blev flyttet op i det cachede præfiks fordi de var
byte-identiske over 99 ture. Målt efter flytningen:

    FØR    7.673 miss/kald   5,65 %   (2.571 kald)
    EFTER 12.184 miss/kald   8,93 %   (120 kald)   ← +59 %

Årsagen: `FORBUNDNE APPS` bygges kun når brugeren HAR forbundne plugins —
86 af 99 ture. Et præfiks der nogle gange har fire sektioner og andre gange
tre, matcher ikke; hver gang sektionen kommer eller går, invalideres alt efter
den, inklusive 120.064 tokens samtalehistorik.

**Uændret indhold og altid til stede er to forskellige egenskaber.** Cachen
kræver begge. Denne test er vagten mod at gentage fejlen.
"""
from __future__ import annotations

import ast
import pathlib

KILDE = pathlib.Path("core/services/prompt_contract.py")


def test_halen_laegges_UDELT_efter_sentinel():
    """Ingen partition af `_dyn_tail` op i præfikset. Prøver nogen igen, skal
    det være et bevidst valg der bryder en test — ikke en omflytning der ser
    uskyldig ud."""
    kilde = KILDE.read_text()
    i = kilde.index("parts.append(DYNAMIC_TAIL_SENTINEL)")
    blok = kilde[i:i + 200]
    assert "parts.extend(_dyn_tail)" in blok, (
        "halen laegges ikke udelt efter sentinel'en — er den partitioneret "
        "igen, saa laes maalingen i denne fils hoved foerst")


def test_ingen_hale_sektion_laegges_i_praefikset():
    """Konkret: `parts.extend` må kun få `_dyn_tail` — ikke et udsnit."""
    traeet = ast.parse(KILDE.read_text())
    for node in ast.walk(traeet):
        if not isinstance(node, ast.Call):
            continue
        if getattr(node.func, "attr", None) != "extend":
            continue
        if getattr(getattr(node.func, "value", None), "id", None) != "parts":
            continue
        arg = ast.unparse(node.args[0]) if node.args else ""
        assert arg in ("_dyn_tail",), (
            f"parts.extend({arg}) — kun hele halen maa laegges efter "
            "sentinel'en, og intet udsnit af den foer")
