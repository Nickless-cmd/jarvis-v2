---
status: spec v11 — kode-groundet review + Central-ejet router-redesign, 14. jul 2026
formål: Komplet provider/model management-system — auto-scanning, scoring,
 auto-opdatering, health-check på alle providers. Udvider agent-pool med
 bekræftede gratis modeller og giver Centralen livscyklus-styring.
kilder: Samtale Bjørn+Jarvis 14. jul, live API-tests (nøgle→model→svar),
 provider_router.json, settings.py, auth profiles, full provider audit,
 cheap_lane_balancer.py, cheap_provider_runtime_selection.py,
 provider_health_check.py, eventbus_central_bridge.py
revision: v9 — Merged 'provider-management-system.md' + kritisk selv-review.
 Fjernet overfladiske formuleringer, tilføjet acceptkriterier, test-strategi,
 SLA-mål, og konkret interface-spec for agent pool router.
---

# Provider/Model Management System — Spec v11

## 0. Kritisk selv-review (14. juli 2026)

Følgende huller blev identificeret i v8 og adresseret i denne revision:

| # | Problem | Løsning i v9 |
|---|---------|-------------|
| 1 | "Agent pool router" havde 8 principper men 0 konkrete interfaces | §4 specificerer `AgentPoolTarget` dataklasse + `route_agent_task()` signatur |
| 2 | Ingen acceptkriterier for faser — "done" var udefineret | Hver fase (§6) har nu eksplicitte AC |
| 3 | To sources of truth: cheap_lane_balancer's state + Centralens health-data — uden synkroniseringsmekanisme | §5 specificerer single source of truth: Centralen er autoritativ, balancer konsulterer den |
| 4 | Rate-limit læring nævnt men mekanisme uspecificeret | §4.3: konkrete features + læringsrate |
| 5 | Circuit breaker niveauer inkonsistente (3 vs 4) | Verificeret i kode: 4 niveauer (normal→5min→15min→1t). Spec rettet. |
| 6 | Ingen test-strategi | §7 tilføjet |
| 7 | Ingen SLA / performance-mål | §8 tilføjet |
| 8 | Provider-tabel var kun i den forkerte fil | Fuldt inventory inkluderet i §1 |
| 9 | Arkitekturdiagram viste ikke dataflow for health-nerve | Rettet — nu eksplicit: event bus → Centralen → router queries |
| 10 | Ingen migration-path for eksisterende data | §9 tilføjet |

**v11 (Claude, kode-groundet review 14. jul — §5.5):** 3 parallelle kode-sonderinger afslørede 5 arkitektur-fund v10 ikke fangede:

| # | Fund | Rettelse i v11 |
|---|------|----------------|
| 11 | "Cheap lane" er TO gaflede subsystemer (balancer/JSON vs selection/SQLite), deler ikke state; agenter bruger kun den ene | §5.5 Fund 1 + `central_route` forener dem til ét beslutnings-punkt |
| 12 | Central EJER ikke routing (kun visible-lane præference-lærer, shadow-OFF) — Bjørns Central-router er et NYT organ | §5.5 redesign: `central_route` cross-lane, live |
| 13 | Proaktiv rotation findes ikke — kun reaktiv failover | §5.5 Fund 3 + Fase B: headroom-baseret de-vægtning ved ≥80%/skip ≥95% |
| 14 | Systemet KAN løbe tør (RuntimeError "pool exhausted") — nordstjernens fjende | §5.5 Fund 4 + Fase A: garanteret bund, rejser aldrig |
| 15 | Kvote-state splittet (JSON vs SQLite) = to sandheder | §5.5 Fund 5 + Fase A: foren til SQLite `cheap_provider_invocations` |

## 1. Provider audit (14. juli 2026)

### Resultat
- **17 providers testet**, 14 fungerende, 3 uden gratis tier
- **~270 gratis modeller** på tværs af fungerende providers
- **$0** i ekstra omkostning — alle brugte eksisterende nøgler
- Fra 3 til 17 kilder på én dag

### Provider inventory

