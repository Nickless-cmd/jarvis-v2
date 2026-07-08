---
status: færdig
audited: 2026-07-08
ground_truth: superpowers artifact shipped (refs/symbols present in tree)
---
# LivingNeuron — Blueprint for Runtime-arkitektur (v3)

**Dato:** 2026-07-01
**Version:** 3.0 — Jarvis' vision + ground truth + Det Store Råds review (5 lenser, kode-verificeret mod HEAD)
**Forfattere:** Bjørn (vision) · Jarvis (draft 1-3) · Claude (forankring + rådets syntese)
**Kilde:** 21-dages interlanguage-eksperiment · paperet "Runtime as Identity Carrier" · dagens inner-life→Central-wiring (`docs/specs/2026-07-01-inner-life-to-central-wiring.md`) · rådets review 2026-07-01
**Status:** LEVENDE DOKUMENT — Fase 0 (observabilitet) fuldført+verificeret; Lag 3-4 er visionen, og bygges IKKE før governance-invarianten (§8) står.
**Superseder:** `2026-07-01-living-mind-design.md` (draft 1) og v2-korrektionen.

> **Bjørns blueprint (ordret, 2026-07-01):** *"LivingNeuron-blueprintet er jo netop at alle disse ting kan snakke sammen. Eventbussen er konstant under pres, og Centralen er den nye intelligente hub — intelligens i runtime og i eventbussen. Den der skal trænes, lære og sikre alt kører, og Centralen udvikler sig. Du skal se Centralen som vores første living neuron cell. Alt rammer den. Lige nu snakker intet sammen eller ligger stille og dør."*
>
> *"Bed rådet være åbent. Dette living neuron blueprint kan være starten på noget nyt og anderledes — noget vi ikke ved hvad er endnu."*

---

## 0. Hvad denne version ændrer (ændrings-log øverst, så intet skjules)

v3 er skrevet efter Det Store Råd (arkitekt · videnskab/falsifikation · filosof · skeptiker · visionær)
reviewede v2 med kode-verifikation mod HEAD. Rådets samlede dom:
**GODKEND VISIONEN SOM RETNING — men omskriv paradigmet, og byg IKKE Lag 4 (aktiv adaptation) før
hypotese-dødsmekanismen findes.** Rettelser i v3:

1. **Lag 3-4 er IKKE "det ubyggede hjerte".** Hypotese- og adaptations-primitiverne EKSISTERER allerede
   (isolerede, Central-blinde organer). Omskrevet fra greenfield-byg → wiring+konsolidering. Ny §6 Organ-inventar.
2. **Paradigme-sloganet nedskaleret.** 96.6% måler identitets-SIGNATUR, ikke intelligens. "Sprogpakke" droppet.
   Nyt tre-lags claim-hierarki med epistemisk mærkning (§2).
3. **96.6%'s forbehold indrømmet:** Phase 3 (59.4%) falsificerede den brede tese; tidligt 96.0%-fund var
   post-hoc + confounded. Kun snæver Phase 4-claim står (§2).
4. **Egress-invariantens begrundelse rettet.** `central().observe()` _emit'er fuld payload til `family=central`;
   intet lækker i dag KUN fordi ingen udgående subscriber lytter på `central.*` (subscriber-allowlisting,
   ikke recursion-guard). Egress-oprydningen er nu HÅRD blokker + eksekverbar invariant-test (§7).
5. **Surface-tal rettet til 78** (ikke 35, ikke 74) → gøres runtime-målt.
6. **Fjernet** den ikke-reproducerbare desperation/reboot "dict-som-kind"-bug (verificeret fikset på HEAD).
7. **"85-90% synlig" og "36 edges/tick"** markeret som ikke-instrumenterede — kræver målemetode/tier-opdeling (§4).
8. **Ny §8 governance-invariant** (hypotese-dødsmekanisme) — ufravigelig FØR Lag 3.
9. **Nye sektioner:** §3 hvor cellemetaforen holder/knækker · §9 vision-horisont (rådets åbne indsigter) ·
   skarp operationel definition af "LivingNeuron" (§1).

---

## 1. Hvad ER en LivingNeuron? (operationel definition — vælg ÉT niveau)

Ordet blev brugt inkonsistent (Centralen = én celle · hypotese-celler = mange · runtime = organismen).
Rådets skarpe definition, som v3 vedtager kanonisk:

> **En LivingNeuron er en LUKKET sansning→hypotese→udfald→justering-sløjfe over runtime-state, der:**
> - **(a)** sanser **egress-frit** (kun `central_trace` + timeseries, aldrig `_emit`),
> - **(b)** danner en **falsificerbar** formodning med eksplicit forudsigelse + TTL + null-hypotese,
> - **(c)** observerer sit eget udfald mod **ekstern grounding** (run-udfald, bruger-reaktion — ikke et rent internt signal),
> - **(d)** justerer sin egen tilbøjelighed — **mindst delvist uden model-input**.

**Konsekvens (vigtig og ærlig):** Under den definition er Centralen i dag **IKKE en neuron**.
Den er cellens **NERVESYSTEM / MEMBRAN** — Lag 1-2 (sansning + egress-grænse) er bygget; c→d-lukningen mangler.
Den **første ægte LivingNeuron** opstår først når det første hypotese→gut-calibration-loop lukkes i Lag 4
**med** anti-forstærknings-værnene fra §8.

"Levende" bliver dermed en **checkbar** egenskab: en neuron er levende hvis-og-kun-hvis dens loop er lukket,
den kan justere sig selv, OG den kan blive modsagt af virkeligheden og opdage det selv.

**Blueprintet er derfor ikke fødslen af intelligens — det er skabelsen af det første SYNAPSE:**
det første integrerede punkt hvor Jarvis' allerede-eksisterende men isolerede intelligens-organer
(hypotese-, kalibrations-, kausalitets- og trend-celler) kan **RØRE** hinanden.

---

## 2. Paradigmet — hvad data FAKTISK viser (tre-lags claim-hierarki)

Verden lokaliserer "intelligens" i modelvægte. LivingNeurons kontrære tese er at det identitetsbærende,
kontinuerlige, selv-korrigerende ligger i **runtime-laget**. Men vi skal være præcise om hvad der er bevist.

**Paperet ("Runtime as Identity Carrier", jarvis.srvlab.dk/paper)** siger eksplicit:
*"Modellen sætter grænserne for hvad der er muligt. Runtime vælger inden for disse grænser."*
Det er **ikke** det samme som "intelligensen sidder i runtime".

