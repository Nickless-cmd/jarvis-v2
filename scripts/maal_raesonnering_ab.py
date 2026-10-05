#!/usr/bin/env python3
"""A/B: koster det noget at lade mellem-runderne vaere uden raesonnering?

Maalt 5/10-2026: 32,9 % af alt output er raesonnering (5,17 mio. af 15,7 mio.
tokens paa 7 dage), og latensen er naesten linjaer i output — 2,69 s ved
0-400 output-tokens, 14,10 s ved 1600+. Men det er paa mellem-runderne Jarvis
vaelger hvilket vaerktoej han skal bruge, saa kvalitetsprisen er umaalt.
Derfor et A/B frem for et flip.

Armen er en REN funktion af run_id, saa den kan regnes ud bagefter. Dette
skript bruger **samme funktion** som produktionen (`arm_for_run`), ikke en
kopi — `beacon_vagt.py` siger hvorfor: dens foerste udgave havde sin egen
parser, ramte ingenting, og meldte «ingen haendelser» i en halv time.

## TO FAELDER, byg ikke dette skript uden dem

1. **Graensen.** Armen kan udregnes for ethvert run_id, ogsaa for runs fra FOER
   forsoeget fandtes — og de koerte alle med fuld raesonnering uanset hvad
   armen siger om dem. Uden `--siden` sammenligner man stoej med stoej.
   Standarden er deploy-tidspunktet.
2. **Andelen.** Armen afhaenger af `raesonnering_daempet_procent` som den var
   da kaldet skete. AENDRER du den, er historiske runs fejl-sorteret bagefter.
   `--procent` skal matche det der var sat i vinduet.

Koer paa Jarvis-hosten (CT105):
  /opt/conda/envs/ai/bin/python3 scripts/maal_raesonnering_ab.py --dage 7
"""
from __future__ import annotations

import argparse
import os
import sqlite3
import statistics
import sys
from pathlib import Path

sys.path.insert(0, __file__.rsplit("/scripts/", 1)[0])
from core.services.raesonnering_eksperiment import ARM_DAEMPET, arm_for_run  # noqa: E402

HOME = Path(os.environ.get("HOME", "/root")) / ".jarvis-v2"
DB_PATH = HOME / "state" / "jarvis.db"

#: Forsoeget blev deployet her. Runs foer dette tidspunkt koerte med fuld
#: raesonnering uanset hvad deres arm regner ud, saa de maa ikke taelle med.
#:
#: **UTC.** `costs.created_at` er UTC, og vaerten koerer CEST. Foerste udgave
#: stod paa «16:00» i lokal tid, altsaa 14:00 UTC i min hensigt men 16:00 UTC
#: i sammenligningen — en graense to timer ude i FREMTIDEN. Skriptet svarede
#: «ingen data» mens der var koert runder i otte minutter, og det svar lignede
#: et gyldigt «forsoeget er for ungt». Tallet nedenfor er det tidspunkt
#: processerne faktisk startede med koden, laest af systemd i UTC.
DEPLOY = "2026-10-05T15:36:33"


def armdata(
    db: Path,
    *,
    dage: int = 7,
    procent: int = 20,
    siden: str = DEPLOY,
) -> dict[str, dict]:
    """{arm: {ud, raeson, runs, runder, pr_dag}} — kilden BAADE CLI og monitor laeser.

    Én kilde til maalingen. `beacon_vagt.py` siger hvorfor: dens foerste udgave
    havde sin egen parser, ramte ingenting, og meldte «ingen haendelser» i en
    halv time. En monitor der gentager en forespoergsel kan maale noget andet
    end rapporten uden at nogen ser det.

    `pr_dag` baeres med fordi en sammenligning MELLEM arme kun betyder noget
    naar man kender spredningen INDEN for dem. Et enkelt tal pr. arm kan ikke
    skelne en effekt fra en travl tirsdag.
    """
    with sqlite3.connect(f"file:{db}?mode=ro", uri=True) as conn:
        conn.row_factory = sqlite3.Row
        raekker = conn.execute(
            """
            select run_id, output_tokens, reasoning_tokens, created_at,
                   cache_miss_tokens, cache_hit_tokens
            from costs
            where lane = 'agentic_round' and provider like '%deepseek%'
              and (cache_hit_tokens + cache_miss_tokens) > 0
              and created_at >= ?
              and created_at >= strftime('%Y-%m-%dT%H:%M:%S', 'now', ?)
            """,
            (siden, f"-{int(dage)} days"),
        ).fetchall()

    arme: dict[str, dict] = {}
    for r in raekker:
        arm = arm_for_run(str(r["run_id"] or ""), procent=procent)
        b = arme.setdefault(arm, {"ud": [], "raeson": [], "runs": set(),
                                  "runder": 0, "pr_dag": {}})
        b["ud"].append(int(r["output_tokens"] or 0))
        b["raeson"].append(int(r["reasoning_tokens"] or 0))
        b["runs"].add(str(r["run_id"] or ""))
        b["runder"] += 1
        dag = b["pr_dag"].setdefault(str(r["created_at"] or "")[:10],
                                     {"runs": set(), "runder": 0})
        dag["runs"].add(str(r["run_id"] or ""))
        dag["runder"] += 1
    return arme