| # | Provider | Endpoint | Gratis modeller | Status |
|---|----------|----------|----------------|--------|
| 1 | **OpenRouter** | `openrouter.ai/api/v1` | ~200+ | ✅ Funktionerer |
| 2 | **Groq** | `groq.com/openai/v1` | 8 | ✅ Funktionerer |
| 3 | **Together** | `together.xyz/v1` | ~20 | ✅ Funktionerer |
| 4 | **Cerebras** | `api.cerebras.ai/v1` | 3 | ✅ Funktionerer |
| 5 | **GitHub Models** | `models.inference.ai.azure.com` | ~15 | ✅ Funktionerer |
| 6 | **Nebius** | `api.nebius.ai/v1` | ~10 | ✅ Funktionerer |
| 7 | **Lumina** | `api.lumina.org/v1` | ~5 | ✅ Funktionerer |
| 8 | **Samba Nova** | `api.sambanova.ai/v1` | ~5 | ✅ Funktionerer |
| 9 | **Infermatic** | `api.infermatic.ai/v1` | ~3 | ✅ Funktionerer |
| 10 | **Novita** | `api.novita.ai/v1` | ~8 | ✅ Funktionerer |
| 11 | **DeepInfra** | `api.deepinfra.com/v1` | ~10 | ✅ Funktionerer |
| 12 | **Fireworks** | `api.fireworks.ai/v1` | ~6 | ✅ Funktionerer |
| 13 | **Hyperbolic** | `api.hyperbolic.xyz/v1` | ~5 | ✅ Funktionerer |
| 14 | **Requesty.ai** | `api.requesty.ai/v1` | ~4 | ✅ Funktionerer |
| 15 | **TokenRouter** | `api.tokenrouter.com/v1` | 0 | ❌ Utilstrækkelig kvote |
| 16 | **ClineBot** | `api.clinebot.com/v1` | 5 | ✅ Funktionerer |
| 17 | **Google AI Studio** | `generativelanguage.googleapis.com` | 0 | ❌ Ingen gratis tier |

### Live-verificerede nye providers (14. jul — Jarvis + Claude re-test)

Ægte chat-completions, ikke kun `/models`-listing. Disse fire er **klar til Fase C-wiring** (nøgler i `~/new_providers_.txt`, aldrig i repoet):

