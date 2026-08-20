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

    # COST-CENTRERET klassifikation. Den run-centrerede version havde en
    # restfejl (Codex): ved én cost-række inde i TO overlappende runs vandt det
    # første run rækken, og kun det andet blev markeret tvetydigt — så en
    # tvetydig række blev alligevel rapporteret som et gyldigt datapunkt.
    # Nu afgøres ejerskabet PR. RÆKKE: har den flere mulige ejere, afvises de
    # ALLE. En tvetydig række må aldrig blive til et tal nogen stoler på.
    owner: dict[int, str] = {}          # cost-index -> run_id
    src_of: dict[int, str] = {}         # cost-index -> "run_id" | "interval"
    contested: dict[str, str] = {}      # run_id -> årsag

    for i, c in enumerate(costs):
        if has_run_id and c.get("run_id"):
            owner[i], src_of[i] = c["run_id"], "run_id"
            continue
        t = parse_ts(c["created_at"])
        if t is None:
            continue
        cand = [r for r in runs
                if (s := parse_ts(r[3])) and (f := parse_ts(r[4]))
                and s <= t <= f and r[1] == c["provider"] and r[2] == c["model"]]
        if len(cand) == 1:
            owner[i], src_of[i] = cand[0][0], "interval"
        elif len(cand) > 1:
            for r in cand:
                contested[r[0]] = f"deler cost-række med {len(cand) - 1} andet/andre run(s)"

    by_run: dict[str, list[int]] = {}
    for i, rid in owner.items():
        by_run.setdefault(rid, []).append(i)

    ambiguous: list[tuple[str, str]] = list(contested.items())

    for run_id, prov, model, started, finished, status in runs:
        rows = by_run.get(run_id, [])
        if run_id in contested or not rows:
            continue
        source = src_of[rows[0]]

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

    orphan = [c for i, c in enumerate(costs) if i not in owner]
    if orphan:
        print(f"\n  ⚠️ {len(orphan)} cost-rækker uden ejer:")
        for c in orphan[:6]:
            print(f"     {c['created_at'][11:19]} lane={c['lane']:<8} {c['model']:<22} {c['inp']:>7} tok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
