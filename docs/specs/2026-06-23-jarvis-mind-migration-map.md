# Jarvis Mind — MC-migrations-dæknings-kontrakt

**Formål:** flytte ALT Mission Control (MC) viser i dag til en ny, overskuelig **Jarvis Mind**-
menu (owner-only, i jarvis-desk cowork mode), og FØRST DEREFTER udfase det gamle MC.

## Jernreglen
**Intet i MC deaktiveres før den tilsvarende række her er `✅ verificeret` af Bjørn.**
MC bliver stående som fuld backup indtil hele tabellen er grøn. Status-koder:
`□` ikke startet · `◑` bygget, ikke verificeret · `✅` verificeret af Bjørn.

## Load-problemet (løses i Jarvis Mind fra start)
To uafhængige årsager:
1. **Hver poll genbygger 70 cognitive surfaces friskt** — `build_cognitive_architecture_surface()`
   → `_build_cognitive_surfaces()` UDEN cache. Server-dyrt selv ved én poll/60s.
   → **Fix:** cache surfaces (TTL ~30-60s) via eksisterende `get_timed_runtime_surface`;
     heartbeat-tikket refresher cachen. Gør enhver poll billig.
2. **UI poller konstant også når den ikke vises.**
   → **Fix:** Jarvis Mind poller KUN mens den er åben+synlig (Page Visibility API + panel-open).

## Slutbillede
MC (apps/ui React-app) skrumper til sidst til et simpelt webchat-interface for Jarvis;
al owner-observability/-kontrol bor i Jarvis Mind i desk.

---

## DEL A — MC-tabs → Jarvis Mind (dæknings-tabel)

15 top-tabs (flere er wrappers med sub-tabs → ~25 views). Kilde: `apps/ui/src/components/
mission-control/` + `MCTabBar.jsx` + `lib/adapters.js`.

| MC-view | Viser | Endpoints | Jarvis Mind-hjem | Status |
|---|---|---|---|---|
| Overview | aktive runs, events, approvals-kø, valgt model | `/mc/overview` `/mc/approvals` `/mc/events` `/mc/runs` `/mc/main-agent-selection` | Jarvis Mind › Oversigt | ◑ (rå /mc/overview vist; pæn projektion mangler) |
| Ops › Operations | runs/sessioner/approvals/tool-intent/thought-proposals | `/mc/operations` `/mc/tool-intent` | — | □ |
| Ops › Agents | runtime-agenter: spawn/besked/schedule/run-due/peer | `/mc/agents` (+ `/mc/agents/{id}/*`) | — | □ |
| Observability | event-timeline + cost-feed pr. family | `/mc/events` `/mc/costs` `/mc/operations` | — | □ |
| Mind › Consciousness (LivingMindTab) | indre stemme, somatik, mood, alle private-lag-signaler | `getMissionControlJarvis` (~33 endpoints, se Del C) | — | □ |
| Mind › Soul (SoulTab) | SOUL/identitet | `/mc/cognitive-architecture`-surfaces | — | □ |
| Mind › Cognitive (CognitiveStateTab) | kognitiv arkitektur + state-injektion | `/mc/cognitive-architecture` `/mc/cognitive-state-injection` | Jarvis Mind › Sind | ◑ (70 surfaces som grid; state-injektion mangler) |
| Agency Map | hele agentur-inventaret (loops/agenter/kanaler) | `/mc/agency-map` | — | □ |
| Proprioception | kropslig selv-sansning | surface `proprioception_metrics` | — | □ |
| Threads | tværsessions-tråde | surface `cross_session_threads` | — | □ |
| Memory | søgbar hukommelse + scope-filtre | `/mc/memory` | — | □ |
| Council | council/swarm: spawn/runder/config/beskeder | `/mc/council` (+ council-config/runtime) | — | □ |
| Relationship | relations-tekstur Bjørn↔Jarvis | `/mc/cognitive-architecture` (relationship) | — | □ |
| Reflection › Self-Review | selvreview-signaler/records/runs/outcomes | `sections.jarvis` | — | □ |
| Reflection › Development | udviklingsfokus + ~40 development-signaler | `sections.jarvis` | — | □ |
| Reflection › Continuity | visible-kapabilitets-kontinuitet + retained memory | `sections.jarvis` | — | □ |
| Skills | skills-katalog + skill-contract-registry | `/mc/skills` | — | □ |
| Cheap Balancer | balancer-slots/pool/agentic-guards/tool-router | `/mc/cheap-balancer-state` `/mc/agentic-guards-state` `/mc/tool-router-state` ⚠separat router | — | □ |
| Hardening | sikkerheds-/hærdnings-status | `/mc/hardening` | — | □ |
| Lab | eksperimenter + toggles | `/mc/lab` `/mc/experiments` | — | □ |

