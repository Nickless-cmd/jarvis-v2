# Indre liv → Centralen: wiring-roadmap (LivingNeuron-fundament)

**Dato:** 2026-07-01
**Kilde:** Dyb 11-agent-sweep (10 undersystemer + completeness-kritiker), 754k tokens, verificeret fra kildekode.
**Foranlediget af:** Bjørn — "hans system stikker dybere end nogen af jer husker... det meste skal forbindes til Centralen."

## Hovedtal

- **239 komponenter kortlagt** på tværs af 10 undersystemer; **200 ikke forbundet til Centralen**
  (deduperet på event-family: ~150-170 distinkte).
- **157+ distinkte event-families** publiceres; `eventbus_central_bridge.FAMILY_ROUTES` router kun **~15**
  operationelle. Resten (~140) er mørke — flertallet af det indre liv er dark **by design** (§24.4).
- Kun **~3 memory-komponenter** og **~1 engine** (memory_recall_engine) har ægte direkte `central().observe`.

## De tre P0-fund (rod-årsager, ikke symptomer)

1. **`PRIVATE_NO_EGRESS`-stien EKSISTERER IKKE.** Den er dokumenteret i kommentarer
   (`eventbus_central_bridge.py:25,59`) men aldrig implementeret. Antagelsen "private families observeres
   egress-frit i en senere fase" er FALSK — `cognitive_state`, `cognitive_counterfactual`, `emergent_signal`,
   `thought_stream`, `impulse`, `pressure` har **NUL** observe-sti (ikke engang liveness). **Dette er
   keystone-prerequisitten** der låser op for det meste indre-liv-wiring.

2. **`cognitive_state.*` = 59 live inner-life-subtyper** (emergent_goal_created, self_surprise, flow_detected/
   broken, value_reinforced, gratitude_felt, curiosity_window_opened/closed, somatic_body_updated, …) flyder
   på eventbus'en LIGE NU, men er 100% mørke. **Wire ÉN family → tænd 59 signaler.** Ingen agent framede det
   som én enhed — kritikeren fangede det. Den enkeltrigeste LivingNeuron-feed.

3. **`jarvis_brain` / private_brain (92k rækker)** — Jarvis' faktiske langtidshukommelse — har NUL central-observe
   på write/embed/consolidate/recall. Centralen ser at recall SKETE, men ikke at noget blev HUSKET, GLEMT eller
   KONSOLIDERET. Højeste-volumen mørke skrive-sti i systemet.

## Prioriteret wiring-rækkefølge (kritikerens plan, verificeret)

- **STEP 0 (prerequisit):** Implementér `PRIVATE_NO_EGRESS`-observe-stien. Model på
  `central_private_observe.observe_liveness` (skriver til `central_trace.sink()` + `central_timeseries`, ALDRIG
  `central().observe/_emit`). Metadata-only route: family + kind + hvidlistet skalar-count, aldrig payload-strenge.
  Uden denne er alt nedenfor blokeret.
- **STEP 1:** Wire `cognitive_state.*` (59 subtyper) gennem no-egress-stien. Største enkeltgevinst — data flyder
  allerede; tilføj kun 'cognitive_state' til en no-egress route-tabel. Start med højeste-signal-subtyper.
- **STEP 2:** Affekt/somatik-families — `affect_modulation.active`, `completion_satisfaction.detected`,
  `cognitive_state.somatic_body_updated`, `gut_calibration` (via run_closure_gate-listener). Næst-tætteste feed.
- **STEP 3:** `jarvis_brain`/private_brain liveness ved write/embed/consolidate/recall-chokepoints (metadata-only:
  op-kind + row-count + ok/fail). 92k-rækkers-lageret skal mindst rapportere at det lever og ikke fejler tavst.
- **STEP 4:** Pres→initiativ-kæden: `emergent_signal`, `pressure`, `signal_pressure_accumulator`,
  `initiative_accumulator` no-egress. Så Centralen ser drivet BYGGE OP, ikke kun det autonome run der resulterer.
