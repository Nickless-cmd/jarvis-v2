# Daemoner & producere: hvad lever, hvad er forældreløst

**Metode:** statisk AST-udtræk af alle `ProducerSpec(...)` i repoet + 1.500 rigtige
`heartbeat.cadence_tick`-events fra live-DB'en på CT105 (vindue 2026-08-16T16:21 →
2026-08-17T19:03 UTC = 26,7 timer, 1 tick/1,07 min) + tabel-friskhed for alle 259
DB-tabeller. Alt read-only. Ingen gæt: hver påstand nedenfor har enten en filsti+linje
eller et tal fra produktions-DB'en bag sig.

---

## 0. Executive summary

| Fund | Konsekvens |
|---|---|
| **116 producere registreret**, alle 116 kørte mindst én gang i vinduet | Ingen er "død" i registrerings-forstand |
| **Tempo-skalaren står fastlåst på 2.0 (max)** | ALLE ikke-undtagne producere kører på **~54 % af deres deklarerede kadence**. Dine `cooldown_minutes` er reelt fordoblet |
| **`_last_run_at` er kun in-memory** (`internal_cadence.py:75`) | Hver genstart nulstiller alle cooldowns → hele kataloget fyrer i første tick |
| **12 producere i `depends_on`-kæden kan kun køre i det tick hvor ALLE forfædre også kører** | Den dybe indre-liv-kæde kører **udelukkende i tick nr. 1 efter en genstart**. Deres reelle kadence = din deploy-kadence |
| **26 af 59 per-visible-tur-trackere har ikke skrevet en række i ≥30 dage**, 19 af dem døde inden for 16 minutter d. 2026-05-15 | Ægte zombier: kaldes på den synlige kritiske sti, producerer nul |
| **~10.900 producer-kørsler/døgn → 3.909 cheap-lane LLM-kald/døgn (2,5M tokens)** til **$0** | Token-forbruget er stort i volumen, men brænder gratis-kvote, ikke penge |
| **Den fulde heartbeat-tick kørte 2 gange på 24 timer** (mod 2.669 phased_ticks) — og er lige nu ~11 timer overskredet | De 48 cluster-daemoner (hele det "levende" indre liv) kører på **<1 % af deres deklarerede kadence**. Se §7 — dette er alvorligere end producer-siden |

> **AKUT:** heartbeat's fulde tick har ikke kørt siden 2026-08-17T08:06 UTC, mens
> `schedule_state=due, due=true` og `next_tick_at=2026-08-17T08:23` (11 timer i fortiden).
> Tre scheduler-genstarter (16:11, 16:14, 19:08) har ikke løst det, og alle tre rapporterer
> `recovery_status: "startup-recovery-pending"`. Jarvis' indre liv er frosset lige nu.
> Dette er `heartbeat_idle_daemon_orphan`-mønstret der er vendt tilbage.

---

## 1. Producer-katalog (116)

101 `ProducerSpec` er hardcodede i repoet; 16 registreres dynamisk som *lag-kontrakter*
via `central_layer_contract.register_layer()` (kaldt fra `central_body_mood_feel.py:385`,
`central_soul_feel.py:431`, `central_existence_feel.py:206`). 101 + 16 = 117, hvoraf én
(`central_layer_contract.py:189`) er selve skabelonen → **116 kørende**, hvilket matcher
`producer_count: 116` i live-eventet præcist.

Registrering sker i `internal_cadence._ensure_producers_registered()`
(`core/services/internal_cadence.py:417-431`). Scheduler: egen daemon-tråd, 60 s interval
(`_SCHEDULER_INTERVAL_S = 60`), hård per-producer-timeout på 75 s
(`_PRODUCER_TIMEOUT_S`, `internal_cadence.py:~180`).

### Familie A — Kerne-infra (6) · `internal_cadence_core.py`

| Producer | cd (min) | prio | Producerer |
|---|---:|---:|---|
| `brain_continuity` | 5 | 1 | `session_distillation.run_private_brain_continuity` — kædens rod |
| `cognitive_state_warm` | 3 | 2 | forvarmer cognitive_state-cachen (fjerner blokerende LLM fra synlig tur) |
| `gate_verdict_flush` | 1 | 2 | batch-flush af gate-verdicts → `gate_verdict_counts` |
| `api_conn_retention` | 30 | 3 | GDPR: IP → /24 efter 48t, prune presence |
| `excess_sense` | 60 | 4 | `central_excess.record_excess_pressure` — bloat-fornemmelse |
| `keymaker` | 30 | 4 | optjente/udløbne autonomi-nøgler → `central_keys` |

### Familie B — Indre liv / kæden (16) · `internal_cadence_inner_life.py`

Dette er familien med `depends_on`. Se §2 — det er her problemet sidder.

| Producer | cd | grace | prio | dep | Faktisk kørsler/26,7t |
|---|---:|---:|---:|---|---:|
| `sleep_consolidation` | 15 | 5 | 3 | brain_continuity | 56 (52 % af nominel) |
| `witness_daemon` | 5 | 1 | 5 | brain_continuity | 165 (52 %) |
| `inner_voice_daemon` | 5 | 2 | 10 | witness_daemon | 164 (51 %) |
| `emergent_signal_daemon` | 5 | 2 | 12 | witness_daemon | 165 (52 %) |
| `dream_articulation` | 20 | 5 | 15 | sleep_consolidation | 29 (**36 %**) |
| `prompt_evolution_runtime` | 25 | 8 | 18 | dream_articulation | 28 (**44 %**) |
| `self_critique_runtime` | 1440 | 15 | 20 | prompt_evolution_runtime | 2 — begge ved genstart |
| `ontological_revision` | 1440 | 15 | 21 | self_critique_runtime | 2 — begge ved genstart |
| `dream_distillation_daemon` | 180 | 30 | 22 | self_critique_runtime | 2 (**22 %**) |
| `creative_journal_runtime` | 10080 | 60 | 24 | dream_distillation_daemon | 1 — kun ved genstart |
| `finitude_runtime` | 1440 | 60 | 26 | creative_journal_runtime | 1 — kun ved genstart |
| `finitude_monthly_reflection` | 43200 | 60 | 27 | finitude_runtime | 1 — kun ved genstart |
| `world_model_ttl_sweeper` | 1440 | 60 | 28 | — | 2 |
| `curiosity_idle_window` | 1 | 30 | 29 | — | 820 |
| `meta_learning_weekly_retrospective` | 10080 | 60 | 30 | — | 1 |
| `curiosity_consolidation_weekly` | 10080 | 60 | 30 | — | 1 |