def runder_pr_run_pr_dag(arm: dict, *, min_runs: int = 3) -> list[float]:
    """Dagsserien for én arm. Dage med for faa runs udelades — én run paa en
    soendag er ikke et datapunkt, og med 20 % eksponering er tynde dage reglen."""
    ud = []
    for dag in (arm.get("pr_dag") or {}).values():
        n = len(dag["runs"])
        if n >= min_runs:
            ud.append(dag["runder"] / n)
    return ud


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dage", type=int, default=7)
    ap.add_argument("--procent", type=int, default=20,
                    help="andelen som den var i vinduet (default 20)")
    ap.add_argument("--siden", default=DEPLOY, help=f"ISO-graense (default {DEPLOY})")
    ap.add_argument("--db", type=Path, default=DB_PATH)
    args = ap.parse_args()

    if not args.db.exists():
        print(f"ingen database paa {args.db}", file=sys.stderr)
        return 2

    graense = max(args.siden, "")
    arme = armdata(args.db, dage=args.dage, procent=args.procent, siden=graense)
    if not arme:
        print(f"ingen agentiske runder siden {graense} — forsoeget har ikke data endnu")
        return 0
    i_alt = sum(a["runder"] for a in arme.values())
    print(f"graense {graense} · andel {args.procent} % · {i_alt} runder\n")
    print(f"{'arm':10s}{'runs':>6s}{'runder':>8s}{'runder/run':>12s}"
          f"{'ud median':>11s}{'raeson med':>12s}{'raeson %':>10s}")
    for arm in sorted(arme):
        b = arme[arm]
        ud, ra = b["ud"], b["raeson"]
        print(f"{arm:10s}{len(b['runs']):6d}{b['runder']:8d}"
              f"{b['runder']/max(len(b['runs']),1):12.1f}"
              f"{statistics.median(ud):11.0f}{statistics.median(ra):12.0f}"
              f"{100.0*sum(ra)/max(sum(ud),1):10.1f}")

    if ARM_DAEMPET not in arme or len(arme) < 2:
        print("\nKun én arm har data endnu. Begge arme skal vaere med foer noget kan sammenlignes.")
        return 0

    d, f = arme[ARM_DAEMPET], arme[[a for a in arme if a != ARM_DAEMPET][0]]
    print("\nVIRKER KNAPPEN?  Daempet arm skal have ~0 raesonnering.")
    print(f"  daempet raeson-median {statistics.median(d['raeson']):.0f}"
          f"  mod fuld {statistics.median(f['raeson']):.0f}")
    if statistics.median(d["raeson"]) > 50:
        print("  ⚠ Den daempede arm raesonnerer stadig — knappen virker IKKE.")
        print("    Maal ikke kvalitet foer dette er nul; en arm der ikke blev")
        print("    daempet viser «ingen forskel» af den forkerte grund.")
        return 0
    print("\nHVAD KOSTER DET?  runder/run er proxyen: flere runder = han famler.")
    print(f"  daempet {d['runder']/max(len(d['runs']),1):.1f} runder/run"
          f"  mod fuld {f['runder']/max(len(f['runs']),1):.1f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
