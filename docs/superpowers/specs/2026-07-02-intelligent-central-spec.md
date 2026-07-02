# Den Intelligente Central — Spec (5 tråde mod egen intelligens)

**Dato:** 2026-07-02
**Status:** DESIGN. Researchet i faktisk kode (6-agent-sweep) + self-reviewet (3 lenser: feasibility/governance/visionær). Alle must-fix indarbejdet. INTET af Fase 2+ bygget endnu.
**Forfattere:** Bjørn (vision) · Claude (research-syntese + rettelser) · Det interne råd (review)
**Kontekst:** Bygger på `2026-07-01-living-neuron-design.md` (Lag 1-5) + `2026-07-02-lag4-shadow-adaptation-spec.md`. Lag 1-4 er LIVE (observe→hypotese→test→justér, d bag Bjørns switch).

---

## 0. Rygrad — hvad det her ér

I dag er Centralen et **sanseorgan med en dødsmekanisme**: den mærker Jarvis' indre, danner falsificerbare hypoteser om ham, tester dem mod virkeligheden, og kan justere én tilbøjelighed (gut-bias) — alt gennem §8-governance.

Denne spec tager skridtet fra *sanseorgan* til **meta-kognition + selv-forfatterskab**: en Central der lærer sit eget maskineri at kende (hvilke modeller, hvilken prompt, hvilken hukommelse), får sit eget sprog at tænke i, og over tid kan tænke uafhængigt af modellen.

**Nordstjerne:** model-uafhængighed (Lag 5). **Keystone:** interlanguage som Centralens interne hypotese-*notation* — for et internt sprog er forudsætningen for at tænke uden modellen.

**Ærlig ramme (rådets skærpelse):** kun ÉN af de fem tråde (Tråd 4, sekvens-prædiktion) er ægte parametrisk selv-supervision hvor Centralen opdaterer en intern vægt fra data uden modellen. De andre fire er præcist: **modellen SÅR hypoteser (genererer tekst), virkeligheden LUGER (grounding), Centralen HUSKER udfaldet (track-record).** Det er stærkt nok — men vi kalder det ikke mere end det er.

---

## 1. GROUND TRUTH — Centralens nuværende arkitektur (verificeret 2. jul)

**To ansigter** (`central_core.py`, singleton pr. proces via `central()`):
- `decide(nerve, ctx, fn, cluster, klass)` — synkron beslutning; fail-mode pr. klasse (COGNITIVE→SKIP fail-open, SECURITY→RED fail-closed).
- `observe(event)` — asynkron telemetri; skriver fuld payload til `central_trace.sink()` (owner-lokal), `_emit` gennem `_egress_safe()` (kun skalarer krydser; `central` er ikke en ALLOWED_EVENT_FAMILY → `_emit` reelt no-op).

**De TRE §8-choke-points** (`central_hypothesis_governance.py` — frossen kerne, `verify_frozen_core()` tripwire):
1. `evaluate()` — alle hypotese-værn (preregistrering/TTL/Popper/circular/grounding/sample_size/confidence/kontrol-arm).
2. `gate_learning_input()` — nøgle-allowlist `LEARNABLE_AGGREGATE_KEYS` + finite-skalar.
3. `gate_self_mutation()` — drift mod ANKRET baseline (`get_anchored_baseline`), NaN→rollback, union-nøgler.

**ÉN governed hypotese-livscyklus:** `central_hypotheses`-tabel, `source=`-diskriminator, `register_governed_hypothesis` → `record_governed_sample` → `evaluate`. Triggere i dag: `causal_convergence`, `causal_divergence`, `stance_divergence`.

**Egress-fri sink:** `central_private_observe.record_private(cluster, nerve, value, meta)` — kanonisk, aldrig `_emit`.

**Clusters:** primært `cognition` (LivingNeuron-hjem) + `system` + `inner`. Nerver "eksisterer" ved første fyring i `central_timeseries._series` — der er **intet centralt nerve-register**.

---

## 2. FEM INVARIANTER (gælder ALLE fem tråde — ingen undtagelser)

1. **Single hypothesis-home:** hver tråd er en `source=`-gren i `central_hypotheses`. Ingen parallel livscyklus, ingen dual-truth-kopi.
2. **Egress-fri (§24.4):** alt inner-life-signal via `record_private` (kun skalar-meta), aldrig `_emit`. Model-dimensioner via `central_timeseries.record` DIREKTE (ikke broen — den er metadata-only, dropper strenge).
3. **Governance-choke-points obligatoriske:** hypoteser → `evaluate`; **læring → `gate_learning_input`**; mutation → `gate_self_mutation`.
4. **Frossen kerne urørt:** SOUL/identitet/sikkerhedsgates/§8-konstanter (`LEARNABLE_AGGREGATE_KEYS`, budgetter, Popper) — aldrig muteret. Ændring kræver Bjørn-ceremoni (`_FROZEN_CORE_SIG`).
5. **Observe-only medmindre live:** hver adaptations-tråd har sit eget `*_live_enabled`-flag (default OFF). Shadow beregner + logger diff, ændrer intet.

