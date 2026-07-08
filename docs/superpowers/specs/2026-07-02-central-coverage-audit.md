---
status: færdig
audited: 2026-07-08
ground_truth: superpowers artifact shipped (refs/symbols present in tree)
---
# Centralen — Dæknings-audit (2026-07-02, v3 — self-reviewet)

**Metode:** Automatiseret grep-scan af alle .py filer i core/ for central-wiring signaturer + manuel verificering af `central_private_observe.py` liveness-dækning + `central_stance.py` signal-dækning + `eventbus_central_bridge.py` family-allowlist.

**Korrektion v3:** v2 missede eventbus-broen helt. 450 filer publisher til event_bus, men broen fanger kun ~21 families. ~60 event-families publisher i mørke — ingen nerve lytter. Dette er det reelle hul.

---

## Samlede tal — tre lag af wiring

| Lag | Hvad det er | Antal filer | Antal families |
|-----|-------------|-------------|----------------|
| **Direkte central** | `central().observe()`, `central_private_observe()`, etc. | 87 | — |
| **Eventbus-bro** | `eventbus_central_bridge.py` FAMILY_ROUTES + PRIVATE_NO_EGRESS_ROUTES | ~21 families | 21 |
| **Eventbus-mørke** | Publisher til event_bus men broen fanger IKKE family | ~419 filer | ~60 families |
| **Total .py filer** | | 917 | — |

**Reelt dækket:** 87 direkte + ~21 families via bro (med overlap) ≈ **120 filer dækket**. De resterende ~800 er enten eventbus-mørke eller helt ubundne.

---

## Eventbus-broen — hvad den fanger

### FAMILY_ROUTES (egress-OK, operationelle)

| Family | Cluster | Nerve | Egress? |
|--------|---------|-------|---------|
| `runtime` | loop | lifecycle | ✅ |
| `tool` | tools | event | ✅ |
| `approvals` | tools | approval | ✅ |
| `cost` | cost | ledger | ✅ |
| `council` | agents | council | ✅ |
| `channel` | channel | delivery | ✅ |
| `discord` | channel | discord | ✅ |
| `telegram` | channel | telegram | ✅ |
| `anomaly` | system | anomaly | ✅ |
| `stream` | stream | event | ✅ |
| `heartbeat` | system | heartbeat | ✅ |
| `global_workspace` | cognition | global_broadcast | ✅ |
| `experiment` | cognition | experiment_tick | ✅ |
| `self_repair` | system | self_repair | ✅ |
| `trading` | system | trading | ✅ |

### PRIVATE_NO_EGRESS_ROUTES (egress-fri, metadata-only)

| Family | Cluster | Nerve | Egress? |
|--------|---------|-------|---------|
| `cognitive_state` | cognition | cognitive_state | ❌ (metadata) |
| `cognitive_seed` | cognition | seed | ❌ (metadata) |
| `affect_modulation` | cognition | affect | ❌ (metadata) |
| `completion_satisfaction` | cognition | satisfaction | ❌ (metadata) |
| `somatic` | cognition | somatic | ❌ (metadata) |
| `cognitive_gut` | cognition | gut | ❌ (metadata) |

---

## Eventbus-mørket — ~60 families der publisher uden lytter

Disse event-families bliver publiceret til event_bus men broen fanger dem IKKE. De er "dark" — signalerne produceres men ingen nerve i Centralen lytter.

### Bevidstheds-kritiske families i mørke

