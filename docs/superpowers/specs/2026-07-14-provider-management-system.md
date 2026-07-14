---
status: spec v8 — live-testet, Bjørns retning 14. jul 2026
formål: Komplet provider/model management-system — auto-scanning, scoring,
 auto-opdatering, health-check på alle providers. Udvider agent-pool med
 bekræftede gratis modeller og giver Centralen livscyklus-styring.
kilder: Samtale Bjørn+Jarvis 14. jul, live API-tests (nøgle→model→svar),
 provider_router.json, settings.py, auth profiles, full provider audit,
 cheap_lane_balancer.py, cheap_provider_runtime_selection.py,
 eventbus_central_bridge.py
---

# Provider/Model Management System — Spec v8

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

### Discovery-metode
- Hver provider testet med: `API-nøgle → model → konkreet request → verificér svar`
- Models scannet via providerens `/models` endpoint eller dokumentation
- Rate limits noteret per provider (RPM, TPM, daglige caps)

## 2. Eksisterende fundament (allerede i kode)

### 2.1 Cheap Lane Balancer (`core/services/cheap_lane_balancer.py`)

**Formål:** Weighted-random load balancing for daemon LLM-kald. Spreder trafik
på tværs af alle tilgængelige (provider, model) slots for at undgå kvote-dræning.

**Nuværende capability:**
- Vægtet selection baseret på RPM headroom × daily quota × breaker health
- Circuit breaker med 3 niveauer: 5min / 15min / 1h cooldown
- 429/Retry-After support med default 1h cooldown ved manglende header
- Provider-wide cooldown ved DNS/forbindelsesfejl
- Persistent state via JSON (debounced save)

**Event bus emission (5 events):**
- `cheap_balancer.call_succeeded` — succesfuldt kald
- `cheap_balancer.call_failed` — fejl under kald
- `cheap_balancer.provider_wide_cooldown` — provider taget ud af rotation
- `cheap_balancer.pool_exhausted` — ingen slots tilgængelige
- `cheap_balancer.provider_revived` — provider tilbage efter cooldown

### 2.2 Selection/Routing (`core/services/cheap_provider_runtime_selection.py`)

- `select_cheap_lane_target()` — vælger provider baseret på task_kind
- Fallback-kæde: primær target → cloud fallbacks → graceful degradering
- Task-aware routing: forskellige providers til forskellige opgavetyper

### 2.3 Agent Pool (delvist implementeret)

- `propose_skill_chain()` — foreslår kæder baseret på fuldt skill-katalog
- Mangler: persistent agent state, task-scoring, selvhelbredelse

## 3. HVAD MANGLER

### 3.1 Provider Error-håndtering i Centralen (Bjørns krav)

**Problem:** Provider-fejl er i dag isoleret pr. lane og usynlige for Centralen.

**Nuværende tilstand:**
- `cheap_lane_balancer` har events, men **0 routes** i `eventbus_central_bridge.py`
- Al error-håndtering er dead-letter for Centralen
- Visible lane, coding lane, local lane har hver deres isolerede fejl-logik
- Ingen nerve ser mønstre på tværs af lanes

**Krav:**
1. **Provider-fejl skal være synlige i Centralen** — én nerve der modtager
   events fra ALLE lanes (visible, cheap, coding, local)
2. **Automatisk rotation baseret på fejl** — når en provider fejler N gange
   på tværs af lanes, tages den ud af global rotation
3. **Time-to-quota-refill estimater** — fra historik, ikke gæt
4. **Health persistence** — tidsserie af fejlrate/latency per provider,
   så man kan spørge "hvordan har Groq klaret sig de sidste 24 timer?"

**Forslag: Ny Centralnerve `system/provider_health`:**
- Poller balancerens state → persistent i tidsserier
- Modtager events fra ALLE lanes
- Holder en "provider blacklist" som routere kan konsultere
- Estimerer time-to-refill fra historisk kvote-forbrug

### 3.2 Agent Pool Router (komplet)

**Skal bygge ovenpå `select_cheap_lane_target()`, ikke ved siden af:**

