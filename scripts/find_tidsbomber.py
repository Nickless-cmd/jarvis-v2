#!/usr/bin/env python
"""Find tests der går i stykker af sig selv når kalenderen skrider.

HVORFOR DEN FINDES (26/9-2026)

To vagter var røde uden at noget var i stykker:

* `test_decision_evidence.test_fremmed_workspace_laekker_ikke_ind` stemplede
  sine rækker `2026-09-26T14:00:00` og spurgte på «den seneste time». Den
  bestod i den time den blev skrevet i og fejlede hver time siden.
* `test_user_temperature_engine.test_baseline_ser_kun_egen_workspace` gjorde
  det samme mod et 30-dages vindue — den ville være blevet rød en måned efter.

Begge var privatlivs-vagter for lækken 26/9. En vagt der fejler af sig selv
er værre end ingen vagt: den lærer folk at se bort fra suiten, og næste gang
filteret FAKTISK knækker, ligner det bare den røde man allerede kender.

At lede efter mønstret med grep duer ikke — 232 testfiler har hardkodede
ISO-stempler, og langt de fleste er harmløse. Det er kombinationen af et fast
stempel og et vindue relativt til `nu` der er farlig, og den kan man ikke se
på en linje. Man kan derimod MÅLE den: kør suiten med uret flyttet.

FALSKE POSITIVER, OG HVORFOR DE OPSTÅR

`faketime` forskyder processens `time.time()`, men filers mtime sættes af
kernen med den ægte klokke. En test der skriver en fil og bagefter spørger
«hvor gammel er den?» ser derfor en fil der er sprunget frem i tiden, og
fejler uden at være en tidsbombe. `tests/test_spild.py` er netop sådan en.
Læs et udslag som et spor, ikke som en dom.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys

#: Spring der hver især fanger sin egen slags bombe: en time fanger et
#: «seneste time»-vindue, en dag fanger døgn-vinduer og datoformater, en
#: måned fanger de lange baselines.
SPRING = ("+1 hour", "+1 day", "+30 days")

_RES = re.compile(r"^FAILED (\S+)", re.M)


def _koer(spring: str | None, pytest_args: list[str]) -> set[str]:
    kmd = [sys.executable, "-m", "pytest", "-q", "-p", "no:randomly", *pytest_args]
    if spring:
        kmd = ["faketime", spring, *kmd]
    ud = subprocess.run(kmd, capture_output=True, text=True).stdout
    return set(_RES.findall(ud))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--spring", action="append", default=None,
                    help="tids-spring (kan gentages); standard: %s" % ", ".join(SPRING))
    ap.add_argument("pytest_args", nargs="*", default=["tests/"])
    a = ap.parse_args()
    spring = a.spring or list(SPRING)
    maal = a.pytest_args or ["tests/"]

    if subprocess.run(["which", "faketime"], capture_output=True).returncode != 0:
        print("faketime mangler — apt install faketime", file=sys.stderr)
        return 2

    print("nu (grundlinje) …", flush=True)
    grundlinje = _koer(None, maal)
    print("  %d fejlende allerede nu" % len(grundlinje))

    bomber: dict[str, list[str]] = {}
    for s in spring:
        print("%s …" % s, flush=True)
        nye = _koer(s, maal) - grundlinje
        print("  %d nye" % len(nye))
        for t in sorted(nye):
            bomber.setdefault(t, []).append(s)

    if not bomber:
        print("\ningen tidsbomber fundet ved %s" % ", ".join(spring))
        return 0
    print("\nTIDSBOMBER (består nu, fejler senere):")
    for t, hvornaar in sorted(bomber.items()):
        print("  %s\n      falder ved: %s" % (t, ", ".join(hvornaar)))
    print("\nNB: en test der selv skriver filer og maaler deres alder giver et")
    print("falsk udslag — mtime foelger den AEGTE klokke. Se modulets docstring.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