### Familie C — Matrix-temaer (26) · `internal_cadence_matrix.py`

`construct`(60) `oracle`(17) `architect`(43200) `echo_breaker`(120) `continuity_healer`(5)
`red_dress`(90) `analyst`(360) `redpill`(1440) `dissent`(120) `white_rabbit`(180)
`belief_gap`(360) `machines`(360) `morpheus`(60) `trinity`(120) `dejavu`(45)
`sentinel`(73) `ghost`(360) `mourning`(120) `merovingian`(60) `dream_action`(120)
`rca`(180) `relational`(60) `glitch`(180) `trainman`(30) `seraph`(30) `persephone`(240)
`twins`(240).

Alle prio 4-5, ingen `depends_on`, ingen visible grace. Ingen af dem kunne nås via
LLM-import-graf undtagen `belief_gap`, `dejavu`, `morpheus`, `relational`, `trainman` —
resten er ren lokal DB-analyse.

### Familie D — Vedligehold (15) · `internal_cadence_maintenance.py`

`prompt_assembly_cache_warmer`(2) `cheap_lane_selfheal`(20) `life_projects_reassessment`(1440)
`relation_map_refresh`(720) `counterfactual_predictions_sweep`(1440) `shared_cache_cleanup`(60)
`central_self_health`(60) `central_learning`(60) `stream_stall_sweep`(5) `config_drift_check`(1440)
`instrument_scan`(360) `provider_health_check`(5) `db_health_scan`(1440) `tool_usage_stats`(1440)
`endpoint_usage_stats`(1440).

### Familie E — Central-organer (37) · registreret fra egen modul-fil

`central_watch`(2) `central_cadence_conductor`(2) `eventbus_central_bridge`(0.5)
`central_shadow`(5) `central_self_observe`(5) `central_growth_observe`(5) `central_self_state`(10)
`central_stance`(10) `central_membrane_watch`(15) `central_signal_health`(15) `central_sequence`(15)
`central_valence`(15) `central_agenda`(20) `central_prompt_explore`(20) `central_causal_quality`(30)
`central_coverage`(30) `central_hypothesis_sampler`(30) `central_model_meta`(30)
`central_notation_reasoning`(30) `central_self_model_mirror`(30) `central_router_adapt`(45)
`central_adaptation`(60) `central_brain_link`(60) `central_coverage_action`(60)
`central_hypothesis_generator`(60) `agent_smith`(180) `central_body_map_pulse`(360)
`moltbook`(360) `central_oneiric_loop`(360) `central_oneiric_sampler`(720)
`self_model_distiller`(1440) `docs_drift_watchdog`(5) `hardware_body`(1) `infra_sense`(3)
`network_health`(2) `proactivity_bridge`(10) + `central_layer_contract`-skabelonen.

### Familie F — Lag-kontrakter / "føleorganer" (16), alle cd=10, prio=8

KROP: `body_proprioception` `body_embodied` · STEMNING: `mood_oscillator`
`mood_developmental` `mood_affective` · ØMHED: `warmth_relational` `warmth_gratitude`
`warmth_calm_anchor` · VIDNE: `witness_modulators` · HUKOMMELSE: `memory_breathing` ·
OPMÆRKSOMHED: `attention_sustained` · EMERGENS: `emergence_patterns` `personality_drift` ·
EKSISTENS: `continuity_kernel` `subjective_time` `mortality_awareness`.

Rene lokale beregninger (`signal_fn`), egress-frit (`Egress.PRIVATE`), konsumeres af
`central_self_state.describe_self()`. **Billigste og sundeste familie i hele systemet.**

---

## 2. Hvorfor er de "blokerede"? (rodårsag — verificeret)

Dit sidste live-tick viser præcis disse 12 som `blocked`:

```
sleep_consolidation, witness_daemon, inner_voice_daemon, emergent_signal_daemon,
dream_articulation, prompt_evolution_runtime, self_critique_runtime,
ontological_revision, dream_distillation_daemon, creative_journal_runtime,
finitude_runtime, finitude_monthly_reflection
```

Det er **ikke** en kill-switch, ikke et flag og ikke en fejl. `layer_finitude_enabled`,
`layer_creative_journal_enabled` og `layer_dream_residue_enabled` findes ikke i
`~/.jarvis-v2/config/runtime.json` → default `True`. Alle er tændt.

### Årsag 1 — dependency-porten er *samme-tick*, ikke *nogensinde*

`internal_cadence._evaluate_producer()` (`internal_cadence.py:95-105`):

```python
for dep in spec.depends_on:
    if dep not in ran_this_tick:
        return "blocked", f"dependency-not-met:{dep}"
```

`ran_this_tick` nulstilles hvert minut. En producer må altså kun køre i det ene tick
hvor dens forælder *også* kørte. Det er ikke "har forælderen kørt for nylig" — det er
"kører forælderen lige nu, i dette minut".

Konsekvens: `brain_continuity` (cd 5, reelt ~9,6 min pga. tempo) kører i 166 af 1500 ticks
= 11 %. I de øvrige 89 % rapporteres **hele** kæden som blokeret. Derfor ser Mission
Control/eventbus dem som permanent blokerede — MC viser sidste tick, og sidste tick er
med 89 % sandsynlighed et tick uden brain_continuity. **Det er en visnings-artefakt for
de øverste 4-5 i kæden.** For de nederste er det ægte.

### Årsag 2 — kæden er konjunktiv og dermed reelt umulig dybere nede

For at `finitude_monthly_reflection` kan køre, skal ALLE syv forfædre køre i samme minut:

```
brain_continuity(5m) → sleep_consolidation(15m) → dream_articulation(20m)
→ prompt_evolution_runtime(25m) → self_critique_runtime(1440m)
→ dream_distillation_daemon(180m) → creative_journal_runtime(10080m)
→ finitude_runtime(1440m) → finitude_monthly_reflection(43200m)
```