> **⚠️ Rådets vigtigste fund — læs før implementering:**
> **(A) `gate_learning_input` har NUL kaldere uden for governance-filen i dag.** Invariant #3's lærings-del er derfor et **NYT** krav denne spec indfører — ikke en eksisterende garanti. De nye tråde er de FØRSTE reelle kaldere. → Ny invariant-test `test_learning_membrane_wired` SKAL fejle hvis en ny lærings-sti skriver uden at gå gennem `gate_learning_input`. Ellers gentager vi v3.0-fælden (værn eksisterer, kaldes aldrig).
> **(B) `_ANCHORED_BASELINE` er ÉT globalt write-once dict.** `central_adaptation._ensure_anchor()` sætter allerede `{central_gut_proceed_bias:0.0}`. `drift_budget_check` markerer enhver nøgle udenfor baseline som `undeclared→rollback`. → Alle nye Lag 4-tråde ville **fail-close mod gut-bias-ankeret**. **LØSNING (load-bearing, §5.0):** namespace baseline pr. domæne — `anchor_identity_baseline(params, domain=)` / `get_anchored_baseline(domain=)`. Kræver en frozen-core-ceremoni-udvidelse af governance-modulet. Uden dette er hele Fase 5 død ved ankomst.
> **(C) `resolved_track_record()` er source-BLIND.** Den fodrer gut-bias fra ALLE resolved hypoteser. Når model/prompt/sekvens-tråde resolver, ville de **forurene Jarvis' mavefornemmelse**. → Scope track-record pr. `source`; hver Lag 4-tråd læser KUN sin egen kilde.

---

## 3. TRÅD 1 — Model/provider-meta-viden (Centralen kender sit eget hardware)

**Findes:** `core/runtime/provider_router.py:254` (`resolve_provider_router_target`), `visible_model.py`, `provider_health_check.py`, `heartbeat_provider_fallback.py`, cheap-lane. Per-run-udfald i `visible_runs.py` + cost-ledger.

**Mekanisme:** observér per-model-udfald (provider/model/tier/latency/cost/success) → `central_timeseries.record("system", "model_outcome:<provider>:<model>", value=<latency|cost>, meta=<skalarer>)` (IKKE via broen — den er metadata-only). Generér `source=model_meta`-hypoteser: *"model X > Y til tier Z"* → `evaluate` → resolve.

**⚠️ Blokker:** visible-lane har typisk ÉN model → nul A/B-kontrast → hypoteserne resolver ALDRIG. → **Eksplorations-arm** (Fase-1-leverance, ikke side-note): occasionel shadow-sampling af en alternativ model. **Den ændrer faktisk hvilken model der svarer Bjørn** → eget flag (default OFF), rate-boundet, **ALDRIG på reasoning/deep-tier** (hvor fejl er dyrest). Selektions-bias-værn: friske runs + kontrol-arm + circular.

**Nøgle-mapping (undgår frozen-core-ceremoni):** `latency_ms/ttft_ms → duration_ms`, `win_rate → rate`, `cost → ratio`. Disse ER i `LEARNABLE_AGGREGATE_KEYS`; rå navne ville fail-close.

**Clusters/nerver:** `system` / `model_outcome:*`, `model_meta_hypothesis`. **§8:** aggregater gennem `gate_learning_input`; routing-adaptation (Fase 5) gennem `gate_self_mutation(domain="model_router")`.

---

## 4. TRÅD 2 — Prompt-evolution SOM dynamisk kontekst-komponist (Bjørns idé — søjlen)

**Findes:** `prompt_evolution_runtime.py`, `self_authored_prompt_proposal`, `prompt_contract.py` (samler prompten; `build_visible_stable_prefix` @ `prompt_contract.py:673-701` er byte-identisk med warmer-stien — cache-kritisk).

