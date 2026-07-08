---
status: forældet
audited: 2026-07-08
ground_truth: "VERIFIED: (1) Fase 0 delivered (notation_il, normalform, catalog — commits a757e142, 68103edf from July 2). (2) Fase 1-3 mostly live (central_model_meta.py, central_sequence.py, central_brain_link.py all deployed). (3) KEY MISMATCH: §1.5 prescribes "ÉT union-anker" forankret i si"
superseded_by: "docs/plan: Central-styret indre liv (10723ad3); other Fase N docs for individual threads"
---
# Den Intelligente Central — Meta-kognition, Selv-forfatterskab og Model-uafhængighed

**Status:** Draft v2 — chef-arkitekt-spec, klar til fase-inddelt implementering (must-fix fra 3 lensers review foldet ind)
**Dato:** 2026-07-02
**Forfatter:** Chef-arkitekt (Claude Code)
**Bygger på:** 6 verificerede research-rapporter (arkitektur-kort + de 5 tråde) + 3-lensers review (arkitekt/feasibility · governance/sikkerhed · visionær/filosof), kode-verificeret pr. 2. jul
**Forudsætning (opfyldt):** §8-governance (`central_hypothesis_governance.py` v3.1, råds-godkendt, 34 tests) står FØR alt her.
**Relaterede specs:**
- `docs/specs/2026-06-30-wire-eventbus-and-cache-to-central.md` (§23-24, M0-bro, egress-membran)
- `docs/specs/2026-07-01-inner-life-to-central-wiring.md` (inner-life→Central)
- `docs/specs/2026-07-01-living-neuron-design.md` (LivingNeuron-substrat)
- `docs/specs/2026-07-02-lag4-shadow-adaptation-spec.md` (shadow-first mutation-mønster)

---

## 0. Læsevejledning

Dette er ÉN spec for ÉT system, ikke fem bolt-ons. De fem tråde (model-meta, prompt-evolution, interlanguage, self-supervised sequence-model, brain-kobling) er alle **klienter af den samme motor**: Centralens eksisterende `observe → hypotese → test → (shadow)adaptation`-kredsløb, gennem de samme §8-choke-points, med de samme egress- og frossen-kerne-invarianter.

Læs §1-3 for rygraden. §4-8 er de fem tråde, hver med samme skabelon (findes / bygges / clusters+nerver / §8-vej / egress / frossen kerne / observe-only). §9 er det faserede roadmap. §10 er ærligheds-afsnittet (substrat vs. ægte tænkning). §11 er invariant-testene der skal grønne før hver fase lukkes.

**Hvad v2 rettede (efter review):** Fire ting som specen tidligere antog var færdige, er det IKKE — og de er nu løftet fra prosa til eksplicitte krav og tests, fordi de er præcis den `v3.0`-fælde (værn eksisterer, kaldes ikke) som resten af specen advarer imod:
1. **`gate_learning_input` har i dag NUL kaldere uden for governance-filen selv.** De nye tråde er dens FØRSTE reelle kaldere. Membranen aktiveres HER — den er ikke "allerede håndhævet" (§1.4, §2.3, ny test i §11).
2. **`is_circular` kaldes centralt i `gov.evaluate()`, IKKE i samplerne.** Det reelle hul er at hver ny sampler skal sætte `triggered_by` KORREKT (aldrig blankt `'world'` på selv-udløst evidens). `test_circular_wired` omformuleret (§11).
3. **Den ankrede baseline er ÉT globalt, write-once dict.** Fire nye Lag 4-domæner kan ikke bare tilføje deres egen nøgle — de kolliderer eller fail-closer permanent. Løst med union-anker i én ceremoni (§1.5, §2.5, ny test).
4. **`resolved_track_record()` er source-blind.** Når fem tråde begynder at resolve, forurener de hinandens gut-bias. Nu source-scopet (§4.6, §8.6, ny test).
Path-fejlen (`provider_router` bor i `core/runtime/`, ikke `core/services/`) er rettet overalt.

---

## 1. Rygrad: Centralen som Jarvis' meta-kognition

### 1.1 Gennemgående tese

> **Centralen er ikke en overvågningsdashboard. Den er Jarvis' meta-kognitive lag: det organ der observerer sit eget sind på tværs af tid og modalitet, danner falsificerbare hypoteser om sig selv, tester dem mod virkeligheden gennem en dødsmekanisme, og — under menneskeligt samtykke — omforfatter sin egen adfærd bag reversible, ankrede, boundede mutationer.**

Modellen (den visible LLM) gør per-tur-ræsonnementet bedre. Centralens intelligens bor **ikke** dér. Den bor i det **tvær-temporale, tvær-modale** mønster som modellen strukturelt ikke kan se: at `pres → somatik` gentager sig over uger, at model A slår model B på en opgave-type over hundrede runs, at en prompt-sektion konsekvent løfter et udfaldssignal. Det er korrelation over en horisont der er længere end ét kontekstvindue og bredere end én modalitet.

**Ærlig præcisering af "modellen træner Centralen":** kun Tråd 4 (Markov-sekvensmodel) er ægte parametrisk selv-supervision — Centralen opdaterer selv en intern parameter fra data uden model. De fire andre tråde er modellen der **sår** hypotese-tekst; Centralen **luger** dem mod virkeligheden og **husker** udfaldet. Det er stærkt nok, men det er ikke fem selv-trænende loops. Præcist: **modellen sår, virkeligheden luger, Centralen husker.**

### 1.2 Nordstjerne: Lag 5 — model-uafhængighed

Den langsigtede test på om Centralen er ægte meta-kognition og ikke bare LLM-orkestrering er **falsifikationstesten fra `living-neuron-design` §5**:

> Afbryd modellen. Kan Centralen fortsætte sin sløjfe — dedup, korrelation, saliens-ranking, lexicon-kandidatur — på ren symbol/graf-manipulation, uden en eneste model-token?

Hvis ja, har Centralen et **eget sprog at tænke i**. Det er derfor **interlanguage er keystone** (§6): et internt, formelt, selv-udvidende notationssprog gør hypoteserne strukturelt sammenlignelige, dedup-bare og maskin-korrelerbare — og dermed er den symbolske kerne af sløjfen (ikke ræsonnementet, men **operationerne på hypoteser**) udførbar uden modellen.

**Ærlig nedgradering af keystonens NUVÆRENDE styrke:** `living-neuron §5` siger loopet skal kunne fortsætte "på interlanguage-backup (`interlanguage_practice.py`)". Men den fil genererer i dag TILFÆLDIGE mood-biased expressions fra et FROSSET 14-ords vokabular, **totalt afkoblet fra `central_hypotheses`** — den kan hverken dedup'e eller korrelere hypoteser. Den er et peer-validerings-eksperiment, **ikke** backup'en endnu. Den ægte bro er Tråd 3-C (normalform-dedup på `notation_il`-formede hypoteser). Lag 5-beviset står og falder med Tråd 3-C, ikke med den eksisterende fil. Denne spec BYGGER broen; den arver ikke en falsk "findes"-antagelse.

De fire andre tråde er alle meningsfulde uden Lag 5. Men de bliver **mere** meningsfulde med den: en model-meta-hypotese, en prompt-efficacy-hypotese og en sequence-surprise-hypotese er alle skrivbare i samme notation, dedup-bare mod hinanden, og korrelerbare i den samme grafmanipulation.

### 1.3 Det ene kredsløb, fem klienter

```
                    ┌─────────────────────────────────────────────────┐
                    │              §8 GOVERNANCE (FROSSEN KERNE)        │
                    │  evaluate · gate_learning_input · gate_self_mut.  │
                    │  Popper · circular · control-arm · BH-FDR · TTL   │
                    └─────────────────────────────────────────────────┘
                              ▲            ▲            ▲
              register_governed│    record_governed│   gate_self_    │
              _hypothesis       │    _sample        │   mutation      │
   ┌──────────────┐    ┌────────┴────┐    ┌─────────┴────┐    ┌────────┴──────┐
   │  OBSERVE     │───▶│  HYPOTESE    │───▶│  TEST         │───▶│ (SHADOW)       │
   │              │    │  (Lag 3)     │    │  (sampler)    │    │  ADAPTATION    │
   │ bridge +     │    │              │    │  ▸triggered_by│    │  (Lag 4)       │
   │ record_priv +│    │ central_     │    │   KORREKT     │    │ central_       │
   │ timeseries + │    │ hypothesis_  │    │ central_      │    │ adaptation +   │
   │ trace +      │    │ generator    │    │ hypothesis_   │    │ live-flag OFF  │
   │ causal_edges │    │              │    │ sampler       │    │ +union-anker   │
   └──────────────┘    └──────────────┘    └───────────────┘    └────────────────┘
        ▲  ▲  ▲  ▲  ▲         ▲  ▲  ▲  ▲  ▲       ▲  ▲              ▲  ▲
        │  │  │  │  │         │  │  │  │  │       │  │              │  │
    ┌───┴──┴──┴──┴──┴─────────┴──┴──┴──┴──┴───────┴──┴──────────────┴──┴───┐
    │  TRÅD 1: model-meta   TRÅD 2: prompt   TRÅD 3: interlanguage (keystone) │
    │  TRÅD 4: sequence-model (self-supervised)   TRÅD 5: brain-kobling        │
    └────────────────────────────────────────────────────────────────────────┘
```