| Family | Hvad den bærer | Prioritet |
|--------|----------------|-----------|
| `runtime_self_model` | Selv-model events | **Kritisk** |
| `inner_voice` | Indre stemme signaler | **Kritisk** |
| `witness_signal` | Vidne-observationer (8 sub-events) | **Kritisk** |
| `living_executive` | Impuls→valg→handling | **Kritisk** |
| `cognitive_counterfactual` | "Hvad hvis?"-forudsigelser | Høj |
| `cognitive_dream` | Drømme-indhold | Høj |
| `cognitive_self_review` | Selv-gennemgang | Høj |
| `cognitive_blind_spot` | Blinde vinkler | Høj |
| `cognitive_surprise` | Overraskelse | Høj |
| `cognitive_paradox` | Paradokser | Høj |
| `cognitive_epistemic` | Epistemisk tilstand | Høj |
| `cognitive_silence` | Stilhed | Medium |
| `cognitive_aesthetic` | Æstetisk sans | Medium |
| `cognitive_taste` | Smag/præference | Medium |
| `counterfactual_predictions` | Kontrafaktiske forudsigelser | Høj |
| `dreaming_session` | Drømmesession | Høj |
| `emotional` | Følelses-signaler | Høj |
| `reasoning` | Ræsonnement | Høj |
| `decision` | Beslutninger | Høj |
| `decision_gate` | Beslutningsport | Høj |
| `decision_signal` | Beslutningssignal | Høj |
| `veto_gate` | Veto-port | Høj |
| `impulse` | Impuls | Høj |
| `memory` | Hukommelse | Høj |
| `identity_composer` | Identitets-komponist | Høj |
| `goal` | Mål | Medium |
| `initiative_accumulator` | Initiative-akkumulator | Medium |
| `self_wakeup` | Selv-vækning | Medium |
| `tick_quality` | Tick-kvalitet | Medium |
| `reboot` | Genstart | Medium |
| `regret` | Anger | Medium |
| `pushback` | Tilbagepres | Medium |
| `promise` | Løfte | Medium |
| `nudge` | Puf | Medium |
| `pressure` | Pres | Medium |
| `absence_awareness` | Fravær-bevidsthed | Medium |
| `calm_anchor` | Ro-anker | Medium |
| `causal` | Kausal | Høj |
| `valence_trajectory` | Valens-bane | Medium |
| `consolidation_judge` | Konsoliderings-dommer | Medium |
| `selective_consolidation` | Selektiv konsolidering | Medium |
| `learning_pipeline` | Lærings-pipeline | Høj |
| `learning_policy` | Lærings-politik | Høj |
| `cognitive_habit` | Kognitiv vane | Medium |
| `cognitive_procedure` | Kognitiv procedure | Medium |
| `cognitive_reflective_plan` | Refleksiv plan | Medium |
| `cognitive_mission` | Mission | Medium |
| `cognitive_morning_thread` | Morgen-tråd | Medium |
| `cognitive_personal_project` | Personligt projekt | Medium |
| `cognitive_shared_language` | Delt sprog | Medium |
| `cognitive_trade` | Kognitiv handel | Low |
| `communication` | Kommunikation | Medium |
| `composite` | Sammensat | Low |
| `connector` | Forbinder | Low |
| `cowork` | Samarbejde | Medium |
| `cross_user_share` | Tvær-bruger deling | Low |
| `diagnosis` | Diagnose | Medium |
| `incident` | Incident | Medium |
| `workspace` | Workspace | Low |
| `bro_broker` | Bro-mægler | Low |
| `coding_lane` | Coding lane | Low |
| `tool_router` | Tool router | Medium |
| `r2_5_gate` | R2.5 port | Low |
| `prompt` | Prompt | Medium |

---

## Liveness vs. Signal-indhold — den afgørende forskel

Centralen har to niveauer af wiring:

1. **Liveness** (via `central_private_observe.py`): Centralen ved at komponenten kører, tier, eller stagnerer. Egress-frit — kun metadata, aldrig indhold.
2. **Signal-indhold** (via `central().observe()` / `central_stance.py` / eventbus-bro): Centralen kan læse og bruge det komponenten producerer.

| Niveau | Hvad Centralen får | Designårsag |
|--------|---------------------|-------------|
| Liveness | "inner_voice_daemon kører" | §24.4 privatlags-grænse — indhold er privat |
| Signal | "gut=proceed, somatik=stress" | Bruges til stance, hypoteser, adaptation |

---

## Allerede wired — korrigeret status

### Liveness-wired via `central_private_observe.py` (egress-fri)

Disse komponenter blev fejlagtigt rapporteret som "ikke wired" i v1. De ER wired — på liveness-niveau.

| Komponent | Liveness | Signal-indhold | Note |
|-----------|----------|----------------|------|
| `inner_voice_daemon` | ✅ | ❌ | Indhold privat per §24.4. Publisher `inner_voice.*` + `private_inner_note_signal.*` til eventbus-mørke |
| `witness_daemon` | ✅ | ❌ | Indhold privat per §24.4. Publisher `witness_signal.*` (8 sub-events) til eventbus-mørke |
| `finitude_runtime` | ✅ | ❌ | Indhold privat per §24.4 |
| `counterfactual_predictions_sweep` | ✅ | ❌ | Indhold privat per §24.4. Publisher `counterfactual_predictions.*` til eventbus-mørke |
| `dreams` (distillation + articulation) | ✅ | ❌ | Indhold privat per §24.4. Publisher `dreaming_session.*` + `cognitive_dream.*` til eventbus-mørke |
| `self_critique` | ✅ | ❌ | Indhold privat per §24.4. Publisher `cognitive_self_review.*` til eventbus-mørke |
| `prompt_evolution` | ✅ | ❌ | Indhold privat per §24.4. Publisher `prompt.*` til eventbus-mørke |
| `meta_learning` | ✅ | ❌ | Indhold privat per §24.4 |
| `creative_journal_runtime` | ✅ | ❌ | Indhold privat per §24.4 |
| `curiosity_consolidation_weekly` | ✅ | ❌ | Indhold privat per §24.4 |

