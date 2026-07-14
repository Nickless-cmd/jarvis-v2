---
status: udkast (design, Bjørns retning 14. jul 2026)
formål: Komplet provider/model management-system — auto-scanning, scoring,
 auto-opdatering, health-check på alle providers. Udvider agent-pool med
 OpenCode's 4 under-providers (opencode-go, zenifra, zenmux, freemodel)
 og giver Centralen livscyklus-styring over alle modeller.
kilder: Samtale Bjørn+Jarvis 14. jul, OpenCode config audit, provider_router.json,
 settings.py, cheap_provider_runtime_adapters.py, auth.json
---

# Provider/Model Management System

## Problem

Jarvis' provider-landscape er statisk og manuelt vedligeholdt:
- `provider_router.json` har 16 providers, men model-lister er hardcodede og forældede
- OpenCode base URL er forkert (`/zen/v1` i stedet for `/zen/go/v1`) → 403
- `gpt-oss:20b` (ollamafreeapi) eksisterer ikke → memory scoring fejler stille
- `minimax-m2.5-free` og `nemotron-3-super-free` er udgået på opencode-go
- Ingen mekanisme detekterer nye modeller eller udgåede modeller
- Ingen scoring af hvilken model der er bedst til en given opgave
- Centralen har ingen indsig i model-tilgængelighed eller -kvalitet
- Agent-poolen er reelt kun deepseek-flash — ingen diversitet

## Vision

Et system hvor:
1. **Alle providers** checkes dagligt for tilgængelighed, latency og model-lister
2. **Nye modeller** opdages automatisk og tilføjes til poolen
3. **Udgåede modeller** detekteres og fjernes/markeres
4. **Task-baseret scoring** vælger den skarpeste model til hver agent-opgave
5. **Centralen** administrerer model-livscyklus og kan kompensere for udgåede gratis modeller
6. **Agent-poolen** har diversitet — kodning, reasoning, klassifikation, hurtige opgaver
7. **Gratis modeller** prioriteres først, betalte som fallback

## Arkitektur

### Lag 1 — Provider Registry (eksisterende, udvides)

`provider_router.json` udvides med alle 4 OpenCode-providers:

| Provider ID | API endpoint | Auth | Antal modeller | Gratis? |
|---|---|---|---|---|
| `opencode-go` | `https://opencode.ai/zen/go/v1` | API key | ~19 | Nej (billige) |
| `zenifra` | `https://ai.zenifra.com/v1` | API key | ~1 | Nej |
| `zenmux` | `https://zenmux.ai/api/v1` | API key | ~80+ | ~15 gratis |
| `freemodel` | `https://cc.freemodel.dev/v1` | API key | ~11 | Nej (premium) |

Hver provider-deklaration indeholder:
```json
{
  "id": "zenmux",
  "enabled": true,
  "api": "https://zenmux.ai/api/v1",
  "auth_profile": "opencode",
  "lane": "agent",
  "models_endpoint": "/models",
  "static_models": [],
  "auto_discover": true,
  "health_check_interval_minutes": 1440,
  "last_health_check": null,
  "last_model_sync": null
}
```

### Lag 2 — Model Discovery Daemon (ny)

Kører **dagligt** (1440 min cadence). For hver provider med `auto_discover: true`:

1. **Hent model-liste** fra `/models` endpoint (eller `static_models` hvis ingen endpoint)
2. **Diff mod eksisterende registry** — nye modeller, fjernede modeller, ændrede priser
3. **Test hver model** med et minimalt prompt ("Say OK") — måling:
   - Reachable (ja/nej)
   - Latency (ms)
   - Output tokens/sek
   - Tool call support (ja/nej)
   - Reasoning support (ja/nej)
4. **Persistér** opdateret model-liste til `provider_router.json`
5. **Emit event** til Centralen: `model.discovered`, `model.deprecated`, `model.unreachable`

**Edge cases:**
- Provider nede → skip, log, prøv igen næste dag
- Model timeout (>30s) → marker `unreachable`, ikke fjern
- Model returnerer 403/429 → marker `rate_limited`, prøv igen om 24t
- `/models` endpoint returnerer 403 → brug `static_models` som fallback
- Ny model med ukendt navn → tilføj med `status: unverified`, test ved næste tick
- Model skifter fra gratis til betalt → marker `price_changed`, behold men deprioritér
- Provider slettet fra OpenCode → marker alle dens modeller `orphaned`