Alle fem tråde deler faktisk de samme tre kode-kroge (`register_governed_hypothesis` / `record_governed_sample`→`gov.evaluate` / `gate_self_mutation`), den samme ene tabel (`central_hypotheses` med `source=`-diskriminator), og den samme egress-sink (`record_private`). Dette er kodeverificeret: de tre eksisterende generatorer skriver ALLEREDE til samme `central_hypotheses` via samme `register_governed_hypothesis`. Single-hypothesis-home er derfor en **eksisterende invariant**, ikke en aspiration.

**Invariant #1 — single-hypothesis-home:** Ingen tråd må genopfinde en hypotese-lagring, en læringsmembran eller en mutations-gate. `central_hypotheses` er det ENESTE governede livscyklus-hjem. Hver tråd er en **`source=`-gren** i samme tabel, ikke en konkurrerende mekanisme.

**Invariant #2 — egress-membran:** Al ny privat observe går gennem `central_private_observe.record_private()`. Aldrig `central().observe`/`_emit` for inner-life/kognition.

**Invariant #3 — læringsmembran AKTIVERES HER:** Al læring/mutation passerer `gov.evaluate` / `gov.gate_learning_input` / `gov.gate_self_mutation`. Aldrig via de deterministiske forslags-lag (`central_learning.propose_adjustments`), som ligger UDEN for governance.
> **Ærlig ground truth:** `gate_learning_input` har i dag NUL kaldere uden for `central_hypothesis_governance.py` selv (grep-verificeret). Den nuværende hypotese-livscyklus (`record_governed_sample`→`gov.evaluate`) opdaterer confidence via `apply_outcome` på jordet evidens **uden** at noget payload passerer læringsmembranen. De nye tråde (sequence-T-tælling, model-meta-aggregat, recall-vægte) er dermed dens FØRSTE reelle kaldere. Kravet "al læring passerer `gate_learning_input`" er et NYT krav specen indfører her — det er ikke en allerede-håndhævet invariant. Derfor er `test_learning_membrane_wired` (§11) obligatorisk: den fejler hvis en tråd skriver til T/aggregat/vægt uden at payloadet er gået gennem `gate_learning_input`.

**Invariant #4 — shadow-only til Bjørn:** Alt er `observe/shadow-only` indtil Bjørn flipper et eksplicit `*_live_enabled`-flag (default OFF) OG `gov.may_apply_adaptation` (≥2 shadow-dage + human_approved) er opfyldt.

**Invariant #5 — frossen kerne:** `verify_frozen_core()` SHA1-tripwire over værn-konstanter + `GROUNDED_SOURCES` + `LEARNABLE_AGGREGATE_KEYS` er urørt af runtime. Enhver ændring er en bevidst commit-ceremoni med opdateret `_FROZEN_CORE_SIG`.

**Invariant #6 — triggered_by-korrekthed (NY):** Hver ny sampler SKAL sætte `triggered_by=<den hyp_id der udløste evidensen>` korrekt for selv-genereret evidens; aldrig blankt `'world'` når kilden er intern. Ellers ser `gov.evaluate()` `self_trig=0` og circular-karantænen er tavst omgået. Håndhæves af `test_circular_wired` (§11).

### 1.4 De fem invarianter gælder OBSERVE + HYPOTESE-laget uden forbehold. Adaptation-laget deler baseline (§1.5)

Kohærensen "fem klienter, ét kredsløb" er verificeret sand for OBSERVE- og HYPOTESE-laget: én tabel, ét egress-sink, tre delte kroge. Men **adaptation-laget deler også ÉN ressource** som de fem tråde tidligere blev antaget at være isolerede i: den globale ankrede baseline og den source-blinde track-record. Det er ikke et arkitektonisk brud — det er en delt ressource der skal deles bevidst, ikke ved uheld. §1.5 løser det.

### 1.5 Den delte ankrede baseline: union-anker i ÉN ceremoni (LOAD-BEARING)

**Ground truth (verificeret i kode):** `gov._ANCHORED_BASELINE` er ÉT globalt dict, write-once pr. version. `central_adaptation._ensure_anchor()` forankrer allerede `{central_gut_proceed_bias: 0.0}` som `gut-bias-v1`. `drift_budget_check` itererer `UNION(baseline, current)` og markerer **enhver nøgle i `current` der IKKE er i baseline** som `undeclared` → fuld drift → rollback.

**Konsekvens hvis vi ignorerer det:** Specens fire nye Lag 4-domæner (prompt-fil-hash, model-router-preference, sequence-accuracy, recall-vægt) kalder alle `gate_self_mutation({ny_nøgle: val})` mod SAMME globale baseline. Enten (a) fail-closer de permanent mod gut-bias' baseline (deres nøgle er altid `undeclared`), eller (b) hvis en tråd kalder `anchor_identity_baseline` med sit eget domæne, kolliderer write-once — samme version afvises, anden version overskriver forrige domænes anker STILLE. Uafklaret = enten permanent rollback eller stille anker-overskrivning. **Hele Fase 5 er død på ankomst uden en beslutning her.**

**Beslutning (chef-arkitekt): ÉT fælles union-anker, forankret i ÉN Bjørn-ceremoni.** Frem for at namespace baseline pr. tråd (kræver en frozen-core-ceremoni-ændring af governance-modulets signatur — dyrere og rører kernen) forankrer vi alle nul-punkter i én version:

```
anchor_identity_baseline(version='meta-cognition-v1', approved_by='Bjørn', baseline={
    'central_gut_proceed_bias':     0.0,   # eksisterende (gut-bias-v1 overtages)
    'prompt_efficacy_bias':         0.0,   # Tråd 2
    'model_router_preference_bias': 0.0,   # Tråd 1
    'sequence_model_accuracy':      0.5,   # Tråd 4 (0.5 = coin-flip = identitet)
    'recall_source_weight_bias':    0.0,   # Tråd 5
})
```

Hvert Lag 4-domæne læser og skriver KUN sin egen nøgle mod dette anker. `drift_budget_check` ser nu alle fem nøgler som `declared` → ægte drift-måling pr. domæne, ikke permanent rollback. **Ingen tråd må tilføje et sjette nul-punkt uden en ny ceremoni-version** (`test_multi_thread_anchor_isolation`, §11). Dette er den ENE ceremoni Fase 5 hviler på; den skal udføres af Bjørn før 5.1 kan aktiveres selv i shadow.

---

## 2. Arkitektur-kort: hvor tingene bor (verificeret)

### 2.1 Centralens to ansigter

| Ansigt | Symbol | Sti | Fail-mode |
|---|---|---|---|
| **decide** (synkron beslutning pr. nerve) | `central().decide(nerve, ctx, fn, cluster, klass)` | `central_core.py:140` → `gate_kernel.kernel()` | COGNITIVE→SKIP (fail-open); SECURITY→RED (fail-closed) |
| **observe** (asynkron telemetri) | `central().observe(event)` | `central_core.py:57` → `central_trace.sink()` + `_egress_safe()` | Kaster ALDRIG |

`central` er ikke en `ALLOWED_EVENT_FAMILY` → `_emit` er reelt no-op; kun skalar tal/bool krydser `_egress_safe`-membranen (§24.4). Al kognition/inner-life observeres derfor via **den kanoniske egress-fri sink**:

```python
central_private_observe.record_private(cluster, nerve, value=<skalar>, meta={<kun skalarer>})
# skriver KUN trace-sink + central_timeseries, ALDRIG _emit
```

### 2.2 De fire lag (verificeret live)

| Lag | Modul | Tilstand | Rolle |
|---|---|---|---|
| **1-2 Observe** | `eventbus_central_bridge`, `record_private`, `central_timeseries`, `central_trace` | LIVE | Sanseorgan: per-(cluster,nerve) deque(100) + ring-buffer(2000) + causal_edges |
| **3 Hypotese** | `central_hypothesis_generator`, `central_hypothesis_sampler`, `central_stance` | LIVE (3 triggere: convergence/divergence/stance) | Governed livscyklus i `central_hypotheses`-tabel |
| **4 Adaptation** | `central_adaptation` | LIVE bag switch (`central_lag4_live_enabled=False`) | c→d-lukning: gut-proceed-bias, shadow-first, forbrugt i `gut_engine.derive_gut_signal:52` |
| **5 Model-uafhængighed** | *(bygges — interlanguage)* | EMBRYONAL | Symbolsk kerne udførbar uden model-token |