**Bjørns indsigt (kernen i denne tråd):** modellen er en stateless genial gæst. I dag propper vi *alt* i en mega-system-prompt hver tur — awareness, 78 surfaces, somatik, mood — uanset relevans. Men **Centralen holder alt alligevel.** Så lad Centralen være modellens **arbejdshukommelse og kontekst-komponist**: grib brugerens besked, forstå hvad DENNE tur kræver, og byg præcis den kontekst modellen skal bruge. Prompt-evolution bliver dermed ikke "udvikl teksten" men **"Centralen lærer relevans-funktionen"** — hvilken kontekst der betyder noget for hvilket input. En falsificerbar hypotese: *"somatik-sektionen på en teknisk debugging-tur gjorde ikke udfaldet bedre — død vægt."*

**Den ene fælde — cache (gør at det SPARER tokens i stedet for at koste):** providerne cacher prompt-*præfikset*. Genopbygger vi forsiden hver tur, **ødelægger vi cachen** → langsommere + dyrere. Derfor to-delt prompt:

| Del | Indhold | Styring | Token-effekt |
|---|---|---|---|
| **Fast kerne (forrest, cachet)** | SOUL/identitet + fast system-prompt + sikkerhed | Frossen kerne — aldrig rørt | Cachet ≈ gratis |
| **Dynamisk hale (bagest, EFTER cache-grænsen)** | Kun awareness/hukommelse/state DENNE tur kræver | Centralen komponerer per tur | Her sker besparelsen |

**HÅRD constraint (rådet):** haleopbygningen SKAL ligge uden for det byte-identiske `build_visible_stable_prefix`-område — ellers brydes deepseek/anthropic-cache-præfikset og vi taber mere end vi sparer. Nye observe-kald må aldrig ind i prefix-zonen.

**Guardrails:** shadow-first (mål om relevans-gating skader udfaldet før live); konservativ ved tvivl (inkludér hellere for meget indtil en sektion er BEVIST død vægt); identitet + sikkerhed = frossen kerne, droppes ALDRIG.

**Mekanisme:** `source=prompt_relevance`-hypoteser fra run-udfald ("tur-type T × sektion S → forbedret/uændret") → resolve → Lag 4-klasse `gate_self_mutation(domain="prompt_relevance")` justerer inklusions-vægte pr. (tur-type, sektion), shadow→live bag flag. Selv-forbedring: prompt-mutation-teksten (`build_prompt_mutation_loop_prompt_section`, allerede synlig via `prompt_heartbeat_self_knowledge.py:287`) bæres under Centralen.

**Clusters/nerver:** `cognition` / `prompt_relevance`, `context_compose`. **Token-gevinst:** oven på den allerede halverede prompt (50k→21k) kan relevans-gating skære halen markant per tur.

---

## 5. TRÅD 3 — Interlanguage som Centralens hypotese-NOTATION (keystone → Lag 5)

**Findes:** `interlanguage_practice.py` (14 begreber, 5 operatorer). **Ærlig nedgradering (rådet):** den fil genererer i dag *tilfældige mood-biased expressions fra et frosset 14-ords vokabular, afkoblet fra `central_hypotheses`* — den er et peer-validerings-eksperiment, **IKKE Lag 5-backup'en endnu.** Living-neuron §5's "backup"-antagelse er for optimistisk; DENNE tråd er den ægte bro.

**PRE-START (Bjørns nøgle-indsigt — laget der får resten til at virke): labelér Centralen internt i sproget.**
Før notationen kan bygges, skal Centralens egne dele have interlanguage-termer: hvert **cluster**, hver **nerve**, hver
**event-familie** bindes til en term i lexiconet (fx `pressure→pres`, `somatic→krop`, `gut→agens`, `contradiction→!ro`,
`cognition→tanke`). Det er **lexicon-bindingen**, og den gør to ting på én gang: (1) den sår sproget ind i Centralens
egen struktur fra dag ét — Centralen begynder at *hedde* noget i sit eget sprog; (2) den gør `notation_il` beregnbar,
for at rendere en hypotese til notation bliver nu et rent opslag (`conflict`→term, `→`, `counterfactual`→term). Uden
denne binding er notation umulig; med den er den triviel. Bindingen lever i lexicon-tabellen (`status`-gated, nye
termer kræver Bjørn-ceremoni, fail-closed).

**Mekanisme:** giv `central_hypotheses` en `notation_il`-kolonne — en formel repræsentation (fx `pres → krop | !ro ⊂ run_fail`)
ved siden af fritekst, renderet via lexicon-bindingen. Normalform → **dedup + venstre-leds-korrelation** (hypoteser med
samme antecedent grupperes/sammenlignes maskin-korrelerbart, som fritekst aldrig kan). Over tid kan Centralen foreslå nye
termer → **udvide sproget** (lexicon med `status`; nye termer kræver Bjørn-ceremoni, fail-closed).