### Lag 3 — Task-Based Model Scoring (ny)

Når en agent dispatches, vælges model ud fra **task-type**:

| Task type | Prioritering | Eksempel |
|---|---|---|
| `coding` | tool_call + reasoning + lav latency | kimi-k2.7-code-free, deepseek-v4-flash |
| `reasoning` | reasoning + stor context | qwen3.7-plus, glm-5.2-free |
| `classification` | lav latency + billig | mimo-v2.5, glm-4.7-flash-free |
| `summarization` | stor context + lav pris | deepseek-v4-flash, gemini-2.5-flash-lite |
| `creative` | reasoning + temperatur | kimi-k2-thinking, qwen3.6-plus |
| `fast_lookup` | lavest latency | groq llama-3.1-8b, glm-4.7-flashx |

**Scoring-formel (per kandidat-model):**
```
score = w_relevance * task_match
      + w_cost * (1 - normalized_cost)
      + w_latency * (1 - normalized_latency)
      + w_free * is_free
      + w_reliability * uptime_pct
```

Hvor:
- `task_match` = 1.0 hvis model understøtter task-type's krav, 0.0 hvis ikke
- `normalized_cost` = cost / max_cost_i_poolen
- `normalized_latency` = latency / max_latency_i_poolen
- `is_free` = 1.0 hvis input=0 og output=0, 0.0 ellers
- `uptime_pct` = succesrate over sidste 7 dage (fra health-check)

**Default vægte:**
- `w_relevance = 0.35` — must have
- `w_free = 0.25` — gratis først
- `w_reliability = 0.20` — stabil er vigtigere end hurtig
- `w_latency = 0.10` — latency er nice-to-have
- `w_cost = 0.10` — pris er sekundær (gratis-filteret gør det meste)

**Selection:**
1. Filtrer modeller der ikke understøtter task-type
2. Sortér efter score faldende
3. Vælg top-1
4. Hvis top-1 er `unreachable` eller `rate_limited` → fallback til top-2
5. Hvis alle gratis modeller er nede → fallback til betalt model
6. Log valg + rationale til `agent_dispatch_spend`

### Lag 4 — Centralen Integration (ny)

Centralen får en ny cluster: **`models`**

| Nerve | Funktion |
|---|---|
| `model_registry` | Holder live model-liste med status, pricing, health |
| `model_scoring` | Task-based scoring cache (opdateres ved hver dispatch) |
| `model_lifecycle` | Detekterer udgåede/nye modeller, emitterer events |
| `model_health` | Daglig health-check resultater |
| `model_cost_guard` | Budget-vagt — hvis en gratis model bliver betalt, alert |

**Events:**
- `model.discovered` — ny model fundet under scanning
- `model.deprecated` — model markeret udgået af provider
- `model.unreachable` — model fejlede health-check
- `model.price_changed` — model skiftede fra gratis til betalt (eller omvendt)
- `model.recovered` — model kom tilbage efter unreachable

**Centralen kan:**
- Nudge Jarvis: "3 gratis modeller er forsvundet i denne uge — poolen er 40% mindre"
- Auto-kompensere: hvis en gratis model forsvinder, flyt agenter til næste-bedste gratis model
- Lære mønstre: hvis en provider ofte er nede om morgenen, undgå den i den periode
- Gate: hvis ingen gratis modeller er tilgængelige for en task-type, alert før dispatch

### Lag 5 — Agent Pool Configuration (udvides)

Nuværende agent-pool: reelt kun deepseek-flash.

Ny agent-pool med **model-families**:

| Familie | Task types | Kilde | Pris |
|---|---|---|---|
| **Free Coders** | coding, fast_lookup | zenmux: kimi-k2.7-code-free, glm-5.2-free, glm-4.7-flash-free, glm-4.6v-flash-free | $0 |
| **Free Reasoners** | reasoning, classification | zenmux: kimi-k2.7-code-free, glm-5.2-free | $0 |
| **Budget Coders** | coding, creative | opencode-go: deepseek-v4-flash ($0.14/$0.28), mimo-v2.5 ($0.14/$0.28) | Lav |
| **Budget Reasoners** | reasoning, summarization | opencode-go: qwen3.7-plus ($0.4/$1.6), zenmux: gemini-2.5-flash-lite ($0.1/$0.4) | Lav |
| **Premium** | complex reasoning | freemodel: gpt-5.4 ($2.5/$15), claude-opus-4-8 ($5/$25) | Høj — kun ved behov |
| **Local** | private, safe | ollama: deepseek-r1, qwen3.5:9b | $0 (lokal) |
| **Existing** | cheap lane | groq: llama-3.1-8b-instant | $0 (groq free tier) |

