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

## Rækkevidde (udvidet 16/10-2026)

Vagten vogtede før kun `MEMORY.md`. Men dens egen begrundelse — «filen læses
ind i prompten hver tur» — gælder syv filer: `core/services/prompt_contract.py`
injicerer SOUL/IDENTITY/STANDING_ORDERS/USER, QUICK_FACTS, VISIBLE_CHAT_RULES
og MEMORY. QUICK_FACTS.md injiceres endda UBETINGET (uden relevans-filter), så
en forældet linje der koster Bjørn et træk hver gang — ikke kun når han spørger
om memory. Listen står i `_BESKYTTEDE`, og `tests/test_memory_status_guard.py`
binder den til prompt_contract.py: omdøbes en fil i prompten, fælder en test i
stedet for at vagten tavst vogter en fil ingen læser.

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


#: De filer prompten injicerer i HVER tur — se core/services/prompt_contract.py
#: (SOUL/IDENTITY/STANDING_ORDERS/USER ~linje 1012, QUICK_FACTS ~linje 1030,
#: VISIBLE_CHAT_RULES og MEMORY). Vagten dækkede før kun MEMORY.md; de øvrige
#: rådner på samme måde, og QUICK_FACTS.md injiceres endda ubetinget.
#: Listen må ikke importere prompt_contract — så døde vagten med den. I stedet
#: binder tests/test_memory_status_guard.py hvert navn til kilden.
_BESKYTTEDE = (
    "MEMORY.md",
    "QUICK_FACTS.md",
    "USER.md",
    "SOUL.md",
    "IDENTITY.md",
    "STANDING_ORDERS.md",
    "VISIBLE_CHAT_RULES.md",
)

#: Sektions-nøgler der MÅ stå i QUICK_FACTS.md. Listen er bevidst HVID: en ny
#: sektion kræver at man redigerer den og dermed tager stilling — opslag (her),
#: fremgangsmåde/fælde (PLAYBOOKS.md) eller hvad-skete-der (MEMORY.md).
#:
#: Målt 23/10-2026: filen var 85.742 tegn med 38 sektioner, hvoraf 26 var
#: opskrifter og fælder. Promptens loft på 20.000 klippede 77 % tavst væk —
#: inklusive mobil-APK-opskriften og «et fix er ikke levende før genstart».
#: Det var derfor jeg gentog kendte fejl med opskriften foran mig i min egen fil.
_QF_SEKTIONER = (
    "⛔ adgangsregel",
    "systemer",
    "netværk",
    "pfsense",
    "logins",
    "hosts",
    "home assistant",
    "paths",
    "priser",
    "værktøjskanaler",
    "værktøjer",
    "bruger",
    "se også",
)


def _qf_loft() -> int:
    """Promptens FAKTISKE klip-loft for QUICK_FACTS — læst fra kilden.

    `_quick_facts_section(max_chars=...)` klipper tavst alt derover. Hardcoder
    vi tallet her, driver de to fra hinanden den dag nogen hæver loftet, og så
    vogter vagten en grænse ingen læser. AST i stedet for import: en vagt der
    importerer det modul den vogter, dør med det.
    """
    import ast

    kilde = ROD / "core" / "services" / "prompt_contract.py"
    try:
        trae = ast.parse(kilde.read_text(encoding="utf-8", errors="replace"))
    except (OSError, SyntaxError) as exc:
        # Kilden kan ikke læses (flyttet fil eller syntaksfejl i prompt_contract).
        # Vi GÆTTER så på promptens kendte standard — men siger det HØJT: et
        # gæt der ikke meldes, er en vagt der vogter den forkerte grænse i
        # stilhed. Vi crasher ikke, for det ville blokere enhver commit.
        print(f"verify-memory-status: kunne ikke laese loftet fra {kilde.name} ({exc}) — bruger 20000", file=sys.stderr)
        return 20000
    for knude in ast.walk(trae):
        if not (isinstance(knude, ast.FunctionDef) and knude.name == "_quick_facts_section"):
            continue
        par = list(zip(knude.args.kwonlyargs, knude.args.kw_defaults))
        par += list(zip(knude.args.args, knude.args.defaults))
        for arg, default in par:
            if arg.arg == "max_chars" and isinstance(default, ast.Constant):
                try:
                    return int(default.value)
                except (TypeError, ValueError) as exc:
                    # Loftet står som noget andet end et tal (fx et navn).
                    # Samme valg som ovenfor: gæt på standarden, men sig det.
                    print(f"verify-memory-status: loftet er ikke et tal ({exc}) — bruger 20000", file=sys.stderr)
                    return 20000
    return 20000