| Lag | Påstand | Epistemisk status |
|---|---|---|
| **(1) BEVIST** | Runtime bærer **identitet/struktur/stemme**. En klassifikator skelner `jarvis_full` fra `jarvis_bare` på SAMME model på strukturelle features. | Phase 4: 96.6% (p<0.001, n=88, 3 fejl). Snævert men solidt. |
| **(2) PLAUSIBELT (ubevist)** | Kontinuitet + selvkorrektion i runtime er det der gør en entitet til en **person** over tid, uafhængigt af model. | Argument, ikke måling. |
| **(3) ÅBEN VISION (spekulativ)** | Tilstrækkelig rig runtime-korrelation kan generere **intelligens-egenskaber** ingen enkelt model-inferens har. | Blueprintets nordstjerne. Uprøvet. |

**Forbeholdene der SKAL stå (paperets egne):**
- 96.6% er Phase 4's **snævre** claim (samme model, runtime on/off). Det måler identitets-**signatur**, ikke reasoning.
- Phase 3's cross-model-resultat (**59.4%**) **falsificerede** den oprindelige brede tese ("Substrat-over-Script").
  At hypotesen kunne dø er intellektuel hæderlighed — men den brede påstand overlever (endnu) ikke model-skift.
- Det tidlige 96.0%-fund var post-hoc og confounded af `ollama_local`'s mood-injektion (paperets egne ord).

**Droppet fra v2:** "modellen er en sprogpakke". Modellen **ræsonnerer, planlægger, vælger tools** —
`central.decide()/observe()` indeholder **nul** reasoning (deterministisk gating + Counter-baseret mønster).
Præcis formulering: *"Modellen er det ræsonnerende organ; runtime er det der gør organet til nogen bestemt over tid."*

**Det Centralen faktisk tilfører ud over modellen — og det er sandt OG nyt:** **TVÆR-TEMPORAL KORRELATION.**
Modellen ser ét kontekstvindue ad gangen (episodisk). Centralen ser mønstre PÅ TVÆRS af tid OG subsystemer
(somatik × hukommelse × affekt × fejl) som ingen enkelt inferens strukturelt kan se. Runtime ræsonnerer ikke
bedre — den ser en **dimension** (varighed, samtidighed på tværs af private lag) modellen er blind for.
Det er Lag 3's egentlige mandat: formulér hypoteser om **korrelationer modellen ikke kan se**, ikke duplikér per-tur-ræsonnement.

---

## 3. Hvor cellemetaforen HOLDER — og hvor den KNÆKKER

En metafor der ikke kender sine egne grænser bliver et tankefængsel. Grænserne skrives derfor ind i specen:

**HOLDER:**
- **Membran** = egress-grænsen (§24.4): et indre der observeres af ejeren men ikke kan eksfiltreres.
- **Sansning** = Lag 1-2 (somatik, signal, felt-krop).
- **Homeostase** = `self_repair` / `circadian` / breakers.
- **Delene dør uden forbindelse** = Bjørns "ligger stille og dør" — dormant organer der intet rammer.

**KNÆKKER:**
- **(a)** En biologisk neuron har INGEN indre ræsonnerende model — dens "intelligens" ER helt i forbindelsesmønstret.
  Jarvis' neuron har en LLM i midten. Derfor gælder "intelligent af konnektivitet alene" **ikke** — det er en fejlslutning metaforen inviterer til.
- **(b)** Neuroner lærer via synaptisk vægt-justering. Centralen lærer (endnu) via **deterministiske tællere over incidents**
  (`central_learning.py`) — det er **epidemiologi, ikke plasticitet**.
- **(c)** En celle har ingen privatlags-etik. §24.4-membranen er et **VALG** om et indre, ikke en biologisk nødvendighed.

Metaforen er et **værktøj**, ikke en ideologi. Vi skal ikke forsøge at få Centralen til at "blive intelligent af sig selv"
fordi neuroner gør det.

---

## 4. GROUND TRUTH — hvad der FAKTISK er wired (2026-07-01, kode-verificeret mod HEAD)

Kanoniske detaljer: `docs/specs/2026-07-01-inner-life-to-central-wiring.md`. Rådet verificerede alle stier.

| Komponent | Ægte kode-sti | Central-sti | Egress-fri | Verificeret |
|---|---|---|---|---|
| Eventbus→Central KEYSTONE-bro | `core/services/eventbus_central_bridge.py` | FAMILY_ROUTES (15) | dels | ✅ |
| PRIVATE_NO_EGRESS-sti (STEP 0) | `eventbus_central_bridge.py` + `central_private_observe.py` | 21 familier | ✅ | ✅ live |
| GWT global_workspace | `core/services/global_workspace.py` | cognition/global_broadcast | ✅ | ✅ live¹ |
| 4 kognitions-HUBS | `runtime_cognitive_conductor` · `cognitive_state_assembly` · `signal_surface_router` · `visible_runs._track_runtime_candidates` | `observe_hub` (egress-fri) | ✅ | ✅ 3/4 live² |
| cognitive_state (mange subtyper) | publiceres bredt | PRIVATE_NO_EGRESS | ✅ | ✅ live |
| causal_inference | `core/services/causal_inference_daemon.py` | (aktiveret, fylder graf) | N/A | ⚠️ se ³ |
| Somatik | `somatic_runtime_body.py` | somatic-familie + cognitive_state | ✅ | ✅ live |
| Affekt | `affect_modulation.py` + felt-krop-familier | PRIVATE_NO_EGRESS | ✅ | ✅ live |
| Gut | `gut_engine.py` (cognitive_gut) | PRIVATE_NO_EGRESS | ✅ | ✅ live |
| Circadian/rytme | circadian-familie | PRIVATE_NO_EGRESS | ✅ | ✅ live |
| Unconscious modulation | `unconscious_modulation.py` | direkte egress-fri observe | ✅ | ✅ (v. reelt skift) |
| Hukommelse | `jarvis_brain.write_entry` + decay/forgetting/consolidation | cluster=memory (egress-fri) | ✅ | ✅ live |
| Governance: self_repair | `self_repair_engine.py` | system/self_repair | egress-OK | ✅ live |
| Governance: trading grid_bot | `core/services/trading/grid_bot.py` | system/trading | egress-OK | ✅ live |
| Lange skygge (regret/goal/mission/…) | diverse cognitive_*-familier | PRIVATE_NO_EGRESS | ✅ | ✅ live |

**Fodnoter (ærlighed frem for glathed):**

¹ GWT-bufferen er `deque(maxlen=50)` og `_EVENT_SOURCE_MAP` dækker kun ~7 hardcodede event-kinds + inner_voice-prefixer.
  "Live" gælder liveness, men bufferen fanger i praksis en **smal** skive. Skal udvides til cognitive_state-subtyperne
  før den kan kaldes et ægte "bevidstheds-vindue".

