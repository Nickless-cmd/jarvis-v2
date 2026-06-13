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
