"""Canary-måling for tool_result_round_collapse — bundet, ikke håndmatchet.

Fælden der gjorde dette nødvendigt: `costs` har INTET run_id, kun created_at.
Jeg koblede TTFT-tal til cost-rækker på tidsnærhed og konkluderede forkert at
cache-hit dominerede over transcriptvægt. Codex viste at de hurtige tal hørte
til 15k-prompts fra en ny session — ikke til de cache-varme 111k-runs, som
ikke producerede synlig tekst overhovedet.

Her bindes hver cost-række til det visible_run hvis [started_at, finished_at]
den falder indenfor. Rækker uden entydig ejer rapporteres som UMATCHEDE i
stedet for at blive gættet på plads.

Kun læsning. Ændrer intet.
"""
import sqlite3
import sys
from pathlib import Path

DB = Path.home() / ".jarvis-v2/state/jarvis.db"
SINCE = sys.argv[1] if len(sys.argv) > 1 else "2026-08-20T18:00"


def iso(s):
    """costs bruger ISO med T/Z, visible_runs med +00:00 — normalisér begge."""
    return (s or "").replace("T", " ").replace("Z", "")[:19]


con = sqlite3.connect(str(DB))
runs = con.execute("""
    SELECT run_id, provider, model, started_at, finished_at, status
    FROM visible_runs WHERE started_at > ? AND lane='primary'
    ORDER BY started_at
""", (SINCE,)).fetchall()

costs = con.execute("""
    SELECT created_at, lane, model, input_tokens, output_tokens,
           cache_hit_tokens, cache_miss_tokens
    FROM costs WHERE created_at > ? AND input_tokens > 40000
    ORDER BY created_at
""", (SINCE,)).fetchall()

print(f"  {len(runs)} runs, {len(costs)} store cost-rækker siden {SINCE}\n")
print(f"  {'run':<10} {'model':<24} {'inp':>7} {'cache%':>6} {'sek':>5}  status")
print("  " + "-" * 66)

matched = set()
for run_id, prov, model, start, fin, status in runs:
    s, f = iso(start), iso(fin)
    mine = [c for i, c in enumerate(costs) if s <= iso(c[0]) <= f and i not in matched]
    if not mine:
        continue
    for i, c in enumerate(costs):
        if s <= iso(c[0]) <= f:
            matched.add(i)
    inp = sum(c[3] for c in mine)
    hit = sum(c[5] for c in mine)
    pct = int(100 * hit / inp) if inp else 0
    dur = ""
    try:
        from datetime import datetime
        dur = f"{(datetime.fromisoformat(fin.replace(' ', 'T')) - datetime.fromisoformat(s.replace(' ', 'T'))).total_seconds():.0f}"
    except Exception:
        pass
    flag = "" if "cloud" not in model else "  ⚠️ :cloud = INGEN cachetal"
    print(f"  {run_id[8:16]:<10} {model:<24} {inp:>7} {pct:>5}% {dur:>5}  {status}{flag}")

umatched = [c for i, c in enumerate(costs) if i not in matched]
if umatched:
    print(f"\n  ⚠️ {len(umatched)} cost-rækker uden entydigt run — IKKE gættet på plads:")
    for c in umatched[:5]:
        print(f"     {iso(c[0])[11:]} lane={c[1]:<8} {c[3]:>7} tok")
con.close()