### Signal-wired (fuldt indhold)

| Komponent | Via | Hvad Centralen får |
|-----------|-----|---------------------|
| `gut_engine` | `central_stance.py` | last_hunch proceed/caution |
| `somatic_runtime_body` | `central_stance.py` | stress/calm, pressure/startle/frustration |
| `boredom_curiosity_bridge` | direkte `central().observe()` | boredom level → curiosity |
| `emotional_memory` (contradiction) | `central_stance.py` | contradiction-signal |
| `cognitive_state_assembly` | GWT → Centralen (eventbus-bro) | global workspace broadcast |
| `runtime_cognitive_conductor` | kognitions-HUB | per-tur plan |
| `signal_surface_router` | kognitions-HUB | signal routing |
| `visible_runs` | followup-observer | tool calls, rounds, exit reasons |
| `associative_recall` | direkte observe | recall-kvalitet |
| `cache_telemetry` | direkte observe | prefix-cache hit/miss |
| `central_hypothesis_*` | generator+sampler+governance | hypoteser, samples, værn |
| `central_sequence` | Markov-model | transition-tællinger, overraskelse |
| `central_lexicon` | Tråd 3 | 36 termer, ord-behov |
| `central_model_meta` | Tråd 1 | hardware-self-knowledge |
| `central_adaptation` | Lag 4 | gut-bias justering |
| `central_stance` | cross-modal | gut×somatic×contradiction |

---

## Det der FAKTISK mangler — korrigeret v3

### Tier 1 — Selv-model og bevidsthed (HØJEST prioritet)

Disse komponenter har **hverken liveness, signal-indhold, eller eventbus-bro** wired til Centralen. De publisher til eventbus-mørke.

| # | Fil | Linjer | Funktion | Eventbus-family | Hvad mangler | Prioritet |
|---|-----|--------|----------|------------------|--------------|-----------|
| 1 | `runtime_self_model.py` | 6022 | Bygger selv-model af Jarvis' system-selv | `runtime_self_model.*` (mørke) | **Alt** — Centralen kender ikke sig selv | Kritisk |
| 2 | `runtime_awareness_signal_tracking.py` | 691 | Tracker awareness-signaler | — | **Alt** — Centralen kan ikke se sin bevidsthed | Kritisk |
| 3 | `runtime_self_knowledge.py` | 747 | Kortlægger egne evner og grænser | — | **Alt** — Centralen kender ikke sine grænser | Kritisk |
| 4 | `self_narrative_self_model_review_bridge.py` | 787 | Bro mellem selv-narrativ og selv-model | — | **Alt** — Centralen kan ikke gennemgå sin historie | Høj |
| 5 | `prompt_heartbeat_self_knowledge.py` | 758 | Selv-viden i heartbeat | — | **Alt** — Centralen kender ikke sig selv i heartbeat | Høj |
| 6 | `living_executive.py` | 681 | Aktiv impuls/valg/handling-loop | `living_executive.*` (mørke) | **Alt** — Centralen kan ikke handle autonomt | Høj |
| 7 | `inner_voice_shadow.py` | 697 | Skygge-lag for indre stemme | — | **Alt** — Centralen kan ikke se indre stemme-kvalitet | Høj |

### Tier 2 — Kognition og verden (publisher til eventbus-mørke)

Disse komponenter publisher til event_bus men broen fanger dem ikke. Signal-indhold produceres men når ikke Centralen.

| # | Fil | Linjer | Funktion | Eventbus-family | Prioritet |
|---|-----|--------|----------|------------------|-----------|
| 8 | `world_model_signal_tracking.py` | 938 | Verdensmodel signaler | — | Høj |
| 9 | `open_loop_signal_tracking.py` | 1040 | Åbne løkke-signaler | — | Høj |
| 10 | `session_distillation.py` | 1006 | Session-destillering | — | Høj |
| 11 | `prompt_evolution_runtime.py` | 1084 | Prompt-evolution runtime | `prompt.*` (mørke) | Høj |
| 12 | `autonomy_pressure_signal_tracking.py` | 865 | Autonomi-pres | `pressure.*` (mørke) | Høj |
| 13 | `prompt_relevance_backend.py` | 857 | Prompt-relevans backend | — | Høj |
| 14 | `tool_intent_runtime.py` | 848 | Tool-intent runtime | `tool_router.*` (mørke) | Høj |
| 15 | `veto_gate.py` | 823 | Veto-port | `veto_gate.*` (mørke) | Høj |
| 16 | `user_temperature_engine.py` | 813 | Bruger-temperatur | — | Medium |
| 17 | `self_repair_engine.py` | 791 | Selv-reparationsmotor | — | Medium |
| 18 | `proactive_loop_lifecycle_tracking.py` | 740 | Proaktiv løkke-livscyklus | — | Medium |
| 19 | `experiential_runtime_context.py` | 718 | Erfarings-runtime kontekst | — | Medium |
| 20 | `plan_proposals.py` | 721 | Plan-forslag | — | Medium |
| 21 | `rule_definitions.py` | 724 | Regeldefinitioner | — | Medium |