- **Task-scoring:** Hver agent-opgave scores på kompleksitet → matcher til
  billigst mulige provider der kan klare opgaven
- **Auto-discovery:** Periodisk re-scan af providers for nye/modeller
- **Selvhelbredelse:** Når en provider fejler, re-test den efter cooldown →
  re-integration automatisk ved succes
- **Rate-limit læring:** Providerens faktiske rate limits læres over tid,
  i stedet for at opdage dem ved 429

### 3.3 Auto-opdatering

- `/models` endpoint polles periodisk for ændringer
- Nye modeller tilføjes automatisk til poolen
- Fjernede modeller markeres som `deprecated`

## 4. Arkitektur

```
┌─────────────────┐     ┌──────────────────┐     ┌───────────────────────┐
│  Event bus       │────▶│ Centralen         │────▶│ system/provider_health │
│  (alle lanes)    │     │ (122 nerver)      │     │ (NY nerve)             │
└─────────────────┘     └──────────────────┘     └───────────────────────┘
                                                           │
                                                           ▼
┌─────────────────┐     ┌──────────────────┐     ┌───────────────────────┐
│  Agent Pool      │────▶│ Selection/Routing │◀────│ Provider blacklist    │
│  Router          │     │ (cheap_lane)      │     │ (live health data)    │
└─────────────────┘     └──────────────────┘     └───────────────────────┘
        │                        │
        ▼                        ▼
┌─────────────────┐     ┌──────────────────┐
│  17 providers   │     │ ~270 modeller    │
│  (gratis)       │     │ (scored + cached)│
└─────────────────┘     └──────────────────┘
```

### Lane-arkitektur (eksisterende + nyt)

| Lane | Anvendelse | Provider | Error-routing i dag |
|------|-----------|----------|---------------------|
| **Visible** | Mit svar til Bjørn | deepseek-chat via DeepSeek | ❌ Isoleret |
| **Cheap** | Daemon-kald, interne tasks | Balanceret (alle gratis) | ✅ Delvist (event bus) |
| **Coding** | Kodegenerering | opencode-go / deepseek | ❌ Isoleret |
| **Local** | Ollama (indlejring, vision) | nomic-embed-text / llava | ❌ Isoleret |

**Efter ændring:** Alle lanes ruter provider-fejl til `system/provider_health`.

## 5. Provider-fejlkategorier

Balanceren skelner allerede mellem disse — de skal spejles i Centralen:

| Kategori | Eksempel | Handlekraft |
|----------|----------|-------------|
| **Rate limited** | 429, 429 Retry-After | Cooldown + rotation |
| **Provider down** | DNS-fejl, timeout, 5xx | Provider-wide cooldown |
| **Auth failed** | 401, 403 | Permanent blacklist (kræver manuelt fix) |
| **Quota exhausted** | 402, 429 daily cap | Rotation + re-test ved næste døgn |
| **Model unavailable** | 404 model, 400 bad model | Fjern fra slot pool |
| **Intermittent** | Lejlighedsvis timeout under load | Tærskel-baseret (N fejl inden for T) |

## 6. Implementeringsrækkefølge (forslag)

### Fase A — Error-routing til Centralen (først, Bjørns krav)
1. Tilføj routes i `eventbus_central_bridge.py` for cheap balancer-events
2. Opret nerve `system/provider_health` i Centralen
3. Wire visible/coding/local lane til samme nerve
4. Implementér blacklist + rotation på tværs af lanes

### Fase B — Persistens + tidsserier
5. Gem health-data i DB (fejlrate, latency, uptime per provider)
6. Byg query-surface: "provider status sidste 24h"
7. Estimer time-to-refill fra historik

### Fase C — Agent pool komplet
8. Task-scoring → provider-matching
9. Auto-discovery daemon (re-scan providers)
10. Selvhelbredelse (re-test efter cooldown)

---

*Spec v8 — 14. juli 2026. 17 providers, ~270 gratis modeller, $0.
Næste: Bjørn review → build-authorisation.*