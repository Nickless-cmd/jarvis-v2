---
status: udkast v4 — live-testet, Bjørns retning 14. jul 2026
formål: Komplet provider/model management-system — auto-scanning, scoring,
 auto-opdatering, health-check på alle providers. Udvider agent-pool med
 bekræftede gratis modeller og giver Centralen livscyklus-styring.
kilder: Samtale Bjørn+Jarvis 14. jul, live API-tests (nøgle→model→svar),
 provider_router.json, settings.py, auth profiles, Groq+Gemini+NVIDIA+Cloudflare+Arko+OpenRouter+Sambanova audit
revision: v4 — alle kendte providers live-testet, reelle tal, key-fixes, fjernet FreeModel
---

# Provider/model management system

## 1. Baggrund

I dag er Jarvis' model-økonomi meget smal:
- **visible lane**: deepseek v4-pro/v4-flash (betalt)
- **cheap lane**: groq llama-3.1-8b-instant (gratis tier)
- **local lane**: lokal ollama
- **relevance**: opencode (død — 403)
- **memory scoring**: ollamafreeapi (kun deepseek-r1 virker)

Mange providers er konfigureret men virker ikke pga. forkerte nøgler, forkerte model-navne, udgåede endpoints eller døde gratis-modeller. Dette system skal:
1. Finde alle providers vi har credentials til
2. Teste hver provider live (nøgle → model → svar)
3. Opdatere config automatisk
4. Scanne dagligt for ændringer
5. Vælge den skarpeste gratis model til hver agent-opgave

## 2. Mål

- **20+ bekræftede gratis modeller** i agent-poolen
- **Auto-discovery** af nye/udgåede modeller hver dag
- **Task-baseret scoring** så den rigtige model vælges til den rigtige opgave
- **Centralen-integration** så vi altid ved hvad der virker
- **Ingen betalte modeller uden godkendelse**

## 3. Arkitektur

### 3.1 Komponenter

```
┌─────────────────────────────────────────┐
│  Provider Discovery Daemon (daglig)     │
│  - Henter /models fra hver provider     │
│  - Sammenligner med provider_router.json│
│  - Rapporterer diff til Centralen       │
└─────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────┐
│  Provider Health Daemon (hver 6. time)    │
│  - Tester nøgle → model → svar          │
│  - Markerer reachable/unreachable       │
│  - Opdaterer health-score               │
└─────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────┐
│  Model Scoring Engine                   │
│  - Task-match: coding/reasoning/etc.    │
│  - Cost: gratis først                   │
│  - Quality: health + latency + output   │
│  - Context: passende context window     │
└─────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────┐
│  Agent Pool Router                      │
│  - Vælger bedste model pr. opgave       │
│  - Fallback-kæde hvis model fejler       │
│  - Budget-guard: ingen betalte uden OK  │
└─────────────────────────────────────────┘
```

### 3.2 Dataformat

Hver model registreres med:
```json
{
  "provider": "groq",
  "model": "llama-3.3-70b-versatile",
  "lane": "cheap",
  "cost_input": 0.0,
  "cost_output": 0.0,
  "context": 128000,
  "tool_support": true,
  "reasoning": false,
  "health": {
    "reachable": true,
    "last_tested": "2026-07-14T14:20:00Z",
    "latency_ms": 150,
    "quality_score": 0.92
  },
  "task_scores": {
    "coding": 0.85,
    "reasoning": 0.80,
    "classification": 0.90,
    "summarization": 0.88,
    "creative": 0.60,
    "fast_lookup": 0.95
  }
}
```

## 4. Live-testede providers (14. jul 2026)

### ✅ Bekræftet fungerende

| Provider | Endpoint | Modeller | Bemærkning |
|---|---|---|---|
| **OpenCode Go** | `https://opencode.ai/zen/v1/responses` | 6 gratis | Kræver `User-Agent: opencode/1.17.18` og `input`-array format |
| **Groq** | `https://api.groq.com/openai/v1` | 12+ | Nøgle i runtime.json var forkert; rigtig nøgle ligger i auth profile |
| **NVIDIA NIM** | `https://integrate.api.nvidia.com/v1` | 120+ | Nøgle virker; model-navne skal være `meta/llama-3.3-70b-instruct` etc. |
| **Cloudflare** | `https://api.cloudflare.com/client/v4/accounts/{id}/ai/v1` | 61 | Model-navne skal have `@cf/` præfiks |
| **Arko** | `https://arko.arcaelas.com/v3/messages` | Agent-baseret | `aid` + `content` + `stream: false` |
| **Gemini** | `https://generativelanguage.googleapis.com/v1beta` | 2 | `gemini-3.1-flash-lite` og `gemma-4-26b-a4b-it` virker; resten quota/udgået |
| **OpenRouter** | `https://openrouter.ai/api/v1` | 4-23 gratis | Mange 429; `nvidia/nemotron-3-super-120b-a12b:free` og `google/gemma-4-26b-a4b-it:free` bekræftet |
| **Lokal Ollama** | `http://localhost:11434` | 10+ | Altid gratis, altid tilgængelig |
| **DeepSeek** | `https://api.deepseek.com` | v4-flash, v4-pro | Betalt; reserveres til visible lane |