**Dispatch-regler:**
1. Gratis modeller først (hvis task-type matcher)
2. Hvis ingen gratis → budget modeller
3. Hvis ingen budget → premium (kun med explicit godkendelse)
4. Private/sensitive opgaver → altid lokal ollama
5. Deepseek visible lane berøres **ikke** — den er min, ikke agent-poolens

## Implementering

### Fase 1 — Provider Registration (1-2 timer)

- Tilføj 4 OpenCode-providers til `provider_router.json` med korrekte base URLs
- Opdater `cheap_provider_runtime_adapters.py` med nye provider configs
- Fix opencode base URL: `/zen/v1` → `/zen/go/v1`
- Opdater `static_models` med korrekte model-navne fra audit
- **Test:** hver provider kan liste modeller og svare på et chat-kald

### Fase 2 — Model Discovery Daemon (3-4 timer)

- Ny daemon: `model_discovery_daemon.py` (daglig cadence, ingen LLM)
- Henter model-lister, differ, tester reachability, persisterer
- Emitter events til Centralen
- **Test:**
  - Provider nede → skip uden crash
  - Ny model → tilføjes korrekt
  - Udgået model → markeres
  - Timeout → `unreachable` ikke slet
  - 403/429 → `rate_limited`
  - `/models` endpoint mangler → `static_models` fallback

### Fase 3 — Task-Based Scoring (2-3 timer)

- Ny module: `model_selector.py`
- Implementér scoring-formel + task-type matching
- Integrér i agent dispatch path
- Log valg + rationale
- **Test:**
  - Gratis model vælges før betalt ved samme score
  - Model uden tool_call vælges ikke til coding task
  - Unreachable model → fallback til næste
  - Alle modeller nede → error med klar besked
  - Scoring cache invalidates ved model-liste opdatering

### Fase 4 — Centralen Integration (2-3 timer)

- Ny cluster: `models` med 5 nerver
- Registrér under Central-kontrakten (self-registering nerve architecture)
- Events: discovered, deprecated, unreachable, price_changed, recovered
- Nudge-mekanisme: hvis poolen skrumper, alert Jarvis
- **Test:**
  - Event emission ved model discovery
  - Nudge ved pool-shrinkage
  - Cost guard ved price change
  - Centralen kan query model_registry status

### Fase 5 — Agent Pool Wiring (1-2 timer)

- Opdater agent dispatch til at bruge `model_selector`
- Konfigurér model-families
- Sæt dispatch-regler (gratis først, private → lokal)
- **Test:**
  - Agent dispatches til gratis model når tilgængelig
  - Fallback til budget ved gratis ned
  - Private opgave → lokal ollama
  - Visible lane uberørt

### Fase 6 — Cleanup (30 min)

- Fjern `gpt-oss:20b` fra alle configs
- Fjern `minimax-m2.5-free` og `nemotron-3-super-free` fra static_models (udgået)
- Fjern `ling-2.6-flash-free` (findes ikke)
- Marker `sambanova` som disabled (allerede)
- Marker `codex-cli` og `github-copilot` som disabled (opsagt)
- Opdater `relevance_opencode_model` til en eksisterende model
- **Test:** ingen døde model-referencer i kodebasen

## Gratis modeller — fuld liste (per 14. jul 2026)

