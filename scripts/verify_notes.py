#!/usr/bin/env python
"""Vagt: en note skal have en status, en slags, og sine fire overskrifter.

## Hvorfor (20/9-2026)

`docs/notes/` var en flad bunke daterede filer. Man kunne ikke se om en note
beskrev noget der VAR bygget, noget foreslået, eller noget opgivet — og slet
ikke finde «alle de gange vi har fjernet noget igen».

DeepSeek-harness deler noterne i status × slags og håndhæver det. Det
væsentlige er ikke mapperne: det er at `forenkling` er en slags på lige fod
med `funktion`. At rulle kompleksitet tilbage skal være dokumenteret arbejde,
ikke noget der sker i tavshed fordi det føles som et nederlag.

Den tredje overskrift er den vigtigste. En note uden «Overvejede
alternativer» er en annoncering, ikke en beslutning, og om et halvt år kan
ingen se hvorfor vejen ikke blev taget.

## Hvad den IKKE gør

De 21 flade filer fra før i dag bliver liggende. En oprydning der omskriver
gammel historik for at passe til en ny form, ødelægger mere end den ordner.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

ROD = Path(__file__).resolve().parents[1]
NOTER = ROD / "docs/notes"
STATUS = ("implementeret", "foreslaaet", "arkiveret")
SLAGS = ("arkitektur", "fejlrettelse", "funktion", "proces", "forenkling", "test")
OVERSKRIFTER = ("## Problem", "## Beslutning", "## Overvejede alternativer",
                "## Konsekvenser")
_DATO_SLUG = re.compile(r"^\d{4}-\d{2}-\d{2}-[a-z0-9][a-z0-9-]*\.md$")


def noter() -> list[Path]:
    """Kun noter i den NYE form. Den flade bunke er frosset og røres ikke."""
    ud: list[Path] = []
    for status in STATUS:
        for slags in SLAGS:
            mappe = NOTER / status / slags
            if mappe.is_dir():
                ud += sorted(p for p in mappe.glob("*.md"))
    return ud


def fejl_i(sti: Path) -> list[str]:
    ud: list[str] = []
    if not _DATO_SLUG.match(sti.name):
        ud.append("filnavnet skal være ÅÅÅÅ-MM-DD-kort-slug.md")
    tekst = sti.read_text(encoding="utf-8")
    status = sti.parent.parent.name
    if f"Status: {status}" not in tekst:
        ud.append(f"mangler linjen «Status: {status}» (mappen siger {status})")
    fundet = [h for h in OVERSKRIFTER if f"\n{h}" in f"\n{tekst}"]
    manglende = [h for h in OVERSKRIFTER if h not in fundet]
    if manglende:
        ud.append("mangler " + ", ".join(f"«{h}»" for h in manglende))
    elif [tekst.index(h) for h in OVERSKRIFTER] != sorted(tekst.index(h) for h in OVERSKRIFTER):
        ud.append("overskrifterne står i forkert rækkefølge")
    return ud


def main(argv: list[str] | None = None) -> int:
    argparse.ArgumentParser(description=__doc__).parse_args(argv)
    alle = noter()
    daarlige = {str(p.relative_to(ROD)): f for p in alle if (f := fejl_i(p))}
    if not daarlige:
        forenklinger = sum(1 for p in alle if p.parent.name == "forenkling")
        print(f"verify-notes: {len(alle)} noter i orden "
              f"({forenklinger} forenklinger).")
        return 0
    print("\n❌ VERIFY-NOTES — en note uden fravalg er en annoncering\n")
    for rel, f in daarlige.items():
        print(f"  {rel}")
        for linje in f:
            print(f"      {linje}")
    print(f"\nFormen står i docs/notes/README.md. Status: {'/'.join(STATUS)}; "
          f"slags: {'/'.join(SLAGS)}.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
