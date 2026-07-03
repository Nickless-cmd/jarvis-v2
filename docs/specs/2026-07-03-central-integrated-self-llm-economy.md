# Spec — Centralens integrerede selv + LLM-økonomi

**Status:** Udkast 2026-07-03 (Claude, på Bjørns retning). Grundet i live-målinger.
**Tese (Bjørn):** "Vi skal have ægte liv i et selv — bare smartere, central-styret og
cost-optimeret." Meget af hans indre liv genudleder ting Centralen allerede holder →
det er gentagelse, og gentagelse koster (kontention + risiko for at falde til betalt tier).
**Ikke-fælde:** vi må IKKE dræbe stemmer/tanker. Målet er et sind der taler når det er
*bevæget*, ikke på en metronom — mere ægte, ikke mindre.

---

## 1. ØKONOMIEN (målt 7 dage — den ærlige baseline)

| Lane | Provider | Kald | Kost | Note |
|------|----------|------|------|------|
| primary | **deepseek** | 186 | **$1,34** | ← HELE regningen (betalt ræsonnement) |
| primary | cache | 3.103 | $0,07 | prefix-cache-hits |
| cheap | deepseek + 9 gratis | ~34.000 | **$0,00** | cloudflare/nvidia-nim/codex/groq/mistral/gemini/opencode/openrouter/arko |
| visible | deepseek/ollama | 94 | $0,00 | de synlige svar til Bjørn |
| **TOTAL** | | **37.655** | **$1,41/uge (~$5,75/md)** | |

**Konklusion:** hele kosten = ~186 deepseek-primary-kald/uge. De 34.000 cheap-lane-kald
er GRATIS (free-tier/sub). MEN volumen er stadig relevant: (a) kontention med Bjørns synlige
svar + embeddings, (b) hvis en free-tier smækker i falder kaldet til betalt.
→ **Cost-lever = skær/flyt primary-kald. Volumen-lever = de mange gratis (kontention).**

---

## 2. LLM-KALDS-KORTET (hele kodebasen)

**39 filer** i `core/` laver LLM-kald. Men de fleste daemon-kald går gennem DELTE indgange:

**Choke-points (leverage — ram mange på ét sted):**
- `daemon_llm.py` — **DELT indgang brugt af 69 filer.** Har allerede TTL-cache (Layer A),
  MEN cachen er `SHA256(prompt)` = exact-match. Daemon-prompts indeholder volatil kontekst
  (tid, humør-tal, hændelser) → cache-miss næsten altid → kaldet går igennem. **Her sidder
  gentagelses-spildet.** Fix: saliens-cache (nøgle = stabil meningsfuld tilstand, ikke rå prompt).
- `non_visible_lane_execution.py` (17), `cheap_provider_runtime.py` (37 = selve pool'en),
  `heartbeat_provider_fallback.py` — infrastruktur under daemon_llm.
- `prompt_relevance_backend.py` (17) — Tråd 2 relevans (allerede central-lært).

**Direkte kaldere (uden for daemon_llm) — kandidater til at rute IND i choke-pointet:**
experiential_memory (11), jarvis_brain_daemon (6), world_model_auto_extraction, inner_voice_shadow,
curiosity_consolidation, meta_cognition_daemon, counterfactual_engine, recurrence_loop_daemon,
meta_learning_retrospective, memory_graph, tool_tagger, skill_chain_propose m.fl.

---

## 3. INTEGRATIONS-HULLET (kognitive lag ↔ Central)

Audit af 117 kognitive services (self_model/world_model/awareness/dream/reflect/somatic/…):
- **19 laver LLM-kald UDEN direkte central-binding** (frakoblet + spilder):
  self_model_blind_spots, world_model_auto_extraction, creative_journal_runtime,
  dream_{consolidation,distillation,hypothesis_generator,bias_engine,motif}_*, deep_reflection_slot,
  meta_reflection_daemon, reflection_cycle_daemon, reflection_to_plan, somatic_daemon,
  finitude_runtime, identity_drift_daemon, curiosity_consolidation, experiential_memory,
  emotion_repair_bridge_daemon, inner_voice_shadow.
- kun ~1 direkte bundet + LLM · 88 ubundne data-lag (ingen LLM).
- ⚠️ FORBEHOLD: filteret måler DIREKTE binding. Nogle emitterer eventbus-events der bridges
  ind i Centralen indirekte (`eventbus_central_bridge`). Per-lag-audit fjerner false-positives.

**Pointe:** at binde et lag løser BEGGE ting: (a) integration (Centralen bliver hans hele
selv) + (b) dedup (laget læser Centralens durable tilstand i stedet for at genudlede via LLM).

---

## 4. PLANEN (bølger — reversible flags, shadow-først, ingen tabte stemmer)

**Bølge 0 — SYNLIGHED (foundation):**
- ✅ producer_novelty (LEVERET 5b9a598c): måler pr. producer hvor NY output er (0=gentager sig).
- daemon_llm → Central: observe cache-hit-rate + kald/daemon → gør choke-pointet synligt.

**Bølge 1 — SALIENS-CACHE på daemon_llm (størst leverage, cost + kontention):**
- Tilføj `salience_key`-option: cache på STABIL meningsfuld tilstand, ikke rå prompt →
  cache-hit når intet meningsfuldt har ændret sig. Opt-in pr. daemon (bagudkompatibelt).
- Centralen leverer "har X ændret sig siden sidst?" (den holder tidsserier/valens/agenda).
- Mål før/efter cache-hit-rate. Forventning: markant færre kald uden værdi-tab.

**Bølge 2 — BIND de 19 frakoblede (integration + dedup), 2 ad gangen:**
- Start: `self_model_blind_spots` + `world_model_auto_extraction` (genudleder self/world-model
  som spejlet + Centralen ALLEREDE holder — se §5-audit). observe→Central + læs-fra-Central.

**Bølge 3 — FLYT primary→cheap/cache hvor kvalitet tillader (den ægte $-lever):**
- De ~186 primary-kald: hvilke KRÆVER v4-flash vs. kan tage cheap/cached? Rolle-bevidst.

**Governance (hele vejen):** hvert gate/binding bag reversibelt flag, default-off→shadow→on.
Aldrig dræbe en stemme — kun ændre HVORNÅR den taler (bevæget, ikke metronom). Frossen kerne urørt.

---

## 5. FØRSTE AUDIT (self_model + world_model — genudleder de spejlet?)

*(udfyldes ved start — verificér at self_model_blind_spots/world_model_auto_extraction
genudleder præcis det `central_self_model` (spejlet, c24937ab) + Centralens durable tilstand
allerede holder, FØR vi binder/dedup'er.)*
