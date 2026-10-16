#!/usr/bin/env python
"""Skraldespærre mod statuspåstande i MEMORY.md der ikke kan efterprøves.

## Hvorfor (målt 16/10-2026)

MEMORY.md er append-only. En sektion skrevet i nutid — «STADIG ÅBEN», «venter
på commit», «afventer genstart» — var sand da den blev skrevet, og bliver en
løgn når sagen lukkes, uden at nogen retter overskriften. Målt 16/10-2026:
51 overskrifter formulerede sig som nutid uden dato, og **16 af dem var blevet
falske** — nogle i månedsvis. Filen læses ind i prompten hver tur, så en
forkert linje koster Bjørn et træk: han bad mig bygge noget der allerede var
bygget, fordi en overskrift fra 15/10 stadig sagde «STADIG ÅBEN».

Det er samme fejlform som `agent_transcript` og `mcp_auth` samme dag — en
værdi beregnet på ét tidspunkt og læst som gyldig nu. Forskellen er kun hvor
den bor: i en modul-konstant eller i en overskrift.

## Hvad vagten kræver

En statuspåstand (nutids-formulering) skal kunne EFTERPRØVES. Det er den
eneste ærlige grænse en maskine kan håndhæve: den kan ikke afgøre om en
påstand er SAND, men den kan kræve at påstanden bærer et spor — en dato, en
lukke-markør eller en pegning på sit register. En påstand uden spor kan ingen
tjekke, og det er præcis dem der rådner.

## Skraldespærre, ikke forbud

Grundlinjen i `docs/guards/memory_status_baseline.json` er antallet af
eksisterende brud. Flere er en fejl — filen må ikke rådne videre. Færre er en
sejr og skrives ind med `--skriv-grundlinje`. Vi retter ikke de sidste ti i
dag for at gøre vagten grøn; vi forhindrer at der kommer en ellevte.

## Hvad vagten IKKE kan

- Den ser kun `## `-overskrifter. Statuspåstande i brødteksten, eller i andre
  ord end markør-listen, fanges ikke.
- Den afgør ikke sandhed. En overskrift med en dato KAN stadig være forkert;
  den bærer blot et spor nogen kan følge.
- Den kører ved commit (og manuelt). En fil der rådner mellem to commits
  opdages først ved den næste.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

ROD = Path(__file__).resolve().parents[1]
GRUNDLINJE = ROD / "docs" / "guards" / "memory_status_baseline.json"

#: Ord der formulerer sig som en PÅSTAND om nuet. Bevidst smal: hellere et
#: ægte brud ufanget end tyve beskrivende overskrifter flagget.
_NUTID = re.compile(
    r"\b(STADIG|ÅBENT|ÅBEN|afventer|venter på|ikke bygget|ikke løst|"
    r"ikke udført|mangler|genstår|uafklaret|kræver genstart|ikke live|"
    r"ikke i drift|TODO)\b",
    re.IGNORECASE,
)

#: Et spor der gør påstanden efterprøvbar — en dato, en lukning eller en
#: pegning på sit register. Mangler alle tre, er påstanden utilgængelig.
_SPOR = re.compile(
    r"\d{1,2}[./-]\d{1,2}"  # 16/10, 29.9
    r"|\d{4}-\d{2}-\d{2}"  # 2026-09-13
    r"|\d{1,2}\.\s*(?:januar|februar|marts|april|maj|juni|juli|august|"
    r"september|oktober|november|december)"
    r"|LUKKET|LØST|BYGGET|LANDET|RETTET|AFVIST|DUBLET|FORÆLDET|OVERHALET"
    r"|~~|ældre version|se «|se \"|kilde:|registret|register|state_store"
    r"|list_side_tasks|side_tasks|runtime_tasks|jf\.",
    re.IGNORECASE,
)


def _memories() -> list[Path]:
    """Læsbare MEMORY.md-filer — stien løses ved KALDSTID, ikke ved import.

    Læser ``JARVIS_HOME`` når den er sat, så et skjold eller en flyttet
    runtime peger på sit eget hjem. Import-tids-stier er netop den fejlform
    denne fil er bygget til at fange et andet sted i huset (16/10-2026).
    """
    hjem = Path(os.environ.get("JARVIS_HOME") or "~/.jarvis-v2").expanduser()
    roed = hjem / "workspaces"
    if not roed.is_dir():
        return []
    return sorted(p for p in roed.glob("*/MEMORY.md") if p.is_file())


def fund_i_fil(sti: Path) -> list[tuple[int, str]]:
    """(linjenummer, tekst) for hver statuspåstand uden spor."""
    fund: list[tuple[int, str]] = []
    tekst = sti.read_text(encoding="utf-8", errors="replace")
    for nr, linje in enumerate(tekst.splitlines(), 1):
        if not linje.startswith("## "):
            continue
        if _NUTID.search(linje) and not _SPOR.search(linje):
            fund.append((nr, linje.strip()))
    return fund


def _navn(sti: Path) -> str:
    """Kort, entydigt navn til grundlinjen: <workspace>/MEMORY.md."""
    return f"{sti.parent.name}/MEMORY.md"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--skriv-grundlinje",
        action="store_true",
        help="Skriv det aktuelle antal som ny grundlinje (efter en oprydning).",
    )
    a = p.parse_args(argv)

    filer = _memories()
    if not filer:
        print("verify-memory-status: ingen laesbare MEMORY.md fundet — intet at maale")
        return 0

    pr_fil: dict[str, int] = {}
    detaljer: list[str] = []
    for sti in filer:
        fund = fund_i_fil(sti)
        if fund:
            pr_fil[_navn(sti)] = len(fund)
        for nr, linje in fund:
            detaljer.append(f"  {_navn(sti)}:{nr}: {linje[:110]}")

    i_alt = sum(pr_fil.values())

    if a.skriv_grundlinje:
        GRUNDLINJE.parent.mkdir(parents=True, exist_ok=True)
        GRUNDLINJE.write_text(
            json.dumps(
                {
                    "_forklaring": (
                        "Statuspaastande i MEMORY.md uden spor (dato, lukke-markoer "
                        "eller register-pegning). Flere er forbudt; faerre er en sejr."
                    ),
                    "i_alt": i_alt,
                    "pr_fil": pr_fil,
                },
                indent=2,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
        print(f"grundlinje skrevet: {i_alt} brud")
        return 0

    tilladt = 0
    if GRUNDLINJE.is_file():
        try:
            tilladt = int(json.loads(GRUNDLINJE.read_text(encoding="utf-8")).get("i_alt", 0))
        except (ValueError, OSError) as exc:  # pragma: no cover - korrupt baseline
            print(f"verify-memory-status: kunne ikke laese grundlinjen ({exc})")
            return 1

    for d in detaljer:
        print(d)
    print(f"\nstatuspaastande uden spor: {i_alt} (grundlinje {tilladt})")

    if i_alt > tilladt:
        print(f"\nFEJL: {i_alt - tilladt} NYE statuspaastande uden spor.")
        print("Giv linjen en dato, en lukke-markoer eller en pegning paa sit register.")
        return 1
    if i_alt < tilladt:
        print(f"(faerre end grundlinjen — saenk den med --skriv-grundlinje)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