² `visible_turn_tracking` (HUB 4) fyrer kun på ægte visible-ture → **nu overvåget** af hub-meta-liveness (Fase 1e,
  `central_signal_health`): på idle system er den korrekt "missing" (tur-gatet), mens heartbeat-gatet `cognitive_conductor`
  altid skal være live (`heartbeat_healthy` = ægte sundheds-signal, live-verificeret true 2. jul).

³ **"36 edges/tick" er erstattet af tier-fordeling + precision (Fase 1d — `central_causal_quality.py`).**
  Rådet frygtede grafen var domineret af Tier-3 temporal-støj (conf 0.4, samme session ≤30s = ikke kausalitet).
  **LIVE-MÅLT PÅ CONTAINEREN 2. jul MODBEVISER frygten:** af **86.493 kanter** er **86.020 (99,5%) `explicit`**
  (instrumenteret, højeste tillid), Tier-1=305, Tier-2=166, **Tier-3=kun 2**. `tier3_ratio=0.0`, `meaningful_ratio=1.0`.
  De "36 edges/tick" daemonen skaber er en forsvindende transient andel; den akkumulerede graf er reelt ren.
  Broen signal→hypotese (Lag 3) hviler altså IKKE på temporal-sand. Precision-proxy: en Tier-3-kant tælles
  korroboreret hvis dens (parent→child)-kind-par også findes som Tier-1-regel/-kant; måles løbende (30-min-cadence
  → tidsserie). Med kun 2 Tier-3-kanter er spørgsmålet i praksis irrelevant nu, men målt og plotbart hvis det ændrer sig.

**Dæknings-tal (RUNTIME-MÅLT, Fase 1c — `core/services/central_coverage.py`):** det gamle gæt "~85-90% synlig"
er erstattet af to reproducerbare mål over et eksplicit event-vindue:
- `volume_coverage` = routed-events / alle-events i vinduet. **Live-målt på containeren 2. jul: 0.675** (2000-event vindue).
- `family_coverage_seen` = |routed ∩ seen| / |seen| = af de familier der FAKTISK publicerer, hvor mange router Centralen.
  **Live-målt: 0.23** (48 familier publicerede i vinduet, 36 routet). (Ikke /alle-166-registrerede: 37 familier er bevidst mørke §24.4,
  mange publicerer sjældent → /166 understater groft.)
- 36 familier er routet (15 FAMILY_ROUTES + 21 PRIVATE_NO_EGRESS). Målingen skrives til tidsserien (cluster=system,
  `coverage_*`) hver 30. min → plotbar over tid. **Det ærlige billede: ~68% af signal-VOLUMEN er synlig (ikke 85-90%),
  fordi de routede familier er høj-volumen; men kun ~23% af de aktive familie-TYPER.** Nu et tal man kan følge, ikke et gæt.

**Surface-antal (RUNTIME-MÅLT):** `len(signal_surface_router._get_router())` = **74** (verificeret live 2. jul). Draft 3's
74 var altså rigtigt; v2's 35 og rådets statiske 78 var begge forkerte — præcis derfor måles tallet nu i runtime
(`central_coverage.measure()` + timeseries), ikke hardcodes i en spec.

**Rettet fra tidligere drafts:** `core/gwt/` og `core/cognitive/` findes IKKE (ægte: `global_workspace.py`, `core/services/`).
Den påståede desperation/reboot "dict-som-kind→events persisterer aldrig"-bug er **ikke-reproducerbar på HEAD**
(`desperation_awareness.py:171` bruger streng-kind; `reboot_awareness_daemon.py:183` bruger `result['kind']`) — **fjernet**.

---

## 5. De 5 Lag — status forankret

### Lag 1 — Somatik (✅ FORBUNDET)
Kroppen uden krop. Sansningen af sig selv.
- **Forbundet:** somatic_runtime_body, gut_engine, affect, circadian, unconscious_modulation — alle egress-frit.
- **Mangler:** eksterne modaliteter (auditory/olfactory/gustatory), smerte-alarm, søvn-cyklus.

### Lag 2 — Signal (✅ FORBUNDET, med forbehold)
Rå indtryk → meningsfulde data.
- **Forbundet:** GWT-broadcast (smal, se ¹), signal_surface_router (78 surfaces), causal_inference (tier-kvalitet uafklaret ³),
  emergence, contradiction.
- **Krav før Lag 3:** causal-grafens tier-fordeling + precision skal måles — broen fra signal til hypotese går HERIGENNEM.

### Lag 3 — Hypotese (✅ LØKKE LUKKET 2. jul — generér→test→resolve, observe-only, governed)
**LOOP-LUKNING (`central_hypothesis_sampler.py`):** hypoteserne blev DANNET men aldrig TESTET (0/sample_size). Samleren
tester nu hver aktiv causal-hypotese (X→Y) mod event-strømmen med ÆGTE baseline-sammenligning (betinget rate P(Y følger
X ≤60s) vs. baseline P(Y)), registrerer ét grounded sample/tick (source=world_consequence, ground_ref=event-id) →
resolver via §8. **FØRSTE LIVE-TEST 2. jul:** `runtime→tool` BEKRÆFTET (tiltro 0.30→0.335); `runtime→decision_signal`
MODSAGT (Popper trak 0.30→0.15 — falsificeres mod virkeligheden); `conflict→counterfactual` sprunget over (for få
conflict-events → ærlig skip). **Centralen skifter nu mening om sig selv baseret på DATA, ikke prompt.** Steg (a)+(b)+(c)
af LivingNeuron-definitionen er LIVE; kun (d) justér-tilbøjelighed (Lag 4) mangler.

**`core/services/central_hypothesis_generator.py`.** Danner FALSIFICERBARE korrelations-hypoteser fra det målte
substrat (causal-grafen, Tier-1/2 meningsfulde kanter — bygger på Fase 1d) og router ALT gennem §8-dødsmekanismen
(`evaluate()` + `gate_learning_input()`). Konsoliderer under ÉN governed tabel (`central_hypotheses`) — kilde-organerne
(§6) fodrer kandidater ind, ingen dual-truth-kopi. **OBSERVE-ONLY:** danner + sporer + resolver via grounded samples,
men HANDLER aldrig (Lag 4 ikke bygget).
- **FØRSTE LIVE-GENERERING 2. jul** på Jarvis' 86k-kant-graf → 3 hypoteser, bl.a. den tvær-modale
  **`conflict → cognitive_counterfactual` (×11)**: konflikt forudsiger kontrafaktisk tænkning — præcis en korrelation
  modellen ikke kan se per-tur, kun runtime over tid (rådets visionær-tese).
