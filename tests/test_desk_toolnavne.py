"""Vagt: desk' værktøjsnavne skal findes i registret.

Desk holder værktøjsnavne i seks tabeller — `TOOL_REGISTRY` (etiket + ikon),
`KENDTE` (resultatform) og fire i `toolRound.ts`: `VERBS` (nutid/datid),
`NO_SUBJECT`, `PLURAL` og `UNIT` (opgørelsen «Kørte 3 filer»). De skal holdes i
sync med registrets 482 værktøjer i hånden, og det kan man ikke.

23/9-2026 stod der 17 navne i de seks lister der ikke fandtes længere:
`glob`, `grep`, `list_dir`, `notify`, `memory_search`, `multi_edit` … Ingen af
dem kaster en fejl. De tegner bare en form der LYVER, eller falder til den
generiske dump — og `bash_session_run` (fjerde mest brugte værktøj i systemet,
1.492 kald) fik den generiske dump i månedsvis fordi nogen skrev navnet uden
`_run`.

Kilden til sandheden er `core.tools.simple_tools.get_tool_definitions`. Denne
test fejler hvis desk nævner et navn der ikke er registreret.

Den fanger IKKE det modsatte — et registreret værktøj uden form. Det er en
anden test: se vagt-testen i `apps/jarvis-desk/src/components/rich/raekkeKroppe.test.tsx`.
"""
from __future__ import annotations

import pathlib
import re

import pytest

from core.tools.simple_tools import get_tool_definitions

REPO = pathlib.Path(__file__).resolve().parents[1]
DESK = REPO / "apps" / "jarvis-desk" / "src"

# (sti relativt til DESK, markør der starter blokken, navn til fejlbeskeden)
BLOKKE = [
    ("lib/toolRegistry.ts", "const TOOL_REGISTRY", "TOOL_REGISTRY"),
    ("lib/toolRound.ts", "const VERBS", "VERBS"),
    ("lib/toolRound.ts", "const NO_SUBJECT", "NO_SUBJECT"),
    ("lib/toolRound.ts", "const PLURAL", "PLURAL"),
    ("lib/toolRound.ts", "const UNIT", "UNIT"),
    ("components/rich/raekkeKroppe.tsx", "const KENDTE", "KENDTE"),
]

# Nøgler står med præcis to mellemrum. `\s{2}` + et bogstav som tredje tegn
# udelukker indlejrede nøgler (fire mellemrum ville fejle på tredje tegn).
NOEGLE = re.compile(r"^\s{2}([a-z][a-z0-9_]*):\s*[\[{]", re.M)

# Nogle steder er navnene en LISTE af strenge, ikke nøgler i et objekt —
# `skalHaveForm` i raekkeKroppe.test.tsx er selv en håndholdt liste, og den
# havde `explore` og `notify` stående 23/9-2026. En vagt der kun ser på
# objekt-tabeller fanger ikke den slags.
LISTE_BLOKKE = [
    ("components/rich/raekkeKroppe.test.tsx", "const skalHaveForm", "skalHaveForm"),
]

STRENG = re.compile(r"'([a-z][a-z0-9_]*)'")


def registrerede_navne() -> set[str]:
    """Alle værktøjsnavne registret kender — uden scope-filter."""
    navne: set[str] = set()
    for definition in get_tool_definitions(role="owner"):
        funktion = definition.get("function") or {}
        navn = funktion.get("name") or definition.get("name")
        if navn:
            navne.add(navn)
    return navne


def noegler_i(sti: pathlib.Path, markoer: str) -> set[str]:
    """Nøglerne i den blok der starter ved `markoer` og slutter ved kolonne-0 `}`."""
    tekst = sti.read_text(encoding="utf-8")
    start = tekst.index(markoer)
    slut = tekst.index("\n}", start)
    return set(NOEGLE.findall(tekst[start:slut]))


def test_registret_svarer():
    """Uden navne ville testen nedenfor bestå af den forkerte grund."""
    navne = registrerede_navne()
    assert len(navne) > 100, f"registret gav kun {len(navne)} navne — er kilden brudt?"


@pytest.mark.parametrize("sti,markoer,label", BLOKKE)
def test_desk_navne_findes_i_registret(sti: str, markoer: str, label: str):
    navne = registrerede_navne()
    doede = sorted(noegler_i(DESK / sti, markoer) - navne)
    assert not doede, (
        f"{label} i {sti} nævner værktøjer der ikke findes i registret "
        f"({len(navne)} navne): {', '.join(doede)}\n"
        "Ret navnet til det registrerede, eller slet indgangen. Et navn der "
        "ikke findes tegner en form der lyver."
    )


@pytest.mark.parametrize("sti,markoer,label", LISTE_BLOKKE)
def test_desk_listenavne_findes_i_registret(sti: str, markoer: str, label: str):
    """Samme vagt, men for blokke hvor navnene står som strenge i en liste."""
    navne = registrerede_navne()
    tekst = (DESK / sti).read_text(encoding="utf-8")
    start = tekst.index(markoer)
    slut = tekst.index("]", start)
    doede = sorted(set(STRENG.findall(tekst[start:slut])) - navne)
    assert not doede, (
        f"{label} i {sti} nævner værktøjer der ikke findes i registret "
        f"({len(navne)} navne): {', '.join(doede)}"
    )
