#!/usr/bin/env python
"""Vagt: en slugt undtagelse skal navngives, og dens `try` skal være kort.

## Hvorfor (20/9-2026)

DeepSeek-harness indførte reglen: «An empty `catch` names the error and why;
keep its `try` to one statement.» Vi har betalt for begge halvdele.

Samme dag som jeg læste den, havde jeg fundet `_app_device_live`, der slog op
i et UBUNDET navn. NameError'en blev slugt af en bar `except`, og funktionen
svarede derfor ALTID nej — en proaktiv besked gik til Discord selv når han sad
med appen åben. Fejlen stod ikke noget sted. Den var ikke en fejl i logikken;
den var en fejl i at ingen kunne SE logikken fejle.

Den anden halvdel er den, folk springer over. Et langt `try` med en tavs
handler fanger ikke den fejl du tænkte på — det fanger ALLE fejl i alle
sætningerne, inklusive dem der kom til bagefter. Det er sådan en tastefejl i
sætning fire bliver til tavshed i stedet for et stakspor.

## Hvordan den måler

En handler er TAVS når dens krop kun er `pass`/`continue`/`break`, eller en
enkelt `return`. Den er UNDSKYLDT hvis den logger, re-raiser, eller bærer en
kommentar der forklarer hvorfor — kommentaren er selve pointen i reglen, så
den læses med `tokenize`, ikke med AST (AST smider kommentarer væk).

## Hvorfor en skraldespærre og ikke et forbud

Der var 5.494 tavse handlere da vagten blev skrevet. Et forbud ville betyde
`--no-verify` hver dag, og så måler vi ingenting. Spærren fastfryser tallet
PR. FIL: flere end grundlinjen er en fejl, færre er en sejr man skriver ind.
"""
from __future__ import annotations

import argparse
import ast
import json
import subprocess
import sys
import tokenize
from collections import Counter
from pathlib import Path

ROD = Path(__file__).resolve().parents[1]
GRUNDLINJE = ROD / "docs/guards/silent_except_baseline.json"
#: Hvor vagten kigger. Tests er med vilje ude: en test der sluger en fejl
#: fejler synligt af sig selv, og `pytest.raises`-mønstre ville støje.
OMRAADER = ("core", "apps/api", "scripts")


def _er_tavs(handler: ast.ExceptHandler) -> bool:
    """Sluger denne handler fejlen uden at sige noget?"""
    krop = handler.body
    if all(isinstance(s, (ast.Pass, ast.Continue, ast.Break)) for s in krop):
        return True
    return len(krop) == 1 and isinstance(krop[0], ast.Return)


def _naevner_fejlen(handler: ast.ExceptHandler, kommentarlinjer: set[int]) -> bool:
    """Er der en forklaring? En kommentar på `except`-linjen eller i kroppen.

    `except X:  # tom besked er normal her` tæller. Det er ikke en høj
    tærskel — den skal bare tvinge et menneske til at skrive HVORFOR ÉN gang.
    """
    start = handler.lineno
    slut = max((getattr(s, "end_lineno", s.lineno) or s.lineno) for s in handler.body)
    return any(start <= n <= slut for n in kommentarlinjer)


def _kommentarlinjer(sti: Path) -> set[int]:
    try:
        with sti.open("rb") as fh:
            return {t.start[0] for t in tokenize.tokenize(fh.readline)
                    if t.type == tokenize.COMMENT}
    except Exception as exc:  # filen kunne ikke tokeniseres — sig hvilken
        print(f"verify-silent-except: kunne ikke læse kommentarer i {sti}: {exc}",
              file=sys.stderr)
        return set()


def fund_i_fil(sti: Path) -> list[tuple[int, str]]:
    """(linje, årsag) for hver tavs handler uden forklaring."""
    try:
        traeet = ast.parse(sti.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError):
        return []
    kommentarer = _kommentarlinjer(sti)
    ud: list[tuple[int, str]] = []
    for n in ast.walk(traeet):
        if not isinstance(n, ast.Try):
            continue
        for h in n.handlers:
            if not _er_tavs(h) or _naevner_fejlen(h, kommentarer):
                continue
            if len(n.body) > 1:
                ud.append((h.lineno, f"tavs handler om et try med {len(n.body)} sætninger"))
            else:
                ud.append((h.lineno, "tavs handler uden forklaring"))
    return ud


def _filer(argumenter) -> list[Path]:
    if argumenter.paths:
        return [Path(p) for p in argumenter.paths if p.endswith(".py")]
    if argumenter.staged:
        r = subprocess.run(["git", "diff", "--cached", "--name-only",
                            "--diff-filter=ACMR"], capture_output=True, text=True,
                           cwd=ROD, check=False)
        return [ROD / line for line in r.stdout.splitlines()
                if line.endswith(".py") and line.split("/")[0] in
                {o.split("/")[0] for o in OMRAADER}]
    ud: list[Path] = []
    for o in OMRAADER:
        ud += [p for p in (ROD / o).rglob("*.py") if "__pycache__" not in str(p)]
    return ud


def _laes_grundlinje() -> dict[str, int]:
    try:
        return json.loads(GRUNDLINJE.read_text(encoding="utf-8"))["pr_fil"]
    except Exception:  # ingen grundlinje endnu = alt er nyt
        return {}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("paths", nargs="*", help="konkrete filer; ellers hele træet")
    p.add_argument("--staged", action="store_true", help="kun det der er staged")
    p.add_argument("--skriv-grundlinje", action="store_true",
                   help="fastfrys nuværende tal som ny grundlinje")
    a = p.parse_args(argv)

    filer = _filer(a)
    tal: Counter[str] = Counter()
    fund: dict[str, list[tuple[int, str]]] = {}
    for f in filer:
        rel = str(f.relative_to(ROD)) if f.is_absolute() else str(f)
        v = fund_i_fil(f if f.is_absolute() else ROD / f)
        if v:
            tal[rel] = len(v)
            fund[rel] = v

    if a.skriv_grundlinje:
        GRUNDLINJE.parent.mkdir(parents=True, exist_ok=True)
        GRUNDLINJE.write_text(json.dumps(
            {"_forklaring": "Tavse except-handlere pr. fil. Flere end her er en "
                            "fejl; færre er en sejr — skriv det nye tal ind.",
             "i_alt": sum(tal.values()), "pr_fil": dict(sorted(tal.items()))},
            indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"verify-silent-except: grundlinje skrevet — {sum(tal.values())} "
              f"tavse handlere i {len(tal)} filer.")
        return 0

    grundlinje = _laes_grundlinje()
    brud = []
    for rel, n in sorted(tal.items()):
        loft = grundlinje.get(rel, 0)
        if n > loft:
            brud.append((rel, n, loft))

    if not brud:
        return 0
    print("\n❌ VERIFY-SILENT-EXCEPT — flere tavse undtagelser end grundlinjen\n")
    for rel, n, loft in brud:
        print(f"  {rel}: {n} tavse handlere (grundlinje {loft})")
        for linje, aarsag in fund[rel][:6]:
            print(f"      {rel}:{linje}  {aarsag}")
    print("\nEn slugt undtagelse skal kunne forklares. Vælg én:")
    print("  • log den:        logger.warning(\"…: %s\", exc)")
    print("  • lad den gå:     raise")
    print("  • forklar den:    en kommentar på except-linjen der siger HVORFOR")
    print("Og hold dit `try` til ÉN sætning, så du fanger den fejl du mente.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
