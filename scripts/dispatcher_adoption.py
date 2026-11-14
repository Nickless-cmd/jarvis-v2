#!/usr/bin/env python3
"""Bliver `call_loaded_tool` faktisk brugt? — tallet der afgør om fletten kan skæres.

## Hvad der skal afgøres

`load_more_tools` henter et værktøj og returnerer dets fulde skema i sit
resultat — altså i beskederne, efter DeepSeeks cache-grænse, hvor det koster
~0. Men `visible_runs.py` fletter DERUDOVER definitionen ind i næste rundes
værktøjsarray, og arrayet ligger FØR hele samtalen i præfikset. Målt
30/9-2026, tre gange uafhængigt:

    mod DeepSeeks API:    én ny definition bagerst   = 8.704 tokens tabt
    produktion (katalog): 59.643 -> 61.120 tegn      = hit 88,0 % -> 17,9 %
    produktion (igen):    +419 tegn                  = 62.672 miss

`call_loaded_tool` gør hentningen til et almindeligt værktøjskald i
beskederne, så arrayet kan stå stille. Men fletten kan først skæres når vi
VED at modellen bruger dispatcheren — gør den ikke det, kan et hentet værktøj
slet ikke kaldes, fordi DeepSeek afviser et værktøj der ikke er deklareret.

## Hvorfor to forskellige events

`tool.invoked` kan IKKE bruges: udpakningen sker før telemetrien, så den
bærer det ægte navn (`delete_file`) også når dispatcheren blev brugt. Det er
med vilje — ellers ville alle gates se dispatcherens navn — men det gør den
ubrugelig til dette. Derfor et eget spor.

    tool_router.load_more_fired   — en hentning skete (resolved_names, run_id)
    tool_router.dispatcher_brugt  — dispatcheren blev brugt (vaerktoej, run_id)

## Hvorfor raten er pr. RUN og ikke et forhold mellem to tællinger (14/11-2026)

Den første version af dette script delte dispatcher-kald med antal hentede
navne: 230 / 614 = «37 %». Det er ikke en adoptionsrate. De to tal tælles over
hele vinduet, ikke pr. run, og et run der henter fem navne og kalder ét af dem
det har brug for, er 100 % dækket — men blev rapporteret som 20 %. Modsat
kunne ét navn overstige 100 %: `db_query` blev hentet 37 gange og kaldt 87
gange, altså «235 %», hvilket en rate ikke kan være. Tallet så præcist ud og
var ubrugeligt.

Raten er derfor: **af de runs der hentede mindst ét værktøj, hvor mange kaldte
bagefter mindst ét af de hentede navne gennem dispatcheren?** Det kræver
run-id'et på BEGGE sider. Hentesiden fik det 14/11-2026; hentninger fra før
den dag kan ikke kobles og tælles derfor som ``ukobbelige`` — ikke som «ikke
adopteret», hvilket ville være at gætte.

## Aflæsning

    conda activate ai
    python scripts/dispatcher_adoption.py --siden 2026-11-14T00:00:00

Hentninger uden dispatcher-brug i SAMME run = modellen kalder stadig direkte,
og fletten kan ikke skæres endnu.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path

DB = Path.home() / ".jarvis-v2" / "state" / "jarvis.db"

#: En run-dækning under dette betyder at fletten ikke kan skæres: de kald der
#: går udenom dispatcheren ville fejle, fordi navnet ikke er deklareret.
GRAENSE_SKAER = 80.0


def _rækker(con: sqlite3.Connection, kind: str, siden: str) -> list[dict]:
    ud = []
    for (nyttelast,) in con.execute(
        "SELECT payload_json FROM events WHERE kind = ? AND created_at >= ?",
        (kind, siden),
    ):
        try:
            ud.append(json.loads(nyttelast or "{}"))
        except (ValueError, TypeError):  # en uparsbar raekke er stoej, ikke et svar
            continue
    return ud


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--siden", required=True, help="ISO-tid, fx 2026-11-14T00:00:00 (UTC)")
    p.add_argument("--db", default=str(DB))
    a = p.parse_args()

    con = sqlite3.connect(f"file:{a.db}?mode=ro", uri=True)
    hentninger = _rækker(con, "tool_router.load_more_fired", a.siden)
    brug = _rækker(con, "tool_router.dispatcher_brugt", a.siden)

    # ── Pr. run: hvad blev hentet, og hvad blev kaldt ──────────────────────
    hentet_pr_run: dict[str, set[str]] = defaultdict(set)
    kaldt_pr_run: dict[str, list[str]] = defaultdict(list)
    ukobbelige = 0
    hentede_navne: Counter[str] = Counter()

    for h in hentninger:
        navne = [str(n) for n in (h.get("resolved_names") or []) if n]
        for n in navne:
            hentede_navne[n] += 1
        rid = str(h.get("run_id") or "").strip()
        if not rid:
            ukobbelige += 1
            continue
        hentet_pr_run[rid].update(navne)

    for b in brug:
        rid = str(b.get("run_id") or "").strip()
        if rid:
            kaldt_pr_run[rid].append(str(b.get("vaerktoej") or "?"))

    kobbelige = len(hentet_pr_run)
    adopteret = 0
    ramte_navne: Counter[str] = Counter()
    for rid, navne in hentet_pr_run.items():
        kaldte = kaldt_pr_run.get(rid, [])
        traef = [k for k in kaldte if k in navne]
        if traef:
            adopteret += 1
            for k in traef:
                ramte_navne[k] += 1

    print(f"siden {a.siden}\n")
    print(f"  hentninger (load_more_fired):     {len(hentninger)}")
    print(f"  hentede vaerktoejsnavne i alt:    {sum(hentede_navne.values())}")
    print(f"  dispatcher-kald (dispatcher_brugt): {len(brug)}")
    print()
    print(f"  kobbelige runs (havde run_id):    {kobbelige}")
    print(f"  ukobbelige hentninger:            {ukobbelige}")
    if ukobbelige:
        print("    (skrevet foer 14/11-2026, hvor hentningen ikke bar run_id —")
        print("     de kan ikke afgoere noget og taelles hverken for eller imod)")
    print()

    if not kobbelige:
        print("INTET AT AFLAESE ENDNU — ingen kobbelige hentninger i vinduet.")
        print("Raten kan foerst maales paa hentninger efter 14/11-2026.")
        return 0

    daekning = 100 * adopteret / kobbelige
    print(f"  RUN-DAEKNING:                     {daekning:.0f} %  "
          f"({adopteret} af {kobbelige} hentende runs kaldte et hentet navn)")
    print()

    if hentede_navne:
        print("  hentede navne (hentet / kaldt via dispatcher i SAMME run):")
        for n, k in hentede_navne.most_common(12):
            print(f"    {k:>3}x hentet   {ramte_navne.get(n, 0):>3}x brugt   {n}")
        print()

    aldrig_brugt = [n for n in hentede_navne if ramte_navne.get(n, 0) == 0]
    if aldrig_brugt:
        print(f"  hentet men ALDRIG kaldt via dispatcher: {len(aldrig_brugt)} navne")
        for n in sorted(aldrig_brugt)[:10]:
            print(f"    {hentede_navne[n]:>3}x  {n}")
        print()

    if daekning >= GRAENSE_SKAER:
        print(f"DOM: den bruges ({daekning:.0f} % af de hentende runs). "
              "Fletten kan skaeres — og dér ligger 8.704 tokens pr. hentning.")
    elif daekning == 0:
        print("DOM: modellen bruger den IKKE. Fletten i visible_runs.py skal blive.")
    else:
        print(f"DOM: blandet brug ({daekning:.0f} %). Skaeres fletten nu, falder "
              "de kald der gaar udenom dispatcheren.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