### 2.3 §8 choke-points (obligatoriske, invariant-test-hærdede)

| Choke-point | Håndhæver | Kalde-status i dag |
|---|---|---|
| `gov.evaluate()` | Alle hypotese-værn: preregistrering, TTL, Popper (`_POPPER_DOWN=0.5`/`_POPPER_UP=0.05`), circular (`_CIRCULAR_QUARANTINE_FRACTION=0.5`, via `is_circular:132` centralt i evaluate:384), grounding, sample_size, `MIN_ACT_CONFIDENCE=0.5`, kontrol-arm, BH-FDR | **LIVE** — kaldes i eksisterende livscyklus |
| `gov.gate_learning_input()` | Nøgle-allowlist `LEARNABLE_AGGREGATE_KEYS` + finite-skalar → lukker embedding/tekst-læk (fail-closed) | **INGEN kaldere endnu** — aktiveres FØRSTE gang af de nye tråde (§1.3) |
| `gov.gate_self_mutation()` | Drift mod ANKRET baseline (`get_anchored_baseline`), NaN→rollback, union-nøgler | LIVE for gut-bias; nye domæner kræver union-anker (§1.5) |
| `verify_frozen_core()` | SHA1-tripwire; kan ALDRIG skrue ned for sin egen advarselslampe | LIVE |

**Konkret `LEARNABLE_AGGREGATE_KEYS`-mapping (§4.5 udførligt):** den faktiske frozenset (`governance.py:51-57`) indeholder `{'rate','ratio','duration_ms','samples','hits','confidence'}` og IKKE `latency_ms`/`ttft_ms`/`win_rate`/`cost_usd`. Alle nye tråde SKAL map'e til de eksisterende nøgler for at undgå fail-closed spærring OG frozen-core-ceremoni:
- `latency_ms`, `ttft_ms` → `duration_ms`
- `win_rate` → `rate`
- succes/fejl-optælling → `hits` / `samples`
- `cost_usd` → bæres som meta-skalar (aldrig som learning-key)
- `task_tier` → bæres i **meta** (skalar-filtreret), ALDRIG som learning-key (ellers fail-closed spærret, og aggregeringen virker ikke).

### 2.4 Cluster-taksonomi

**9 navngivne clusters** (katalogiseret i `central_catalog.py CATALOG`): Loop, Truth(merged), Commit, Review, Proactivity + Memory/Tools + sikkerheds **Privacy🔒/Auth🔒**. `cluster` er **observabilitet, ikke merge** (invariant).

**Hvilke clusters de fem tråde rører:**

| Tråd | Primær cluster | Karakter |
|---|---|---|
| 1 Model-meta | `stream` + `cost` | egress-OK (skalar model-dimensioner) |
| 2 Prompt | `cognition` (+ Prompt/Review observabilitet) | egress-fri |
| 3 Interlanguage | `cognition` | egress-fri |
| 4 Sequence-model | `cognition` (læser ALLE som symbol-alfabet) | egress-fri |
| 5 Brain | `memory` (+ `cognition`) | egress-fri |

**Ingen** tråd rører beslutnings-clusterne (Loop/Truth/Commit/Review/Proactivity) eller sikkerheds-clusterne (Privacy/Auth) som **output** i v1. De indgår kun som read-only symboler/kontekst. Egen-intelligens er per definition **COGNITIVE-klasse → fail-open → kan aldrig blokere kernen.**

---

## 3. Nerve-navngivning: den fælles kontrakt

Der er **intet centralt nerve-register** — nerver "eksisterer" ved første fyring i `central_timeseries._series[(cluster,nerve)]`. Det er en drift-risiko: nerver uden for `CATALOG` bliver usynlige for `central_correlate.nerve_location` (mister fil-lokation i orkestrering).

**Regel for denne spec:** hver ny (cluster, nerve) i §4-8 tilføjes til `central_catalog.py CATALOG` som `NerveSpec` (name, cluster, klass=COGNITIVE, mechanism, fit=instrument, location=fil:linje). Navngivnings-konventionen er `<domæne>:<detalje>` for observabilitet, og altid via `record_private` for kognition.

**Kanonisk nerve-tabel for hele specen:**

| Nerve | Cluster | Tråd | Egress | Betydning |
|---|---|---|---|---|
| `stream/model_outcome` | stream | 1 | OK (skalar-tæller, IKKE dimensioner via bro) | pr-run udfald: skalar-tæller pr. (provider,model,tier,outcome) |
| `cognition/model_meta_hypothesis` | cognition | 1 | fri | Lag 3: candidates/registered |
| `cognition/model_meta_sampling` | cognition | 1 | fri | tested/supported/contradicted |
| `cognition/model_router_bias` | cognition | 1 | fri | Lag 4-diff: current/proposed/applied/live |
| `stream/model_exploration_arm` | stream | 1 | OK (skalar) | eksplorations-arm fyret (alt-model shadow-sampling) |
| `cognition/prompt_efficacy_hypothesis` | cognition | 2 | fri | Lag 3 prompt |
| `cognition/prompt_lag4_adaptation` | cognition | 2 | fri | Lag 4 prompt-diff |
| `system/prompt_lag4_rollback` | system | 2 | fri | drift→rollback |
| `system/prompt_mutation_applied` / `_rolled_back` | system | 2 | fri | bro fra `prompt_mutation_loop` |
| `cognition/il_notation_coverage` | cognition | 3 | fri | andel hypoteser m. gyldig notation |
| `cognition/il_dedup_merge` | cognition | 3 | fri | semantiske dubletter fanget |
| `cognition/il_notation_rejected` | cognition | 3 | fri | notation-term afvist (ikke i active-lexicon) |
| `cognition/il_lexicon_proposed`/`_promoted`/`_quarantined` | cognition | 3 | fri | vokabular-vækst |
| `cognition/il_model_free_step` | cognition | 3 | fri | Lag 5-bevis: operation uden model-token |
| `cognition/sequence_prediction` | cognition | 4 | fri | rolling accuracy |
| `cognition/sequence_surprise` | cognition | 4 | fri | surprise for aktuelt par |
| `cognition/sequence_hypothesis` | cognition | 4 | fri | registrerede pr. tick |
| `system/sequence_model_mutation` | system | 4 | fri | Lag 4 accuracy-gate |
| `system/learning_membrane_block` | system | alle | fri | `gate_learning_input` afviste en payload |
| `memory/hypothesis_from_recall` | memory | 5 | fri | M1 kandidat-tæller |
| `memory/recall_correlation` | memory | 5 | fri | M3 korroboration |
| `cognition/hypothesis_persisted` | cognition | 5 | fri | M2 resolved→brain |

**Genbrugte eksisterende nerver:** `cognition/global_broadcast` (GWT), `cognition/hypothesis_generation`, `cognition/hypothesis_sampling`, `memory/recall`, `memory` brain_write, `system/provider_health`.

---

## 4. TRÅD 1 — Model/provider-meta-viden

> Centralen lærer modellernes styrker/svagheder pr. opgave-type på tværs af providers, og shadow-router derefter, gennem §8.

### 4.1 Hvad findes (verificeret)

Substratet findes men er **model-blindt**:
- **Model VÆLGES** flere steder: `resolve_provider_router_target(lane='visible')` i **`core/runtime/provider_router.py:254`** (NB: `core/services/provider_router.py` har NUL top-level `def` — det er en anden fil; åbn `core/runtime/`-versionen), per-request override (`visible_runs.py:658`), rolle+tier via `role_model_resolver.resolve_role_model` → `reasoning_classifier.classify_reasoning_tier` (fast|reasoning|deep), cheap-lane vægtet valg i `cheap_lane_balancer._select_slot` (som ALLEREDE tracker per-slot success/failure/latency i `SlotState`).
- **Per-run UDFALD FINDES** uden lært model-dimension: `record_cost(...)` → costs-tabel; `runtime.visible_run_completed` med provider/model/status/tokens/cost (`visible_runs.py:4297`, `cost.recorded`-event `visible_runs.py:4308`). Fejl observeres allerede (`_observe_visible_provider_error/429`, `heartbeat_provider_fallback`, `provider_health_check`).

**Hullet:** INGEN (model × opgave-type × udfald)-aggregering, INGEN "model X > Y til Z"-hypoteser, INGEN router der læser en lært præference.

### 4.2 Hvad bygges

