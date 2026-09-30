#!/usr/bin/env python3
"""Bliver `call_loaded_tool` faktisk brugt? — tallet der afgør etape B.

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

    tool_router.load_more_fired   — en hentning skete (med `resolved_names`)
    tool_router.dispatcher_brugt  — dispatcheren blev brugt (med `vaerktoej`)

## Aflæsning

Hentninger uden dispatcher-brug bagefter = modellen kalder stadig direkte,
og fletten kan ikke skæres endnu.

    conda activate ai
    python scripts/dispatcher_adoption.py --siden 2026-09-30T15:00:00
"""
from __future__ import annotations

import argparse
import json
import sqlite3
from collections import Counter
from pathlib import Path

DB = Path.home() / ".jarvis-v2" / "state" / "jarvis.db"


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
    p.add_argument("--siden", required=True, help="ISO-tid, fx 2026-09-30T15:00:00 (UTC)")
    p.add_argument("--db", default=str(DB))
    a = p.parse_args()

    con = sqlite3.connect(f"file:{a.db}?mode=ro", uri=True)
    hentninger = _rækker(con, "tool_router.load_more_fired", a.siden)
    brug = _rækker(con, "tool_router.dispatcher_brugt", a.siden)

    navne: Counter[str] = Counter()
    for h in hentninger:
        for n in h.get("resolved_names") or []:
            navne[str(n)] += 1
    brugte: Counter[str] = Counter(str(b.get("vaerktoej") or "?") for b in brug)

    print(f"siden {a.siden}\n")
    print(f"  hentninger (load_more_fired):     {len(hentninger)}")
    print(f"  hentede vaerktoejsnavne i alt:    {sum(navne.values())}")
    print(f"  dispatcher brugt:                 {len(brug)}")
    print()
    if not hentninger:
        print("INTET AT AFLAESE ENDNU — ingen hentninger i vinduet.")
        print("load_more_tools fyrer 1-10 gange i doegnet, saa giv det tid.")
        return 0
    andel = 100 * len(brug) / max(1, sum(navne.values()))
    print(f"  dispatcher-brug pr. hentet navn:  {andel:.0f} %")
    print()
    if navne:
        print("  hentede navne:")
        for n, k in navne.most_common(10):
            print(f"    {k:>3}x  {n}   (kaldt via dispatcher: {brugte.get(n, 0)}x)")
    print()
    if len(brug) == 0:
        print("DOM: modellen bruger den IKKE. Fletten i visible_runs.py skal blive.")
    elif andel >= 80:
        print("DOM: den bruges. Fletten kan skaeres — og dér ligger 8.704 tokens pr. hentning.")
    else:
        print("DOM: blandet brug. Skaeres fletten nu, falder de kald der gaar udenom.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
