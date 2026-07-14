---
status: spec v9 — kritisk review + merge, 14. jul 2026
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

# Provider/Model Management System — Spec v9

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

### 4.3 Rate-limit læring

Features der trackes per (provider, time_of_day):

- `rpm_burst_capacity` — gennemsnitlige RPM før 429 (opdateres eksponentielt: læringsrate 0.1)
- `refill_after_s` — median tid fra 429 til næste succesfulde kald
- `daily_exhaustion_hour` — klokkeslæt hvornår daglig kvote typisk løber tør
- `weekday_pattern` — 0=mindre trafik weekend, 1=samme hver dag

## 5. Centralen integration — single source of truth

**Princip:** Centralens `system/provider_health` nerve er autoritativ for provider-status. Balancer og router konsulterer den — de ejer ikke deres egen sandhed.

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

## 6. Implementeringsfaser

### Fase A — Error-routing til Centralen (først)

**AC:**
- [ ] `eventbus_central_bridge.py` har routes for ALLE 5 cheap balancer events
- [ ] Nerve `system/provider_health` modtager og logger events fra cheap lane
- [ ] Visible/coding/local lane wired til samme nerve
- [ ] `central_query status` viser aktuelle provider-fejl som anomalier
- [ ] Test: simuler provider-fejl → verifcér at de dukker op i Centralen inden for 60s

### Fase B — Persistens + tidsserier

**AC:**
- [ ] Health-data gemmes i DB (tabel: `provider_health_events`)
- [ ] Query-surface: `central_query provider_history --provider groq --hours 24` returnerer fejlrate, latency, oppetid
- [ ] Time-to-refill estimat fra historisk kvote-forbrug (inden for ±30% nøjagtighed)
- [ ] Provider blacklist der konsulteres af ALLE lanes

### Fase C — Agent pool komplet

**AC:**
- [ ] `route_agent_task()` implementeret og testet med 10+ task-kinds
- [ ] Auto-discovery daemon: daglig re-scan af alle providers' `/models` endpoints, diff mod `provider_router.json`
- [ ] Selvhelbredelse: hvis 3+ providers fejler samtidig → eskaler til Bjørn via Discord
- [ ] Model-drift auto-fix: 404 model → fjernes automatisk fra pool, logges til Centralen

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

- **Eksisterende data:** Balancerens persisted state (`cheap_lane_state.json`) forbliver — den er balancerens private cache. Centralen bygger sin egen tidsserie uafhængigt.
- **Ingen nedetid:** Alle ændringer er additive (nye routes, ny nerve). Eksisterende `call_balanced()` flow ændres ikke.
- **Rollback:** Fjern event bus routes → systemet falder tilbage til nuværende isolerede fejlhåndtering.

---

*Spec v9 — 14. juli 2026. 17 providers, ~270 gratis modeller, $0.
Næste: Bjørn review → build-authorisation.*