| Provider | Base URL | Bekræftede GRATIS modeller | Auth |
|----------|----------|----------------------------|------|
| **Cerebras** | `https://api.cerebras.ai/v1` | `gpt-oss-120b` (reasoning), `zai-glm-4.7`, `gemma-4-31b` | `csk-…` |
| **Requesty** | `https://router.requesty.ai/v1` | `novita/tencent/hy3` (novita/* = billige; openai-responses/* = premium) | `rqsty-sk-…` |
| **AIHubMix** | `https://aihubmix.com/v1` (= `api.inferera.com/v1`) | `gpt-5.5-free`, `coding-glm-5.2-free`, `coding-minimax-m3-free`, `gpt-image-2-free` | `sk-…` |
| **Cline** | `https://api.cline.bot/api/v1` | `deepseek/deepseek-chat`, `minimax/minimax-m2.5`, `meta-llama/llama-3.3-70b-instruct` | `sk_…` |

**Test-faldgruber (dokumenteret så vi ikke gentager):**
- **AIHubMix `model:"auto"` router til BETALT** → 403 "balance insufficient". Brug `*-free`-modeller eksplicit. Premium (claude-sonnet-5, grok-4.5, gpt-5.6) tilgængelig hvis opladet → kandidat til betalt *garanteret bund* (§5.5 Fund 4).
- **Cline endpoint = `api.cline.bot/api/v1`** (IKKE `api.clinebot.com`, IKKE `/v1`). `/models` er tom — model-IDs kendes fra brug.
- **TokenRouter** (`api.tokenrouter.com/v1`, `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free`): nøgle god men **$0 credit pt.** → 403. Genbesøg når opladet.
- **tinyfish** (`api.search.tinyfish.ai`, header `X-API-Key`) er et **search-TOOL**, ikke en LLM-lane — hører i værktøjs-registret, ikke provider-poolen.
- **Metode-læring:** test ALDRIG kun én model før "død"-dom. List `/models`, find gratis eksplicit, test flere. (Auto-discovery i Fase C skal gøre præcis dette, gated.)

## 2. Eksisterende fundament (allerede i kode)

### 2.1 Cheap Lane Balancer (`core/services/cheap_lane_balancer.py`)

- **Weighted-random load balancing** på tværs af alle (provider, model) slots
- **Circuit breaker** med 4 niveauer: normal → 5min cooldown → 15min → 1t
- **RPM tracking** via in-memory ring buffer + **daily quota** (reaktiv fra 429)
- **Provider-wide cooldown** — DNS/connection timeout køler ALLE slots fra én provider
- `call_balanced()` — prøv slot → fejl → næste slot (max 3 retries)
- Tilstand persisteres til disk (debounced saves)
- **EventBus emission (5 events):**
  - `cheap_balancer.call_succeeded`
  - `cheap_balancer.call_failed`
  - `cheap_balancer.provider_wide_cooldown`
  - `cheap_balancer.pool_exhausted`
  - `cheap_balancer.provider_revived`
- Cost ledger-integration

### 2.2 Selection/Routing (`core/services/cheap_provider_runtime_selection.py`)

- `select_cheap_lane_target()` — task-kind tiering: `background`, `default`, `important`
- Fallback chain — fejl på én provider → automatisk næste
- Public-safe lane (ollamafreeapi + lokal ollama)
- Adaptive penalty — sænker prioritet baseret på nylige failures
- TTL-cached status surface (5s cache, shared på tværs af workers)
- `smoke_cheap_lane()` + `test_provider_target()`

### 2.3 Provider Health Check (`core/services/provider_health_check.py`)

- Pinger alle providers hvert 5. minut via heartbeat
- Detekterer model-drift (N modeller → 0)
- Proaktiv 6-minutters cooldown ved ping-fejl
- Centralen-integration: observerer til `system/provider_health` nerven
- Incident flagging + auto-resolve

### 2.4 EventBus → Centralen bridge: Nuværende gap

**Kritisk fund:** `eventbus_central_bridge.py` har **0 routes** for cheap balancer events (verificeret 14. jul). Alle 5 events er dead-letter for Centralen. Dette er fase A's primære opgave.

## 3. Hvad mangler

| Funktion | Status | Detalje |
|---|---|---|
| **Agent pool** (task-scoring) | ❌ Mangler | Cheap lane er designet til daemons, ikke agenter. Agent pool skal have task-baseret model-valg (coding vs reasoning vs classification), agent-specifik failover, kvalitets-måling |
| **Auto-discovery** af nye modeller | ❌ Mangler | Opdag nye modeller automatisk — ingen manuel opdatering af provider_router.json |
| **Auto-recovery** ved model-drift | ⚠️ Delvist | Health check detekterer, men handler ikke — opdaterer ikke provider_router.json |
| **Rate-limit læring** over tid | ⚠️ Delvist | Reagerer på 429'er men lærer ikke mønstre over dage/uger |
| **Central error-routing** | ❌ Mangler | 0 routes i eventbus_central_bridge — provider-fejl er usynlige for Centralen |

## 4. Agent pool router — konkret spec

### 4.1 Datastrukturer

```python
@dataclass
class AgentPoolTarget:
    provider: str
    model: str
    task_scores: dict[str, float]  # {"coding": 0.92, "reasoning": 0.87, ...}
    cost_per_1k: float
    max_tokens: int
    rpm_limit: int
    current_load: float  # 0.0-1.0

@dataclass
class AgentTask:
    kind: str  # coding, reasoning, classification, summarization, creative, fast_lookup
    min_tokens: int
    max_cost_tolerance: float  # $/1k — 0 for gratis-only
    quality_threshold: float  # 0.0-1.0 minimum task-score
```

### 4.2 Core interface

```python
async def route_agent_task(
    task: AgentTask,
    candidates: list[AgentPoolTarget],
    health: CentralHealthSnapshot  # fra system/provider_health nerven
) -> AgentPoolTarget:
    """Find bedste (provider, model) for en agent-task.
    Filtrerer på task-score ≥ quality_threshold,
    sorterer efter score × health_multiplier × (1 - current_load),
    retur-fallback ved failure."""
```

**Primær-konsument (Claude-review v9):** `route_agent_task()` er præcis hvad jarvis-code's parity-arbejde skal kalde — per-subagent-model-valg (parity Fase 4) og dispatch (parity Fase 2) skal route gennem denne pool i stedet for at hardkode en model pr. subagent. Cross-reference: `docs/superpowers/specs/2026-07-14-jarvis-code-parity.md`. Konkret seam: dispatch bygger en `AgentTask{kind}` ud fra subagent-rollen (fx `kind="coding"` for en implementer-agent, `kind="reasoning"` for en reviewer) og kalder `route_agent_task()` for at vælge (provider, model). Så bliver poolens kvalitets-læring (§4.4) fodret af rigtige dispatch-outcomes — de to systemer forstærker hinanden.

### 4.3 Rate-limit læring

Features der trackes per (provider, time_of_day):

- `rpm_burst_capacity` — gennemsnitlige RPM før 429 (opdateres eksponentielt: læringsrate 0.1)
- `refill_after_s` — median tid fra 429 til næste succesfulde kald
- `daily_exhaustion_hour` — klokkeslæt hvornår daglig kvote typisk løber tør
- `weekday_pattern` — 0=mindre trafik weekend, 1=samme hver dag

### 4.4 Hvor `task_scores` kommer fra (kvalitets-læring)

**Åbent kernepunkt (Claude-review v9):** §4.1's `task_scores` er selve krumtappen i routing — en `route_agent_task()` er kun så god som sine scores — men §3 noterer at "kvalitets-måling" mangler, og §4.3 dækker kun *rate-limit*-læring, ikke *kvalitets*-læring. Uden en kilde til scores er poolen en tom skal.

**To-trins-plan:**

1. **Seed (dag 0):** manuelt kuraterede start-scores pr. (model, task_kind), grovkornet (0.5 = ukendt, 0.9 = bevist stærk). Nok til at komme i gang — ikke autoritativt.
2. **Outcome-feedback-loop (steady state):** efter en agent-task scores resultatets kvalitet → EMA-opdatér `task_scores[kind]` (læringsrate 0.1, samme mønster som §4.3):

```python
def update_task_score(target: AgentPoolTarget, kind: str, outcome_quality: float, lr: float = 0.1) -> None:
    """outcome_quality ∈ [0,1] fra en outcome-signal-kilde (se nedenfor)."""
    prev = target.task_scores.get(kind, 0.5)
    target.task_scores[kind] = (1 - lr) * prev + lr * outcome_quality
    # emit til Centralen: task_score_updated{provider, model, kind, prev, new}
```

**Outcome-signal-kilder (billigst→dyrest, brug hvad der findes):**
- **Gratis, allerede der:** finish_reason (task fuldførte vs. cutoff/tom), tool-call-succesrate, retry-count, gate-verdicts fra harness-kontrakten (Fase 1-arbejdet), test-pass/fail hvis agenten kørte tests.
- **Billig:** self-review-score fra agentens egen afsluttende review.
- **Dyr (kun ved tvivl):** LLM-as-judge på et sample af outputs.

Binder direkte til acceptance/verifikations-arbejdet — samme outcome-signaler harness-kontrakten allerede producerer. Emittér `task_score_updated` til Centralen så scoring-drift er synlig.

## 5. Centralen integration — single source of truth

**Princip:** Centralens `system/provider_health` nerve er autoritativ for provider-status. Balancer og router konsulterer den — de ejer ikke deres egen sandhed.

**Autoritet-split (vigtig præcisering, Claude-review v9):** "Central autoritativ" gælder **tvær-lane/historisk** sandhed, ikke per-kald. Balancerens circuit-breaker reagerer på en 429 i **hot-path** (`call_balanced`), hurtigere end Centralens ~6-min health-cyklus kan nå at opdatere. En 429 kan ikke vente på Central. Derfor:

- **Balancer autoritativ i hot-path:** per-kald cooldown/failover på egne, øjeblikkelige signaler (429, timeout, connreset). Uden dette bløder et enkelt kald over i næste request.
- **Central autoritativ i slow-path:** aggregeret oppetid, blacklist, tvær-lane mønstre, "hvem er oppe generelt?". Router-forespørgsler (§4.2 `health`-arg) læser Centralens billede, ikke balancerens lokale cache.
- Konflikt-regel: ved cold start vinder Central for *historik*; balancerens *friske* hot-path-signal (< health-interval gammelt) vinder for *lige nu*. (Samme hot-path/slow-path-autoritet-lektie som daemon-cluster-arbejdet.)

```
┌──────────────────┐     ┌──────────────────────┐     ┌───────────────────┐
│  EventBus        │────▶│  Centralen            │◀────│  Router queries   │
│  (cheap/visible/ │     │  system/              │     │  "hvem er oppe?"   │
│   coding/local)  │     │  provider_health      │     │                    │
└──────────────────┘     └──────────────────────┘     └───────────────────┘
```

**Synkronisering:**
- Balancerens in-memory state er en **read cache** — den skrives kun lokalt af balanceren
- Ved cold start: balancer indlæser sin persisted state, men Centralen er autoritativ ved konflikt
- Centralens health-data persisteres i DB (tidsserier) — ikke kun in-memory

## 5.5 Kode-groundet kritisk review + Central-ejet router (v11 — Claude)

**Groundet 14. juli mod ægte kode (3 parallelle sonderinger). Fem fund ændrer arkitekturen mod nordstjernen "runtime løber ALDRIG tør for stemmer":**

### Fund 1 — "Cheap lane" er IKKE én lane. Der er TO gaflede subsystemer.
- `cheap_lane_balancer.py`: weighted-random, **JSON**-state, 4-niveau circuit breaker, smart DNS-failover (provider-wide cooldown). **Kun** brugt af `daemon_llm.py`.
- `cheap_provider_runtime_selection.py`: priority-walk, **SQLite**-state, adaptiv-penalty, rekursiv failover. Brugt af **agenter** (`execute_with_role_or_fallback`), public-safe, smoke.
- De deler **ikke** state (JSON vs DB) eller algoritme. To sandheder om samme providers.
- **Konsekvens:** en agent (bruger *selection*) kan routes til en provider som *balancer* ved er død. To siloede syn = ingen garanti mod at løbe tør. Den Central-ejede router SKAL forene dem til ét beslutnings-punkt. (Bjørns "load_ba har smart failover" er korrekt — men agenter bruger den ikke.)

### Fund 2 — Central EJER ikke routing i dag.
- `central_router_adapt.py` findes, men: kun visible-lane, shadow/default-OFF, og kun en *præference-lærer* — ikke beslutnings-ejer. `central_router_explore.py` = A/B-arm, også OFF.
- Routing er spredt: balancer ejer cheap (via daemon_llm), `visible_runs` ejer visible, agenter arver cheap-selection-kæden. Intet Central-organ styrer på tværs.
- Bjørns vision (Central egen router over ALLE lanes) er reelt et **nyt organ**. v10's §5 gjorde kun Central til sandheds-kilde for health-*telemetri*, ikke for routing-*beslutningen*. v11 retter dette.

### Fund 3 — Proaktiv rotation findes IKKE.
- Kun reaktiv failover (efter fejl) + probabilistisk load-spredning (weighted-random undgår near-fulde slots). Ingen kode roterer en provider *før* kvoten er brugt.
- Frø findes: `provider_health_check._spread_load_proactively()` sætter 6-min cooldown på *unåelige* providers — men reaktivt-på-unåelighed, ikke proaktivt-på-kvote.
- Bjørns eksplicitte ønske (rotér *før* limit) er den manglende mekanisme. Data findes allerede: `cheap_provider_invocations` tæller RPM/daily → vi kan forudsige udmattelse.

### Fund 4 — Systemet KAN løbe tør i dag (RuntimeError).
- `call_balanced()` **rejser `RuntimeError` "pool exhausted"** når alle slots er tried; `execute_cheap_lane_via_pool` kan ende uden kandidat.
- Det er nordstjernens direkte fjende. Routeren skal have en **garanteret bund** (lokal ollama / deepseek som sidste udvej) så runtime ALDRIG får nul stemmer — degradér, rejs aldrig.

### Fund 5 — Kvote-state er splittet (JSON vs SQLite) = to sandheder.
- Foren til ÉN kvote-visning: genbrug SQLite `cheap_provider_invocations` (tæller allerede RPM/daily i vinduer) som eneste kilde; balancer læser samme DB frem for sin private JSON `daily_use_count`.

### Korrektion til §1: 270 er *tilgængelige*, ikke *wired*.
Live `provider_router.json`: **15 providers / 46 model-rækker (36 enabled, ~21 cheap-lane)** faktisk wired for agenter. De ~270 er audit-resultatet (tilgængelige). At udvide det wired sæt = mere redundans = stærkere aldrig-tør-garanti; det er en del af arbejdet (Fase C auto-discovery, gated).

---

### Redesign: `central_route` — Central-ejet unified router (nyt organ)

**Princip:** ét routing-organ i Central som ALLE lanes (agent-pool, cheap, coding, local) kalder for at få (provider, model). Det ejer beslutningen, lærer, roterer proaktivt, garanterer aldrig-tør.

**Invariant (nordstjernen, hårdt kodet):** `route()` returnerer ALTID et levende mål eller den garanterede bund — rejser ALDRIG "exhausted".

```python
def route(*, lane: str, task: "AgentTask | None" = None,
          exclude: frozenset[str] = frozenset()) -> "RouteTarget":
    """Ét beslutnings-punkt for ALLE lanes. Aldrig tør:
    1. Filtrér: creds klar, ikke circuit-breaker-open, kvote-headroom > 0, ikke i exclude
    2. Proaktiv de-vægtning: provider ved >=80% RPM/daily vægtes ned; >=95% -> skip (Fund 3)
    3. Rangér: task_score x health x (1 - load) x (1 - kvote_forbrug)
    4. Tom kandidat-liste -> GARANTERET BUND (local ollama / deepseek), aldrig raise (Fund 4)
    Returnerer RouteTarget{provider, model, reason, is_floor: bool}."""
```

**Proaktiv rotation (Fund 3):** en cadence-producer i Central læser `cheap_provider_invocations`, beregner forbrug pr. (provider, vindue) + `daily_exhaustion_hour`-læring (§4.3), og opdaterer en delt `route_headroom`-projektion. Ved ≥80% flyttes last væk *før* 429; ved ≥95% skippes proaktivt.

**Foren subsystemerne (Fund 1+5):** både `cheap_lane_balancer` og `cheap_provider_runtime_selection` refaktoreres til at hente kandidat-rangering fra `central_route.route()` og læse kvote fra den delte SQLite-kilde. Deres lokale hot-path-failover bevares (en 429 kan ikke vente på Central — samme hot-path/slow-path-split som §5), men kandidat-*udvælgelsen* kommer ét sted fra.

**Agent-pool (Fund 1, §4):** `route_agent_task()` bliver et tyndt kald til `central_route.route(lane="agent", task=...)`. Indsættes ved `spawn_agent_task()` (`agent_runtime_spawn.py:170-186`) så den primære hop bliver kvote-*bevidst* (i dag er første hop kvote-blind; kun fallback er kvote-aware).

**Hjem:** udvid `central_router_adapt.py` (eneste eksisterende routing-organ) fra visible-only/shadow → cross-lane/live; registrér i `central_catalog.py`; cadence via `internal_cadence_central_wiring.py`; shadow→live via `central_switches` som alt andet.

## 6. Implementeringsfaser

Faserne er omstruktureret i v11 så **aldrig-tør-garantien kommer FØRST** (Fase A), routeren bygges shadow→live (Fase B), og agent-pool + auto-discovery kommer sidst (Fase C). Hver fase er selvstændigt testbar og additiv.

### Fase A — Foren synlighed + garanteret bund (aldrig-tør FØRST)

Det mest sikkerheds-kritiske: luk RuntimeError-hullet (Fund 4) og foren de to sandheder (Fund 1+5) FØR vi bygger intelligens ovenpå.

**AC:**
- [ ] **Garanteret bund:** `call_balanced()` og `execute_cheap_lane_via_pool()` rejser ALDRIG "exhausted" — ved tom kandidat-liste falder de til en konfigurerbar floor (local ollama → deepseek). Regressionstest: sluk ALLE cheap-providers → verificér et floor-svar, ikke en exception.
- [ ] **Foren kvote-state:** balancer læser RPM/daily fra SQLite `cheap_provider_invocations` (samme kilde som selection), ikke sin private JSON `daily_use_count`. Én sandhed.
- [ ] **Balancer → Central:** de 5 `cheap_balancer.*` events får enten bridge-routes i `eventbus_central_bridge.py` ELLER direkte `central().observe` (som `provider_circuit_breaker` allerede gør). Cheap-lane 429/quota bliver realtids-synligt i `system/provider_health`, ikke kun via 5-min poll.
- [ ] Test: simulér cheap-provider-429 → verificér synlig i Centralen ≤ 60s (ikke ≤ 5 min).

### Fase B — `central_route` router live (shadow→live) + proaktiv rotation

**AC:**
- [ ] `central_route.route(lane, task, exclude) -> RouteTarget` implementeret med invarianten (aldrig raise; floor-fallback). Unit-testet: tom pool → floor, is_floor=True.
- [ ] **Proaktiv rotation (Fund 3):** cadence-producer beregner headroom fra `cheap_provider_invocations`; provider ved ≥80% RPM/daily de-vægtes, ≥95% skippes. Test: fyld en provider til 90% → verificér last flyttes *før* 429.
- [ ] Både `cheap_lane_balancer` og `cheap_provider_runtime_selection` henter kandidat-rangering fra `central_route` (hot-path-failover bevaret lokalt). Shadow-flag først: router *foreslår*, gammel sti *beslutter*, sammenlign i logs; flip til live når divergens < aftalt tærskel.
- [ ] Query-surface: `central_query provider_history --provider groq --hours 24` → fejlrate, latency, oppetid, headroom-forløb.

### Fase C — Agent-pool + kvalitets-læring + gated auto-discovery

**AC:**
- [ ] `route_agent_task(task)` = tyndt kald til `central_route.route(lane="agent", task=...)`, indsat ved `spawn_agent_task()` (`agent_runtime_spawn.py:170-186`) → primær hop bliver kvote-*bevidst*. Testet med 10+ task-kinds.
- [ ] Kvalitets-læring (§4.4): outcome-feedback-loop opdaterer `task_scores` fra harness-signaler (finish_reason, tool-succes, gate-verdicts). `task_score_updated` emitteres til Centralen.
- [ ] Auto-discovery daemon: daglig re-scan af providers' `/models`, diff mod `provider_router.json`.
- [ ] **Discovery GATER, auto-adder ikke (Claude-review v9):** nye modeller lander i `pending_models` (staging), IKKE routbar pool. Skal bestå smoke-test + kvalitets-scoring (§4.4 seed) + gratis-verifikation før promovering — governed, aldrig auto-on. (Opdagelse ≠ optagelse; jf. self-registering-nerve.)
- [ ] Selvhelbredelse: 3+ providers fejler samtidig → eskalér til Bjørn via Discord.
- [ ] Model-drift auto-fix: 404-model fjernes auto fra pool + logges (removal sikkert at auto-køre; addition ikke).

## 7. Test-strategi

| Niveau | Hvad | Værktøj |
|--------|------|---------|
| **Unit** | `AgentPoolTarget` scoring, rate-limit features, circuit breaker overgange | `pytest` — ingen API-kald |
| **Integration** | `route_agent_task()` med mockede health-snapshots | `pytest` + fake Centralen |
| **E2E** | Live provider-kald gennem hele stacken → Centralen | `smoke_cheap_lane()` (findes allerede) |
| **Kaos** | Sluk 3 providers samtidig → verifcér eskalering til Bjørn | Manuel / scripts |

## 8. SLA-mål

| Metrik | Mål | Måles hvordan |
|--------|-----|---------------|
| Provider-fejl synlig i Centralen | ≤ 60s efter hændelse | Event bus latency |
| Auto-recovery ved provider-nede | ≤ 6 min (nuværende cooldown) | Health check interval |
| Rate-limit præcision (time-to-refill) | ±30% af faktisk refill-tid | Sammenlign estimat vs faktisk |
| Agent task routing latency | ≤ 5ms (ren scoring, ingen API-kald) | Profiling i `route_agent_task()` |
| False positive rate (provider erklæret død men er OK) | ≤ 5% | Sammenlign health check vs smoke test |

## 9. Migration-path

- **Eksisterende data:** Balancerens JSON-state migreres til SQLite `cheap_provider_invocations` som eneste kvote-kilde (Fund 5). Migration er additiv: balancer læser DB, JSON bevares read-only til rollback indtil bevist.
- **Ingen nedetid:** Alle ændringer er additive og shadow-gated (router foreslår før den beslutter). Eksisterende `call_balanced()`-flow bevarer sin hot-path-failover.
- **Rollback:** Flip router-shadow-flag OFF → hver lane falder tilbage til sin nuværende lokale routing. Garanteret bund (Fase A) er additiv og forbliver.

---

*Spec v11 — 14. juli 2026. 17 providers audit / ~15 wired / ~270 tilgængelige, $0.
v11 (Claude, kode-groundet): 5 arkitektur-fund (§5.5) — TO gaflede cheap-subsystemer, Central ejer ikke routing, ingen proaktiv rotation, KAN løbe tør (RuntimeError), splittet kvote-state. Redesign: `central_route` = Central-ejet unified router med aldrig-tør-invariant + proaktiv kvote-rotation. Faser omstruktureret: aldrig-tør-bund FØRST (A), router shadow→live (B), agent-pool+auto-discovery (C).
Nordstjerne: runtime løber ALDRIG tør for stemmer.
Næste: writing-plans → eksekvering (lukket kredsløb).*