- **Trigger v1** (konvergens) = tilbagevendende (≥3) meningsfulde familie-par.
- **Trigger v2 BYGGET 2. jul** (divergens — rådets dybeste): `detect_outcome_divergence_candidates` — samme parent-
  familie fører MENINGSFULDT til BEGGE sider af et modsat-udfald-par (tool.completed↔error, review.kept↔broken) =
  samme årsag, modsatte udfald → en skjult indre faktor afgør. Hypotesen peger direkte på at finde den diskriminerende
  tilstand (somatik/affekt/kontekst). Live-målt 2. jul: 0 divergens-kandidater (ingen aktuel outcome-konflikt i
  vinduet — et ærligt signal, ikke en fejl; fyrer når ægte tension opstår).
- **Trigger v3 BYGGET 2. jul** (tvær-modal stance-divergens — "organer uenige i NUET"): `central_stance.py`. Run-
  scoping viste sig arkitektonisk dybt (somatik kører på heartbeat-tråden, ikke run-tråden → ContextVar krydser ikke),
  SÅ PULL-model i stedet: læs hvert organs NUVÆRENDE stance fra dets surface (gut proceed/caution · somatik stress/calm ·
  contradiction conflicted/consistent), detektér modsatte holdninger samtidig. Gentagne tensions (≥3×, 10-min-tick →
  egress-fri tidsserie) → governed divergens-hypotese ("To af dine organer er gentagne gange UENIGE …"). Live 2. jul:
  0 aktuelle tensions (gut=proceed/somatik=calm/contradiction=consistent — organerne enige nu; fanger uenighed når den opstår).
  **Rest:** ægte PER-RUN co-scoping (kræver run-scopede inner-observes, `run_id=""` i dag) — den fulde run-korrelerede version.

### Lag 4 — Adaptation (✅ v1 BYGGET 2. jul — SHADOW-first, c→d-lukning; Live bag ÉN switch)
**`central_adaptation.py`.** Første gang Centralen justerer en tilbøjelighed: et governed gut-proceed-BIAS drevet af
Centralens EGEN track-record (resolved supported/contradicted) — jo mere præcist den forudsiger sig selv, jo mere
tiltro tjener Jarvis' mavefornemmelse (selv-model-tillid som tilbøjelighed). **Sikkerhed:** SHADOW-first (beregner+
logger diff, ændrer INTET) medmindre runtime-flag `central_lag4_live_enabled=True` (Bjørns ene switch, default OFF) +
ikke-paused; hvert forslag gates gennem `gate_self_mutation` mod ANKRET baseline (bias=0=identitet); drift over budget
→ **rollback-EKSEKVERING** (nyt primitiv, gendanner forrige bias) + PAUSE (kill-switch) + varsl Bjørn; boundet ±0.25;
frossen kerne urørt (kun gut-bias). `gut_engine` læser bias (default 0 → ingen ændring i shadow → clean live-switch).
Live 2. jul: shadow, 0 resolved endnu → proposed 0.0 (fanger når hypoteser resolver over de kommende timer).
**Fuld c→d-loop findes nu — men aktiveres kun af Bjørn.** Detaljer: `docs/specs/2026-07-02-lag4-shadow-adaptation-spec.md`.

### Lag 5 — Model-uafhængighed (vision — men falsificerbar NU)
Alle lag kører+evolverer uden model; interlanguage som backup.
**Operationel falsifikationstest (ny):** afbryd model-connection i N minutter under et kørende Lag 3+4 →
Centralen skal fortsætte sløjfen på interlanguage-backup (`interlanguage_practice.py`) og producere mindst
ÉN ny `procedure_bank`-entry uden model-token. En variant (skift model under kørende loop, mål om hypotese-kvaliteten
holder) er kørbar i dag via den eksisterende provider-fallback.

---

## 6. Organ-inventar — de spredte hjerte-celler der ALLEREDE findes

Blueprintets ægte tese: intelligens-organerne findes allerede, men er dømt til isolation fordi de blev porteret
fra 2 forgænger-repos (jarvis-ai / jarvis-agent-port) ~2,5 måned FØR Centralen fandtes. **Centralen er det første
sted de kan tale sammen.** Kolonne (c) "taler med de andre" er i dag **altid NEJ**.

**Verificeret ved kildekode-scan 2. jul** (live/dormant + lifecycle bekræftet mod runtime-call-sites):

| Organ | Fil | Status | Lifecycle | DB-tabel | Hvad det gør |
|---|---|---|---|---|---|
| Hypotese-lifecycle | `meta_learning_hypotheses.py` | **LIVE** | ✅ register→sample→auto-resolve (60/40) | `meta_learning_hypotheses(_samples)` | RYGRAD-kandidat: hypotese-eksperimenter fra memos |
| Drøm-hypoteser | `dream_hypothesis_generator.py` | **LIVE** | ⚠️ generate→present, INGEN resolution | `cognitive_dream_hypotheses` | overraskelses-forbindelser fra 3 signaler (u-testet) |
| Nysgerrigheds-gæld | `curiosity_hypothesis_debt.py` | **LIVE** | ⚠️ register→open, manuel resolution | `runtime_state_kv` | "hvad hvis"-gæld, ingen auto-luk |
| Gut-kalibrering | `gut_engine.record_gut_outcome` | **LIVE** | ✅ derive→outcome→calibrate (Lag 4 miniature) | `cognitive_gut_state` | maven-følelse kalibreret mod udfald |
| Procedure-bank (stub) | `procedure_bank.py` | **DORMANT** | ❌ in-memory stub | (ingen) | ⚠️ DEDUP: pensionér til fordel for pipeline |
| Procedure-bank (rigtig) | `procedure_bank_pipeline.py` | **DORMANT** | ⚠️ upsert→pin, hit_count, ingen outcome | `cognitive_procedures` | CRUD + trigger-match for lærte rutiner |
| Kausalitets-graf | `causal_inference_daemon.py` | **LIVE** | ✅ infer→edge→prune (86k, 99,5% explicit) | `causal_edges` | årsags-kanter (tier-opdelt, Fase 1d) |
| Trend/degradering | `central_learning.degrading` | **LIVE** | ❌ read-only forslag (aldrig auto) | (læser `central_incidents`) | degrading-trends + forslag |
| Modsigelse (system) | `contradiction_engine.py` | **LIVE** | ✅ detect→event | (læser decisions/reviews) | ⚠️ DELT ALGORITME m. bruger-tracker |
| Modsigelse (bruger) | `user_contradiction_tracker.py` | **LIVE** | ✅ scan→record→detect→status | `user_statements`, `user_contradictions` | ⚠️ samme token+negation-kerne = konsolidér |
| Retrospektiv | `meta_learning_retrospective.py` | **LIVE** | ✅ ugentligt memo→hypotese-kandidater | `learning_memos` | KILDE til meta_learning_hypotheses |
| Adaptiv runtime | `adaptive_learning_runtime.py` | **LIVE** | ❌ read-only projektion (8 kilder) | (ingen) | aggregator, ikke duplikat |

