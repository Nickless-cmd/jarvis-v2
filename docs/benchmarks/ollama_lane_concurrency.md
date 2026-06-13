# Ollama lane-concurrency — etappe-målinger

Mål: udnytte abon.'s 3-samtidig-kapacitet til at dæmpe Ollama-latency.
Metode: `scripts/bench_ollama_concurrency.py` (raw mod Ollama, infra-loft, gratis).
Kør på containeren (10.0.0.39) hvor Ollama er local. Disciplin: baseline →
etappe → mål → diff → revert hvis ingen gevinst.

Etappe-rækkefølge (sikrest først):
1. Parallelisér interne lanes (rører ikke beskyttet kerne)
2. Council/swarm parallelt (eksperimentel)
3. Race på synlig lane (beskyttet kerne — kræver eksplicit godkendelse)

Loft bekræftet: op til **3 parallelle kald ~gratis** (k3 ≈ k1), k4 begynder at kø'e.

## Baseline — 2026-06-13 (GLM-5.1:cloud)

```json
{
  "chat":            { "ttft_median_s": 0.549, "total_median_s": 4.683 },
  "sequential_loop": { "rounds": 3, "wall_median_s": 10.11 },
  "concurrency":     { "k1": 2.847, "k2": 2.305, "k3": 3.082, "k4": 4.039 }
}
```

Observation: sekventiel 3-round loop (10,1s) er den største smerte. 3-concurrency
hjælper ikke sekventiel afhængighed direkte — kun parallelt arbejde. Stage 1 sigter
derfor mod at fjerne kunstig serialisering MELLEM lanes (visible vs daemon/cheap).

## Etappe 1-2 diagnose — 2026-06-13 (FØR implementering)

Diagnose før ændring (disciplin: implementér ikke no-ops). Fund:

- **Ingen lock/semaphore** i visible-lanen (visible_model/runs/followup) eller
  globalt i core/. Ingen kunstig serialisering mellem lanes.
- **Heartbeat-tick = ægte afhængigheds-kæde**: `sense → reflect → act → self-eval`
  (`heartbeat_phases.tick_with_phases`). Kan ikke paralleliseres — act kræver
  reflection kræver signals. Ligesom den agentiske tool-loop.
- **Swarm er ALLEREDE parallel**: `agent_runtime._run_collective_round` linje 1323-1338
  bruger `ThreadPoolExecutor(max_workers=MAX_SWARM_WORKERS)` for mode=swarm.
- **Council er BEVIDST sekventiel** ("preserves deliberation order" — medlemmer
  reagerer på hinanden). Legitim design, ikke en bug.
- `MAX_SWARM_WORKERS = 8` > Ollama-loft 3 → workers 4-8 kø'er hos Ollama. Ingen
  fejl, men "8-wide" er reelt 3-wide. At sænke = samme throughput, ingen gevinst.

**Konklusion:** Systemet er allerede concurrency-optimeret hvor det hjælper (swarm),
og bevidst sekventielt hvor rækkefølge betyder noget (council, heartbeat-kæde).
Etappe 1-2 har INGEN headroom at høste — vi stopper ved diagnosen frem for at bygge
no-ops. Den resterende latency (sekventielle kæder, 10s) er iboende afhængigheds-
latency, ikke noget mere parallelisme kan fjerne.

Eneste tilbageværende lever for den sekventielle tool-loop er **spekulativ
tool-eksekvering** (gæt næste skridt parallelt) — komplekst og risikabelt, ikke
scoped nu. Etappe 3 (synlig-lane-race) rører beskyttet kerne OG hjælper ikke den
faktiske smerte (chat er allerede hurtig, TTFT 0,55s; racet fikser ikke 10s-loopet).