def quick_facts_brud(sti: Path) -> list[str]:
    """QUICK_FACTS.md skal være et OPSLAG — ikke en hukommelsesbank.

    To krav, begge målt 23/10-2026:

    1. Filen må ikke overstige promptens klip-loft. Alt derover forsvinder
       TAVST, og det er slutningen — altså det nyeste — der forsvinder.
    2. Hver `## `-sektion skal være en erklæret opslags-sektion.

    Hvorfor ikke dato-tæthed: målt 23/10-2026 matcher IP-adresser
    (`10.0.0.36`) dato-mønstret, så en dato-tælling gav 20 «datoer» i en
    sektion der ikke indeholder én. Længde alene fanger heller ikke en kort
    fælde-sektion. Hvidlisten er den eneste regel der præcist kræver et VALG.
    """
    if sti.name != "QUICK_FACTS.md":
        return []
    tekst = sti.read_text(encoding="utf-8", errors="replace")
    brud: list[str] = []
    loft = _qf_loft()
    if len(tekst) > loft:
        brud.append(
            f"QUICK_FACTS.md er {len(tekst)} tegn — promptens loft er {loft}. "
            f"Alt derover klippes tavst væk (slutningen først). Flyt "
            f"fremgangsmåder til PLAYBOOKS.md og forløb til MEMORY.md."
        )
    for nr, linje in enumerate(tekst.splitlines(), 1):
        if not linje.startswith("## "):
            continue
        titel = linje[3:].strip()
        if not any(titel.lower().startswith(n) for n in _QF_SEKTIONER):
            brud.append(
                f"QUICK_FACTS.md:{nr}: «{titel[:60]}» er ikke en erklæret "
                f"opslags-sektion. Tag stilling: opslag → tilføj nøglen til "
                f"_QF_SEKTIONER; fremgangsmåde/fælde → PLAYBOOKS.md; "
                f"hvad skete der → MEMORY.md."
            )
    return brud


def _filer() -> list[Path]:
    """De vogtede filer — stien løses ved KALDSTID, ikke ved import.

    Læser ``JARVIS_HOME`` når den er sat, så et skjold eller en flyttet
    runtime peger på sit eget hjem. Import-tids-stier er netop den fejlform
    denne fil er bygget til at fange et andet sted i huset (16/10-2026).

    Kun filer der FAKTISK findes tælles med: et medlems-workspace er krypteret
    (``.enc``), og en fil vagten ikke kan læse må den ikke gætte om.
    """
    hjem = Path(os.environ.get("JARVIS_HOME") or "~/.jarvis-v2").expanduser()
    roed = hjem / "workspaces"
    if not roed.is_dir():
        return []
    ud: list[Path] = []
    for mappe in sorted(p for p in roed.iterdir() if p.is_dir()):
        for navn in _BESKYTTEDE:
            sti = mappe / navn
            if sti.is_file():
                ud.append(sti)
    return ud


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
    """Kort, entydigt navn til grundlinjen: <workspace>/<fil>."""
    return f"{sti.parent.name}/{sti.name}"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--skriv-grundlinje",
        action="store_true",
        help="Skriv det aktuelle antal som ny grundlinje (efter en oprydning).",
    )
    a = p.parse_args(argv)

    filer = _filer()
    if not filer:
        print("verify-memory-status: ingen laesbare filer fundet — intet at maale")
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

    qf_brud: list[str] = []
    for sti in filer:
        qf_brud.extend(quick_facts_brud(sti))

    i_alt = sum(pr_fil.values())

    if a.skriv_grundlinje:
        GRUNDLINJE.parent.mkdir(parents=True, exist_ok=True)
        GRUNDLINJE.write_text(
            json.dumps(
                {
                    "_forklaring": (
                        "Statuspaastande uden spor (dato, lukke-markoer eller "
                        "register-pegning) i de filer prompten injicerer hver tur "
                        "— i overskrifter OG broedtekst. Flere er forbudt; faerre "
                        "er en sejr."
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

    if qf_brud:
        print()
        for b in qf_brud:
            print(f"FEJL: {b}")

    if i_alt > tilladt:
        print(f"\nFEJL: {i_alt - tilladt} NYE statuspaastande uden spor.")
        print("Giv linjen en dato, en lukke-markoer eller en pegning paa sit register.")
        return 1
    if qf_brud:
        return 1
    if i_alt < tilladt:
        print("(faerre end grundlinjen — saenk den med --skriv-grundlinje)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