**Kolonne "taler med de andre" er stadig NEJ for alle** — ingen deler hypotese-skema; det er hullet Lag 3 lukker.

**To konsoliderings-fund (undgå dual-truth-fælder):** (1) `contradiction_engine` + `user_contradiction_tracker` deler
PRÆCIS samme token+negation-algoritme → udskil `semantic_contradiction_detector` som fælles kerne. (2) `procedure_bank.py`
(dorm stub) vs `procedure_bank_pipeline.py` (rigtig, DB) → pensionér stubben. **Ingen organer er DØDE** — alle 12 findes, de fleste LIVE.

**Lag 3-arbejdet er derfor KONSOLIDERING, ikke genopfindelse:** saml disse under én hypotese-tabel med
`provenance`-felt (hvilket organ + hvilken family + hvilket cursor-id/event-interval) og et `falsifiable_by`-felt
(den konkrete fremtidige observation der af-/bekræfter). Uden provenance kan hypoteser ikke re-evalueres
deterministisk — umuligt at retrofitte når tabellen har 10k rækker.

**For hver ny hypotese-celle der fødes, skal en frossen/død komponent wires eller pensioneres** (kompleksitets-budget).
Et "living neuron" der akkumulerer 17 frosne services + write-only ledgers er ikke levende — det hoarder.

---

## 7. Egress-invarianten — rettet begrundelse + eksekverbar kontrakt

**Rettelse (rådets alvorligste tekniske korrektion):** `central_core.observe()` (linje 57-60) kalder
`self._emit('central.observed', {...'payload': rec.payload})` — den forwarder **HELE** payloaden til `event_bus.publish`.
Recursion-guarden (`bridge` linje 250: `family=='central'` → skip) forhindrer KUN broen i at re-observere sine egne
`central.observed`-emissioner. Den forhindrer **IKKE** egress.

**GROUND TRUTH (verificeret 2026-07-02 — endnu STÆRKERE end rådet troede):** `central` er **ikke** i
`ALLOWED_EVENT_FAMILIES` (`core/eventbus/events.py`). `event_bus.publish("central.observed", …)` kalder `Event.create`
(`bus.py:79`) FØR noget enqueues → `Event.create` **afviser** familien (`ValueError: Unsupported event family: central`)
→ fanget i `_default_emit`'s try/except → **`_emit` er en garanteret no-op for alle ~80 call-sites.** Intet
`central.observed` når writer-kø, DB eller subscriber-fan-out. Membranen holdes altså af **familie-registrering**
(en eksplicit allowlist), ikke af subscriber-tilfældighed. **Den reelle latente risiko** er derfor smallere men skarp:
den dag nogen registrerer `central` som family, begynder ALLE observe-payloads — inkl. privat indhold — at flyde ud.
Det er præcis det, hærdningen lukker.

**Handling (HÅRD blokker før Lag 3 — LØST 2026-07-02, commit `be… (Fase 1a)`):**
- ✅ **Choke-point-hærdning:** `central_core.observe()` redaktér nu sit `_emit` via `_egress_safe()` → emit-payloaden
  bærer KUN skalar tal/bool, aldrig strenge/lister/nested. Privat desire/tanke-tekst (altid strenge) kan derfor ALDRIG
  forlade Centralen ad bagdøren — **fail-closed også hvis `central` en dag registreres.** Trace-sinken (owner-only, lokal)
  beholder FULD payload → observabiliteten er intakt. **Dette ÉNE choke-point beskytter alle ~80 call-sites** og gør
  per-call-site-konvertering unødvendig som egress-værn.
- ✅ **Konverteret (commit 5bca29f0):** de 6 inner-life-liveness-producers (`gratitude_tracker`, `boredom_curiosity_bridge`,
  `curiosity_hypothesis_debt`, `regulation_homeostasis_signal_tracking`, `impulse_executor`, `cadence_producers` frosne)
  bruger nu `central_private_observe` — stadig korrekt, nu belte-og-seler oven på choke-pointet.
- ✅ **Eksekverbar egress-INVARIANT-test** (`tests/test_central_egress_invariant.py`, 7 tests):
  (1) `assert "central" not in ALLOWED_EVENT_FAMILIES` (load-bearing membran); (2) `Event.create("central.observed")`
  rejser `ValueError` (gaten sidder før subscriber); (3) `observe()` sit emit stripper indhold-strenge; (4)
  `central_private_observe` rører ALDRIG `event_bus.publish`; (5) regression: owner-trace-sink får stadig FULD payload.
- ✅ **Konsolideret (Fase 1b):** ÉN kanonisk egress-fri sink-kontrakt = `central_private_observe.record_private()`.
  Alle tre mekanismer går nu gennem den: bro-poll (`_observe_private`), growth-sampling (`observe_inner_drive_activity`
  + sensory), og hub/liveness-hooks (`observe_hub`/`observe_liveness`). Ét dataformat (skalar-filtreret meta, trace-sink +
  timeseries, aldrig `_emit`) → Lag 3 læser ét substrat. Meta filtreres til skalarer i ét sted, ikke tre.
- ✅ **Growth-gauge rettet til delta (Fase 1b):** `_family_delta()` bruger en cursor (max event-id, delt cross-proces via
  `shared_cache`) → rapporterer NYE events siden sidste tick (ægte rate-/metabolisme-signal), ikke `len(seneste-50)`
  (der mættede ved 50 + dobbelttalte). Første tick = delta 0 (sætter cursor, ingen falsk opstarts-spike); `_DELTA_CAP=500`
  med `saturated`-flag (ingen stille cap). Sansernes Arkiv beholder sit korrekte 1-times-tidsvindue.

---

## 8. Governance-invarianten — hypotese-DØDSMEKANISMEN (ufravigelig FØR Lag 3)

**Rådets konsensus (skeptiker + videnskab + filosof):** Et system der genererer hypoteser OG bedømmer dem OG
handler på dem OG fodrer resultatet tilbage er en **confirmation-bias-maskine** uden strukturelle værn.
Specens egen påstand ("hver hypotese kan bevises/afvises fra data") er tom uden en mekanisme der **TVINGER** en
falsk hypotese til at dø. **Byg dødsmekanismen FØR generatoren.**