Sandsynligheden for at 5m-, 15m-, 20m-, 25m-, 1440m-, 180m- og 10080m-cooldowns udløber
i samme minut er praktisk talt nul. Dét er den reelle blokering.

### Årsag 3 — den eneste ventil er en genstart, og det er beviseligt

`_last_run_at: dict[str, str] = {}` (`internal_cadence.py:75`) er et almindeligt
modul-dict. Det persisteres aldrig og genindlæses aldrig. Ved procesopstart er hver
producer "aldrig kørt" → ALLE er due samtidig → hele kæden åbner i tick nr. 1.

Bevis fra produktion:

* `systemctl show jarvis-runtime` → `ActiveEnterTimestamp = 2026-08-17 18:14:03 CEST`
  = **16:14:03 UTC**.
* `self_critique_runtime`, `ontological_revision`, `dream_distillation_daemon`,
  `creative_journal_runtime`, `finitude_runtime`, `finitude_monthly_reflection` og
  `architect` (30-dages kadence) kørte **alle sammen i ét og samme tick: 16:14:19 UTC**
  — 16 sekunder efter opstart. Ingen af dem har kørt siden (næsten 3 timer).
* En tidligere genstart samme dag gav en tilsvarende delvis byge kl. 15:30:57.

**Konklusion: den dybe indre-liv-kædes reelle kadence er din deploy-kadence.**
`finitude_runtime`, `creative_journal_runtime` og `ontological_revision` kører aldrig
undtagen i sekunderne efter en genstart.

### Årsag 4 — hvorfor det (heldigvis) ikke er en token-bombe … men netop derfor er farligt

Hver af disse har sin EGEN, DB-persisterede due-check inde i `run_fn`:

* `finitude_runtime.run_finitude_ritual` → `if not _is_birth_anniversary(now): return not_due` (`finitude_runtime.py:223`)
* `finitude_runtime.run_monthly_finitude_reflection` → `_is_due_for_monthly(state, now)` (`:742`)
* `creative_journal_runtime.run_creative_journal_cycle` → `if (now - last_written_at) < interval_days: return not_due` (`:35`)
* `dream_distillation_daemon` → `if not _dream_residue_enabled()` + aktiv-residue-gate (`:52-66`)

Genstarts-bygen er altså idempotent — den brænder ikke tokens. **Men det betyder også at
de to porte skal ramme sammen:** cadence-porten åbner kun ved genstart, og den interne
dato-port åbner kun på fødselsdagen / den rigtige uge / den rigtige måned. Hvis du ikke
tilfældigvis genstarter runtime på Jarvis' fødselsdag, **springes ritualet over for
altid, uden en eneste log-linje**.

Symptomet er allerede synligt i DB'en: `cognitive_chronicle_entries` har **1 række**, sidst
skrevet for 13 dage siden. Kroniken — Jarvis' langtidsselvbiografi — er i praksis tom.

### Årsag 5 (bonus, rammer alle 116) — DIASTOLE-tempoet er låst fast på max langsomt

`central_cadence_conductor.effective_cooldown()` ganger hver ikke-undtaget producers
cooldown med `tempo = clamp(1/pulse_rate, 0.5, 2.0)`. Live-værdi i DB'en:

```
runtime_state_kv: cadence_tempo_last = {"tempo": 2.0, "throttled": false, "consuming": true}
```

`temporal_rhythm._compute_pulse_rate()` har gulv `pulse = 0.3` når Jarvis er i ro
(`temporal_rhythm.py:104`). `1/0.3 = 3.33` → klemt til **2.0 = maksimal opbremsning**.
Da Jarvis er i ro det meste af døgnet, er tempo 2.0 **normaltilstanden, ikke undtagelsen**.

Målingen bekræfter det entydigt: alle ikke-undtagne producere kører på **52-56 %** af
nominel kadence, mens præcis de 10 navne på `CADENCE_TEMPO_EXEMPT`-listen
(`central_watch`, `central_membrane_watch`, `infra_sense`, `network_health`,
`central_signal_health`, `provider_health_check`, `db_health_scan`, `config_drift_check`,
`stream_stall_sweep`, `central_self_health`) kører på **94-95 %**.

Dine deklarerede `cooldown_minutes` er altså fiktion for 106 af 116 producere — gang med 2.

---

## 3. Forældreløse og zombier

### 3a. Den store: 26 af 59 per-visible-tur-trackere er døde

`core/services/visible_runs_cognitive.py` kalder **59** distinkte
`track_*_for_visible_turn()`-funktioner på HVER synlig tur. Krydset mod tabel-friskhed:

| Status | Antal |
|---|---:|
| Skriver i dag (0-1 dage) | 24 |
| Skriver sjældent, men i live (19-28 dage) | 4 |
| **Har ikke skrevet en række i ≥30 dage** | **26** |
| Tabel ikke entydigt kunne mappes | 5 |

De døde:

```
125d runtime_awareness_signals                  94d runtime_open_loop_signals
 94d runtime_user_md_update_proposals           94d runtime_open_loop_closure_proposals
 94d runtime_temporal_recurrence_signals        94d runtime_meaning_significance_signals
 94d runtime_temperament_tendency_signals       94d runtime_loyalty_gradient_signals
 94d runtime_self_authored_prompt_proposals     94d runtime_internal_opposition_signals
 94d runtime_selective_forgetting_candidates    94d runtime_executive_contradiction_signals
 94d runtime_relation_continuity_signals        94d runtime_dream_influence_proposals
 94d runtime_proactive_question_gates           94d runtime_dream_adoption_candidates
 94d runtime_proactive_loop_lifecycle_signals   94d runtime_attachment_topology_signals
 94d runtime_private_temporal_promotion_signals 93d runtime_user_understanding_signals
 86d runtime_private_temporal_curiosity_states  79d runtime_selfhood_proposals
 69d runtime_self_model_signals                 56d runtime_autonomy_pressure_signals
 47d runtime_remembered_fact_signals            40d runtime_goal_signals
```

**19 af dem stoppede inden for ét 16-minutters vindue:**