### ❌ Ikke fungerende / fjernet

| Provider | Fejl | Årsag |
|---|---|---|
| **FreeModel.dev** | ToS-violation | Claude-modeller returnerer 200 med advarsel om uautoriseret brug; GPT 403 |
| **Sambanova** | 402/timeout | Halvdelen kræver betaling; resten timeout |
| **ZenMux** | 403 | Nøgle har ikke adgang |
| **Zenifra** | Utestet | Kræver sandsynligvis separat nøgle |
| **opencode (relevance backend)** | 403 | Udgået endpoint; erstattes af OpenCode Go |
| **ollamafreeapi** | Delvist død | Kun `deepseek-r1` svarer |

## 5. Bekræftede gratis modeller (agent-pool kandidater)

### OpenCode Go (6)
- `big-pickle`
- `deepseek-v4-flash-free`
- `hy3-free`
- `mimo-v2.5-free`
- `nemotron-3-ultra-free`
- `north-mini-code-free`

### Groq (12)
- `llama-3.1-8b-instant`
- `llama-3.3-70b-versatile`
- `qwen/qwen3-32b`
- `qwen/qwen3.6-27b`
- `meta-llama/llama-4-scout-17b-16e-instruct`
- `allam-2-7b`
- `openai/gpt-oss-20b`
- `openai/gpt-oss-120b`
- `openai/gpt-oss-safeguard-20b`
- `llama-prompt-guard-2-22m`
- `llama-prompt-guard-2-86m`
- `deepseek-r1`

### NVIDIA NIM (120+, highlights)
- `meta/llama-3.1-8b-instruct`
- `meta/llama-3.3-70b-instruct`
- `meta/llama-3.2-3b-instruct`
- `nvidia/nemotron-3-super-120b-a12b`
- `nvidia/nemotron-3-ultra-550b-a55b`
- `google/gemma-4-26b-a4b-it`
- `deepseek/deepseek-r1`

### Cloudflare (61, highlights)
- `@cf/meta/llama-3.3-70b-instruct-fp8-fast`
- `@cf/meta/llama-4-scout-17b-16e-instruct`
- `@cf/deepseek/deepseek-r1-distill-qwen-32b`
- `@cf/qwen/qwen2.5-coder-32b-instruct`
- `@cf/01-ai/glm-5.2-9b-instruct`
- `@cf/moonshotai/kimi-k2.7-code`

### OpenRouter (4 bekræftet, 23 listed)
- `nvidia/nemotron-3-super-120b-a12b:free`
- `nvidia/nemotron-3-ultra-550b-a55b:free`
- `google/gemma-4-26b-a4b-it:free`
- `tencent/hy3:free` (ustabil)

### Gemini (2)
- `gemini-3.1-flash-lite`
- `gemma-4-26b-a4b-it`

### Arko (agent-baseret)
- Bruger agent ID `973c6091-988a-4c3c-bb0f-ea0aaa73c184`

## 6. Task-baseret scoring

For hver opgave beregnes:

```
score = (
  task_match * 0.35 +
  is_free * 0.25 +
  health_score * 0.20 +
  context_fit * 0.10 +
  latency_score * 0.10
)
```

| Faktor | Værdi | Bemærkning |
|---|---|---|
| `task_match` | 0.0–1.0 | Gradient: hvor godt model egner sig til opgaven |
| `is_free` | 1.0 hvis gratis, 0.0 hvis betalt | Betalte modeller fravælges medmindre godkendt |
| `health_score` | 0.0–1.0 | Baseret på seneste health-check + historik |
| `context_fit` | 0.0–1.0 | 1.0 hvis context window > 2× forventet input |
| `latency_score` | 0.0–1.0 | Hurtigere = højere |

## 7. Auto-discovery

### 7.1 Daglig scanning

