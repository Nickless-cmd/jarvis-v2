# Fit-pass: Commit, Review, Proactivity (2026-06-22)

Kortlægning af de tre kognitive clusters til central_catalog. Verificeret at alle
nerve-filer findes. Detaljer pr. cluster nedenfor; catalog-entries i `central_catalog.py`.

## Commit (beslutnings-disciplin)
Eneste request-path-gate = `decision_gate` (`core/services/decision_gate.py:27-92`,
kaldt fra `visible_runs.py:4823` pre-exec) → **merge**. Resten instrument/leave:
`decision_create` (behavioral_decisions), `decision_signals` (inline turn-eval),
`decision_review` (persistens), `credit_assignment` (Lag-1 outcome).
- **Bemærk:** adherence-review-daemon er DEAKTIVERET siden 2026-06-11 (LLM-self-bias);
  skal erstattes af external-truth review (git-log + tool-history).
- **Stille fejl:** decision_gate fail-open uden signal (`decision_gate.py:50`,
  `visible_runs.py:4831`); credit_assignment event-publish `except:pass`
  (`db_credit_assignment.py:154,287`); decision_signals trigger-fejl kun warning.

## Review (selv-review + trackers)
INGEN request-path-gates — alt kører post-done/async → **alle leave**.
`self_review_unified` (daemon, 24t heartbeat-kadence) + kaskaden
signal→record→run→outcome→cadence (5 trackere i `_track_runtime_candidates`).
- **Trace-hul (stort):** alle review-trackere er `except Exception: return` UDEN
  logging (`visible_runs.py:4280-4313`). Kaskaden er usynlig hvis et led fejler.
  Også skjulte `except:pass`: self_review_unified LLM-enrichment (l.229),
  incident-trigger i self_review_run (l.247), dream_bias i outcome (l.94).
- world_model Phase-2 (cheap-lane LLM-extract, rate-limited 15/dag) = instrument-kandidat.

## Proactivity (uopfordret initiativ)
Request-path-gates = `proactive_question_gate` + `proactive_loop_lifecycle`
(begge `_track_runtime_candidates`) → **merge**. Tærskel-bærende = **instrument**:
`pressure_threshold`, `longing_signal`, `r2_5_blocking_gate`, `action_router`.
Filtre/køer = **leave**: `signal_noise`, `initiative_queue`.

### Hardcodede tærskler = config-kandidater (Bjørn vil justere uden deploy)
| Tærskel | Sted | Værdi |
|---|---|---|
| R2.5 heed_rate-blok | `r2_5_blocking_gate.py:53` | 0.4 |
| R2.5 unverified pr. tier | `r2_5_blocking_gate.py:47-51` | deep 3 / reasoning 5 / fast 8 |
| pressure direction-tærskler | `pressure_threshold_gate.py:34-50` | explore 0.45 / fix 0.35 / reach_out 0.55 |
| proaktiv dag-cap + cooldown | `action_router.py:40-43` | 3/dag, 2t |
| initiative-kø | `initiative_queue.py:21-25` | max 8, expire 90 min |
| proactive-gate stale/force-close | `*_tracking.py` | 7 / 21 dage |

- **Stille fejl:** queue-full uden signal, r2_5 `_heed_rate_24h()`→None uden fallback,
  "why-gate-didn't-form" usporbar, action-selection utraceret.

## Næste skridt (når Bjørn vil)
1. Disse 19 nerver er nu i central_catalog (5 clusters kortlagt: loop/truth/commit/review/proactivity).
2. Mangler fit-pass: **Tools** (note findes), **Memory**, **Privacy🔒**, **Auth🔒** (sikkerhed sidst, fail-closed).
3. Migrations-rækkefølge (merge → instrument → trace) pr. cluster i egne planer.
4. Proactivity's hardcodede tærskler = oplagt config-batch (samme mønster som tool-render-lofterne).