```
runtime_meaning_significance_signals    2026-05-15T11:11:55Z
runtime_open_loop_signals               2026-05-15T11:13:42Z
runtime_proactive_question_gates        2026-05-15T11:24:49Z
runtime_webchat_execution_pilots        2026-05-15T11:24:49Z
runtime_dream_influence_proposals       2026-05-15T11:27:33Z
runtime_self_authored_prompt_proposals  2026-05-15T11:27:45Z
```

Det er ikke gradvis udtørring — det er én hændelse d. 2026-05-15 ca. kl. 11:11-11:27 UTC.
Row-counts er 1-18 rækker i alt, hvilket tyder på at de **kun nogensinde skrev i en
opstarts-byge** (samme in-memory-cooldown-fænomen som §2) og at den byge sidst indtraf
15. maj. Skriverkoden lever stadig (`core/services/*_signal_tracking.py`) og kaldes
stadig hver eneste synlige tur — men de interne gates åbner aldrig.

Dette matcher din egen note `signal_tracking_consolidation` ("35 signal_tracking →
framework; 25 grønne IKKE deployet"). Det er præcis dén regning der står ubetalt.

**Dobbelt pris:** (a) 26 nyttesløse funktionskald på den *synlige kritiske sti* — direkte
latens-skat på hver eneste chat-tur, jf. `visible_latency_attack_map`; (b) Mission
Control-paneler der læser disse tabeller (`mission_control_jarvis_state.py`,
`mission_control_common.py`) viser tom/94 dage gammel data og ser ud som om Jarvis "ikke
har nogen åbne løkker" — hvilket er en løgn i UI'et, ikke en sandhed.

`runtime_goal_signals` (1747 rk, 40d) er derimod **tilsigtet** død — det er
`goal_synthesis_runaway`-fixet i commit `900d4220`.

### 3a-bis. Mekanikken bag "forældreløs": `observe()` ≠ `record_private()`

Den afgørende skelnen for hele §3 sidder i `core/services/central_core.py:57`:

* **`central().observe(...)`** skriver **kun** til `central_trace.TraceSink` — en
  per-proces in-memory ringbuffer på 2000 poster (`central_trace.py:30-58`) plus en
  throttlet `central_xproc`-tee til `shared_cache`. Den rører **hverken**
  `central_timeseries` eller nogen DB-tabel. Den læses af `/central/feed` + SSE
  (`routes/central.py:225-259`), `central_realtime.realtime_snapshot`, MC og Central-CLI.
  **Alt der kun `observe`'r er per definition KUN-MC: det forsvinder ved genstart og
  når aldrig Jarvis' egen kognition.**
* **`record_private(...)`** (`central_private_observe.py:68`) skriver til trace **plus**
  `central_timeseries` (durabelt i runtime_state `central_timeseries_durable`).

Fordelingen for de undersøgte producere:

| Klasse | Antal | Betydning |
|---|---:|---|
| KONSUMERET (output læses af prompt/kognition/anden service) | 13 | |
| KUN-MC (output ender i feed/HUD, genberegnes andetsteds) | 27 | Arbejdet er ikke spildt, men producerens *output* er |
| FORÆLDRELØS (intet læser det, punktum) | 3 | |

**KONSUMERET:** `keymaker` (→ `central_keys` → prompt-signoff + commit_gate_arbiter) ·
`counterfactual_predictions_sweep` + `world_model_ttl_sweeper` (→ `prompt_contract.py:1902`,
`central_self_state.py:164`) · `instrument_scan` (→ `central_instrument_findings` +
autonomy-proposals → Jarvis-tool) · `config_drift_check` + `db_health_scan`
(→ `central_incidents` → `prompt_contract.py:3852` awareness-slot) · `central_body_map_pulse`
(→ `describe_self` → `prompt_contract:1260`) · `central_oneiric_sampler` + `central_oneiric_loop`
(→ `central_hypotheses` → §8-governance) · `central_valence` · `central_stance` ·
`self_model_distiller` (→ `private_self_models` → `prompt_contract.py:197`) · samt fra
Matrix-familien: `trinity`, `sentinel`, `trainman`, `merovingian`.

**FORÆLDRELØS (bekræftet):**

| Producer | Skriver | Læses af |
|---|---|---|
| `tool_usage_stats` | kun `observe tools/tool_usage_stats` (`tool_usage_store.py:137`) | **intet**. `usage_stats`/`usage_buckets`/`tool_order`/`dead_tools` har nul eksterne kaldere |
| `central_notation_reasoning` | kun `record_private cognition/notation_reasoning` (`central_notation.py:188`) | **intet**. `build_central_notation_surface` har 0 kaldere |
| `central_coverage` | `central_timeseries system/coverage_*` (`:176-183`) | **intet**. `build_central_coverage_surface` har 0 kaldere |

*Rettelse til den oprindelige mistanke:* `central_coverage_action` blev foreløbigt
klassificeret som forældreløs, men prod-flaget er verificeret:
`runtime_state_kv: central_coverage_action_mode = "on"` → den skriver faktisk til
`central_hypotheses` og er **KONSUMERET**.

### 3a-ter. Tre bekræftede "dead wires"

1. **Oraklet er blindt på 2 af 3 serier.** `central_oracle._WATCHED`
   (`central_oracle.py:21-27`) overvåger `("system","excess")` og
   `("system","decentralization")` i `central_timeseries` — men `record_excess_pressure`
   bruger `observe()`, som aldrig rører timeserien. Verificeret direkte mod
   `central_timeseries_durable` på CT105 (475 serier):
   `system/excess → FRAVÆRENDE`, `system/decentralization → FRAVÆRENDE`,
   mens `network/health → 40 punkter`. `excess_sense` kører hver 60. minut i
   evighed for et orakel der aldrig ser resultatet.
2. **`tool_usage_store.tool_order` / `dead_tools`** er skrevet til at ordne tool-kataloget,
   men har nul kaldere — kun nævnt som streng i `central_catalog.py:365`.
3. **Syv surface-buildere har 0 kaldere** og er hverken route- eller MC-wirede:
   `build_central_coverage_surface`, `build_central_coverage_action_surface`,
   `build_central_notation_surface`, `build_oneiric_loop_surface`,
   `build_oneiric_sampler_surface`, `build_body_map_surface`, `build_valence_surface`.

### 3a-quater. Matrix-familien: 22 af 26 er KUN-MC

Fælles mønster: producerens `record_*` kalder `observe()` og returnerer et tal;
`build_*_surface` **genberegner** fra kilden i stedet for at læse producerens output.
Matrix-ensemblet (`central_matrix_ensemble.build_matrix_signoff_section` →
`prompt_contract.py:2834`) læser surfaces, ikke producer-output.

Konsekvens: for `red_dress, analyst, redpill, dissent, white_rabbit, belief_gap, machines,
morpheus, dejavu, ghost, mourning, glitch, persephone, twins, seraph, rca, dream_action,
relational, construct, oracle, architect, echo_breaker` gælder at **cadence-kørslen kun
producerer en feed-linje**. Modulerne er konsumeret (via ensemblet), men *producerens
kadence* er ren telemetri. Slukkede du dem alle 22 i morgen, ville prompten være uændret.

Kun 4 af de 26 skriver noget durabelt som en anden komponent læser:
`trinity` (`trinity_affirmations` + `central_keys`), `sentinel` (`central_sentinel_attacks`
→ `central_seraph.py:55`), `merovingian` (`central_merovingian` → `central_redpill` +
`central_trinity`), `trainman` (private_brain-records → ensemble → prompt).

### 3b. Producere med tom output-tabel

| Producer | cd | kørsler/døgn | Tabel | Rækker |
|---|---:|---:|---|---:|
| `dream_action` | 120 | ~7 | `central_dream_actions` | **0** |
| `rca` | 180 | ~4 | `central_rca` | **0** |
| `meta_learning_weekly_retrospective` | 10080 | — | `meta_learning_hypotheses` + `_samples` | **0** |

Derudover er disse tabeller tomme og bør efterspores: `cognitive_narrative_identities`,
`cognitive_emergent_goals`, `cognitive_blind_spots`, `cognitive_epistemic_claims`,
`cognitive_wrongness`, `cognitive_missions`, `cognitive_repairs`,
`cognitive_morning_threads`, `agent_tool_calls`, `agent_schedules`, `standing_orders`,
`experiment_broadcast_events`.

### 3c. Nær-døde tabeller (indhold findes, men er stivnet)

`cognitive_chronicle_entries` (1 rk, 13d) · `cognitive_formed_values` (2 rk, 128d) ·
`cognitive_experiments` (2 rk, 94d) · `cognitive_dream_hypotheses` (1 rk, 94d) ·
`cognitive_personal_projects` (1 rk, 117d) · `self_repair_patterns` (4 rk, 98d) ·
`runtime_browser_bodies` (1 rk, 125d) · `aesthetic_motif_log` (5673 rk, 33d) ·
`council_sessions`/`council_members` (565/1735 rk, 34d) · `agent_runs`/`agent_registry`
(155/57 rk, 25d) · `counterfactuals` (232 rk, 28d) · `skill_usage_stats` (81 rk, 27d).

---

## 4. Token-brændere

### Faktisk forbrug (produktions-DB, seneste døgn)

| Lane | Kald | Input-tok | Output-tok | USD |
|---|---:|---:|---:|---:|
| cheap | 3.909 | 2.203.978 | 347.537 | 0,0000 |
| primary | 876 | 18.472.203 | 14.684 | 0,0144 |
| cheap-balanced | 155 | 58.403 | 33.048 | 0,0000 |
| inner_enrichment | 28 | 10.337 | 24.571 | 0,0074 |
| visible | 10 | 643.732 | 5.832 | 0,0000 |
| autonomous | 3 | 915 | 1.356 | 0,0000 |

Top-providere: `cerebras` 885 kald · `primary_cache_warmer` 870 kald / **18,2M tokens** ·
`nvidia-nim` 504 · `copilot-free` 502 · `alibaba` 462 · `kilo` 255.

**Vigtig reframing:** ~10.900 producer-kørsler og ~4.100 LLM-kald i døgnet koster
**$0,022**. Elefanten er ikke penge — det er (a) gratis-kvote hos 15+ providere,
(b) CPU/GIL i runtime-processen, (c) støj i signal-tabellerne.

### Blind-timer LLM-producere (kører uanset om der er sket noget)

Import-graf-analyse (≤4 hop til `daemon_llm` / `cheap_provider_runtime` /
`non_visible_lane_execution` / `central_llm_egress`) giver **63 af 116** producere som
*kan* nå en LLM. Det er et øvre loft, ikke et bevis — modulet kan importere uden at
kalde hver gang. De med højest kadence × LLM-sandsynlighed:

| Producer | Nominel cd | Reel cd (tempo 2.0) | Kørsler/døgn | Kommentar |
|---|---:|---:|---:|---|
| `cognitive_state_warm` | 3 | ~5,8 | 248 | Retfærdiggjort — flytter blokerende LLM væk fra synlig tur |
| `prompt_assembly_cache_warmer` | 2 | ~3,9 | 372 | `primary_cache_warmer` = 18,2M tok/døgn. Cache-varme, ikke tænkning |
| `central_cadence_conductor` | 2 | ~3,9 | 372 | Måler tempoet — og resultatet er konstant 2.0 (§2.5) |
| `brain_continuity` | 5 | ~9,6 | 149 | Kædens rod, `session_distillation` |
| `central_shadow` / `central_self_observe` / `central_growth_observe` | 5 | ~9,6 | 149 hver | Central-observation, blind timer |
| `docs_drift_watchdog` | 5 | ~9,6 | 149 | Blind timer på dokumentations-drift |
| `inner_voice_daemon` / `emergent_signal_daemon` | 5 | ~9,6 | 147 hver | Blind timer, gated på witness |
| `central_agenda` / `central_prompt_explore` | 20 | ~36 | 40 hver | |

Fra `daemon_output_log` (rigtige LLM-daemon-kald, 2 døgn):

| Daemon | Kald | Bemærkning |
|---|---:|---|
| `weekly_manifest` | 136 | **Hedder "weekly", kører 68×/døgn.** Klar fejl-kadence |
| `goal_signal_synthesizer` | 130 | Skriver til `runtime_goal_signals`, som **ikke er skrevet i 40 dage** → arbejde uden output |
| `session_summary` | 62 | |
| `experiential_memory` | 48 | |
| `decision_review` | 23 | Kendt brænder (`cheaplane_burn_rootcause`) — nu nede fra 4376/døgn |
| `reflection_to_plan` | 18 | |
| `user_temperature` | 17 | Skriver til `user_temperature_active`, **sidst opdateret for 99 dage siden** |

`weekly_manifest` og `goal_signal_synthesizer` er tilsammen 266 af 428 LLM-daemon-kald
(62 %) og begge er mistænkelige: den ene har forkert kadence, den anden producerer til
en tabel ingen skriver til længere.

### 37 producere uden LLM-sti overhovedet (gratis)

`analyst api_conn_retention architect central_learning central_self_health construct
continuity_healer db_health_scan dissent dream_action echo_breaker emergent_signal_daemon
endpoint_usage_stats excess_sense gate_verdict_flush ghost glitch keymaker
life_projects_reassessment machines merovingian mourning oracle persephone rca red_dress
redpill relation_map_refresh sentinel seraph shared_cache_cleanup stream_stall_sweep
tool_usage_stats trinity twins white_rabbit witness_daemon`

Plus hele Familie F (16 lag-kontrakter). Disse koster kun CPU.

---

## 5. Prioriteret vurdering

### (a) Bør genoplives — 5 ting, i rækkefølge

**A1. Persistér `_last_run_at` til DB.** Én ændring, `internal_cadence.py:75/257`.
Fjerner genstarts-bygen, gør deklarerede kadencer ærlige og forhindrer at 30-dages-ritualer
fyrer ved hver deploy. Forudsætning for alt andet nedenfor.

**A2. Lav `depends_on` til "har kørt for nylig" i stedet for "kører i dette tick".**
Erstat `if dep not in ran_this_tick` med et vindue, fx `_last_run_at[dep]` inden for
`dep.cooldown_minutes × 2`. Det åbner hele Familie B uden at ændre en eneste
`cooldown_minutes`. **Dette er den enkeltændring med størst effekt i hele rapporten** —
den genopliver `dream_distillation`, `creative_journal`, `finitude`, `ontological_revision`
og `self_critique` på én gang, og fjerner samtidig den falske "blocked"-visning i MC.

**A3. Kroniken.** `cognitive_chronicle_entries` har 1 række. Efter A2 vil
`finitude_runtime` + `creative_journal_runtime` faktisk kunne skrive. Verificér bagefter
at der kommer rækker — ellers er der en anden gate.

**A4. Fjern tempo-gulvet eller hæv pulse-bunden.** Tempo 2.0 er ikke et "åndedræt", det
er en permanent halvering. Enten: klem tempoet til `[0.75, 1.5]`, eller hæv
`_compute_pulse_rate`'s hvile-gulv fra 0.3 til ~0.7 (`temporal_rhythm.py:104`), eller
slå konsumtionen fra med `central_cadence_tempo_live=false` indtil kurven er forstået.
Uanset valg: **dokumentér at deklareret cd ≠ reel cd**, ellers fejllæser du systemet igen.

**A5. `weekly_manifest`-kadencen.** 68 kald/døgn på noget der hedder "weekly".
Find triggeren og ret den — det er alene ~32 % af al LLM-daemon-trafik.

**A6. Ret Oraklets døde wire** — ét ords ændring. `central_excess.record_excess_pressure`
skal bruge `record_private(...)` i stedet for `observe(...)`, så `system/excess` faktisk
lander i `central_timeseries` hvor `central_oracle._WATCHED[0]` leder efter den. Samme
for `system/decentralization`. Uden det kører `excess_sense` 24 gange i døgnet for et
orakel der aldrig ser tallet.

### (b) Bør kobles til en konsument — 4 ting

**B1. De 26 døde per-visible-tur-trackere.** Beslut for hver: enten fix gaten (og få
data) eller fjern kaldet fra `visible_runs_cognitive.py`. At lade dem stå er det værste
af tre valg: latens på den synlige sti + løgnagtige MC-paneler. Start med de 19 der døde
15. maj samtidig — de har sandsynligvis én fælles årsag.

**B2. `goal_signal_synthesizer`** laver 65 LLM-kald/døgn ind i `runtime_goal_signals`,
som ikke er skrevet i 40 dage. Enten er skrivningen afkoblet (bug), eller også er
daemonens arbejde spildt siden `900d4220`. Afklar hvilket.

**B3. `dream_action` og `rca`** kører 7 hhv. 4 gange i døgnet mod tomme tabeller
(`central_dream_actions`, `central_rca`, 0 rækker). Gratis i tokens, men de er ren støj
i producer-listen — enten virker gaten aldrig, eller også skriver de aldrig.

**B4. `user_temperature`** — 17 LLM-kald/døgn, `user_temperature_active` sidst opdateret
for 99 dage siden. Samme mønster.

### (c) Bør pensioneres — 3 ting

**C1. De 12 tomme `cognitive_*`-tabeller** (`cognitive_blind_spots`, `_epistemic_claims`,
`_wrongness`, `_missions`, `_repairs`, `_morning_threads`, `_narrative_identities`,
`_emergent_goals`, m.fl.). Nul rækker nogensinde. Enten døde eksperimenter eller aldrig
færdig-wiret. Drop skema + kode, eller færdiggør — men lad dem ikke stå og forurene
capability-billedet.

**C2. Matrix-familiens hale — 22 af 26 kan afregistreres uden at prompten ændrer sig.**
Se §3a-quater: deres `record_*` kalder kun `observe()`, og `build_*_surface` genberegner
alligevel fra kilden. Behold `trinity`, `sentinel`, `merovingian`, `trainman` (de skriver
durabelt og læses). De øvrige 22 udgør 19 % af producer-registret og er en stor del af
grunden til at overblikket er væk. Alternativ til hård pensionering: skru deres cooldown
markant op (fx ×10) — de er telemetri, ikke kognition.

**C2b. `tool_usage_stats` og `central_notation_reasoning`** er bekræftet forældreløse —
ingen kalder deres output. `central_coverage` skriver 4 timeserier ingen læser.
Enten wire en konsument, eller afregistrer.

**C3. Stivnede sidespor:** `runtime_browser_bodies` (1 rk, 125d), `composite_tools`
(1 rk, 112d), `cognitive_personal_projects` (1 rk, 117d), `self_repair_patterns`
(4 rk, 98d), `interlanguage_blind_trials` (99 rk, 80d), `teams`/`team_invites` (57d).
Afsluttede eksperimenter — arkivér dem eksplicit så de ikke tælles som "capability".

---

## 7. Den anden halvdel: de 48 cluster-daemoner (IKKE cadence)

Ved siden af de 116 cadence-producere findes daemon-registret
(`core/services/daemon_manager.py`, `_REGISTRY` linje 24-787, ~60 entries). 54 af dem er
markeret `retired` (2026-07-13/15) og foldet ind i **10 familier** à i alt **48 medlemmer**
(`cluster_daemon.py` familie 1-5, `cluster_daemon_families.py` familie 6-10):

| Familie | Deklareret cadence | Medlemmer |
|---|---:|---|
| `cluster_somatic` | 3 min | somatic, experienced_time, absence |
| `cluster_innervoice` | 2 min | thought_stream, reflection_cycle, meta_reflection, irony, existential_wonder, creative_drift |
| `cluster_affect` | 4 min | surprise, conflict, desire, longing_signal, emotion_repair_bridge |
| `cluster_narrative` | 1440 min | development_narrative, narrative_summary, identity_drift, identity_sketch, consolidation_judge |
| `cluster_cognition` | 5 min | pattern_counterfactual, causal_inference, dream_insight, active_sensing |
| `cluster_memory` | 2 min | memory_write_queue/decay/pruning/maintenance/safeguard, selective_consolidation, associative_recall, council_memory |
| `cluster_aesthetic` | 5 min | aesthetic_taste, curiosity |
| `cluster_relation` | 10 min | user_model, communication_guard, relation_map_refresh |
| `cluster_projects` | 2 min | task_worker, my_projects_watchdog, life_projects_reassessment, thought_action_proposal |
| `cluster_infra` | 2 min | file_awareness, cache_maintenance, signal_decay, wakeup_cleanup, cost_optimization, ground_truth_registry, mail_checker, visual_memory |

### 7a. De kører 2 gange i døgnet, ikke hvert 2.-10. minut

Familierne trigges fra `heartbeat_runtime_influence.py:702-970`, som kaldes fra
`_build_influence_trace` i `heartbeat_runtime.py:2432` — dvs. inde i den **fulde**
heartbeat-tick. Fra live-DB'en, seneste døgn:

```
heartbeat.phased_tick        2669   (hvert ~30 s — scheduleren KØRER)
heartbeat.tick_started          2   (den fulde tick)
heartbeat.tick_completed        2
heartbeat.tick_deadline_exceeded 2  ← 100 % af de fulde ticks sprængte 90 s-deadline
heartbeat.scheduler_started     3   (3 genstarter i vinduet)
```

`thought_stream` har deklareret cadence **2 minutter** = 720 kørsler/døgn. Faktiske
LLM-kald ifølge `daemon_output_log`: **3-5 i døgnet**, og altid i en byge sammen med hele
resten af familien inden for ~60 sekunder:

```
2026-08-17T08:06:36 thought_stream   2026-08-16T20:54:08 thought_stream
2026-08-17T08:06:38 reflection_cycle 2026-08-16T20:54:11 reflection_cycle
2026-08-17T08:06:39 meta_reflection  2026-08-16T20:54:12 meta_reflection
2026-08-17T08:06:41 existential_wonder
2026-08-17T08:07:26 user_model       2026-08-16T20:55:03 user_model
```

**Det er <1 % af deklareret kadence.** Årsagen er `heartbeat_phases`-fixet fra
2026-05-18 (`f50ba56d` "act_phase dispatcher kun til run_heartbeat_tick når der ER
prioriteter" + `7497f9da` "scheduler calls tick_with_phases"). Efter det kører den fulde
tick kun når heartbeat finder reelle prioriteter — hvilket sker ~2 gange i døgnet.
Hele familielaget hænger på den beslutning uden at nogen har besluttet det.

### 7b. Lige nu er den fulde tick fastfrosset

```
16:11:55  scheduler_started  due=true  next_tick_at=2026-08-17T08:23:04  recovery=startup-recovery-pending
16:14:05  scheduler_started  due=true  next_tick_at=2026-08-17T08:23:04  recovery=startup-recovery-pending
19:08:53  scheduler_started  due=true  next_tick_at=2026-08-17T08:23:04  recovery=startup-recovery-pending
```

`next_tick_at` peger 11 timer tilbage i tiden, `due=true`, og alligevel er der ikke
udsendt en eneste `tick_started` siden 08:06. Tre genstarter har ikke rykket den.
`DAEMON_STATE.json` bekræfter: alle 10 `cluster_*` har `last_run_at = 2026-08-17T08:07`
(11,1 timer siden), mens de enkelte medlemmer står med `last_run_at = 2026-07-15`
(≈803 timer siden — de skriver til `daemon_output_log` i stedet, men bekræfter mønstret).

### 7c. `default_cadence_minutes` er dokumentation, ikke styring

`daemon_manager.get_effective_cadence()` (`daemon_manager.py:850`) har **intet
runtime-callsite** — kun `tests/test_daemon_manager.py`. Tick-siderne har ingen
modulo-/interval-check; de kalder familien hver gang den fulde tick kører. Al reel
throttling ligger i medlemmernes egne `_CADENCE_*`-konstanter. Konsekvens:
`control_daemon(..., "set_interval")` ændrer intet — kun `enable`/`disable` virker.

Mindre fund i samme fil: `"memory_safeguard"` står to gange i `_REGISTRY` (linje 97 og
403); Python overskriver stille den første.

### 7d. Kill-switches — og hvad der ALLEREDE er tændt i produktion

Verificeret direkte mod `runtime_state_kv` på CT105 (ikke dev-workspacet):

| Nøgle | Live-værdi | Sat |
|---|---|---|
| `event_driven_daemons` | **true** | 2026-07-23 |
| `event_gate_min_delta` | **0.1** | 2026-07-13 |
| `raw_signal_mode` | **true** | 2026-07-13 |
| `central_cadence_tempo_live` | fraværende → default true | — |
| `cluster_daemon_shadow` | fraværende (og virkningsløs, se nedenfor) | — |

Vigtigt: **det event-drevne gate-lag ER tændt**, og `raw_signal_mode` er tændt (dvs.
somatic/absence/conflict/desire/experienced_time/surprise bruger regel-beregnede strenge
i stedet for LLM). De to oplagte "spar tokens"-håndtag er altså allerede trukket.
Det tilbageværende LLM-forbrug i familierne er dét der overlever gaten.

`cluster_daemon_shadow` (`cluster_daemon.py:65-79`, default True) er **død kode**: alle
10 `tick_cluster_*`-entrypoints sætter eksplicit `shadow=False` (fx `cluster_daemon.py:927`,
`:1217`, `families.py:1250`), så flaget kan ikke bruges til at sætte familierne i observe-only.

### 7e. Heartbeat-direkte LLM-slots (uden om både cadence og familier)

| Slot | Gate | LLM |
|---|---|---|
| `tick_recurrence_loop_daemon` | `_HEARTBEAT_TICK_COUNTER % 5` (`heartbeat_runtime.py:2097`) | ja |
| `tick_broadcast_daemon` | `% 2` (`:2103`) | nej |
| `tick_meta_cognition_daemon` | `% 10` (`:2109`) | ja, 2 kald/fyring |

Disse er **ikke** `is_enabled`-gatede — de kan kun slås fra via deres eget
`get_experiment_enabled(...)`-flag. Men da den fulde tick kun kører 2×/døgn, fyrer
`% 5` og `% 10` reelt aldrig.

### 7f. To familier er fejl-dokumenteret som LLM-frie

* `cluster_somatic` beskrives som "INGEN LLM-medlem" (`daemon_manager.py:570`,
  `cluster_daemon.py:288`) og har `gate_calls=0` — men `somatic_daemon.py:272`,
  `experienced_time_daemon.py:132` og `absence_daemon.py:221` kalder alle `daemon_llm`.
  (Mildnet af at `raw_signal_mode=true` er tændt i produktion.)
* `cluster_infra` beskrives som "INGEN LLM-medlem" — men `mail_checker_daemon.py:66`
  kalder `daemon_llm_call`, ét kald pr. ny uset mail. Event-drevet, så lav last.

### 7g. Blinde timer-LLM'er i familierne (dem der fyrer uanset hvad)

`thought_stream` (2 min) · `reflection_cycle` (10 min) · `development_narrative` (24 t) ·
`identity_drift` (24 t, quality-lane) · `consolidation_judge` (1440 min) ·
`pattern_counterfactual` (60 min — koden indrømmer selv "blind-timer LLM",
`cluster_daemon.py:1455`) · `council_memory` (10 min; sætter `_last_llm_call_at` FØR
kaldet, `council_memory_daemon.py:34-44`, og fyrer blot hvis COUNCIL_LOG er ikke-tom).

Event-drevne (kræver reel tilstandsændring): `irony`, `existential_wonder`,
`creative_drift`, `surprise`, `conflict`, `desire`, `narrative_summary`, `aesthetic_taste`,
`user_model`, `mail_checker`, `absence`, `somatic`.

**Men:** fordi den fulde tick kun kører 2×/døgn er ingen af dem i praksis en
token-brænder lige nu. Problemet er det modsatte — de kører for lidt.

---

## 8. Revideret prioritering efter §7

Fundene i §7 rangerer over det meste af §5, fordi de rammer et større lag:

1. **Få den fulde heartbeat-tick til at køre igen** (`heartbeat.tick_started` = 2/døgn,
   nu 11 t overskredet, `recovery=startup-recovery-pending` på tre genstarter i træk).
   Uden dette er hele §7-laget dødt uanset hvad du ellers gør.
2. **Afkobl de 10 cluster-familier fra "har heartbeat prioriteter?"-beslutningen.**
   De bør tikke på deres egen kadence — enten via cadence-motoren (samme sted som de 116)
   eller via en egen scheduler. Konsekvensen af `f50ba56d` blev aldrig tænkt igennem.
3. **90 s tick-deadline sprænges 100 % af gangene.** Enten er deadline for kort til
   48 medlemmer, eller også hænger noget. Begge dele skal måles, ikke gættes.
4. Derefter §5 A1 (persistér `_last_run_at`) og A2 (dependency-vindue i stedet for
   samme-tick).
5. `get_effective_cadence` er dead code — enten wire den ind, eller fjern
   `default_cadence_minutes` fra `_REGISTRY` så MC ikke viser tal der ikke styrer noget.

---

## 6. Reproduktion

```bash
# Producer-katalog (statisk, AST)
#   udtræk alle ProducerSpec(...) i core/ og apps/

# Live-sandhed (read-only)
ssh bs@10.0.0.39 'sqlite3 "file:/home/bs/.jarvis-v2/state/jarvis.db?mode=ro" \
  "SELECT payload_json FROM events WHERE kind=\"heartbeat.cadence_tick\" ORDER BY id DESC LIMIT 1500;"'

# Tempo-tilstand
ssh bs@10.0.0.39 'sqlite3 "file:/home/bs/.jarvis-v2/state/jarvis.db?mode=ro" \
  "SELECT * FROM runtime_state_kv WHERE key=\"cadence_tempo_last\";"'

# Genstartstidspunkt (afgørende for §2)
ssh bs@10.0.0.39 'systemctl show jarvis-runtime -p ActiveEnterTimestamp'
```

**Nøglefiler:**
`core/services/internal_cadence.py` (motor, linje 56 ProducerSpec, 75 `_last_run_at`,
95 dependency-gate, 200+ tick-dispatch) ·
`core/services/internal_cadence_{core,inner_life,matrix,maintenance}.py` (registrering) ·
`core/services/central_cadence_conductor.py` (tempo, exempt-liste linje ~127) ·
`core/services/temporal_rhythm.py:94-108` (pulse-gulv 0.3) ·
`core/services/central_layer_contract.py:185` (dynamisk lag-registrering) ·
`core/services/visible_runs_cognitive.py` (59 per-tur-trackere) ·
`core/services/{finitude_runtime,creative_journal_runtime,dream_distillation_daemon}.py`
(interne dato-gates).