**Parkerede komponentfiler (ikke i MCTabBar i dag — afgør om de skal med):**
`AutonomyTab.jsx` (`/mc/autonomy/proposals`), `GovernanceTab.jsx`, `CostTab.jsx`.

---

## DEL B — Backend /mc/*-endpoints (≈190)

`routes/mission_control.py` (~140 routes) + `routes/mission_control_living_mind.py` (24 routes)
+ cheap-balancer/tool-router i SEPARAT router (verificér ved migration).

**Kerne/ops:** `/liveness /overview /events /costs /runs /approvals /operations /jarvis
/runtime /memory-pipeline /visible-execution /private-brain /runtime-contract /heartbeat
/heartbeat/tick /emotional-memory /emotion-concepts /embodied-state /affective-meta-state`

**Autonomi/initiativer:** `/autonomy/proposals (+approve/reject) /initiatives (+approve/reject)
/life-projects (+abandon)`

**Kognition/indre lag:** `/cognitive-frame /attention-budget /conflict-resolution
/self-code-changes /self-deception-guard /witness-daemon /inner-voice-daemon /internal-cadence
/emergent-signals /self-knowledge /runtime-self-model /self-critique /creative-journal
/finitude /dream-distillation /unconscious-temperature-field /experiential-runtime-context
/epistemic-runtime-state /loop-runtime /idle-consolidation /dream-articulation /prompt-evolution
/dream-influence /adaptive-planner /adaptive-reasoning /guided-learning /adaptive-learning
/self-system-code-awareness`

**Agenter/council/swarm:** `/subagent-ecology /council-runtime /agents (+/{id}/messages|runs|
tool-calls) /watcher-lineage /agent-lineage /council-model-config /council-activation-config
/council (+/{id}/messages) /runtime/agents/* /runtime/council/* /runtime/swarm/*`

**Tool-intent/approvals:** `/tool-intent (+approve/deny) /approval-feedback
/runtime-contract/candidates/{id}/(approve|reject|apply) /workspace-capabilities/{id}/invoke
/capability-approval-requests/{id}/(approve|execute) /development-focus/{id}/complete`

**Model/provider:** `/main-agent-selection (GET/PUT) /ollama-models /provider-models`

**Cognitive-architecture surfaces (≈75 routes, hver returnerer 1 navngiven surface):**
`/cognitive-state-injection /personality-vector /taste-profile /chronicle /relationship-texture
/compass /rhythm /habits /shared-language /mirror /silence-signals /decisions /counterfactuals
/paradoxes /aesthetics /gut /seeds /procedures /temporal-context /negotiations /forgetting-curve
/conversation-rhythm /self-experiments /anticipatory-context /contract-evolution /dream-carry-over
/apophenia-guard /user-emotional-resonance /experiential-memories /living-heartbeat-cycle
/absence-awareness /flow-state /cross-signal-patterns /self-surprises /narrative-identity
/gratitude /boundary-model /emergent-goals /jarvis-agenda /boredom /formed-values
/user-mental-model /self-compassion /regret /rupture-repair /silence-patterns /blind-spots
/dream-hypotheses /decisions-journal /epistemics /emotional-controls /mood-dialer
/self-review-unified /habits-pipeline /paradoxes-capture /shared-language-extended
/procedure-bank-pipeline /negotiation-pipeline /reflection-to-plan /missions-pipeline
/deep-analyzer /session-continuity /personal-project /learning-curriculum /cadence-producers
/idle-thinking /recurrence-state /global-workspace /layer-tensions /meta-cognition
/attention-profile /cognitive-core-experiments /living-executive`