Hver dag kl. 04:00:
1. Hent `/models` fra hver provider
2. Sammenlign med `provider_router.json`
3. Rapporter nye/udgåede modeller til Centralen
4. Kør health-check på nye modeller
5. Opdater scoring

### 7.2 Diff-format

```json
{
  "provider": "groq",
  "added": ["meta-llama/llama-4-scout-17b-16e-instruct"],
  "removed": ["llama-3.1-70b-versatile"],
  "changed": [{"model": "llama-3.3-70b-versatile", "was_free": true, "now_free": false}]
}
```

## 8. Health-check

### 8.1 Hvad testes

For hver model:
1. `GET /models` eller tilsvarende — tjek om model findes
2. Send prompt: `"Say OK"` — tjek om der kommer svar
3. Tjek om svaret faktisk indeholder "OK" (ikke bare 200)
4. Mål latency
5. Gem resultat

### 8.2 Kvalitetsflag

| Flag | Betydning |
|---|---|
| `quality_pass` | Svar indeholder forventet indhold |
| `quality_suspect` | Svar kom, men indhold var uventet |
| `quality_fail` | Ingen svar, 4xx/5xx, eller ToS-advarsel |

## 9. Centralen-integration

### 9.1 Nyt cluster: `models`

| Nerve | Ansvar |
|---|---|
| `discovery` | Daglig scanning |
| `health` | Health-checks |
| `scoring` | Task-scoring |
| `router` | Valg af model pr. opgave |
| `budget_guard` | Blokerer betalte modeller uden godkendelse |

### 9.2 Events

- `model.discovered`
- `model.removed`
- `model.health_changed`
- `model.quality_degraded`
- `provider.auth_failed`
- `budget.betal_model_blocked`

## 10. Edge cases

1. **Provider nede** → marker alle modeller unreachable, fallback til næste provider
2. **Model forsvinder** → fjern fra pool, nudge hvis den var i brug
3. **Model går fra gratis til betalt** → budget_guard blokerer, nudge
4. **Rate limit** → backoff + prøv næste model
5. **Tomt svar / ToS-advarsel** → quality_fail, fjern fra pool
6. **Forkert model-navn** → discovery daemon finder korrekt navn
7. **Forkert nøgle** → auth_failed event, brug auth profile i stedet
8. **DNS fejl** → retry med exponential backoff
9. **Context for lille** → vælg større model
10. **Ingen gratis modeller til opgaven** → nudge Bjørn, tilbyd betalt model
11. **Alle providers nede** → fallback til lokal ollama
12. **Ny model tilføjet** → shadow-test før den aktiveres
13. **Model duplicate på flere providers** → vælg efter health/latency
14. **Quality falder over tid** → degrading alert
15. **Rollback trigger** → hvis >50% modeller bliver unreachable, ruller til sidste backup
16. **Betalingsmetode kræves** → marker som "kræver setup", ikke som gratis
17. **429 Too Many Requests** → rate-limit queue, prøv igen senere

## 11. Implementeringsfaser

| Fase | Hvad | Estimeret tid |
|---|---|---|
| 1 | Discovery daemon + model-liste sync | 1 dag |
| 2 | Health-check daemon med kvalitetsflag | 1 dag |
| 3 | Scoring engine + task-mapping | 2 dage |
| 4 | Agent pool router + fallback-kæde | 2 dage |
| 5 | Centralen cluster + events | 1 dag |
| 6 | Tests + edge cases + rollback | 2 dage |

## 12. Åbne spørgsmål

1. **OpenRouter rate limits** — hvor mange gratis kald pr. minut? Skal testes over tid.
2. **Gemini quota** — hvor mange kald pr. dag på gratis tier?
3. **NVIDIA NIM limits** — 120+ modeller, men hvor mange er faktisk gratis?
4. **Cloudflare model format** — `@cf/` præfiks er bekræftet; skal håndtere specielle auth headers.
5. **Arko agent ID** — hardcoded til én agent; skal generaliseres.
6. **ZenMux/Zenifra** — kræver separat nøgle/adgang; udskydes indtil vi har credentials.
7. **Sambanova** — død; fjernes eller genbesøges senere.

## 13. Principper

- **Gratis først.** Altid.
- **Betalte modeller kræver godkendelse.** Ingen auto-fallback til betalte.
- **Rå data til Centralen.** Ingen gæt — kun live-testede facts.
- **Fail soft.** Hvis en model fejler, prøv næste. Hvis alle fejler, ollama.
- **Ingen ToS-brud.** FreeModel blev droppet af den grund.