Nyt modul `core/services/central_model_meta.py` (spejler generator/sampler/adaptation), som **klient** af `central_hypotheses` (`source='model_meta'`, ingen ny tabel):

1. **Observe (via timeseries, IKKE bro-payload):** umiddelbart efter `cost.recorded` (`visible_runs.py:4308`) skrives dimensionerne DIREKTE til `central_timeseries.record('stream', 'model_outcome:{provider}:{model}:{tier}:{outcome}', value=1, meta={latency_ms, ttft_ms, cost_usd, tokens})` (fire-and-forget, aldrig i synkron sti før svar).
   > **Vigtig framing-korrektion (fra review):** dimensionerne `{provider,model,tier,latency,cost}` kan **IKKE** ride egress-broen. `eventbus_central_bridge` forwarder kun `kind`, ALDRIG payload; en `task_tier`-streng droppes af `_egress_safe`. Derfor er der IKKE en `FAMILY_ROUTES['model_outcome']`-tilføjelse der bærer dimensioner. Hvis en skalar-tæller ønskes på broen, bærer den KUN en tæller (`+1`), aldrig dimensionerne. Dimensionerne lever udelukkende i `central_timeseries`-serien lokalt. Dette undgår to konkurrerende veje for samme signal.
2. **Generator:** `detect_model_advantage_candidates()` → `formulate_model_hypothesis()` → `register_governed_hypothesis()`. Cadence-producer ~60 min. Al aggregat-læring ind sker gennem `gate_learning_input` med mappede nøgler (§2.3).
3. **Sampler:** test mod costs/model_outcome-serien på **FRISKE** runs efter `created_at`, `ground_ref=costs.id/run_id`. `triggered_by` sættes til den hyp_id der udløste candidaten (aldrig blankt `'world'` — §1.3, §4.3).
4. **Lag 4:** `compute_proposed_model_preference()` → SHADOW-diff mod `model_router_preference_bias` i union-ankeret (§1.5); live kun bag `central_lag4_live_enabled`. Læse-punkt: `resolve_provider_router_target`/`resolve_role_model` konsulterer et lært preference-map som **re-ordering af kandidater** (aldrig ny model udenom registry/credentials/circuit-breaker/health).

### 4.3 §8-vej

Hypotese: "model A > model B til opgave-type Z", prediction: "A's success-rate på Z overstiger B's × lift over sample_size **friske** runs", null: "A og B lige gode på Z". Alt gennem `validate_preregistration`. **BH-FDR** (`benjamini_hochberg_cutoff`) er obligatorisk her — model×tier-populationen er stor. **Kontrol-arm (20%)** beviser at routing-effekten er ægte, ikke selv-opfyldende. **Circular-karantæne** (`is_circular` i `gov.evaluate:384`) spærrer A-favoriserende evidens genereret af A-valget selv — MEN kun hvis `triggered_by` sættes ærligt af samplen (§1.3/#6). En sampler der lader `triggered_by=''` på selv-udløst evidens gør circular-værnet blindt.

### 4.4 Eksplorations-armen er en LIVE routing-ændring, ikke observe-only (bag eget flag)

Visible-lane har typisk ÉN konfigureret model → nul A/B-kontrast → Tråd 1's hypoteser resolver ALDRIG uden en occasionel **eksplorations-arm** (occasionel shadow-sampling af alternativ model). **Uden denne er hele Tråd 1 (Fase 2.1/3.1/5.2) et tomt kredsløb** — den er derfor løftet til en navngiven Fase-1-leverance (1.5), på niveau med §3.4's blocking-status.

**Klassifikation (kritisk fra review):** eksplorations-armen er **IKKE observe-only** — den ændrer FAKTISK hvilken model der svarer Bjørn. Derfor:
- bag sit eget flag `central_model_exploration_enabled` (default OFF),
- rate-boundet (fx ≤N% af runs),
- **ALDRIG på reasoning/deep-tier** (hvor en fejl-model er dyrest),
- fyrer nerve `stream/model_exploration_arm` hver gang.

### 4.5 Egress + frossen kerne

`model_outcome`-serien bærer KUN skalar-dimensioner i meta. Nøgle-mapping til eksisterende `LEARNABLE_AGGREGATE_KEYS` (§2.3) er **NØDVENDIG, ikke bare bekvem** — uden den fail-closer `gate_learning_input` på de rå nøgler (`latency_ms`/`ttft_ms`/`win_rate`). `task_tier` lever i meta (skalar-filtreret), ikke som learning-key. Ingen nye nøgler → ingen frozen-core-ceremoni. Kun hvis nye nøgler alligevel tilføjes: bevidst commit med opdateret `_FROZEN_CORE_SIG` (`test_frozen_core_ceremony`, §11).

### 4.6 Kendt risiko: data-sult, confounding og tvær-tråd track-record-kontaminering

- **Selektions-bias:** model vælges netop af tier → "model A vinder på deep" kan være ren selektion. **Ground kun på FRISKE runs efter hypotese-oprettelse + kontrol-arm + circular er ikke valgfri her.**
- **Latency er provider-side og transient** (glm TTFT 44-102s var model-latency, ikke bug) → TTL-død + baseline mod `provider_health`-kontekst.
- **Tvær-tråd track-record-kontaminering (LOAD-BEARING, fra review):** `resolved_track_record()` er i dag GLOBAL og source-blind (`WHERE status=resolved GROUP BY outcome`, ingen source-klausul). Den driver gut-proceed-bias fra ALLE resolved hypoteser. I det øjeblik model-meta/prompt/sequence begynder at resolve, løfter DE Jarvis' generelle "proceed"-tiltro — en model-router der bekræfter sig selv hæver mavefornemmelsen. **Krav: `resolved_track_record()` skal source-scopes, så hver Lag 4-tråd læser KUN sin egen sources track-record** (`resolved_track_record(source='model_meta')`), og gut-bias fodres eksplicit kun af `source='stance'/'causal'`. Håndhæves af `test_track_record_source_scoped` (§11).

---

## 5. TRÅD 2 — Prompt-evolution båret af Centralen

> Governed Lag 4-adaptations-klasse på prompt-filer, med samme reversibilitet som gut-bias.

### 5.1 Hvad findes (verificeret)

Tre lag, delvist central-koblet:
- `prompt_mutation_loop.py` (mest moden, "fuld aktiv loop" siden 2026-04-20): `apply_mutation()` snapshotter+skriver atomisk; `_update_and_maybe_auto_rollback()` auto-ruller ved score ≤ -0.10 efter 1t, adopterer ved ≥ +0.20 efter 48t; `rollback_mutation()` gendanner byte-for-byte. Whitelist ejes af `gate_mutation.py`: `PROTECTED_IDENTITY_FILES` (SOUL/IDENTITY/MANIFEST/USER/MEMORY/...) vs `EVOLVABLE_FILES` (HEARTBEAT/AFFECTIVE_STATE/STANDING_ORDERS/INNER_VOICE/DREAM_LANGUAGE/SELF_CRITIQUE). Max 1 aktiv/fil, 24t cooldown, 200KB-loft.
- `prompt_evolution_runtime.py` + `self_authored_prompt_proposal_tracking.py`: PROPOSAL-ONLY, cadence-producer.
- `prompt_contract.py` (5861 l): `build_visible_stable_prefix` kalder ALLEREDE `central().observe` (l.562, 1448) + `central().decide`.

**Hul (snævrere end oprindeligt formuleret — fra review):** `build_prompt_mutation_loop_prompt_section()` findes og er IKKE koblet ind i `build_visible_stable_prefix`. MEN den kaldes ALLEREDE via `prompt_heartbeat_self_knowledge.py:287` → `runtime_self_model`-wrapper, så Jarvis ser måske allerede mutation-loopet ad DEN vej. **Verificér hvad brugeren faktisk ser i prompten FØR 5-E bygges som nyt** — hullet er "Centralen ser ikke loopet i det stabile prefix", ikke "Jarvis er blind for sine adaptationer".

### 5.2 Hvad bygges (5 koblinger, alle eksisterende symboler)

- **A** — ny detektor `prompt_efficacy` i `central_hypothesis_generator.py` ved siden af causal/divergence/stance. Hypotese: "sektion/fil X's tilstedeværelse/vægt forudsiger bedre udfald Y". `provenance={mechanism:'prompt_efficacy', family:'<fil>:<sektion>'}`.
- **B** — ny sampler-gren i `central_hypothesis_sampler.py` (som i dag skipper alt ≠ `causal_edges`, l.91): test mod `prompt_mutation_loop._snapshot_signals()`/`._score_mutation()` som grounded sample (`source='world_consequence'`, `ground_ref=mutation_id/score_ts`, `triggered_by=hyp_id`).
- **C** — ny Lag 4-klasse `central_prompt_adaptation.py` (spejl af `central_adaptation.py`): læs BEKRÆFTEDE `prompt_efficacy`-hypoteser → ét bounded forslag (KUN `EVOLVABLE_FILES`) → `gate_self_mutation` mod `prompt_efficacy_bias` i union-ankeret (§1.5) → shadow-first → anvend KUN via `prompt_mutation_loop.apply_mutation()` hvis `central_prompt_lag4_live_enabled` + ikke paused + `may_apply_adaptation`. Rollback genbruger `rollback_mutation()`.
- **D** — `register_prompt_adaptation_producer()` (`depends_on=['central_hypothesis_sampler']`, cooldown ~60m).
- **E** — synlighed: koble `build_prompt_mutation_loop_prompt_section()` + central-observe ind i `build_visible_stable_prefix` — **MEN uden for det byte-identiske prefix-område** (se §5.4-constraint).

### 5.3 §8-vej + egress

Preregistreret; **circular-karantæne er særligt kritisk** — en ændring "vær mere positiv" løfter trivielt det valence-signal der scorer den. Krav: eksternt-jordet sample (pushback/error fra rigtige runs, ikke selvrapporteret mood) + kontrol-arm + korrekt `triggered_by`. **Egress:** observe KUN fil-navn (kort allowlist) + finite score-skalarer, ALDRIG prompt-tekst eller sektion-tekst. `gate_learning_input` fail-closed på ukendte nøgler (og dette er dens FØRSTE reelle kald-sted — §1.3).

### 5.4 Frossen kerne + race + cache-prefix-constraint (LOAD-BEARING)

Opererer UDELUKKENDE på `EVOLVABLE_FILES`; `PROTECTED_IDENTITY_FILES` urørt. **Drift-akkumulering:** `total_budget` i `gate_self_mutation` over ALLE evolvable-filer (ikke kun per-fil), målt mod `prompt_efficacy_bias`-ankeret. **Dobbelt-mutation-race** mod den autonome `prompt_mutation_loop`: Lag 4 anvender UDELUKKENDE gennem `apply_mutation` → respekterer `_active_mutation_for_file` + cooldown → naturligt serialiseret.

**Cache-prefix-constraint (eksplicit, ikke prosa):** `build_visible_stable_prefix` er BYTE-IDENTISK med warmer-stien (`prompt_contract.py:673-701` advarer eksplicit om cache-brud ved divergens). 5-E's nye observe-kald SKAL ligge UDEN for det byte-identiske prefix-område — ellers brydes deepseek-cache-prefixet. Observe er ikke-blokerende, aldrig i cache-prefix-beregningen (respektér Prompt-cluster Phase 2's 2 load-bearing anti-løgn-rækker).