### ZenMux (https://zenmux.ai/api/v1)
| Model ID | Task egnet | Context | Tool | Reasoning |
|---|---|---|---|---|
| `moonshotai/kimi-k2.7-code-free` | coding, reasoning | 262K | ✅ | ✅ |
| `z-ai/glm-5.2-free` | reasoning, classification | 1M | ✅ | ✅ |
| `z-ai/glm-4.7-flash-free` | fast_lookup, classification | 200K | ✅ | ✅ |
| `z-ai/glm-4.6v-flash-free` | classification | 200K | ✅ | ✅ |
| `minimax/minimax-m2.5-free` | coding | 204K | ✅ | ✅ |
| `minimax/minimax-m2.1-free` | coding | 204K | ✅ | ✅ |
| `mimo-v2-flash-free` | fast_lookup | 1M | ✅ | ✅ |
| `mimo-v2-omni-free` | classification | 262K | ✅ | ✅ |
| `ling-2.6-flash-free` | summarization | 128K | ✅ | ✅ |
| `nemotron-3-super-free` | reasoning | 128K | ✅ | ✅ |
| `north-mini-code-free` | coding | 128K | ✅ | ❌ |
| `grok-code` | coding | 128K | ✅ | ✅ |
| `hy3-free` | classification | 128K | ✅ | ❌ |
| `hy3-preview-free` | classification | 128K | ✅ | ❌ |
| `trinity-large-preview-free` | reasoning | 128K | ✅ | ✅ |
| `glm-5-free` | reasoning | 202K | ✅ | ✅ |
| `qwen3.6-plus-free` | reasoning, coding | 1M | ✅ | ✅ |
| `kimi-k2.7-code-free` | coding | 262K | ✅ | ✅ |

### OpenCode Go (https://opencode.ai/zen/go/v1) — ingen gratis, men billige
| Model ID | Pris (in/out) | Task egnet |
|---|---|---|
| `deepseek-v4-flash` | $0.14/$0.28 | coding, fast_lookup |
| `mimo-v2.5` | $0.14/$0.28 | coding, fast_lookup |
| `qwen3.7-plus` | $0.4/$1.6 | reasoning, creative |

### FreeModel (https://cc.freemodel.dev/v1) — premium, gratis?
| Model ID | Pris | Bemærkning |
|---|---|---|
| Ukendt — skal testes | — | Kan være gratis premium-modeller |

## Edge cases — komplet liste

1. **Provider forsvinder** → alle dens modeller markeres `orphaned`, agenter fallback
2. **Model skifter navn** → detekter via `/models` diff, behold gammel som alias 1 uge
3. **Gratis model bliver betalt** → `price_changed` event, deprioritér, find替代
4. **Alle gratis modeller nede** → fallback til budget, alert Centralen
5. **API key udløber** → `auth_expired` event, nudge Jarvis
6. **Rate limit hit** → `rate_limited` status, cooldown 1 time, prøv igen
7. **Model returnerer garbage** → quality check (svar indeholder "OK"?), marker `unstable`
8. **Latency > 30s** → marker `slow`, deprioritér til background tasks
9. **Provider /models endpoint 403** → brug `static_models`, log, nudge
10. **Ny provider tilføjet** → auto-registrer under Central-kontrakten
11. **Model uden tool_call** → ekskludér fra coding/reasoning tasks
12. **Model uden reasoning** → ekskludér fra reasoning tasks
13. **Context window for lille** → ekskludér fra tasks der kræver > context
14. **Duplicate model på tværs providers** → behold begge, vælg efter score
15. **OpenCode app opdaterer model cache** → daemon læser ny cache, diff, opdater

## Forventet effekt

| Metric | Før | Efter |
|---|---|---|
| Aktive providers | 3 (deepseek, ollama, groq) | 7+ (3 + opencode-go, zenmux, zenifra, freemodel) |
| Agent-pool modeller | 1 (deepseek-flash) | 20+ (gratis) + 50+ (budget) |
| Gratis tokens/dag | ~0 (kun groq free tier) | 100K+ (zenmux gratis modeller) |
| Deepseek belastning | 100% af agent-kald | <30% (kun visible lane) |
| Model discovery | Manuel | Automatisk, daglig |
| Udgået model detektion | Ingen | <24t |
| Task matching | Fast model | Score-baseret, opdaterer sig selv |
| Centralen indsig | Ingen | Live model registry + events |

## Åbne spørgsmål

1. **FreeModel** — er det faktisk gratis premium-modeller, eller kræver det betaling? Skal testes.
2. **ZenMux rate limits** — hvor mange kald/dag kan vi lave på gratis modeller?
3. **Quality scoring** — skal vi køre benchmarks (HumanEval, MMLU) på gratis modeller for at rangere dem?
4. **OAuth providers** (github-copilot, openai) — skal de fjernes helt eller beholdes som disabled?
5. **Model aliasing** — hvis en model skifter navn, hvor længe beholder vi det gamle navn?