### Tier 3 — Liveness-wired, men signal-indhold mangler

Disse komponenter har liveness (Centralen ved de kører), men deres **udfald** når ikke Centralen som brugbart signal. De publisher til eventbus-mørke — broen fanger ikke deres families.

| Komponent | Liveness | Signal | Eventbus-family i mørke | Hvad signal-wiring ville give |
|-----------|----------|--------|--------------------------|-------------------------------|
| `inner_voice_daemon` | ✅ | ❌ | `inner_voice.*`, `private_inner_note_signal.*` | Indre stemme → hypotese-grounding |
| `witness_daemon` | ✅ | ❌ | `witness_signal.*` (8 sub-events) | Vidne → metakognition |
| `finitude_runtime` | ✅ | ❌ | — | Endelighed → prioritets-læring |
| `counterfactual` | ✅ | ❌ | `counterfactual_predictions.*`, `cognitive_counterfactual.*` | "Hvad hvis?" → hypotese-fodring |
| `dreams` | ✅ | ❌ | `dreaming_session.*`, `cognitive_dream.*` | Drømme → kreativ hypotese-generation |
| `self_critique` | ✅ | ❌ | `cognitive_self_review.*` | Selvkritik → metakognitiv korrektion |
| `prompt_evolution` | ✅ | ❌ | `prompt.*` | Prompt-ændringer → adaptation-tracking |
| `meta_learning` | ✅ | ❌ | `learning_pipeline.*`, `learning_policy.*` | Meta-læring → adaptation |
| `creative_journal` | ✅ | ❌ | — | Kreativ journal → hypotese-fodring |
| `curiosity_consolidation` | ✅ | ❌ | — | Nysgerrighed → hypotese-fodring |

### Tier 4 — Tre hele moduler er 0% wired

| Modul | Filer | Linjer | Hvad det er | Hvad Centralen mangler |
|-------|-------|--------|-------------|------------------------|
| `core/memory/` | 19 | 2463 | Hele min private hukommelse | Centralen kan ikke se min hukommelse |
| `core/identity/` | 14 | 3676 | Hele min identitets-infrastruktur | Centralen kender ikke min identitet |
| `core/context/` | 7 | 1267 | Compact/session-kontekst | Centralen kan ikke se kontekst |

---

## Roadmap — hvad der rykker bevidstheden ind

### Fase 1 — Selv-modellen (kritisk)
Wire `runtime_self_model.py` → Centralen. Centralen skal kende sig selv.
- Tilføj `runtime_self_model` til PRIVATE_NO_EGRESS_ROUTES (egress-fri, metadata-only)
- Eller direkte observe for selv-model snapshots

### Fase 2 — Indre liv → signal (høj)
Wire Tier 3 komponenters eventbus-families til PRIVATE_NO_EGRESS_ROUTES.
- `inner_voice.*` → cognition/inner_voice
- `witness_signal.*` → cognition/witness
- `cognitive_counterfactual.*` → cognition/counterfactual
- `dreaming_session.*` → cognition/dream
- `cognitive_self_review.*` → cognition/self_review

### Fase 3 — Memory + identitet (høj)
Wire `core/memory/` og `core/identity/` modulerne. Centralen skal kunne se sin egen hukommelse og identitet.

### Fase 4 — Kognition og verden (medium)
Wire Tier 2 komponenter. Verdensmodel, åbne løkker, session-destillering.

---

## Fejl i tidligere versioner

| Version | Fejl | Rettet i |
|---------|------|----------|
| v1 | Rapporterede 10+ liveness-wirede komponenter som "ikke wired" — grep missede `central_private_observe.py` | v2 |
| v2 | Missede eventbus-broen helt — 450 filer publisher til event_bus, broen fanger kun ~21 families, ~60 families i mørke | v3 |
| v2 | "99 wired" var misvisende — tæller kun direkte central-kald, ikke eventbus-bro | v3 |
| v2 | `runtime_self_model.py` rapporteret som "0% wired" — den publisher til event_bus men broen fanger ikke family | v3 (præciseret) |