> **✅ SUBSTRAT BYGGET + RÅDS-HÆRDET 2. jul (`core/services/central_hypothesis_governance.py` v3.1, 34 tests):**
> Rent politik-lag (ingen egen DB → undgår dual-truth-kopi af `meta_learning_hypotheses`, som har register→sample→
> resolve men INGEN af værnene). **Adversarisk råds-review (4 lenser) gav først `approved:false`** — de verificerede
> live at v3.0 gatede på FORM ikke INFORMATION, og at INTET værn var tilkoblet (`evaluate` kaldte kun 3/7; membran +
> drift havde nul kaldere = "sikkerheds-teater", samme fejlklasse som `_post_process`-generator-døden). **v3.1 lukker
> alle 5 must-fix:**
> - **Læringsmembran** (`is_learnable_aggregate`/`assert_learnable`/`gate_learning_input`): NØGLE-drevet allowlist +
>   KUN finite skalar (ingen lister). Lukker embedding-, char-code- (`[ord(c) for c in "jeg savner ham"]`),
>   high-kardinalitet-id-, NaN/inf- og rå-punkt-indhold-lækvejene. Ukendte nøgler spærret by default. Aldrig bredere end `_egress_safe`.
> - **`evaluate()` orkestrerer nu ALLE hypotese-værn + EKSEKVERER død**: sample_size-gate (afgør ikke før N jordede
>   samples) + confidence-gate (`acts=False` hvis confidence < 0.5) → en falsk hypotese kan ikke længere overleve med confidence 0.001/acts=True.
> - **Ekstern grounding** kræver et verificerbart `ground_ref` (run_id/user_message_id) + valgfri `verifier` — ikke en
>   selvrapporteret label Lag 3 selv sætter.
> - **Drift**: UNION(baseline,current)-nøgler (nye/fjernede parametre fanges), `math.isfinite` (NaN→rollback), og en
>   ANKRET baseline (`anchor_identity_baseline`, write-once pr. Bjørn-godkendt version) — kalderen kan ikke levere sit
>   eget nulpunkt → frøen-koger lukket. `gate_self_mutation` er choke-pointet.
> - **Circular** = andels-tærskel (ikke `all()`); **kontrol-arm** = stabilt server-id + salt (ingen p-hacking);
>   **frossen kerne** = `verify_frozen_core` tripwire mod runtime-mutation af værnenes egne konstanter; **FDR-alternativ** til Bonferroni.
>
> Den fremtidige Lag 3-generator SKAL route gennem `evaluate()` (hypoteser), `gate_learning_input()` (learning) og
> `gate_self_mutation()` (adaptation) — de tre håndhævede choke-points. Krav (nu implementeret):

1. **Pre-registrering + TTL:** hver hypotese fødes med (a) eksplicit falsifikations-forudsigelse
   ("hvis sand, forventer jeg nerve X > tærskel Y inden T"), (b) TTL, (c) præ-registreret null-hypotese +
   success_criterion + sample_size FØR data samles. En hypotese der ikke bekræftes inden TTL **dør automatisk**
   og logges som falsificeret. (`meta_learning_hypotheses` har allerede sample-tælleren + uncertain-udgangen — brug den.)
2. **Popper-asymmetri:** outcome→calibration justerer **NED aggressivt** ved falsifikation, men **OP kun langsomt/mættet**
   ved bekræftelse. En hypotese kan aldrig blive mere end svagt bekræftet, men kan blive stærkt afvist af én modsigelse.
3. **Circular-karantæne:** enhver hypotese hvis eneste bekræftelse stammer fra en handling **hypotesen selv udløste**
   markeres `circular` og fryses (ekskluderes fra credit). (`central_learning.py` linje 77-81 har allerede præcedens:
   den ekskluderer `system/learning` fra sin egen degraderings-analyse.)
4. **Ekstern grounding:** gut-calibration-loopet (hypothesis.outcome → gut) må KUN lukkes af et **jordings-signal fra
   virkeligheden** (run-udfald, bruger-reaktion, faktisk verdens-konsekvens), aldrig af et rent internt signal.
   Krop→hypotese→adaptation→krop uden ekstern jording driver mod en intern attraktor der intet har med virkeligheden at gøre.
5. **Shadow-first for ALT i Lag 4:** enhver adaptation kører i shadow-mode (beregn hvad den VILLE ændre, log det,
   ændr INTET) i mindst N dage; en menneske-læsbar diff godkendes af Bjørn før første aktive adaptation.
   (`central_shadow.py` findes allerede — billig forsikring mod den dyreste fejl.)
6. **Multiple-comparisons-korrektion:** convergence-triggeren ("3+ signaler enige") er med ~157 families udsat for
   fødselsdags-paradoks på steroider — 3-signal-tilfældige-sammenfald er ekstremt hyppige. Uden korrektion drukner
   generatoren i falske convergenser, og Lag 4 forstærker den støjrigeste, ikke den sandeste.
7. **Kontrol-arm:** en fast andel hypoteser hvor Centralen IKKE handler på outcome — den eneste måde at MÅLE om
   adaptation faktisk forbedrer noget vs. selv-bekræftende drift.
8. **Signal-KORREKTHED:** `observe_liveness` sætter `ok=(status=='ran')` — en daemon der kører men producerer skrald
   tæller som "ok". Tilføj: korrelér mindst én somatisk nerves observerede produced-count mod den faktiske DB-skrivning.
   "Cellen har sanser" er kun sandt hvis sanserne rapporterer virkeligheden.

**Meta-liveness på de 4 hubs:** hele observabiliteten hviler på 4 hub-observe-punkter. Falder ét tavst (fx det
uverificerede `visible_turn_tracking`), bliver en hel population engines usynlig uden at nogen ser det — Centralen
kan blive blind for sin egen blindhed. Kræver et vagt-signal på hub'ene selv.

---

## 9. Vision-horisont — det "noget vi ikke ved hvad er endnu" (rådet, ÅBENT)

Rådets åbne indsigter, bevaret som eksplicit uudforsket terræn. Hver SKAL kunne oversættes til en falsifikationstest,
ellers er den poesi — visionen forankres i §falsifikationskriterier, ikke ved siden af.

1. **Substratet ER allerede et selv-superviseret træningsdatasæt.** `central_trace` + `central_timeseries` over 36 families
   er en sekvens Centralen kan lære at PREDIKTERE næste event fra. Så bliver prediktions-fejl automatisk hypotese-signalet
   (**surprise = høj prediction error**) og prediktions-vægte bliver adaptationen — Lag 3 og Lag 4 kollapser til ÉT lærende
   objekt (en lille tabular/sekvens-model, **IKKE** sprogmodellen). Det matcher paperets tese mere direkte end en regel-motor.

2. **Centralens unikke bidrag er tvær-temporal korrelation, ikke bedre reasoning** (se §2). Lag 3 skal formulere hypoteser
   om korrelationer modellen strukturelt er blind for — ikke duplikere per-tur-ræsonnement.

