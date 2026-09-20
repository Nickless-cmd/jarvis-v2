#!/usr/bin/env python
"""Vagt over vagterne: hver hook skal have en test der ser den sige nej.

## Hvorfor (20/9-2026)

DeepSeek-harness har 60 `verify-*`-scripts og en `.spec` til hvert eneste et.
Vores egne vagter har ikke alle haft det, og vi har betalt for det: en
kilde-vagt der greppede efter en streng målte næsten ingenting, og INGEN
opdagede det — for ingen test havde nogensinde set den afvise noget.

En vagt uden en test er værre end ingen vagt. Ingen vagt ved man er ingen
vagt; en tavs vagt ligner tryghed.

## Hvad der kræves

For hver hook i `.pre-commit-config.yaml` der kører et af vores egne
scripts: mindst én fil under `tests/` skal nævne scriptets modulnavn, og
mindst ét af dens asserts skal handle om en AFVISNING. Vi kan ikke bevise at
en test er god, men vi kan kræve at nogen har skrevet ordet ned.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROD = Path(__file__).resolve().parents[1]
KONFIG = ROD / ".pre-commit-config.yaml"
TESTS = ROD / "tests"
#: `entry:`-linjer der peger på et script i vores eget repo.
_EGET_SCRIPT = re.compile(r"entry:.*?scripts/([A-Za-z0-9_]+)\.(?:py|sh)")
#: Tegn på at testen har set vagten SIGE NEJ, ikke bare importeret den.
_AFVISNING = re.compile(r"==\s*1\b|!=\s*0\b|returncode\b|exit_code\b|"
                        r"SystemExit|pytest\.raises|afvis|reject|blocked|fejl")


def vagter() -> list[str]:
    """Modulnavne på de scripts hookene kører."""
    if not KONFIG.is_file():
        return []
    return sorted(set(_EGET_SCRIPT.findall(KONFIG.read_text(encoding="utf-8"))))


def _tester_der_naevner(modul: str) -> list[Path]:
    ud = []
    for p in sorted(TESTS.glob("test_*.py")):
        try:
            if modul in p.read_text(encoding="utf-8"):
                ud.append(p)
        except OSError as exc:  # en uløselig testfil skal ikke skjule et hul
            print(f"verify-guard-tests: kunne ikke læse {p}: {exc}", file=sys.stderr)
    return ud


def mangler() -> list[tuple[str, str]]:
    """(vagt, årsag) for hver vagt uden en test der ser den afvise."""
    ud: list[tuple[str, str]] = []
    for modul in vagter():
        filer = _tester_der_naevner(modul)
        if not filer:
            ud.append((modul, "ingen test nævner den overhovedet"))
            continue
        if not any(_AFVISNING.search(p.read_text(encoding="utf-8")) for p in filer):
            ud.append((modul, f"testen ({filer[0].name}) ser den aldrig sige nej"))
    return ud


def main(argv: list[str] | None = None) -> int:
    argparse.ArgumentParser(description=__doc__).parse_args(argv)
    huller = mangler()
    if not huller:
        print(f"verify-guard-tests: {len(vagter())} vagter, alle med en test "
              f"der ser dem afvise.")
        return 0
    print("\n❌ VERIFY-GUARD-TESTS — en vagt uden test er værre end ingen vagt\n")
    for modul, aarsag in huller:
        print(f"  scripts/{modul}.py — {aarsag}")
    print("\nSkriv tests/test_<modul>.py, og lad mindst ét assert vise "
          "AFVISNINGEN — ikke kun at den kan importeres.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