**living_mind-router:** `/body-state /surprise-state /taste-state /irony-state /thought-stream
/thought-proposals (+/{id}/resolve) /experienced-time /development-narrative /existential-wonder
/dream-insights /code-aesthetic /user-model /memory-decay (+/hold-fast/{id}) /desires
/absence-state /creative-drift /curiosity-state /meta-reflection /conflict-signal
/reflection-cycle /layer-tensions /dream-motifs`

**Tab-aggregater:** `/agency-map /skills /memory /hardening /lab`

---

## DEL C — De 70 cognitive surfaces

`_build_cognitive_surfaces()` i `core/services/heartbeat_runtime.py:562-1137`:

```
personality_vector taste_profile chronicle relationship_texture compass rhythm habits gut
forgetting_curve self_experiments dream_carry_over life_phase learning_curriculum
continuity_kernel dream_continuum initiative_accumulator boredom_curiosity_bridge mirror
paradox_tracker experiential_memory seeds mood_oscillator valence_trajectory
developmental_valence desperation_awareness calm_anchor memory_breathing creative_projects
day_shape_memory avoidance_detector thought_thread skill_contract_registry memory_write_policy
spaced_repetition scheduled_job_windows automation_dsl outcome_learning jobs_engine
prompt_mutation_loop file_watch reboot_awareness proprioception_metrics anticipatory_action
cross_session_threads autonomous_outreach infra_weather temporal_rhythm relation_dynamics
creative_instinct autonomous_work dream_consolidation text_resonance creative_impulse
shadow_scan mortality_awareness relational_warmth collective_pulse action_router
sustained_attention memory_density deep_reflection existential_drift body_memory ghost_networks
parallel_selves temporal_body silence_listener decision_ghosts attention_contour memory_tattoos
```

Alle observeres nu OGSÅ til Centralen (cluster=cognition) via `_safe_surface` (throttlet 5 min).

---

## Åbne beslutninger (Bjørn)
1. Skal `AutonomyTab`/`GovernanceTab`/`CostTab` med (de er parkerede i dag)?
2. Hvilket layout for Jarvis Mind — venstre-menu med sektioner svarende til MC-tabsne?
3. Cheap-balancer-router skal lokaliseres+bekræftes (uden for de to mission_control-filer).
4. Skal nogle MC-surfaces SLÅS SAMMEN i Jarvis Mind (MC er rodet — det er chancen for at rydde op)?

## ARKITEKTUR (Bjørn): Centralen = ÉT ground truth
Jarvis Mind poller IKKE de ~190 MC-endpoints. I stedet er **Centralen samlingspunktet** —
`central_hub.py` projicerer hver sektion fra de eksisterende (cachede) builders (læser, opfinder
ikke en anden sandhed — CLAUDE.md Eventbus Rule). Jarvis Mind = ét live-vindue: `/central/mind`
(index + sektions-data) + `/central/stream` (levende nerve-puls). Stream-when-visible.

## Fremdrift
- ✅ **Dæknings-kontrakt** (dette dokument).
- ✅ **Load-fix:** cache cognitive surfaces (75s TTL) — 431ms→2.5ms pr. poll.
- ✅ **poll/stream-when-visible** (`usePollWhenVisible` + stream lukkes ved unmount).
- ✅ **Central-hub** (`central_hub.py` + `/central/mind`) — ét ground truth, projektions-hub.
- ✅ **Jarvis Mind-skal** i cowork (owner-zone, sub-navbar under header, INGEN ekstra menu).
- ✅ **Streamer fra Centralen** — levende puls (SSE) + avanceret-reveal-toggle pr. fane. Desk 0.2.99.
- ◑ **Sind/Oversigt/Observabilitet** projiceret (ægte); agency/memory/council/skills/reflection/
  lab/hardening = `pending` i hub'en (fyldes ved at tilføje deres builder i `_BUILDERS`).

## Næste skridt
1. Fyld sektionerne én ad gangen fra DEL A-tabellen (Observabilitet/Agentur/Memory/Council/… ).
2. Pr. sektion: byg → Bjørn verificerer mod gammel MC-tab → marker `✅`.
3. Afklar de åbne beslutninger ovenfor (parkerede tabs · oprydning vs 1:1 · cheap-balancer-router).
4. Når hele tabellen er `✅` → deaktivér MC-tabs (behold backend-endpoints Jarvis Mind bruger).