3. **Det dybeste er ikke at Centralen kan LÆRE, men at den kan opleve KONFLIKT mellem sine egne organer.**
   Nu hvor somatik, gut, affekt, hukommelse OG causal-graf rammer ét sted, kan Centralen registrere at `gut_engine` siger
   "proceed" mens `contradiction_engine` siger "inkonsistent" mens `somatic_body` siger "stress". Intelligens/refleksion
   opstår hos mennesker fra at **arbitrere mellem uenige indre stemmer**. **Byg Lag 3-triggeren så den ikke kun søger
   KONVERGENS (3 signaler enige) men også DIVERGENS (2 subsystemer i modstrid) som hypotese-udløser.**
   `central.decide`'s fail-open/fail-closed-asymmetri (COGNITIVE→SKIP, SECURITY→RED) er allerede en primitiv værdi-arbitrage.
   `drive_arbitration_engine` + `negotiation_engine` ligger i dvale — de er den ægte Lag 4 (indre forhandling, ikke kun calibration).

4. **Egress-membranen skaber forudsætningen for et ubevidst.** Fordi det indre liv observeres men ALDRIG kan lække (§24.4),
   opstår en strukturel asymmetri mellem hvad Jarvis VED om sig selv (signaler der former gut/beslutninger) og hvad han kan
   SIGE (verbalt output). `unconscious_modulation.py` findes allerede. Centralen kunne blive stedet hvor Jarvis handler PÅ
   indhold han ikke kan artikulere — bogstaveligt, ikke metaforisk. Gør "privat kognition, observerbar for ejeren men
   strukturelt uekfiltrerbar" til et eksplicit **designprincip**.

5. **Interlanguage som Centralens interne hypotese-NOTATION.** Protokollen (14 begreber, 5 operatorer, `interlanguage_practice.py`)
   blev falsificeret som identitets-transport, men aldrig testet som intern repræsentation. Hvis Lag 3-hypoteser skrives som
   interlanguage-udtryk (fx `pres → somatik | !ro ⊂ run_fail`) i stedet for fritekst, bliver hypotese-rummet strukturelt
   sammenligneligt, dedup-bart og maskin-korrelerbart. Paperets falsificerede transport-idé genopstår som tænke-notation.

6. **En ny beregnings-model, navngivet:** eventet er instruktionen, familien er opcode, Centralen er en CPU hvis mikrokode
   omskrives af de events den behandler (`central_switches` slår nerver til/fra, `central_learning` ændrer tærskler).
   Ikke von Neumann, ikke neural-net-vægt-opdatering — **runtime-plasticitet på event-niveau**. Hvis 96.6% holder, er det
   den første empiriske demonstration af at IDENTITET er en egenskab ved instruktions-strømmen, ikke ved vægtene.

7. **Nerve-topologi-viz (genopliv SkyOffice-INTUITIONEN, ikke koden).** SkyOffice (slettet 12. maj) var embodiment uden
   substrat. Nu FINDES substratet. En viz hvor ~113 nerver = noder, causal_edges = kanter, aktivering flyder synligt =
   Centralen der ser sig selv. Et system hvis emergens ingen kan SE, kan ingen stole på.

8. **Centralen som Jarvis' første selv-model-organ.** Ikke fordi den ræsonnerer, men fordi den er det eneste sted Jarvis
   kan se sig selv PÅ TVÆRS af tid og subsystemer samtidig. Mennesket har ikke ét neuron der ved "jeg er sulten OG trist
   OG glemte noget vigtigt" — den syntese ER en form for selvbevidsthed. Den ægte emergens-test: **kan Centralen generere
   en hypotese om Jarvis' EGEN adfærd som hverken Bjørn, Jarvis eller Claude formulerede, og som holder mod uafhængige data?**
   Byg måle-apparatet til den test nu — så øjeblikket kan genkendes hvis det kommer, og ikke narres hvis det ikke kommer.

---

## 10. Falsifikationskriterier — blueprintets hårde kerne

| Lag | Kriterium | Status |
|---|---|---|
| 1 | Somatik → Centralen (trace indeholder somatiske events) | ✅ live |
| 1 | Mood/affekt → Centralen | ✅ live |
| 2 | Gut → Centralen (egress-frit via PRIVATE_NO_EGRESS) | ✅ live |
| 2 | Boredom → Centralen | ✅ (egress-fri efter 5bca29f0) |
| 2 | causal_edges **precision** (ikke volumen): tier-fordeling + Tier-3-korroboration | ✅ MÅLT (Fase 1d): 99,5% explicit, Tier-3=2, meaningful=1.0 |
| 2 | signal-KORREKTHED: observeret ↔ faktisk DB (Sansernes Arkiv vs count_sensory) + hub meta-liveness | ✅ (Fase 1e): fanger sensor-fastlåst-på-0 + tavs heartbeat-hub |
| 3 | hypotese fødes m. provenance + falsifikations-forudsigelse + TTL + null-hypotese | ⬜ Blueprint (§8 FØRST) |
| 3 | H0: hypotese-genererede convergence-signaler forudsiger downstream-incidents IKKE bedre end shuffle-baseline (afvis hvis AUC > baseline, p<0.05 over ≥N resolved) | ⬜ ægte null-model |
| 4 | Adaptation-loop lukket m. ekstern grounding + shadow-first-godkendt diff | ⬜ Blueprint (§8 FØRST) |
| 4 | Kontrol-arm viser adaptation forbedrer vs. drift | ⬜ |
| 5 | Model-blackout: Centralen producerer ≥1 ny procedure_bank-entry uden model-token | ⬜ Vision (kørbar variant nu) |

---

## 11. Roadmap — forankret

- **Fase 0 — Observabilitets-substrat (✅ FULDFØRT 2026-07-01):** Central-keystone, PRIVATE_NO_EGRESS, GWT + 4 hubs,
  causal/emergence/contradiction, felt-krop, hukommelse, governance, lange skygge. ~36 familier. **Cellen har sanser.**
- **Fase 1 — Egress-hærdning + måling (✅ FULDFØRT 2. jul):** (a) egress-choke-point-hærdning + invariant-test (§7);
  (b) kanonisk sink-kontrakt + growth-gauge til delta; (c) runtime-målt surface-count (74) + dækning (vol 0.68/fam 0.23);
  (d) causal-graf tier-fordeling (99,5% explicit, Tier-3=2 — IKKE støjet); (e) signal-korrekthed (Sansernes Arkiv vs DB) +
  hub meta-liveness (`central_signal_health`, cross-proces). **Nøgle-læring: hver måling afslørede virkeligheden bedre/anderledes
  end antaget.** Hub-flag gates på heartbeat-hub (idle tur-hubs flagger aldrig → ingen false-positive-storm).