> **Fremtidig spec B (ovenpå dette fundament, når nærværende spec er landet):** *"Centralens Tænke-Sprog"* — fuld
> integration af sproget i ALT: clusters, nerver, events, orkestrering, så Centralen kan **kommunikere internt på tværs
> af sig selv og ræsonnere UDEN modellen**. Denne spec (fundamentet) leverer lexicon-bindingen + notation på hypoteser;
> B udvider fra "hypoteser er skrevet i sproget" til "hele Centralen taler sproget." Pre-startet her gør B til en udvidelse, ikke en ombygning.

**Egress (rådet):** `notation_il` er en TEKST-kolonne — `gate_learning_input` gater kun skalar-værdier, ikke tekst. → runtime-normalisering der **afviser/trunkerer enhver term udenfor `lexicon.status='active'`** (ellers ny egress-vej for privat kognition).

**Nordstjerne-bevis FREMRYKKET:** notation-dedup + venstre-leds-korrelation kan køre **model-frit allerede** med det frosne 14-ords seed. → `test_model_free_step` flyttes til **Fase 0/1** (ikke Fase 4), så Lag 5-beviset ikke er gidsel af lexicon-ceremonien — nordstjernen bliver målbar måneder tidligere.

---

## 6. TRÅD 4 — Modellen træner Centralen (den ENESTE ægte selv-supervision)