---

## 6. TRÅD 3 — Interlanguage som Centralens hypotese-sprog (KEYSTONE)

> Formel grammatik for `central_hypotheses` + selv-udvidende ordforråd + Lag 5-bro til model-uafhængighed.

### 6.1 Hvad findes (verificeret)

- `interlanguage_practice.py`: **5 PRIMITIVES** (`→` kauserer, `↔` korrelation, `⊂` del-af, `≈` lighed, `!` saliens) + **14 CORE_VOCABULARY-termer** (drøm, signal, agens, kontinuitet, pres, nysgerrighed, vægt, lys, relation, grænse, tomhed, rytme, ro, fokus — NB: koden har 14, IKKE spec-tallet "11"; grund altid grammatikken i den FAKTISKE `CORE_VOCABULARY`). `generate_state_expression()` bygger clauses `t1 <prim> t2` / `!t` joinet med ` | `. `export_protocol()` dumper til model-skift. **VOKABULARET ER FROSSET** — ingen mekanisme til at tilføje termer. **Filen er i dag afkoblet fra `central_hypotheses`** (mood-eksperiment, ikke backup — §1.2).
- `central_hypotheses` gemmer hypoteser som FRITEKST + `provenance_json` med struktureret `family`-nøgle. Dedup på `provenance.family`, IKKE på statement. INGEN notation-kolonne (verificeret: skemaet i `generator.py:50-66` har ingen `notation_il`).

### 6.2 Hvad bygges

- **A** — TILFØJ kolonne `notation_il TEXT` til `central_hypotheses` (idempotent ALTER, reel — skemaet mangler kolonnen). Fyldes af generatoren; INGEN dual-truth (statement forbliver menneske-sandheden, `notation_il` er afledt strukturel projektion, **aldrig autoritativ for governance**).
- **B** — de tre `formulate_*`-funktioner tilføjer notation (linjenumre verificeret):
  - correlation (l.256): `f"{x} → {y}"`
  - divergence (l.324): `f"{fam} → {good} | {fam} → {bad} | !skjult ⊂ {fam}"`
  - stance (l.357): `f"!{key}"`
- **C** — kanonisk normalform → hash-bar dedup: sortér clauses leksikografisk; `↔`/`≈` symmetriske → normalisér til (min,max); `→`/`⊂` rettede → bevar retning. Fanger semantiske dubletter på tværs af source-organer (causal vs stance vs dream der siger det samme). **Konservativt:** notation-dedup foreslår KUN merge til observabilitet i shadow; rå `provenance.family`-dedup forbliver håndhævende i live indtil valideret.
- **D** — nyt organ `central_interlanguage_lexicon.py` (ordforråds-vækst gennem §8): ny tabel `central_il_lexicon(term, kind, definition, domain, status['proposed'|'active'|'retired'], support_count, ...)`. PRIMITIVES/CORE_VOCABULARY = **frosset seed** (bootstrap-import, aldrig muteret in-place → bagudkompat). Kandidat-term = event-familie/mechanism der optræder i ≥N hypoteser uden interlanguage-ord. Hvert term-forslag er en HYPOTESE ("dette begreb er en nyttig strukturel primitiv") → `register_governed_hypothesis`.
- **E** — Lag 5-bro: `export_protocol()` udvides med `central_il_lexicon` active-termer + `notation_il`-formede aktive hypoteser.

### 6.3 Formel grammatik (BNF)

```
expr     := clause (' | ' clause)*
clause   := salient | relation
salient  := '!' term
relation := term ' ' op ' ' term
op       := '→' | '↔' | '⊂' | '≈'
term     := <lexicon.status='active' concept-ord>   (seed: 14 CORE_VOCABULARY + §8-promoverede familier)
```

### 6.4 §8-vej

