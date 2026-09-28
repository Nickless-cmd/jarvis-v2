#!/usr/bin/env python
"""Hvor braekker praefiks-cachen — og hvilken besked gjorde det?

## Hvorfor scriptet findes

28/9-2026 faldt cache-hit i ét synligt run fra 148.352 til 67.840 mellem runde
11 og 12, og blev haengende praecis dér i fem runder mens miss voksede til
94.193. `system_sha`, `tools_sha` og `tail_sha` var uaendrede hele vejen — de
tre felter kunne altsaa ikke pege paa noget. Bruddet laa inde i samtalen, og
der havde vi ingen maaler.

En tidligere aflaesning kaldte det «frosset hit» og gik efter en
aldrings-mekanisme der viste sig **aldrig at have koert** i produktion. Det er
derfor dette script maaler **deltaet mellem to paa hinanden foelgende runder**
og ikke om et tal staar stille: et hit der staar stille og et hit der er
faldet ligner hinanden i en taelling og er to forskellige fejl.

## Hvad det laeser

`msg_shas` fra `core.services.cache_telemetry` — ét aftryk pr. besked, i
raekkefoelge. Den foerste plads hvor to runder er uenige ER bruddet. Summen af
`msg_lens` foer den plads er hvor langt cachen kunne naa.

Brug:  cache_break_report.py [ISO-skaeringspunkt] [--alle]
"""
from __future__ import annotations

import collections
import json
import pathlib
import sqlite3
import sys


def _faelles_praefiks(a: list, b: list) -> int:
    n = 0
    for x, y in zip(a, b):
        if x != y:
            break
        n += 1
    return n


def _hent(skaer: str) -> dict[str, list[dict]]:
    db = pathlib.Path.home() / ".jarvis-v2" / "state" / "jarvis.db"
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    pr_run: dict[str, list[dict]] = collections.defaultdict(list)
    # created_at er ISO MED 'T'. Skaeringspunktet skal have samme form — 'T'
    # sorterer efter mellemrum, saa en graense med mellemrum slipper hele
    # doegnet igennem uden at fejle. Det kostede én forkert konklusion.
    for r in con.execute(
        "SELECT payload_json FROM events WHERE kind=? AND created_at >= ? ORDER BY created_at",
        ("cache.telemetry", skaer),
    ):
        try:
            p = json.loads(r["payload_json"] or "{}")
        except json.JSONDecodeError:
            # En enkelt beskadiget linje maa ikke stoppe rapporten; den taeller
            # bare ikke med. Telemetrien skrives self-safe og kan vaere afkortet
            # hvis processen doede midt i en skrivning.
            continue
        rid = str(p.get("run_id") or "")
        if rid and isinstance(p.get("round"), int) and p.get("msg_shas"):
            pr_run[rid].append(p)
    return pr_run


def main() -> int:
    argv = [a for a in sys.argv[1:] if not a.startswith("--")]
    alle = "--alle" in sys.argv
    skaer = argv[0] if argv else "2026-01-01T00:00:00"
    pr_run = _hent(skaer)
    if not pr_run:
        print(f"ingen telemetri med msg_shas siden {skaer} — er den nye maaler deployet?")
        return 1

    brud: list[tuple] = []
    runder_i_alt = afkortede = 0
    for rid, poster in pr_run.items():
        poster.sort(key=lambda p: p["round"])
        for foer, efter in zip(poster, poster[1:]):
            runder_i_alt += 1
            a, b = foer.get("msg_shas") or [], efter.get("msg_shas") or []
            # Ramte listen loftet, mangler halen — og bruddet kan ligge derude.
            if len(a) < int(foer.get("msg_count") or len(a)):
                afkortede += 1
            k = _faelles_praefiks(a, b)
            if k >= len(a):
                continue  # ren tilfoejelse — cachen kan vokse, intet brud
            stabile_tegn = sum((foer.get("msg_lens") or [])[:k])
            omskrevne = len(a) - k
            brud.append((
                int(efter.get("miss") or 0), rid[-12:], efter["round"], k, len(a), omskrevne,
                stabile_tegn, int(foer.get("hit") or 0), int(efter.get("hit") or 0),
                foer.get("system_sha") != efter.get("system_sha"),
                foer.get("tools_sha") != efter.get("tools_sha"),
                foer.get("tail_sha") != efter.get("tail_sha"),
            ))

    print(f"skaeringspunkt {skaer}   runs {len(pr_run)}   runde-par {runder_i_alt}")
    if afkortede:
        print(f"ADVARSEL: {afkortede} par hvor besked-listen ramte loftet — bruddet kan ligge efter det")
    print(f"par med et brud inde i samtalen: {len(brud)}   "
          f"({100.0 * len(brud) / max(runder_i_alt, 1):.0f} %)")
    if not brud:
        print("\nIntet brud: hver runde var en ren tilfoejelse til den foregaaende.")
        return 0
    spildt = sum(b[0] for b in brud)
    print(f"miss i de runder: {spildt:,} tokens\n")
    print("%-14s %5s %7s %7s %9s %11s %11s  %s" % (
        "run", "runde", "brud@", "af", "omskrevet", "hit foer", "hit efter", "sys/tools/hale"))
    for r in sorted(brud, reverse=True)[: (len(brud) if alle else 15)]:
        miss, rid, runde, k, n, omskrevne, tegn, h0, h1, ds, dt, dh = r
        maerker = "".join(bogstav if aendret else "-"
                          for aendret, bogstav in ((ds, "S"), (dt, "T"), (dh, "H")))
        print("  %-12s %5d %7d %7d %9d %11s %11s  %s   stabilt: %s tegn" % (
            rid, runde, k, n, omskrevne, f"{h0:,}", f"{h1:,}", maerker, f"{tegn:,}"))

    # Hvilken PLADS braekker oftest? Et fast indeks peger paa en fast afsender.
    pladser = collections.Counter(b[3] for b in brud)
    print("\nhyppigste brudsted (besked-indeks):")
    for plads, n in pladser.most_common(8):
        print(f"   indeks {plads:4}  {n} gange")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
