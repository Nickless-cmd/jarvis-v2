# Fit-pass-rapport — Intelligent Central (§13.2)

> Genereret fra `core.services.central_catalog.CATALOG` (2026-06-21). Maskinlæsbar
> kilde er kataloget; denne rapport er den menneskelæsbare projektion. Verificér:
> `python -c "from core.services import central_catalog as c; print(len(c.CATALOG), c.clusters(), c.validate())"`
> → `9 ['loop', 'truth'] []`

**Fit-betydning:**
- `merge` — homogen Verdict-gate; logik kan smelte sammen i den unified cluster-gate. Gammel kode fjernes efter paritet.
- `instrument` — beslutningen flyttes til at kalde Centralen på stedet; gammel standalone-duplikat fjernes.
- `leave` — IKKE en request-path-gate (daemon/filter/tool/persistens). Bliver hvor den er; registreres kun til observation.

## Kortlagte nerver

| Nerve | Cluster | Klasse | Mekanisme | Fit | Lokation | Begrundelse |
|---|---|---|---|---|---|---|
| run_closure | loop | kognitiv | daemon | **leave** | `core/services/run_closure_gate.py` | Eventbus-listener (post-run), publicerer events; ingen request-path-beslutning |
| tool_budget | loop | kognitiv | inline | **instrument** | `core/services/visible_runs.py:1754-2351` | Ægte loop-beslutning (hard-brake) men yield'er SSE + muterer loop-state → kan ikke køre i kernens thread-pool; instrumentér på stedet |
| capability_cap | loop | kognitiv | filter | **leave** | `core/tools/tool_scoping.py` | Statisk pre-request tool-filter, ikke per-runde-gate |
| good_enough | loop | kognitiv | tool | **leave** | `core/services/good_enough_gate.py` | Frivilligt tool modellen selv kalder; returnerer score, ingen håndhævelse |
| checkpoints | loop | kognitiv | persistence | **leave** | `core/services/agentic_checkpoints.py` | Persistens/genoptag-lag, ikke en beslutning |
| presentation_invariant | loop | kognitiv | validation | **instrument** | `core/services/visible_runs.py:5758-5806` | Post-output-validering der raiser; ren beslutning men sidder på stedet → instrumentér |
| claim_scanner | truth | kognitiv | verdict | **merge** | `core/services/claim_scanner.py` | Homogen post-output Verdict-gate (adapter findes) |
| fact_gate | truth | kognitiv | verdict | **merge** | `core/services/fact_gate.py` | Homogen post-output Verdict-gate (adapter findes) |
| diagnosis | truth | kognitiv | verdict | **merge** | `core/services/diagnosis_gate.py` | Homogen post-output Verdict-gate (adapter findes) |

## Opsummering pr. cluster

| Cluster | merge | instrument | leave | Note |
|---|---|---|---|---|
| **loop** | 0 | 2 | 4 | Bekræfter at "LoopGate" IKKE er en sammensmeltning: kun 2 instrumenteres, 4 er ikke-gates der bliver. Ingen merge. |
| **truth** | 3 | 0 | 0 | Ægte homogen klynge — kan smelte sammen i én TruthGate (adaptere findes allerede). |

## Mangler at blive fit-passet

Kun **loop** + **truth** er kortlagt. Følgende clusters fit-passes i deres egne
cluster-planer (B–H), hvor hver nerve mappes til cluster/klasse/mekanisme/fit og
tilføjes `CATALOG`:

- **commit** (decision + decision_adherence + decision_review)
- **privacy** (cross_user_share + share_guard_store) — sikkerhed, fail-closed
- **review** (self_review_unified + trackers) — async, ud af hot-path
- **proactivity** (signal_noise + pressure_threshold + proactive_question + r2_5)
- **auth** (member-block + owner-allow + override + sudo + identity + abuse) — sikkerhed, SIDST

## Konsekvens for "antal gates"

Fit-passet bekræfter Bjørns intuition: det reelle tal er **færre ægte gates end de
spredte nerver**. Af loop-klyngens 6 nerver er kun 2 request-path-beslutninger; resten
er en daemon, et filter, et tool og et persistens-lag. Centralen samler dem alle som
ÉN observerbar rygrad (cluster-taksonomi), men kun de ægte beslutninger instrumenteres/
merges — resten observeres. Det er sådan vi ender med få intelligente gates + én central,
ikke 50 spredte.
