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

## To flader (brødteksten tilføjet 16/10-2026)

Vagten så før kun `## `-overskrifter. Men brødteksten bar 23 statuspåstande
mere — «**Åbent:** fixet er ikke i drift før genstart», «- **Kræver genstart
af `jarvis-api` for at virke.**» — og de rådner på samme måde. Filen læses
som helhed, ikke kun som overskrifter.

Brødteksten scannes IKKE bredt, og det er målt: en scanning af alle linjer med
nutids-ord uden spor gav **455** træf (ubrugelig støj). Kravet «linjen STARTER
med statusordet» gav **59**, og et længde-loft på 160 tegn gav de **23** ægte.
En længere linje er en analyse, ikke en statuslinje.

## Skraldespærre, ikke forbud

Grundlinjen i `docs/guards/memory_status_baseline.json` er antallet af
eksisterende brud. Flere er en fejl — filen må ikke rådne videre. Færre er en
sejr og skrives ind med `--skriv-grundlinje`.

## Hvad vagten IKKE kan

- Den afgør ikke sandhed. En påstand med en dato KAN stadig være forkert; den
  bærer blot et spor nogen kan følge.
- Brødtekst-fund kræver at påstanden STARTER med statusordet. En påstand
  formuleret midt i en sætning fanges ikke — den er også sværere at skelne fra
  almindelig prosa. Det er et bevidst valg: hellere et ægte brud ufanget end
  tyve beskrivende linjer flagget.
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

#: Markdown-foranstillinger der ikke tæller som indhold: listepunkt, nummer,
#: citat og fed/kursiv-begyndelse. Brødtekst-linjen vurderes EFTER disse er
#: strippet, så «- **Åbent:**» bedømmes på «Åbent:».
_BROEDTEKST_PREFIX = re.compile(r"^\s*(?:[-*+>]\s+|\d+\.\s+)?(?:\*\*|__|\*|_)?\s*")

#: Længere linjer er analyser, ikke statuslinjer. Målt 16/10-2026.
_BROEDTEKST_MAX = 160


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
    """(linjenummer, tekst) for hver `## `-overskrift der er en påstand uden spor."""
    fund: list[tuple[int, str]] = []
    tekst = sti.read_text(encoding="utf-8", errors="replace")
    for nr, linje in enumerate(tekst.splitlines(), 1):
        if not linje.startswith("## "):
            continue
        if _NUTID.search(linje) and not _SPOR.search(linje):
            fund.append((nr, linje.strip()))
    return fund


def fund_i_broedtekst(sti: Path) -> list[tuple[int, str]]:
    """(linjenummer, tekst) for hver brødtekst-linje der er en påstand uden spor.

    Kun linjer der STARTER med statusordet (efter markdown-foranstilling) og
    er kortere end ``_BROEDTEKST_MAX``.

    Kodehegn springes bevidst IKKE over. Et forsøg 16/10-2026 på at skippe
    linjer mellem ```-hegn slog **16.782 linjer fra** — fordi filen har et
    ulige antal hegn, så tællingen tippede og resten af filen stod som
    «inde i en kodeblok». En filtrering der blindt slår 72 % af filen fra er
    farligere end den støj den skulle fjerne: en statuspåstand inde i en
    kodeblok er sjælden, en blind vagt er dyr.
    """
    fund: list[tuple[int, str]] = []
    tekst = sti.read_text(encoding="utf-8", errors="replace")
    for nr, linje in enumerate(tekst.splitlines(), 1):
        if linje.startswith("#"):
            continue
        if len(linje) > _BROEDTEKST_MAX:
            continue
        rest = _BROEDTEKST_PREFIX.sub("", linje)
        if _NUTID.match(rest) and not _SPOR.search(linje):
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
    n_overskrift = 0
    n_broedtekst = 0
    for sti in filer:
        ov = fund_i_fil(sti)
        bt = fund_i_broedtekst(sti)
        n_overskrift += len(ov)
        n_broedtekst += len(bt)
        if ov or bt:
            pr_fil[_navn(sti)] = len(ov) + len(bt)
        for nr, linje in ov:
            detaljer.append(f"  overskrift {_navn(sti)}:{nr}: {linje[:110]}")
        for nr, linje in bt:
            detaljer.append(f"  broedtekst {_navn(sti)}:{nr}: {linje[:110]}")

    i_alt = sum(pr_fil.values())

    if a.skriv_grundlinje:
        GRUNDLINJE.parent.mkdir(parents=True, exist_ok=True)
        GRUNDLINJE.write_text(
            json.dumps(
                {
                    "_forklaring": (
                        "Statuspaastande i MEMORY.md uden spor (dato, lukke-markoer "
                        "eller register-pegning) — i overskrifter OG broedtekst. "
                        "Flere er forbudt; faerre er en sejr."
                    ),
                    "i_alt": i_alt,
                    "overskrift": n_overskrift,
                    "broedtekst": n_broedtekst,
                    "pr_fil": pr_fil,
                },
                indent=2,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
        print(f"grundlinje skrevet: {i_alt} brud ({n_overskrift} overskrift, {n_broedtekst} broedtekst)")
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
    print(
        f"\nstatuspaastande uden spor: {i_alt} "
        f"({n_overskrift} overskrift, {n_broedtekst} broedtekst) (grundlinje {tilladt})"
    )

    if i_alt > tilladt:
        print(f"\nFEJL: {i_alt - tilladt} NYE statuspaastande uden spor.")
        print("Giv linjen en dato, en lukke-markoer eller en pegning paa sit register.")
        return 1
    if i_alt < tilladt:
        print("(faerre end grundlinjen — saenk den med --skriv-grundlinje)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