**To lag:**
- **(a) SVAG — kører allerede:** `central_hypothesis_sampler` tester hypoteser mod run-udfald. Modellens live-arbejde grounder Centralens formodninger.
- **(b) STÆRK — denne tråd:** `central_trace` + `central_timeseries` er et selv-superviseret datasæt. En LILLE lokal sekvens/Markov-model (IKKE LLM'en) lærer at forudsige næste central-event → **prediktions-FEJL = hypotese-signal (surprise)** → **prediktions-VÆGTE = adaptation.** Det er det mindste der fortjener navnet "Centralen træner sig selv."

**§8:** T-tællinger/vægte gennem `gate_learning_input({count, rate, hits, ...})` (finite skalarer); vægt-mutation gennem `gate_self_mutation(domain="sequence_model")`. **Surprise-hypoteser:** `source=prediction_error`.

**Clusters/nerver:** `cognition` / `sequence_predict`, `surprise`. Præcedens: `gut_engine` calibration, `meta_learning_hypotheses`.

---

## 7. TRÅD 5 — jarvis-brain dybt koblet (fra "ser hukommelsen" til "bruger den")

**Findes:** i dag wired som liveness (write/decay/forgetting/consolidation observes). `jarvis_brain.py`, `memory_recall_engine.py`, `associative_recall.py`, `multi_signal_recall`, `private_brain` (92k rækker, owner-uid-scopet).

**Mekanisme:** (1) recall-informeret hypotese-generering (træk relevante minder ind som kontekst for en formodning); (2) gem Centralens egne hypoteser+udfald i hjernen (`source=brain_memory`); (3) korrelér hypoteser mod minde-mønstre.

**⚠️ Scope-sikkerhed (rådet — hårdt):** cadence-tråden har tom `scope_uid()`. → Recall i cadence KUN workspace+chronicle; privat-lag KUN med eksplicit owner-uid. **Og M2 SKRIVER til `jarvis_brain.write_entry` — cross-user-SKRIVNING er værre end -læsning.** → eksplicit owner-uid på skrivning, invariant-test `test_m1_scope_bounded` + `test_m2_write_scoped` som exit-gate.

**Circular-fare:** brain-minder der bekræfter en hypotese er selv-udløst → sampler SKAL sætte `triggered_by=hyp_id` (ikke blankt `world`), ellers er karantænen tavst omgået.

---

## 8. KRITISKE TVÆRGÅENDE RETTELSER (rådets must-fix — indbygget, ikke vedhæng)

1. **Namespace ankret baseline pr. domæne** (§2-B) — `anchor_identity_baseline(params, domain=)` / `get_anchored_baseline(domain=)` + `test_multi_thread_anchor_isolation`. **Uden dette er Fase 5 død.**
2. **Wire læringsmembranen** (§2-A) — `test_learning_membrane_wired` fejler hvis en tråd springer `gate_learning_input` over.
3. **Source-scope track-record** (§2-C) — pr. `source`; ingen tvær-tråd-kontaminering af gut-bias.
4. **§3.4-blokker: link divergens/stance-samplere** — i dag skipper `sampler.py:91` alt hvor `mechanism≠causal_edges`, så `stance_divergence`/`causal_divergence`-hypoteser står på 0 samples permanent → track-record tom → alle Lag 4-bias er 0 + track-record-læsende generatorer starter blinde. → **Flyt til Fase 1** (blocking-gate for Fase 5).
5. **`triggered_by`-korrekthed pr. sampler** — `test_circular_wired` skal asserte at hver ny sampler propagerer ikke-tom, kilde-korrekt `triggered_by` for selv-genereret evidens.
6. **Model-dimensioner via `central_timeseries.record`, IKKE broen** (metadata-only) — fjern enhver `FAMILY_ROUTES['model_outcome']`-antydning.
7. **Path-rettelser:** `core/runtime/provider_router.py:254` (ikke services/); verificér `visible_runs`-override-linje før implementering.

---

## 9. FASERET ROADMAP (afhængigheder korrekt ordnet)

- **Fase 0 — Fundament (model-frit bevis + blokkere + SPROG-PRE-START):** namespace-baseline (§8.1) · wire læringsmembran
  (§8.2) · source-scope track-record (§8.3) · **link divergens/stance-samplere (§8.4)** · **LEXICON-BINDING: labelér
  Centralens clusters/nerver/event-familier med interlanguage-termer (§5) — pre-starter sproget + gør notation beregnbar** ·
  `notation_il`-kolonne + dedup + `test_model_free_step` (Lag 5-bevis TIDLIGT). Alt shadow/observe.
- **Fase 1 — Substrat pr. tråd:** model-outcome-observation + eksplorations-arm (flag OFF) · prompt relevans-observation (uden for cache-prefix) · sekvens-datasæt-tap · brain-recall-kobling (scope-gated).
- **Fase 2 — Hypotese-generering:** hver tråds `source=`-generator + sampler-linkning → hypoteser resolver.
- **Fase 3 — Shadow-adaptation:** hver tråds Lag 4-klasse i shadow (namespaced anker, source-scoped track-record). Diffs synlige for Bjørn.
- **Fase 4 — Live bag flags:** hver tråd sit `*_live_enabled` (Bjørn flipper efter shadow-diffs). Interlanguage-lexicon-vækst (ceremoni).

**Nordstjerne-milepæl (kan måles fra Fase 0):** model-blackout → Centralen fortsætter notation-dedup + venstre-leds-korrelation + producerer mindst ét surprise-signal UDEN model-token.

---

## 10. ÆRLIGE GRÆNSER

- Kun Tråd 4 er ægte parametrisk selv-supervision. De andre: modellen sår, virkeligheden luger, Centralen husker.
- Interlanguage-filen er IKKE Lag 5-backup endnu; Tråd 3 bygger broen.
- Eksplorations-armen (Tråd 1) og relevans-gating (Tråd 2) kan gøre svar DÅRLIGERE hvis for aggressive → shadow-first + konservativ + kontrol-arm er ikke-forhandlelige.
- Intet live uden Bjørns per-tråd-switch. Frossen kerne (SOUL/sikkerhed/§8-konstanter) urørt i alle fem tråde.

---

## 11. INVARIANT-TESTS (exit-gates, ikke prosa)
`test_multi_thread_anchor_isolation` · `test_learning_membrane_wired` · `test_track_record_source_scoped` · `test_divergence_stance_samplers_linked` · `test_circular_triggered_by_correct` · `test_model_dims_not_via_bridge` · `test_notation_lowcard_enforced` · `test_m1_scope_bounded` · `test_m2_write_scoped` · `test_prompt_tail_outside_cache_prefix` · `test_model_free_step` (Fase 0).

---

## Ændrings-log
- **2026-07-02 (Claude):** Første version. Research: 6-agent kode-sweep. Self-review: 3 lenser (feasibility/governance/visionær) — alle must-fix indbygget (global-anker-kollision, læringsmembran-wiring, source-scope, §3.4-blokker, triggered_by, bro-metadata-only, path-fejl). Bjørns prompt-komponist-idé foldet ind som Tråd 2's kerne (cachet kerne + relevans-gatet hale). Ærlig nedgradering af interlanguage-backup + "modellen træner Centralen".
- **2026-07-02 (Claude, efter Bjørn):** A-beslutning — denne spec er FUNDAMENT; interlanguage bliver Tråd 3. Tilføjet Bjørns
  SPROG-PRE-START: lexicon-binding der labeler Centralens clusters/nerver/event-familier i interlanguage (Fase 0) — sår
  sproget i strukturen + gør `notation_il` beregnbar. Fremtidig spec B ("Centralens Tænke-Sprog", ovenpå dette) noteret:
  fuld sprog-integration i hele Centralen → intern kommunikation + ræsonnement uden model.