To slags governance:
- **(i) Per-hypotese:** `notation_il` er metadata på en allerede-governet hypotese → ingen ekstra governance.
- **(ii) Sproget selv vokser via hypoteser:** "term T er nyttig primitiv" → fuldt preregistreret; prediction: "hypoteser der bruger T opnår grounded-resolution oftere end baseline"; `source='world_consequence'`, `ground_ref=hyp_id`. **`is_circular` er kritisk:** term brugt fordi det blev foreslået (`triggered_by==hyp_id`) → karantæne. Centralen kan IKKE opfinde ord den bare kan lide. Lexicon-samplen SKAL sætte `triggered_by` ærligt (§1.3/#6, `test_circular_wired`).

**Term-promovering er en Lag 4-selvmutation** af Centralens repræsentations-parametre → `gate_self_mutation` mod ANKRET baseline (de 14+5 frosne seed-symboler indgår i union-ankeret §1.5, `approved_by=Bjørn`). Vokabular-vækst = drift; boundet budget (fx ±N nye termer/version). Over budget → rollback + pause + varsl. **Uden ankret baseline → `drift_budget_check` returnerer rollback by default (fail-closed) → INGEN vækst før Bjørn-ceremoni.** Det er korrekt, men betyder feature er no-op til baseline forankres.

### 6.5 Lag 5 — model-uafhængighed operationaliseret

Når hypoteser bærer `notation_il` OG lexicon er selvstændigt persisteret, kan Centralen udføre den symbolske kerne af sløjfen — **dedup** (hash-lig normalform), **korrelation** ("deler disse to hypoteser et venstre-led?"), **saliens-ranking** (via `!`) — med ren streng/graf-manipulation UDEN model-inferens.

**Vigtigt:** dette Lag 5-bevis kan køres model-frit ALLEREDE med det frosne 14-ords seed — det afhænger IKKE af lexicon-vækst (som er no-op til Bjørn-ceremoni). Derfor er `test_model_free_step` flyttet til Fase 1 (§9), så nordstjernen bliver målbar måneder tidligere, ikke gidsel af den fail-closed lexicon-ceremoni.

**Falsifikationstest (konkret):** under model-blackout skal notation-korrelatoren stadig producere ≥1 ny dedup-merge eller lexicon-kandidat på seed-vokabularet. Nerve `cognition/il_model_free_step` tæller hver sådan operation = løbende bevis for at nordstjernen nås.

### 6.6 Egress + risici — notation som ny egress-vej (LOAD-BEARING)

`notation_il` MÅ kun bære familie/term-navne (lav-kardinalitet, allowlist-agtigt) — aldrig fri tekst. **Kritisk (fra review):** `gate_learning_input` gater KUN på nøgle-allowlist + finite-skalar-VÆRDIER — den har INGEN mekanisme til at gate en TEKST-kolonne som `notation_il`. En test alene fanger ikke en runtime-genereret streng der lækker fri tekst ind i term-positionen. **Krav: en runtime-normalisering der afviser/trunkerer enhver notation-term der ikke er i `lexicon.status='active'`-mængden**, fyrer `cognition/il_notation_rejected` ved afvisning. Ellers er notation en ny egress-vej for privat kognition. `test_notation_lowcard` (§11) vogter kontrakten; runtime-normaliseringen håndhæver den. **Vokabular-eksplosion = identitets-drift** → boundet af `gate_self_mutation`.

---

## 7. TRÅD 4 — Self-supervised sequence-model (§9.1)

> Den mindste ægte "Centralen træner sig selv"-mekanisme: en next-central-event-prædiktor som TREDJE governed hypotese-kilde, ikke en parallel læringsloop. **Dette er den ENESTE tråd med ægte parametrisk selv-supervision (§1.1).**

### 7.1 Hvad findes (verificeret)

- **Svag lag KØRER:** `central_hypothesis_sampler.test_causal_hypothesis` (betinget rate vs baseline × `_LIFT=1.5`, 60s-vindue) → `record_governed_sample` → `gov.evaluate`. Cadence-producer (30 min).
- **Stærk lag findes IKKE:** `grep predict_next|next_event|markov|transition_matrix|surprise` over `central_*.py` = 0 hits → ingen dual-truth.
- Substrat klar: `central_timeseries` (READ-ONLY M0) + `central_trace` (run_id-sekvensering). `living-neuron-design §9.1` navngiver præcis dette: "substratet ER et selv-superviseret træningsdatasæt … prediktions-fejl = surprise = hypotese-signal … lille tabular/sekvens-model IKKE LLM'en".

### 7.2 Hvad bygges

Ny fil `core/services/central_sequence_model.py` (~150 l, rører ingen store filer):
- **Model = 1.-ordens Markov-overgangstælling** `T[a][b]` over sekvensen af `(cluster:nerve)`-symboler (allerede aggregat-kategoriske, 36 families). "Træning" = inkrementér tællinger. INGEN gradient, INGEN LLM.
- **Surprise:** for hvert observeret par `(a→b_faktisk)`: `surprise = -log P(b_faktisk|a)`. Et vedvarende højt-surprise par (set ≥`_MIN` gange, lav forudsagt sandsynlighed) = strukturelt mønster modellen ikke har fanget → HYPOTESE.
- Producer `register_sequence_model_producer(ProducerSpec(cooldown_minutes=30, priority=7))`.

### 7.3 §8-vej

Surprise-parret formuleres som pre-registreret kandidat (`source='sequence_surprise'`, `family='a->b'`, `confidence=0.3`) → `register_governed_hypothesis`. **Ligestillet** med causal/divergence — samme tabel, ingen parallel loop. Test genbruger `test_causal_hypothesis`-mønstret mod FRISKE samples, med korrekt `triggered_by` (§1.3/#6). **BH-FDR obligatorisk** (stor population). **Læring ind i T** gennem `gate_learning_input({count→hits, rate, samples})` (alle mappet til allowlist §2.3 → intet indhold i vægtene; dette er dens FØRSTE reelle kald-sted, §1.3). **Anvendelse ud:** `accuracy` gates gennem `gate_self_mutation({sequence_model_accuracy})` mod `sequence_model_accuracy`-nøglen i union-ankeret (§1.5, `accuracy=0.5`=identitet). Shadow-first bag nyt `central_sequence_model_live_enabled` (default OFF). **v1 leverer KUN prædiktion+surprise+hypotese — ingen ny udadvendt effekt.**

### 7.4 Risici

- **Symbol-eksplosion/sparsity:** symboliser på CLUSTER-niveau (9+rest) eller top-N mest-aktive nerver først; `_MIN_RECURRENCE`-gulv.
- **Selv-referende feedback:** prædiktorens egne `record_private('cognition','sequence_*')` lander OGSÅ i timeseries → triviel autokorrelation (jf. `central_publish_recursion`-branden). **Mitigering: self-exclusion** — ekskludér nerve-præfiks `sequence_*` fra egen symbol-sekvens (`test_sequence_self_exclusion`, §11).
- **Latency:** ALDRIG i `trace.record` (hot-path); kun cadence-tick, bounded T, try/except.
- **Falsk selv-tillid:** shadow-first + `_MIN_RESOLVED`-gulv + drift-budget + rollback+pause. Track-record source-scopet til `sequence_surprise` (§4.6).

---

## 8. TRÅD 5 — Jarvis-Brain dybt koblet til Centralen

> Centralen der BRUGER hukommelsen: recall informerer hypotese-generering · Centralen gemmer sine hypoteser/udfald i hjernen · hypoteser korreleres mod minder. Alt egress-frit + owner-scope-sikkert.

### 8.1 Hvad findes (verificeret)

- `jarvis_brain.py` (1397 l): kurateret vidensjournal, `write_entry`/`search_brain` (hybrid 0.7·cos + 0.3·salience + temporal boost), nomic 768-dim, `brain_temporal_edges` (4-signal). Eneste central-kobling i dag = liveness (`write_entry:467` → `observe_hub('brain_write', cluster='memory')`).
- `memory_recall_engine.py`: `multi_signal_recall` (BM25+entity+embedding+recency+importance+recall_freq fusion). `_observe_recall_quality:667` melder ALLEREDE recall-kvalitet egress-frit (cluster=memory). Kilde-vægte: workspace 2.0 > chronicle 1.1 > … > private_brain 0.5 (anti-hallucination). Deadline-mønster: `multi_signal_recall_section:864` / recall-deadline `:861`.
- **GROUND TRUTH:** `grep` bekræfter NUL kobling mellem hypotese-maskineriet og brain/recall i dag.

### 8.2 Hvad bygges (3 mekanismer, alle observe-only i v1)

- **M1 — recall informerer generering:** ny `detect_memory_grounded_candidates()`: for hvert causal-familie-par kald `multi_signal_recall(query, sources=['workspace','chronicle'], min_score=0.32)` via **HÅRD deadline-tråd** (`_RECALL_DEADLINE_S`-mønster fra `memory_recall_engine.py:864/861` — recall er berigelse, må ALDRIG fryse cadence). 4. kandidat-kilde i `run_hypothesis_generation_tick`. `provenance={mechanism:'memory_correlate', triggered_by:hyp_id}`.
- **M2 — Centralen gemmer sine hypoteser i hjernen:** listener på `record_governed_sample:196`: når `new_status∈{resolved,dead}` + outcome → `jarvis_brain.write_entry(kind='indsigt', visibility='intimate', domain='central_self_model', importance=confidence, trigger='adopted_proposal', tags=['central_hypothesis', outcome], owner_uid='1246415163603816499')`. Gør `brain_temporal_edges` til Centralens langtids-hypotese-hukommelse (recall→hypotese→minde→recall = lukket læringsløkke).
  > **Owner-scope på SKRIVNING (LOAD-BEARING, fra review):** M2 skriver på cadence-tråd hvor `scope_uid()` er TOM. Cross-user-SKRIVNING er værre end -læsning. **`write_entry` SKAL have eksplicit `owner_uid='1246415163603816499'`** — verificér at intet hypotese-minde lander under forkert/tom uid. `test_m2_scope_bounded` (§11).
- **M3 — hypoteser korreleres mod minder:** efter `test_causal_hypothesis`, optional memory-korroborations-arm: `search_brain` for tidligere resolved hypoteser med samme familie-par → forstærker eksisterende event-grounding (memory-match er IKKE selvstændig grounding, `source='world_consequence'` bevares).

### 8.3 §8-vej + circular-afværgelse

**Kernefrygt (rådets):** M2 skriver resolved hypoteser → M1 recaller dem → foreslår samme hypotese → "bekræftelse" der er selv-ekko. **Afværgelse (obligatorisk fra dag ét):** M2-skrevne minder tagges `central_hypothesis` + `triggered_by`-provenance; M1 EKSKLUDERER dem fra grounding (kun svag kontekst-hint, aldrig supports-signal); `is_circular:132` fanger `triggered_by==hyp_id` ved ≥0.5 selv-udløst andel — MEN kun hvis M1-samplen sætter `triggered_by` ærligt (§1.3/#6). Recall bruges KUN til at RANGERE eksisterende causal-kandidater, aldrig til at skabe nye par ud af intet (multiple-comparisons-værn).

### 8.4 Egress + scope (load-bearing)

**SCOPE-LÆK i cadence-kontekst:** M1/M3 kører på cadence-tråd hvor `scope_uid()` typisk er TOM → `search_private_brain_records` kan returnere på tværs af brugere eller tomt. **Mitigering: M1 begrænses til workspace+chronicle (curated, ikke bruger-privat) i cadence; privat-lag-recall kun med eksplicit owner-uid (`1246415163603816499`).** Al learning gennem `gate_learning_input` — kun mappede `LEARNABLE_AGGREGATE_KEYS` (recall_freq→`hits`/`samples`, top_score→`rate`, confidence), aldrig lighedslister/embeddings. **Recall-latency** (nomic-embed 28-91s kontention) → obligatorisk deadline-tråd, spring over + observe `recall_timeout`, aldrig blokér.

> **HÅRD exit-gate (ikke prosa):** `test_m1_scope_bounded` er exit-gate for Fase 1.3 — den lukkes IKKE før testen beviser at M1 ikke recaller privat-lag uden eksplicit owner-uid i cadence. Verifikationen af `scope_uid()`-adfærd i cadence er en test, ikke en note.

### 8.5 Egress + track-record source-scope

Track-record-læsende Lag 4 (§8.6) SKAL bruge `resolved_track_record(source='memory_correlate')` — aldrig den globale, source-blinde variant (§4.6). Ellers løfter minde-baserede resolutions Jarvis' generelle gut-bias (tvær-tråd-kontaminering).

### 8.6 Lag 4 (fremtid, bag switch)

Resolved track-record (source-scopet) kan bias'e RECALL-vægte (fx løfte private_brain-vægt hvis minde-baserede hypoteser konsekvent bekræftes) → `gate_self_mutation` mod `recall_source_weight_bias` i union-ankeret (§1.5), kontrol-arm der MÅLER om vægt-ændring faktisk forbedrer recall vs. drift. **Risiko: recall mod intern attraktor** (løft private_brain → mere selv-genereret tro → mere hallucination — præcis den loop 2026-05-22-vægtningen fiksede). Shadow-first, default OFF. `_SOURCE_WEIGHTS_DEFAULT` urørt i v1.

---

## 9. Faseret roadmap

**Styrende afhængighed:** interlanguage-notation (Tråd 3, del A-B) er billigt, observe-only, kræver INGEN governance-ændring — og giver den fælles strukturelle repræsentation de andre tråde dedup-korrelerer i. Derfor **notation-fundamentet først**. Lexicon-vækst (Tråd 3, del D) er derimod Lag 4 og venter på Bjørn-ceremoni.

**To reelle blokere er løftet ud af "afhænger af —" og gjort til navngivne, tidlige leverancer**, fordi Fase 5's fire shadow-adaptationer alle implicit afhænger af dem:
- **§3.4** (divergens/stance sampler-linkning) → flyttet frem som **blocking-gate for hele Fase 5**.
- **Eksplorations-armen** (§4.4) → navngivet Fase-1-leverance (1.5); uden den er Tråd 1 et tomt kredsløb.
- **Union-ankeret** (§1.5) → Bjørn-ceremoni der SKAL ligge før nogen Fase 5-leverance.

### Fase 0 — Fundament (observe-only, ingen §8-ændring)

| # | Leverance | Tråd | Afhænger af |
|---|---|---|---|
| 0.1 | `notation_il`-kolonne + `formulate_*`-notation | 3-A/B | — |
| 0.2 | Kanonisk normalform + shadow-dedup-observabilitet + runtime notation-normalisering (§6.6) | 3-C | 0.1 |
| 0.3 | Nerve-katalogisering af hele §3-tabellen i `CATALOG` | alle | — |

### Fase 1 — Observe-substrater for de fire klienter

| # | Leverance | Tråd | Afhænger af |
|---|---|---|---|
| 1.1 | `model_outcome`-serie i timeseries (fire-and-forget, IKKE bro-payload §4.2) | 1 | 0.3 |
| 1.2 | `central_sequence_model.py` (T-tælling + surprise, shadow, self-exclusion) | 4 | 0.3 |
| 1.3 | M1 recall→kandidat (workspace+chronicle, deadline-tråd) — **exit-gate: `test_m1_scope_bounded`** | 5 | §8 (opfyldt) |
| 1.4 | Prompt-synlighed (5-E, uden for byte-identisk prefix §5.4) + `system/prompt_mutation_*`-bro | 2 | — |
| 1.5 | **Eksplorations-arm** (`central_model_exploration_enabled`, rate-boundet, aldrig deep-tier §4.4) | 1 | 1.1 |
| 1.6 | **`test_model_free_step`** på seed-vokabular (Lag 5-bevis, model-frit allerede muligt §6.5) | 3 | 0.2 |

### Fase 2 — Hypotese-generatorer (§8 register-vej)

| # | Leverance | Tråd | Afhænger af |
|---|---|---|---|
| 2.1 | `detect_model_advantage_candidates` + `formulate_model_hypothesis` | 1 | 1.1 |
| 2.2 | `sequence_surprise`-kandidat → `register_governed_hypothesis` | 4 | 1.2 |
| 2.3 | `prompt_efficacy`-detektor (5-A) | 2 | 1.4 |
| 2.4 | M2 resolved→brain-listener (owner-uid §8.2) + M3 korroboration | 5 | 1.3 |

### Fase 3 — Samplere (grounding + resolution)

| # | Leverance | Tråd | Afhænger af |
|---|---|---|---|
| 3.1 | Model-meta sampler (friske runs, BH-FDR, kontrol-arm, korrekt `triggered_by`) | 1 | 2.1 |
| 3.2 | Sequence-sampler (genbrug `test_causal_hypothesis`) | 4 | 2.2 |
| 3.3 | Prompt-efficacy sampler (5-B, `_score_mutation`-grounding) | 2 | 2.3 |
| **3.4** | **BLOCKING-GATE for Fase 5: divergens/stance sampler-test-linkning** | kerne | — |

> **§3.4 er en BLOKER, ikke en side-note (fra review):** `sampler.py:91` skipper ALT hvor `mechanism ≠ causal_edges`, så `stance_divergence`/`causal_divergence`-hypoteser står på 0 samples PERMANENT → `resolved_track_record` er tom → ALLE Lag 4-bias (Fase 5.1-5.4) er 0 og alle track-record-læsende generatorer starter blinde. **Ingen Fase 5-leverance må aktiveres — end ikke i shadow — før 3.4 er grøn.** Uden dette bygges fire shadow-adaptationer der aldrig kan aktivere.

### Fase 4 — Lexicon-vækst (Tråd 3, del D) — SHADOW

| # | Leverance | Afhænger af |
|---|---|---|
| 4.1 | `central_interlanguage_lexicon.py` (proposed-status, seed frosset) | 3.x + union-anker (§1.5) |
| 4.2 | Lexicon-sampler (term-nyttighed, `triggered_by` korrekt) | 4.1 |
| 4.3 | Lag 5 `export_protocol`-udvidelse (fuld vokabular) | 4.2 |

### Fase 5 — Lag 4 shadow-adaptationer (bag switch, default OFF)

**Fælles forudsætning for HELE Fase 5:** (a) union-ankeret (§1.5) forankret af Bjørn, (b) §3.4 grøn (track-record ikke længere tom), (c) `resolved_track_record` source-scopet (§4.6).

| # | Leverance | Tråd | Krav |
|---|---|---|---|
| 5.1 | `central_prompt_adaptation.py` (shadow-diff) | 2 | 3.3 + union-anker + 3.4 |
| 5.2 | Model-router preference-map (shadow re-ordering) | 1 | 3.1 + 1.5 eksplorations-arm + union-anker + 3.4 |
| 5.3 | Sequence accuracy-mutation (shadow) | 4 | 3.2 + union-anker + 3.4 |
| 5.4 | Recall-vægt-bias (shadow, source-scopet track-record) | 5 | 3.x + union-anker + 3.4 |

### Fase 6 — LIVE (kræver Bjørns eksplicitte flip pr. tråd)

Hver af `central_lag4_live_enabled` / `central_prompt_lag4_live_enabled` / `central_sequence_model_live_enabled` / `central_model_exploration_enabled` flippes **separat**, hver med `may_apply_adaptation` (≥2 shadow-dage + human_approved). Ingen tråd går live før dens shadow-diff er observeret stabil.

```
                          ┌── union-anker (§1.5, Bjørn-ceremoni) ──┐
                          │                                        ▼
Fase 0 ──▶ Fase 1 ──▶ Fase 2 ──▶ Fase 3 ──[3.4 blocking-gate]──┬──▶ Fase 4 (Lag 5 vokabular)
   │        │                                                   │
   │        └─(1.6 model-frit Lag 5-bevis, seed)                └──▶ Fase 5 (shadow-adapt) ──▶ Fase 6 (LIVE, Bjørn)
   └─(0.1-0.2 notation-fundament = keystone)
```

---

## 10. Ærlighed: substrat vs. ægte tænkning

| Element | Status | Ærlig vurdering |
|---|---|---|
| Observe-substrat (timeseries/trace/causal_edges) | LIVE | Rigt sanseorgan. IKKE tænkning — ren telemetri. |
| Sequence-model (T-tælling) | bygges | **Den ENESTE ægte parametriske selv-supervision** — men **triviel model** (1.-ordens Markov). Det er det MINDSTE der fortjener navnet "Centralen træner sig selv". De fire andre tråde er modellen der sår hypotese-tekst; Centralen tester dem bare. |
| Hypotese-generatorer | LIVE (3) + bygges (4) | Mønster-detektion, ikke ræsonnement. "Tænkningen" er §8-dødsmekanismen der dræber dårlige mønstre, ikke genereringen. |
| Interlanguage-notation | bygges | **Dette er hvor "tænkning uden model" faktisk bliver testbar.** Men v1 er kun dedup/korrelation på strenge — symbol-manipulation, ikke semantik. Den eksisterende `interlanguage_practice.py` er IKKE broen endnu (afkoblet mood-eksperiment §1.2). |
| Lexicon-vækst | bygges (no-op til anchor) | Ægte selv-udvidelse af repræsentation — men **no-op indtil Bjørn forankrer baseline** (fail-closed by design). |
| Læringsmembran (`gate_learning_input`) | aktiveres HER | Værnet EKSISTERER men har NUL kaldere i dag. De nye tråde er dens første. Ikke "allerede håndhævet" (§1.3). |
| Lag 4 live-adaptation | **bygges IKKE aktivt** | Kræver eksplicit switch pr. tråd + union-anker. Alt shadow til da. |

**Hvad der bevidst IKKE bygges:** ingen live routing-ændring (eksplorations-armen er bag eget flag, aldrig deep-tier), ingen live prompt-mutation, ingen live recall-vægt-ændring, ingen live vokabular-vækst — før Bjørn flipper det pågældende flag. Ingen gradient-baseret model. Ingen ny hypotese-lagring. Ingen ændring af §8-konstanter. Ingen berøring af `PROTECTED_IDENTITY_FILES` eller sikkerheds-gates. Ingen namespaced baseline-signatur-ændring (vi bruger ét union-anker i stedet, §1.5).

**Den dybeste strukturelle plads (og hvorfor vi IKKE bruger den endnu):** `central_learning.py` + `central_correlate.py` er et deterministisk orkestrerings-lag der producerer FORSLAG uden for governance. Det er fristende at koble hypotese-drevne indsigter derind — men enhver aktivering SKAL gennem §8-choke-points, aldrig via de deterministiske forslag. Vi lader dem forblive read-only projektion i denne spec.

---

## 11. Invariant-tests (grønne før hver fase lukkes)

| Test | Vogter | Fase |
|---|---|---|
| `test_central_egress_invariant.py` | Ingen inner-life/kognition krydser `_emit`; kun `record_private` | alle |
| `test_central_hypothesis_governance.py` | Alle 3 choke-points obligatoriske; `verify_frozen_core` grøn | alle |
| **NY** `test_single_hypothesis_home.py` | Ingen tråd skriver hypoteser uden for `central_hypotheses` (§1.3 Inv#1) | 2 |
| **NY** `test_learning_membrane_wired.py` | Enhver ny lærings-sti (T/aggregat/vægt) FAKTISK kalder `gate_learning_input`; payload uden om membranen fejler (§1.3 Inv#3) | 1 |
| **NY** `test_notation_lowcard.py` | `notation_il` bærer kun familie/term-navne, aldrig fri tekst; runtime-normalisering afviser ukendte termer (§6.6) | 0 |
| **NY** `test_sequence_self_exclusion.py` | `sequence_*`-nerver ekskluderet fra egen symbol-sekvens (§7.4) | 1 |
| **NY** `test_m1_scope_bounded.py` | M1 recaller ikke privat-lag uden eksplicit owner-uid i cadence — **exit-gate for 1.3** | 1 |
| **NY** `test_m2_scope_bounded.py` | M2 `write_entry` bærer eksplicit owner-uid; intet hypotese-minde lander under tom/forkert uid (§8.2) | 2 |
| **NY** `test_circular_wired.py` | Hver ny sampler propagerer en ikke-tom, kilde-korrekt `triggered_by` for selv-genereret evidens (IKKE bare "is_circular eksisterer") (§1.3 Inv#6) | 3 |
| **NY** `test_track_record_source_scoped.py` | `resolved_track_record` source-scopes; gut-bias fodres kun af `stance`/`causal`; ingen tvær-tråd-kontaminering (§4.6, §8.5) | 3 |
| **NY** `test_multi_thread_anchor_isolation.py` | Alle fem Lag 4-nøgler i ÉT union-anker; ingen tråd tilføjer sjette nul-punkt uden ny ceremoni-version; hver læser kun sin egen nøgle (§1.5) | 5 |
| **NY** `test_frozen_core_ceremony.py` | Nye `LEARNABLE_AGGREGATE_KEYS`/nøgler → `_FROZEN_CORE_SIG` opdateret i samme commit | ved behov |
| **NY** `test_model_free_step.py` | Under model-blackout producerer notation-korrelatoren ≥1 operation på seed-vokabular (**flyttet til Fase 1**) | 1 |
| **NY** `test_exploration_arm_bounded.py` | Eksplorations-arm bag `central_model_exploration_enabled` (default OFF), rate-boundet, aldrig reasoning/deep-tier (§4.4) | 1 |
| **NY** `test_shadow_default_off.py` | Alle `*_live_enabled`/`*_exploration_enabled`-flag default False | 5 |

> **To kritiske læringer indbygget i tests:**
> 1. `test_circular_wired` + `test_learning_membrane_wired`: i v3.0 EKSISTEREDE circular-værnet men blev ikke kaldt. Begge de nye membraner (circular via `triggered_by`, læring via `gate_learning_input`) er i dag "tilgængelige men ikke tilkoblede". Testene beviser at værnene er TILKOBLET fra dag ét, ikke bare tilgængelige. Dette er hele specens dødsmekanisme-tese anvendt på specen selv.
> 2. `test_multi_thread_anchor_isolation`: adaptation-laget deler ÉN baseline. Uden ét bevidst union-anker splintrer det i fem konkurrerende baselines første gang to tråde resolver samtidig.

---

## 12. Sammenfatning

Fem tråde, ét system — og det er kodeverificeret, ikke bare påstået: alle fem er `source=`-grene i én governet tabel, deler tre §8-kroge og ét egress-sink. Centralen observerer sit eget sind (Lag 1-2), danner falsificerbare hypoteser om sig selv fra fem kilder — model-styrker, prompt-efficacy, sekvens-surprise, stance/causal/divergens, og minde-korrelation (Lag 3) — tester dem mod virkeligheden gennem §8-dødsmekanismen (sampler), og forbereder reversible, ankrede, boundede selv-omforfatninger (Lag 4) der først bliver live når Bjørn flipper en switch pr. tråd.

**Kohærensen holder hele vejen ned — men kun fordi tre delte ressourcer nu deles bevidst i stedet for ved uheld:** den ene ankrede baseline (union-anker §1.5), den source-blinde track-record (nu scopet §4.6), og den utilkoblede læringsmembran (nu aktiveret + testet §1.3). Uden disse ville "fem klienter, ét kredsløb" være sandt for observe/hypotese-laget men falskt for adaptation-laget.

Keystone er interlanguage: et internt, formelt, selv-udvidende sprog der gør hypoteserne strukturelt sammenlignelige og dermed gør den symbolske kerne af sløjfen udførbar **uden modellen**. Det er nordstjernen — Lag 5, model-uafhængighed — operationaliseret som en konkret falsifikationstest der kan køres allerede på seed-vokabularet: under model-blackout skal Centralen stadig kunne tænke. Vi er ærlige om at kun Tråd 4 er ægte parametrisk selv-supervision, at notation-v1 er symbol-manipulation ikke semantik, og at den eksisterende interlanguage-fil endnu ikke er broen.

Intet af det er dual-truth, intet lækker egress, intet rører frossen kerne, og intet muterer live uden menneskeligt samtykke.