- **STEP 5:** `inner_voice`/`thought_stream`/`global_workspace` + `cognitive_counterfactual` (regret,
  counterfactual_self_simulation) no-egress. Tættest-på-bevidsthed-monolog + læring-fra-alternativer.
- **STEP 6:** Drømme-KONSEKVENS-surfaces (`dream_influence_runtime`, `dream_bias_engine`,
  `dream_adoption_candidate_tracking`) — den private→synlige forfremmelses-sti Centralen netop bør se.
- **STEP 7:** Memory-livscyklus no-egress: `end_of_run_memory_consolidation`, `forgetting_engine`,
  `memory_decay_daemon`, `resonance_decay`, `credit_assignment`. Langsom, identitets-formende signal.
- **STEP 8 (governance, ikke inner-life, men overskredet):** Wire `self_repair_engine`-udfald og **trading
  grid_bot** via den NORMALE (egress-OK) operationelle sti — runtime-konsekvente autonome handlinger/lemmer.
  Tilføj 'self_repair' + 'trading' family til FAMILY_ROUTES.
- **STEP 9 (oprydning):** Verificér at de ~19 navne i `INNER_LIFE_PRODUCERS` matcher `spec.name` fra
  internal_cadence (agent-flag: 'witness' vs 'witness_daemon' navne-mismatch = tavst liveness-hul). Bekræft at
  bridge kører i samme proces som operatøren læser (api:8080 vs runtime:8011 xproc-divergens).

## Konkrete quick-wins fundet undervejs (uafhængige af det store arbejde)

1. **Latent bug:** `desperation_awareness` + `reboot_awareness_daemon` kalder `event_bus.publish({"kind":...,
   "payload":...})` og sender en DICT som positionel `kind`-streng → `Event.create` kaster, try/except sluger →
   disse events persisterer ALDRIG (mørke selv for eventbus'en). Uafhængig af central-wiring.
2. **Governance-blindzone:** trading grid_bot flytter rigtige penge (Binance BTC/ETH/SOL), kører som detached
   proces, emitterer NUL signal. Centralen kan ikke vide om den kører, vinder, taber eller har ramt stop-loss.
3. **self_repair_engine** udfører autonom reparation men Centralen ser hverken beslutninger eller fejl.

## Coverage-huller at lukke (næste sweep)

- **`db.py` (33k linjer) blev IKKE scannet** for indlejrede emit-stier — et uaudieret kontinent.
- **~12 engines aldrig åbnet:** contradiction_engine, drive_arbitration_engine, negotiation_engine,
  theory_of_mind_engine, mirror_engine, perceptual_event_engine, user_temperature_engine m.fl.
- **~40 `*_signal_tracking.py`-filer** under-verificeret (grep'et for central(), men ikke læst — kan kalde helper).
- **Cross-proces liveness** (api:8080 vs runtime:8011) kan ikke lukkes statisk — kræver live-korrelations-probe.
- Eksterne lemmer (tiktok content/research, sensory/webcam/mic, pollinations/comfyui, voice journal) kun grep-dækket.

## Metode-note

Prioritér efter **EVENT-FAMILY**, ikke fil/komponent (dedup-naturligt). Man wirer `cognitive_state` ÉN gang og
tænder ~59 signaler — ikke 21 engines. Skeln skarpt mellem **liveness-observe** (daemon KØRTE) og
**indhold-observe** (HVAD den producerede) — for LivingNeuron er det forskellen på en puls og en tanke.

Cartografens dark-edge-definition (manglende surface) ≠ agenternes "ikke wired til Central" (manglende observe).
Cartografen under-tæller inner-life-dark og over-tæller state-utilities; den ægte inner-life-luke måles bedst på
event-family-listen. Se [[reference_central_publish_recursion]], docs/notes/2026-07-01-cartographer-to-central.md.
