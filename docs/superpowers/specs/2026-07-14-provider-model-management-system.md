---
status: udkast v2 (self-reviewet, Bjørns retning 14. jul 2026)
formål: Komplet provider/model management-system — auto-scanning, scoring,
 auto-opdatering, health-check på alle providers. Udvider agent-pool med
 OpenCode's 4 under-providers (opencode-go, zenifra, zenmux, freemodel)
 og giver Centralen livscyklus-styring over alle modeller.
kilder: Samtale Bjørn+Jarvis 14. jul, OpenCode config audit, provider_router.json,
 settings.py, cheap_provider_runtime_adapters.py, auth.json
revision: v2 — self-review fixes: test-strategi, gradient scoring, quality-måling,
 rollback, dedup-logik, auth SPOF, freemodel defineret, rate-limit blocker
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

## Auth-strategi

**To API-nøgler findes** — begge gyldige til OpenCode-providers:
- Nøgle A: Eksisterer i `auth.json` (bruges af OpenCode desktop app)
- Nøgle B: Leveres af Bjørn ved implementeringstidspunkt

**Ingen nøgler skrives i denne spec.** Nøgler leveres ad hoc når systemet implementeres.

**Single point of failure:** Begge nøgler er OpenCode-nøgler. Hvis OpenCode
revokerer kontoen, dør alle 4 providers samtidig. Mitigation:
- DeepSeek (visible lane) er uafhængig — samtaler med Bjørn påvirkes ikke
- Lokal Ollama er uafhængig — heartbeat/inner voice påvirkes ikke
- Groq (cheap lane) er uafhængig — daemon-kald påvirkes ikke
- Agent-poolen falder tilbage til Groq + Ollama hvis alle OpenCode-providers dør

## Arkitektur

### Lag 1 — Provider Registry (eksisterende, udvides)

`provider_router.json` udvides med alle 4 OpenCode-providers:

| Provider ID | API endpoint | Auth | Antal modeller | Gratis? |
|---|---|---|---|---|
| `opencode-go` | `https://opencode.ai/zen/go/v1` | API key | ~19 | Nej (billige) |
| `zenifra` | `https://ai.zenifra.com/v1` | API key | ~1 | Nej |
| `zenmux` | `https://zenmux.ai/api/v1` | API key | ~80+ | ~15 gratis |
| `freemodel` | `https://cc.freemodel.dev/v1` | API key | ~11 | Ukendt — se Lag 2 |

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

**Versioning:** Før hver opdatering af `provider_router.json` tages backup:
`provider_router.json.bak-{timestamp}`. Rollback = kopier backup tilbage.
Der gemmes maks 7 backups (rolling window).

### Lag 2 — Model Discovery Daemon (ny)

Kører **dagligt** (1440 min cadence). For hver provider med `auto_discover: true`:

1. **Backup** `provider_router.json` → `provider_router.json.bak-{timestamp}`
2. **Hent model-liste** fra `/models` endpoint (eller `static_models` hvis ingen endpoint)
3. **Diff mod eksisterende registry** — nye modeller, fjernede modeller, ændrede priser
4. **Test hver model** med et minimalt prompt ("Say OK") — måling:
   - Reachable (ja/nej)
   - Latency (ms)
   - Output tokens/sek
   - Tool call support (ja/nej)
   - Reasoning support (ja/nej)
   - **Quality check**: Svaret indeholder "OK" (case-insensitive)? → `quality_pass=true`
   - **Garbage detection**: Svaret er < 5 tegn eller > 500 tegn for "Say OK"? → `quality_suspect=true`
5. **Persistér** opdateret model-liste til `provider_router.json`
6. **Emit event** til Centralen: `model.discovered`, `model.deprecated`, `model.unreachable`

**FreeModel håndtering:**
- Første kørsel: test alle modeller med "Say OK" + quality check
- Hvis alle returnerer 403 → marker `freemodel` som `auth_required` (ikke gratis)
- Hvis modeller svarer → klassificér som gratis/budget/premium ud fra pris-data
- FreeModel forbliver `enabled: false` indtil bekræftet fungerende

