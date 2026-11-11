---
status: maalt
slags: analyse
fravalg: [aendring af produktionskode, ny prompt-linje]
---

# Rundebudget-signalet: effekten kan ikke maales i den telemetri vi har

**Konklusion: signalets effekt er IKKE målt. Ikke fordi der er for få data, men fordi
telemetrien ikke indeholder nogen kørsel hvor signalet kan have fyret.** Tallene
nedenfor er baseline, ikke effekt.

## 1. Kaldes `_budget_note`?

Ja, men kun ét sted: `core/services/agent_loop_core.py:414`, i `run_tool_loop`
(`while rounds < max_rounds`, noten appendes som user-besked på :416). Betingelser
(`:94-98`): `max_rounds - rounds` ∈ {10, 5, 2} OG sidste besked er et `tool`-resultat.

`grep` efter `budget_note|Rundebudget` i `core/` finder ingen andre kaldere.
`visible_runs.py` importerer hverken `agent_loop_core` eller `_budget_note`.

## 2. Hvem kører `run_tool_loop`?

Kun agent-workere: `agent_runtime_base.py:336` (`max_rounds=60`, `_AGENT_TOOL_LOOP_MAX_ROUNDS`)
og `agent_worker_main.py:101` (`job["max_rounds"]`, default 8). **Ikke** den synlige
chat.

Den synlige chat har sit eget loop i `visible_runs.py` med
`_AGENTIC_MAX_ROUNDS = compute_agentic_loop_budget(...)["max_rounds"]`
(`:2278`; `affect_modulation.py:65` = 45, sænket til 18/12 ved kropspres/fatigue).
Det loop har ingen budgetnote.

## 3. Hvad telemetrien indeholder

Begge filer læst (`cache_telemetry.jsonl.1` 2.955 linjer + aktiv 141 linjer = 3.096),
dækker 2026-11-04 17:49 UTC → 2026-11-05 20:17 UTC.

- Lanes: `visible` 2.841, `visible-call` 255. Skrives af
  `cheap_provider_runtime_streaming.py` og `visible_followup_adapters.py` — begge
  synlig-chat. **Ingen agent-worker-lane findes.**
- Højeste `round` er 44 (= 45 runder, cappet af `max_rounds=45`). 199 run_ids; 27 nåede
  runde 35+, men det er det synlige loop, som ikke har signalet.
- Efter deploy (19:49 UTC = 20:49 dansk): 166 linjer, 15 runs, højeste runde 43. De
  er også synlige runs.

### Rettelser til opgavens forudsætninger

- **Der ER et tidsstempel**: feltet hedder `timestamp` (ISO, UTC). Fælde 2 i opgaven
  er forkert på dette punkt; filtrering efter deploy-tidspunkt er mulig.
- **«Runde 35+» er det forkerte tærskeltal for agent-loopet.** 35 = 45−10 gælder kun
  for `max_rounds=45`, altså det synlige loop, som ikke har noten. For
  `run_tool_loop` fyrer noten ved `rounds = max_rounds − 10/5/2`: ved 60 runder
  rundt 50/55/58; ved default 8 allerede ved runde 3 og 6.
- Fælde 1 og 3 stemmer: filen roterer (`.1` er læst), og kald pr. runde afledes som
  `msg_count`-vækst − 1.

## 4. Hvad der blev målt (baseline, synligt loop, ingen signal)

Metode: pr. `run_id` (lane `visible`), sorteret på `round`, kun på hinanden følgende
runder; kald = `msg_count[n+1] − msg_count[n] − 1`.

- 2.646 runde-overgange. Kald pr. runde: 0 → 0,9 %, 1 → 73,4 %, 2 → 22,9 %, 3+ → 2,8 %.
  (Opgavens baseline: 67,3 / 28,1 / 3,5 % over 1.646 overgange — min stikprøve er
  større og viser endnu flere enkeltkald; mønstret er det samme, tallene er ikke
  identiske.)
- Kald/runde pr. rundetal, kørsler der nåede runde ≥39 (22 runs):

  | runde | kald/runde | n |
  |---|---|---|
  | 0-4 | 1,60 | 110 |
  | 5-9 | 1,38 | 110 |
  | 10-14 | 1,19 | 110 |
  | 15-19 | 1,22 | 110 |
  | 20-24 | 1,21 | 110 |
  | 25-29 | 1,08 | 110 |
  | 30-34 | 1,12 | 110 |
  | 35-39 | 1,30 | 108 |
  | 40-44 | 1,21 | 63 |

  Før runde 34: 1,26 (748). Fra runde 34: 1,24 (193). Faldet 1,6 → 1,1 genfindes;
  stigningen i 35-39 er der også, **uden** signal — så et løft i slutningen er ikke
  i sig selv bevis for noten.

## 5. Hvad der ikke kunne måles

Effekten af `_budget_note` på kald/runde: der er nul agent-worker-runder i telemetrien,
og ingen af de målte runs fik noten. Ingen kontrolgruppe, ingen før/efter.

## 6. Ærlig konklusion

1. Signalet er bygget i et loop (agent-workere) som ikke er det der skaber
   problemet i data (synlig chat). Hvis målet var at få den synlige Jarvis til at
   batche, **rammer commit `26e75b3b4` ikke den kørsel**. Det er en designbeslutning
   der skal tages, ikke noget målingen kan afgøre.
2. Hvis målet var agent-workere, mangler der telemetri for dem.
3. Der er ingen evidens for effekt, hverken positiv eller negativ.

## 7. Hvad der skal til for at måle

Telemetri kan ikke gøre det alene i dag. Først skal én af to ting ske (kræver
kodeændring, bevidst ikke gjort her): enten log kald/runde fra `run_tool_loop`
(f.eks. `lane="agent"` + `run_id` i `cache_telemetry`), eller indfør noten i
`visible_runs.py`.

Derefter, N dage efter at en af dem er deployet (vælg tidspunkt T = deploy i UTC):

```bash
python3 - <<'E'
import json, collections
T = "2026-11-DDTHH:MM"            # <- deploy-tidspunkt i UTC (ISO-streng, samme format som feltet timestamp)
LANE = "agent"                    # eller "visible" hvis noten flyttes dertil
rows = []
for f in ("cache_telemetry.jsonl.1", "cache_telemetry.jsonl"):   # begge: filen roterer ved ~8 MB
    for l in open(f"/home/bs/.jarvis-v2/logs/{f}"):
        try: rows.append(json.loads(l))
        except ValueError: pass
runs = collections.defaultdict(list)
for r in rows:
    if r["lane"] == LANE: runs[r["run_id"]].append(r)
# 'efter' = run_id hvis FØRSTE linje er >= T; 'foer' = runs der slutter før T.
# Bland ikke runs der spænder over T. Filtrér pr. run, ikke pr. linje.
# Signalpunkter: round >= max_rounds-10 (kræv max_rounds logget eller kendt pr. run).
# kald pr. runde = msg_count[n+1] - msg_count[n] - 1 på hinanden følgende round.
E
```

Rotationen kan have slettet `.1`-historik efter N dage (kun én generation gemmes), så
kør målingen før filen har rullet to gange. Mindstekrav: ≥30 runs der har passeret
første signalpunkt, ellers er forskellen støj. `affect_modulation` kan sænke
`max_rounds` til 12/18, så signalpunktet skal beregnes pr. run, ikke som fast tal.
