#!/usr/bin/env python3
"""Tænke-sprog A/B — snapshot og sammenligning (30/9-2026).

Måler hvilket spor tænke-sprog-skiftet sætter i tallene, pr. lane:

  * tænke-andel af output   (reasoning_tokens / output_tokens)
  * tænke-tokens pr. kald
  * output-tokens pr. kald
  * rundetid (proxy — se nedenfor)
  * pris

## Brug

    # baseline: vinduet FØR skiftet
    python scripts/think_language_ab.py --until 2026-09-30T15:30:00 --save /tmp/tl_baseline.json

    # om et par timer: vinduet EFTER skiftet
    python scripts/think_language_ab.py --since 2026-09-30T15:30:00 --save /tmp/tl_efter.json

    python scripts/think_language_ab.py --compare /tmp/tl_baseline.json /tmp/tl_efter.json

`--since`/`--until` er ISO-tid i UTC (samme form som `costs.created_at`).

## Rundetid — hvorfor det er et PROXY og ikke en måling

Der findes ingen timing-tabel, og `visible_runs` indeholder kun `primary`-lanen
— ikke `agentic_round`, som er den lane der bærer tænkningen. Derfor udledes
rundetiden af afstanden mellem `created_at` på to på hinanden følgende runder i
SAMME run_id: den afstand er hvor længe den næste runde tog (kald + tænkning).
Det er et ægte signal, men det indeholder også netværk og værktøjskørsel — så
det kan vise retning, ikke isolere tænkningens andel af tiden.

## Hvad der IKKE kan måles — og hvorfor det skal siges højt

`reasoning_tokens` fyldes kun af de kaldesteder der læser DeepSeeks
`completion_tokens_details`. Målt 30/9 fylder den i `agentic_round` og ikke i
`visible` — så `visible` står med 0, og det betyder «ikke målt», ikke «ingen
tænkning». Konklusioner må derfor hvile på `agentic_round`.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from datetime import UTC, datetime

sys.path.insert(0, ".")

from core.runtime.db import connect  # noqa: E402

# Kolonnen begyndte først at fylde her (målt 30/9-2026).
FIRST_MEASURED = "2026-09-30T14:20:53"

MEASURED_LANE = "agentic_round"


def _roundtime_proxy(conn, lane: str, since: str, until: str | None) -> dict:
    """Median afstand mellem på hinanden følgende runder i samme run_id."""
    sql = "SELECT run_id, created_at FROM costs WHERE lane = ? AND created_at >= ?"
    params: list = [lane, since]
    if until:
        sql += " AND created_at < ?"
        params.append(until)
    sql += " ORDER BY run_id, created_at"
    rows = conn.execute(sql, params).fetchall()

    deltas: list[float] = []
    prev_run = prev_ts = None
    for r in rows:
        ts = datetime.fromisoformat(str(r["created_at"]))
        if prev_run == r["run_id"] and prev_ts is not None:
            d = (ts - prev_ts).total_seconds()
            # Spring absurditeter over (fx en tur der har ligget stille i timer).
            if 0 < d < 600:
                deltas.append(d)
        prev_run, prev_ts = r["run_id"], ts

    if not deltas:
        return {"n": 0, "median_s": None, "gns_s": None}
    return {
        "n": len(deltas),
        "median_s": round(statistics.median(deltas), 2),
        "gns_s": round(statistics.mean(deltas), 2),
    }


def snapshot(since: str, until: str | None = None) -> dict:
    """Tag et snapshot af alle laner i vinduet [since, until)."""
    conn = connect()
    try:
        sql = """
            SELECT lane,
                   COUNT(*)              AS n,
                   SUM(reasoning_tokens) AS reas,
                   SUM(output_tokens)    AS out,
                   SUM(input_tokens)     AS inp,
                   SUM(cache_hit_tokens) AS hit,
                   SUM(cache_miss_tokens) AS miss,
                   SUM(cost_usd)         AS usd
            FROM costs
            WHERE created_at >= ?
        """
        params: list = [since]
        if until:
            sql += " AND created_at < ?"
            params.append(until)
        sql += " GROUP BY lane ORDER BY out DESC"

        lanes = conn.execute(sql, params).fetchall()
        roundtime = _roundtime_proxy(conn, MEASURED_LANE, since, until)
    finally:
        conn.close()

    out = {
        "since": since,
        "until": until,
        "taget": datetime.now(UTC).isoformat(),
        "rundetid_proxy": roundtime,
        "lanes": {},
    }
    for r in lanes:
        out_tok = int(r["out"] or 0)
        reas = int(r["reas"] or 0)
        n = int(r["n"] or 0)
        out["lanes"][r["lane"]] = {
            "n": n,
            "reasoning_tokens": reas,
            "output_tokens": out_tok,
            "input_tokens": int(r["inp"] or 0),
            "cache_hit": int(r["hit"] or 0),
            "cache_miss": int(r["miss"] or 0),
            "cost_usd": round(float(r["usd"] or 0), 6),
            "taenke_andel": round(reas / out_tok, 4) if out_tok else 0.0,
            "output_pr_kald": round(out_tok / n, 1) if n else 0.0,
            "taenke_pr_kald": round(reas / n, 1) if n else 0.0,
        }
    return out


def _fmt(snap: dict) -> str:
    window = f"{snap['since'][:19]} → {(snap.get('until') or 'nu')[:19]}"
    lines = [f"  snapshot {snap['taget'][:19]}   vindue: {window}", ""]
    rt = snap.get("rundetid_proxy") or {}
    if rt.get("median_s"):
        lines.append(f"  rundetid ({MEASURED_LANE}, proxy): median {rt['median_s']}s "
                     f"· gns {rt['gns_s']}s · n={rt['n']}")
        lines.append("")
    lines.append(f"  {'lane':<16}{'n':>6}{'tænke/kald':>12}{'out/kald':>10}"
                 f"{'tænke-andel':>13}{'$':>10}")
    for lane, d in sorted(snap["lanes"].items(), key=lambda kv: -kv[1]["output_tokens"]):
        mark = "  ← målt" if lane == MEASURED_LANE else ""
        lines.append(
            f"  {lane:<16}{d['n']:>6}{d['taenke_pr_kald']:>12.0f}"
            f"{d['output_pr_kald']:>10.0f}{d['taenke_andel']*100:>12.1f}%"
            f"{d['cost_usd']:>10.4f}{mark}"
        )
    return "\n".join(lines)


def compare(a: dict, b: dict) -> str:
    lines = [_fmt(a), "", _fmt(b), "", "  ── ÆNDRING ──", ""]
    ra = (a.get("rundetid_proxy") or {}).get("median_s")
    rb = (b.get("rundetid_proxy") or {}).get("median_s")
    if ra and rb:
        lines.append(f"  rundetid (proxy)   median {ra:.1f}s → {rb:.1f}s "
                     f"({(rb - ra) / ra * 100:+.1f}%)")
    for lane in sorted(set(a["lanes"]) | set(b["lanes"])):
        da, db_ = a["lanes"].get(lane), b["lanes"].get(lane)
        if not da or not db_:
            continue
        ra_, rb_ = da.get("taenke_pr_kald", 0), db_.get("taenke_pr_kald", 0)
        if not ra_ and not rb_:
            continue
        delta = ((rb_ - ra_) / ra_ * 100) if ra_ else 0.0
        mark = "  ← MÅLT LANE" if lane == MEASURED_LANE else ""
        lines.append(
            f"  {lane:<16} tænke/kald {ra_:>7.0f} → {rb_:>7.0f} ({delta:+.1f}%)"
            f"   andel {da.get('taenke_andel', 0)*100:>5.1f}% → {db_.get('taenke_andel', 0)*100:>5.1f}%"
            f"   n {da.get('n', 0)} → {db_.get('n', 0)}{mark}"
        )
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--since", default=FIRST_MEASURED,
                    help=f"ISO-tid UTC (default: {FIRST_MEASURED}, hvor kolonnen begyndte at fylde)")
    ap.add_argument("--until", help="ISO-tid UTC — eksklusiv øvre grænse")
    ap.add_argument("--save", help="skriv snapshot til denne JSON-fil")
    ap.add_argument("--compare", nargs=2, metavar=("FOER", "EFTER"),
                    help="sammenlign to gemte snapshots")
    args = ap.parse_args()

    if args.compare:
        with open(args.compare[0]) as f:
            a = json.load(f)
        with open(args.compare[1]) as f:
            b = json.load(f)
        print(compare(a, b))
        return 0

    snap = snapshot(args.since, args.until)
    print(_fmt(snap))
    if args.save:
        with open(args.save, "w") as f:
            json.dump(snap, f, indent=2, ensure_ascii=False)
        print(f"\n  gemt → {args.save}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
