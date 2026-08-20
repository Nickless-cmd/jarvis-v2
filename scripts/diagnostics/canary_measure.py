"""Canary-måling for tool_result_round_collapse — eksakt kobling, ingen gæt.

Skrevet efter at jeg selv lavede den fejl værktøjet skal forhindre: jeg
matchede TTFT-tal til cost-rækker på tidsnærhed og konkluderede at cache-hit
dominerede over transcriptvægt. De hurtige tal hørte i virkeligheden til
15k-prompts fra en NY session, ikke til de cache-varme 111k-runs — som slet
ikke producerede synlig tekst (de brændte hele reasoning-budgettet).

Første version af dette script havde fire fejl, fundet af Codex:
  1. "UMATCHET" var en løgn: ved overlappende runs tog det første run rækken,
     og de øvrige sprang den over via `matched` — tvetydighed blev til stilhed.
  2. Ingen provider/model-verifikation, så en samtidig stor cost kunne
     tilskrives det forkerte run og vises under dettes modelnavn.
  3. Tidsstempler blev trunkeret til sekunder, hvilket gjorde overlap og
     boundary-fejl mere sandsynlige.
  4. (Og selve scriptet var aldrig deployet, mens jeg rapporterede det som det.)

Nu: `run_id` bruges direkte når det findes; interval-match er KUN en historisk
fallback, kræver præcis ÉN kandidat med matchende provider/model, og alt andet
rapporteres eksplicit som umatchet med årsag.

Kun læsning. Ændrer intet.
"""
from __future__ import annotations

import sqlite3
import sys
from datetime import datetime
from pathlib import Path

DB = Path.home() / ".jarvis-v2/state/jarvis.db"


def parse_ts(raw: str) -> datetime | None:
    """Fuld præcision — mikrosekunder OG timezone bevares.

    costs skriver ISO med 'Z', visible_runs med '+00:00'. Begge normaliseres
    uden at kaste information væk; trunkering til sekunder var netop dét der
    gjorde boundary-fejl sandsynlige.
    """
    if not raw:
        return None
    txt = raw.strip().replace(" ", "T")
    if txt.endswith("Z"):
        txt = txt[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(txt)
    except ValueError:
        return None
    if dt.tzinfo is None:
        from datetime import timezone
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def main() -> int:
    since = sys.argv[1] if len(sys.argv) > 1 else "2026-08-20T18:00"
    con = sqlite3.connect(str(DB))

    cols = {r[1] for r in con.execute("PRAGMA table_info(costs)")}
    has_run_id = "run_id" in cols
    print(f"  costs.run_id: {'JA — eksakt kobling' if has_run_id else 'NEJ — kun interval-fallback'}")

    runs = con.execute("""
        SELECT run_id, provider, model, started_at, finished_at, status
        FROM visible_runs WHERE started_at > ? ORDER BY started_at
    """, (since,)).fetchall()

    sel = ("SELECT created_at, lane, provider, model, input_tokens, output_tokens, "
           "cache_hit_tokens, cache_miss_tokens" + (", run_id" if has_run_id else "") +
           " FROM costs WHERE created_at > ? AND input_tokens > 40000 ORDER BY created_at")
    costs = [dict(zip(
        ["created_at", "lane", "provider", "model", "inp", "out", "hit", "miss"] +
        (["run_id"] if has_run_id else []), row)) for row in con.execute(sel, (since,))]
    con.close()

    print(f"  {len(runs)} runs, {len(costs)} cost-rækker >40k tokens siden {since}\n")
    print(f"  {'run':<10} {'model':<24} {'inp':>7} {'cache%':>7} {'sek':>5}  kilde")
    print("  " + "-" * 72)

    claimed: dict[int, str] = {}   # cost-index -> run_id
    ambiguous: list[tuple[int, str]] = []

    for run_id, prov, model, started, finished, status in runs:
        rows: list[int] = []
        source = ""
        if has_run_id:
            rows = [i for i, c in enumerate(costs) if c.get("run_id") == run_id]
            source = "run_id"
        if not rows:
            # Historisk fallback: præcis ÉN kandidat, og provider/model SKAL matche.
            s, f = parse_ts(started), parse_ts(finished)
            if not (s and f):
                continue
            cand = [i for i, c in enumerate(costs)
                    if (t := parse_ts(c["created_at"])) and s <= t <= f
                    and c["provider"] == prov and c["model"] == model]
            if len(cand) != 1:
                if cand:
                    ambiguous.append((run_id, f"{len(cand)} kandidater i intervallet"))
                continue
            rows, source = cand, "interval"

        # Er nogen af rækkerne allerede taget af et andet run? Så er den tvetydig
        # — og skal SIGES, ikke skjules bag en 'matched'-mængde.
        stolen = [i for i in rows if i in claimed and claimed[i] != run_id]
        if stolen:
            ambiguous.append((run_id, f"deler række med run {claimed[stolen[0]][8:16]}"))
            continue
        for i in rows:
            claimed[i] = run_id

        inp = sum(costs[i]["inp"] for i in rows)
        hit = sum(costs[i]["hit"] for i in rows)
        pct = f"{100 * hit // inp}%" if inp else "-"
        dur = ""
        s, f = parse_ts(started), parse_ts(finished)
        if s and f:
            dur = f"{(f - s).total_seconds():.0f}"
        warn = "  ⚠️ :cloud → INGEN cachetal" if "cloud" in model else ""
        print(f"  {run_id[8:16]:<10} {model:<24} {inp:>7} {pct:>7} {dur:>5}  {source}{warn}")

    if ambiguous:
        print(f"\n  ⚠️ {len(ambiguous)} runs UDEN entydig kobling (ikke gættet på plads):")
        for rid, why in ambiguous[:8]:
            print(f"     {rid[8:16]}  {why}")

    orphan = [c for i, c in enumerate(costs) if i not in claimed]
    if orphan:
        print(f"\n  ⚠️ {len(orphan)} cost-rækker uden ejer:")
        for c in orphan[:6]:
            print(f"     {c['created_at'][11:19]} lane={c['lane']:<8} {c['model']:<22} {c['inp']:>7} tok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