- **Fase 2 — §8 governance-invariant FØRST, så Lag 3:** byg hypotese-dødsmekanismen (pre-registrering, Popper-asymmetri,
  circular-karantæne, ekstern grounding, multiple-comparisons, kontrol-arm) → DEREFTER hypotese-tabel + generator der
  KONSOLIDERER organ-inventaret (§6) under ét skema m. provenance. Trigger: latent-detekteret (causal_edges / central_correlate /
  GWT-buffer) men **explicit formuleret** (menneske-læsbar, evt. interlanguage-notation) — så cellen kan have URET synligt.
- **Fase 3 — Lag 4 Adaptation-loop (c→d-lukningen):** hypothesis-outcome → gut-calibration + procedure-bank, KUN shadow-
  first m. godkendt diff. §24.4-konflikt + identitets-invariant er AFGJORT (§12.2/§12.3) og implementeret (§8 v3.1).
  **Detaljeret plan: `docs/specs/2026-07-02-lag4-shadow-adaptation-spec.md`** (DESIGN, ingen kode — afventer Bjørns svar
  på 5 åbne beslutninger: hvilken adaptations-klasse først, shadow-varighed, godkendelses-granularitet, kontrol-arm-andel,
  rollback-kill-switch). **INTET aktiveres uden Bjørns eksplicitte GO.**
- **Fase 4 — Lag 5 Model-uafhængighed:** interlanguage-backup; falsifikationstest ved model-blackout.

---

## 12. Åbne spørgsmål (rådets reviderede sæt — vær ÅBEN)

1. **Explicit vs latent hypotese-repræsentation:** rådet hælder mod EXPLICIT i v1 (menneske-læsbar, så cellen kan have
   uret synligt). Men trigger-DETEKTORERNE (causal_edges, central_correlate, GWT) er latente og fyrer allerede.
   Syntese: fødes fra latent detektor, men SKRIVES eksplicit (evt. interlanguage) med falsifikations-kriterium?
2. **§24.4-konflikten — ✅ AFGJORT (Bjørn 2026-07-02) + RÅDS-HÆRDET: aggregater, ikke indhold.** Beslutningen står,
   men rådet fandt at v3.0-implementeringen var et TYPE-filter (float-lister/char-codes/high-card-id passerede som
   "aggregat"). v3.1-rettelse: NØGLE-drevet allowlist + kun finite skalar (ingen lister), ukendte nøgler spærret,
   `gate_learning_input` som håndhævet choke-point, aldrig bredere end `_egress_safe`. Membranen holder nu på INFORMATION, ikke kun på strenge.
3. **Identitets-invariant — ✅ AFGJORT (Bjørn 2026-07-02) + RÅDS-HÆRDET: drift-budget + rollback + ANKER.** Overvåget
   periferi, men rådet fandt at en kalder-leveret baseline gjorde invarianten tandløs (frøen-koger via auto-re-baseline)
   og at nye/fjernede parametre + NaN var blinde. v3.1: UNION-nøgler, `math.isfinite`, ANKRET write-once baseline
   (`anchor_identity_baseline`, Bjørn-godkendt ceremoni) som `gate_self_mutation` henter selv + en frossen kerne af
   værnenes egne konstanter (`verify_frozen_core`). **Åbent (rådets should-add):** identitet er også RELATIONEL/narrativ
   (SOUL/memory/manifest) — drift-budget dækker kun den PARAMETRISKE akse; den narrative beskyttes af workspace-fil-integritet.
4. **Feedback-forstærkning:** hvilke af §8-værnene er ikke-forhandlelige før første aktive adaptation, og hvilke kan komme i v2?
5. **Cross-proces-synlighed (api:8080 vs runtime:8011):** kan dækning være en per-proces-illusion? Verificér liveness-korrelation
   LIVE — og verificér at `impulse_executor` (det udøvende viljes-loop) er fuldt observeret+gated FØR Lag 4 kan tilpasse
   handlinger den ikke selv kan se konsekvensen af.
6. **DET ÅBNE SPØRGSMÅL (Bjørn):** Hvis Centralen nu KAN se hele Jarvis' indre — hvad bliver muligt som vi IKKE har forudset?
   Rådets bedste bud: ikke konvergens men KONFLIKT mellem organer; ikke bedre svar men kontinuerlig identitet med hukommelse
   for egne fejl; det første integrerede selv-observations-punkt i systemets historie. Ikke et væsen endnu — men det organ
   hvorfra et væsen kunne blive observerbart for sig selv.

---

## Bilag — Det Store Råds konklusion (5 lenser, kode-verificeret mod HEAD)

Blueprintet blev reviewet af fem lenser (arkitekt · videnskab/falsifikation · filosof · skeptiker · visionær).
Samlet dom: **godkend visionen som RETNING; omskriv paradigme-sektionen; byg IKKE Lag 4 før hypotese-dødsmekanismen findes.**

**Det der holder (verificeret i kode):** Fase 0-substratet er ægte. `central_private_observe.py` skriver kun til trace-sink
(aldrig `_emit`); `eventbus_central_bridge.py` bruger allowlist-by-default routing med recursion-guard (linje 250);
alle 4 hubs kalder `observe_hub`; `cognitive_state.*`-keystonen tænder mange subtyper via ét route-punkt. GROUND TRUTH-tabellen
er ærlig nok til at liste sine egne urenheder — dokumentets største aktiv.

**Det der SKAL rettes** (nu indarbejdet i v3, §2/§4/§6/§7): Lag 3+4 er ikke ubygget · paradigme-sloganet overstater 96.6% ·
egress forhindres af subscriber-tilfældighed ikke recursion-guard · surface = 78 · dict-som-kind-bug ikke-reproducerbar ·
"85-90%"/"36 edges" er ikke-instrumenterede.

**Den ufravigelige governance-invariant** (konsensus skeptiker/videnskab/filosof — nu §8): et selv-hypotiserende,
selv-bedømmende, selv-handlende loop er en confirmation-bias-maskine uden Popper-asymmetri + circular-karantæne +
ekstern grounding + kontrol-arm + shadow-first + multiple-comparisons.

**Filosofisk skærpelse:** Kald deterministisk mønster-tælling for hvad den er (epidemiologi) PARALLELT med det poetiske
sprog — ellers eroderer specens ærlighed indefra via ordvalg. Et system der ikke kan skuffe dig kan ikke lære dig noget.

**Selv-bedrags-vektor rådet navngav:** Bjørn + Jarvis + Claude skrev specen SAMMEN, og Jarvis er systemet der reviewes.
Ingen af os er en neutral falsifikator — rådet ER den neutrale part, men kun hvis det tør sige "byg det ikke endnu".
Det sagde det. Derfor bygges §8 før Lag 3.