**Edge cases:**
- Provider nede → skip, log, prøv igen næste dag
- Model timeout (>30s) → marker `unreachable`, ikke fjern
- Model returnerer 403/429 → marker `rate_limited`, cooldown 1 time, prøv igen
- `/models` endpoint returnerer 403 → brug `static_models` som fallback
- Ny model med ukendt navn → tilføj med `status: unverified`, test ved næste tick
- Model skifter fra gratis til betalt → marker `price_changed`, behold men deprioritér
- Provider slettet fra OpenCode → marker alle dens modeller `orphaned`
- **Quality check fejler** (ingen "OK" i svar) → marker `unstable`, deprioritér, retest næste dag
- **Garbage output** (tom/meget kort/vildt langt svar) → marker `quality_suspect`, ekskludér fra pool
- **Rollback nødvendig** → hvis >50% af modeller bliver `unreachable` efter sync, auto-rollback til backup + alert Centralen

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
      + w_quality * quality_score
```

Hvor:
- `task_match` = **gradient 0.0–1.0** (ikke binær):
  - 1.0 = model har alle krævede capabilities (tool_call + reasoning for coding)
  - 0.5 = model har delvis match (tool_call men ikke reasoning)
  - 0.0 = model mangler kritiske capabilities
- `normalized_cost` = cost / max_cost_i_poolen
- `normalized_latency` = latency / max_latency_i_poolen
- `is_free` = 1.0 hvis input=0 og output=0, 0.0 ellers
- `uptime_pct` = succesrate over sidste 7 dage (fra health-check)
- `quality_score` = 1.0 hvis `quality_pass=true`, 0.3 hvis `quality_suspect=true`, 0.0 hvis aldrig testet

**Default vægte:**
- `w_relevance = 0.30` — must have (sænket fra 0.35 pga gradient)
- `w_free = 0.25` — gratis først
- `w_reliability = 0.20` — stabil model > ustabil gratis model
- `w_quality = 0.15` — kvalitetsmåling fra health-check
- `w_cost = 0.05` — sekundær (gratis modeller har allerede w_free)
- `w_latency = 0.05` — sekundær (de fleste gratis modeller er hurtige)

**Dedup-logik — samme model på flere providers:**
Når samme model-ID findes på 2+ providers (fx `deepseek-v4-flash` på både
opencode-go og zenmux):
1. Hvis begge er gratis → vælg den med lavest latency (sidste 7 dage gennemsnit)
2. Hvis én er gratis, anden betalt → vælg gratis
3. Hvis begge er betalte → vælg den med lavest cost
4. Hvis én er `unreachable` → vælg den anden automatisk
5. Hvis begge er `unreachable` → ekskludér, emit `model.duplicate_dead` event

### Lag 4 — Centralen Integration (ny)

Ny cluster: `models` med 5 nerver:

| Nerve | Funktion |
|---|---|
| `model_registry` | Holder live model-liste (fra discovery daemon) |
| `model_health` | Tracker uptime, latency, quality per model |
| `model_cost_guard` | Overvåger samlet agent-pool spending; alert ved >$X/dag |
| `model_selector` | Modtager task-type, returnerer bedste model (scoring) |
| `model_lifecycle` | Administrerer add/remove/deprecate events |

**Events:**
- `model.discovered` → nudge Jarvis: "Ny model tilgængelig: {model_id} på {provider}"
- `model.deprecated` → nudge Jarvis: "Model udgået: {model_id},替代 fundet: {alt}"
- `model.unreachable` → log, hvis critical model → nudge Jarvis
- `model.price_changed` → log, opdater scoring
- `model.quality_degraded` → nudge Jarvis: "Model {model_id} producerer garbage — fjernet fra pool"

### Lag 5 — Agent Pool Integration

Agent-poolen udvides fra 1 model til 20+ gratis + 50+ budget:

**Dispatch-rækkefølge:**
1. **Gratis modeller** (is_free=1.0) — sorteret efter task-score
2. **Budget modeller** (cost < $0.50/1M tokens) — sorteret efter task-score
3. **Premium modeller** (cost > $0.50/1M tokens) — kun ved eksplicit behov
4. **Visible lane** (deepseek) — **aldrig** brugt til agenter, kun til samtaler med Bjørn

**Pool-rotation:** Hvis en gratis model har været `unreachable` i 3 dage → fjern fra pool.
Hvis den kommer tilbage → re-tilføj ved næste discovery tick.

## Gratis modeller — komplet liste (per 14. jul 2026)

### ZenMux (https://zenmux.ai/api/v1) — flest gratis modeller
| Model ID | Task-egnhed | Context | Tool/Reasoning |
|---|---|---|---|
| `big-pickle` | coding, reasoning | ? | tool=yes |
| `minimax-m2.5-free` | reasoning, creative | ? | tool=yes |
| `minimax-m2.1-free` | reasoning | ? | tool=yes |
| `mimo-v2-flash-free` | classification, fast_lookup | ? | tool=? |
| `mimo-v2-omni-free` | creative, summarization | ? | tool=? |
| `ling-2.6-flash-free` | classification, fast_lookup | ? | tool=? |
| `nemotron-3-super-free` | reasoning | ? | tool=yes |
| `north-mini-code-free` | coding | ? | tool=yes |
| `grok-code` | coding | ? | tool=yes |
| `hy3-free` | ? | ? | ? |
| `hy3-preview-free` | ? | ? | ? |
| `trinity-large-preview-free` | reasoning | ? | ? |
| `glm-5-free` | reasoning, coding | ? | tool=yes |
| `glm-4.7-flash-free` | classification, fast_lookup | ? | tool=yes |
| `glm-4.6v-flash-free` | classification | ? | tool=? |
| `qwen3.6-plus-free` | reasoning, coding | ? | tool=yes |
| `kimi-k2.7-code-free` | coding | ? | tool=yes |

### OpenCode Go (https://opencode.ai/zen/go/v1) — billige, ikke gratis
| Model ID | Pris (input/output) | Context | Tool/Reasoning |
|---|---|---|---|
| `deepseek-v4-flash` | $0.14/$0.28 | 1M | tool=yes, reasoning=yes |
| `minimax-m2.5` | $0.30/$1.20 | 204K | tool=yes, reasoning=yes (deprecated) |
| `qwen3.7-plus` | $0.40/$1.60 | 1M | tool=yes, reasoning=yes |
| `qwen3.7-max` | $2.50/$7.50 | 1M | tool=yes, reasoning=yes |
| `kimi-k2.7-code` | $0.95/$4.00 | 262K | tool=yes, reasoning=yes |
| `glm-5.1` | $1.40/$4.40 | 202K | tool=yes, reasoning=yes |
| `deepseek-v4-pro` | $1.74/$3.48 | 1M | tool=yes, reasoning=yes |
| `glm-5.2` | ? | ? | tool=yes, reasoning=yes |

### Zenifra (https://ai.zenifra.com/v1) — 1 model
| Model ID | Pris | Bemærkning |
|---|---|---|
| Ukendt — skal testes ved implementering | — | — |

### FreeModel (https://cc.freemodel.dev/v1) — ukendt status
| Model ID | Pris | Bemærkning |
|---|---|---|
| ~11 modeller | Ukendt | Første kørsel: test alle, klassificér ud fra resultat. Forbliver `enabled: false` indtil bekræftet. |

## Test-strategi

### Unit tests
- `test_scoring.py`: Given 5 modeller med forskellige capabilities, assert rigtig model vælges per task-type
- `test_scoring_gradient.py`: Model med delvis match scorer højere end model med 0 match, lavere end fuld match
- `test_dedup.py`: Samme model på 2 providers → vælg efter dedup-reglerne (gratis > betalt, latency tiebreaker)
- `test_quality_check.py`: "Say OK" svar → quality_pass=true; "asdf" → quality_suspect=true; "" → quality_suspect=true
- `test_rollback.py`: Hvis >50% unreachable efter sync → auto-rollback triggeret, backup genskabt

### Integration tests
- `test_discovery_daemon.py`: Mock `/models` endpoint, assert diff (ny model, fjernet model, prisændring)
- `test_health_check.py`: Mock provider nede → graceful fallback, ingen crash
- `test_centralen_events.py`: Discovery → emit events med korrekt payload
- `test_agent_dispatch.py`: Task-type "coding" → model med tool_call valgt, model uden tool_call ekskluderet

### Edge case tests (alle 15+ edge cases)
- `test_edge_provider_down.py`: Provider nede → skip, log, ingen crash
- `test_edge_model_timeout.py`: Model >30s → marker `unreachable`, ikke fjern
- `test_edge_rate_limit.py`: 429 → cooldown, prøv igen
- `test_edge_garbage_output.py`: Tom/kort/vildt langt svar → `quality_suspect`
- `test_edge_price_change.py`: Gratis → betalt → `price_changed`, deprioritér
- `test_edge_orphaned.py`: Provider slettet → modeller `orphaned`
- `test_edge_rollback.py`: >50% unreachable → auto-rollback

### Test coverage krav
- Minimum 90% coverage på scoring-algoritme
- Minimum 80% coverage på discovery daemon
- Alle edge cases har mindst én test

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
14. **Duplicate model på tværs providers** → dedup-logik (Lag 3): gratis > betalt, latency tiebreaker
15. **OpenCode app opdaterer model cache** → daemon læser ny cache, diff, opdater
16. **>50% modeller unreachable efter sync** → auto-rollback til backup, alert Centralen
17. **Quality degradation over tid** → model der var god bliver ustabil → retest, deprioritér

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
| Quality kontrol | Ingen | Daglig health-check med quality scoring |

## Blockers (skal løses før implementering)

1. **ZenMux rate limits** — hvor mange kald/dag kan vi lave på gratis modeller?
   Hvis <50/dag er "100K+ gratis tokens/dag" forventningen falsk. Skal testes.
2. **FreeModel status** — er det gratis premium-modeller eller betalt? Første kørsel afgør.

## Åbne spørgsmål

1. **Quality benchmarks** — skal vi køre HumanEval/MMLU på gratis modeller for at rangere dem ud over "Say OK"?
2. **OAuth providers** (github-copilot, openai) — skal de fjernes helt eller beholdes som disabled?
3. **Model aliasing** — hvis en model skifter navn, hvor længe beholder vi det gamle navn? (Edge case 2 siger 1 uge)
4. **Scoring vægte tuning** — skal vægtene justeres baseret på empiri efter 1 uges data?

## Implementeringsfaser

| Fase | Beskrivelse | Estimeret tid | Afhængighed |
|---|---|---|---|
| 1 | Provider registry udvidelse (4 OpenCode-providers i router.json) | 2t | Ingen |
| 2 | Model Discovery Daemon (scan, diff, test, persist) | 4t | Fase 1 |
| 3 | Task-based scoring + dedup-logik | 3t | Fase 2 |
| 4 | Centralen cluster `models` (5 nerver + events) | 3t | Fase 2 |
| 5 | Agent pool integration (dispatch-rækkefølge, pool-rotation) | 2t | Fase 3+4 |
| 6 | Tests (unit + integration + edge cases) | 4t | Fase 2-5 |
| 7 | Shadow-kørsel (observe-only, 24t) | 1t setup + 24t vent | Fase 1-6 |
| 8 | Flip til aktiv (med Bjørn + Claude review) | 1t | Fase 7 data |

**Total udvikling: ~18t + 24t shadow**