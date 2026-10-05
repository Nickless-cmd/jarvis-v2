#!/usr/bin/env python3
"""Vaerktoejer pr. agentisk runde — dagsserie.

Bygget 5/10-2026. Ventetiden i et synligt run er `runder x output pr. runde`,
og den foerste faktor var aldrig maalt. Maalingen 5/10 gav 1,59 vaerktoejer pr.
runde, 55 % af alle kald fulgte et kald til SAMME vaerktoej, og kaederne gik op
til 16 i traek — 78 % af dem rent laesende. Runtime'en udfoerer allerede hvert
`tool_call` i en runde, saa manglen var instruktionen.

Metrikken kan beregnes BAGUD, og det er hele pointen: stoejgulvet kommer
gratis fra historikken, saa en aendring kan doemmes mod dag-til-dag-spredningen
i stedet for mod ét foer-tal. Se memory `uaendret_er_ikke_altid_til_stede`.

VIGTIGT: runder maales paa `runtime.agentic_round_start`-events. Maaler man dem
paa `content_json`, faar man 100,0 % "praecis ét vaerktoej pr. runde", fordi
blokkene dér er par-ordnede — det er lagerformatet, ikke adfaerden. Se memory
`runder_maales_paa_round_start`.

Koer paa Jarvis-hosten (CT105) — en lokal DB svarer paa et andet spoergsmaal:
  /opt/conda/envs/ai/bin/python3 scripts/maal_vaerktoejer_pr_runde.py --dage 14
"""
from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from pathlib import Path

HOME = Path(os.environ.get("HOME", "/root")) / ".jarvis-v2"
DB_PATH = HOME / "state" / "jarvis.db"

# ISO-tidsstempler med 'T' sorterer ikke som `datetime('now',...)`-output
# (mellemrum < 'T'), saa en graense bygget med datetime() slipper hele dagen
# igennem. Se memory `cheaplane_health_and_query_trap`.
_SIDEN = "strftime('%Y-%m-%dT%H:%M:%S','now',?)"

_SQL = f"""
with runder as (
  select substr(created_at, 1, 10) as dag,
         json_extract(payload_json, '$.run_id') as run_id,
         json_extract(payload_json, '$.round') as runde
  from events
  where kind = 'runtime.agentic_round_start' and created_at >= {_SIDEN}
), pr_run as (
  select dag, run_id, max(runde) as runder_i_run, count(*) as events_i_run
  from runder group by dag, run_id
), vaerktoej as (
  select substr(created_at, 1, 10) as dag, count(*) as resultater
  from chat_messages
  where role = 'tool' and created_at >= {_SIDEN}
  group by 1
)
select pr_run.dag                                        as dag,
       count(*)                                          as runs,
       sum(events_i_run)                                 as runder,
       coalesce(vaerktoej.resultater, 0)                 as vaerktoejskald,
       round(1.0 * coalesce(vaerktoej.resultater, 0)
             / nullif(sum(events_i_run), 0), 2)          as pr_runde,
       round(1.0 * sum(events_i_run) / count(*), 1)       as runder_pr_run,
       max(runder_i_run)                                  as flest_runder
from pr_run
left join vaerktoej on vaerktoej.dag = pr_run.dag
group by pr_run.dag
order by pr_run.dag
"""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dage", type=int, default=14, help="antal dage tilbage (default 14)")
    ap.add_argument("--db", type=Path, default=DB_PATH)
    args = ap.parse_args()

    if not args.db.exists():
        print(f"ingen database paa {args.db} — koerer du paa den rigtige vaert?", file=sys.stderr)
        return 2

    graense = f"-{int(args.dage)} days"
    with sqlite3.connect(f"file:{args.db}?mode=ro", uri=True) as conn:
        conn.row_factory = sqlite3.Row
        raekker = conn.execute(_SQL, (graense, graense)).fetchall()

    if not raekker:
        print("ingen runder i vinduet")
        return 0

    print(f"{'dag':12s}{'runs':>6s}{'runder':>8s}{'kald':>8s}"
          f"{'pr.runde':>10s}{'runder/run':>12s}{'flest':>7s}")
    for r in raekker:
        print(f"{r['dag']:12s}{r['runs']:6d}{r['runder']:8d}{r['vaerktoejskald']:8d}"
              f"{r['pr_runde'] or 0:10.2f}{r['runder_pr_run'] or 0:12.1f}{r['flest_runder'] or 0:7d}")

    tal = [float(r["pr_runde"]) for r in raekker if r["pr_runde"]]
    if len(tal) >= 2:
        snit = sum(tal) / len(tal)
        spredning = (sum((x - snit) ** 2 for x in tal) / (len(tal) - 1)) ** 0.5
        print(f"\nvaerktoejer pr. runde: snit {snit:.2f}, spredning {spredning:.2f} "
              f"({min(tal):.2f}-{max(tal):.2f})")
        print("En aendring skal overstige spredningen for at vaere en aendring.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
