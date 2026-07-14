---
status: udkast v4 — live-testet, Bjørns retning 14. jul 2026
formål: Komplet provider/model management-system — auto-scanning, scoring,
 auto-opdatering, health-check på alle providers. Udvider agent-pool med
 bekræftede gratis modeller og giver Centralen livscyklus-styring.
kilder: Samtale Bjørn+Jarvis 14. jul, live API-tests (nøgle→model→svar),
 provider_router.json, settings.py, auth profiles, full provider audit
revision: v4 — NVIDIA NIM (+120 modeller), Cloudflare (61 modeller), Arko (v3/messages)
---

# Provider/Model Management System

## Problem

Jarvis' provider-landscape er statisk og manuelt vedligeholdt:
- `provider_router.json` har 16 providers, men model-lister er hardcodede og forældede
- OpenCode base URL var forkert → 403
- Groq brugte **forkert API-nøgle** i runtime.json (rigtig nøgle lå i auth profile)
- Gemini model-navne er udgået
- NVIDIA NIM brugte forkert model-navn (`nemotron-3-super-free` findes ikke, men 120+ andre virker)
- Cloudflare brugte forkert model-navn-format (skal være `@cf/meta/llama-...`)
- Arko DNS-fejl var forbigående — endpoint `/v3/messages` virker
- `gpt-oss:20b` (ollamafreeapi) eksisterer ikke → memory scoring fejler stille
- FreeModel.dev returnerer ToS-advarsel — ulovlig at bruge
- Ingen mekanisme detekterer nye modeller eller udgåede modeller
- Centralen har ingen indsigt i model-tilgængelighed eller -kvalitet
- Agent-poolen er reelt kun deepseek-flash + lokal ollama

## Live-testet provider-status (14. juli 2026)

### ✅ Virker — gratis (bevist med rigtigt model-svar)

| Provider | Endpoint | Modeller der virker | Latency |
|---|---|---|---|
| **OpenCode Go** | `https://opencode.ai/zen/v1/responses` | `big-pickle`, `deepseek-v4-flash-free`, `hy3-free`, `mimo-v2.5-free`, `nemotron-3-ultra-free`, `north-mini-code-free` | 1-7s |
| **Groq** | `https://api.groq.com/openai/v1` | `llama-3.1-8b-instant`, `llama-3.3-70b-versatile`, `qwen/qwen3-32b`, `qwen/qwen3.6-27b`, `meta-llama/llama-4-scout-17b-16e-instruct`, `allam-2-7b`, `openai/gpt-oss-20b`, `openai/gpt-oss-120b`, `openai/gpt-oss-safeguard-20b`, `deepseek-r1`, `llama-prompt-guard-2-22m`, `llama-prompt-guard-2-86m` (13 chat-modeller i alt) | 0.1-0.4s |
| **NVIDIA NIM** | `https://integrate.api.nvidia.com/v1` | **120+ modeller** inkl. `meta/llama-3.1-8b-instruct` (0.4s), `meta/llama-3.3-70b-instruct` (7.2s), `mistralai/mistral-large`, `nvidia/nemotron-4-340b` og 27 Llama-varianter | 0.4-7s |
| **Cloudflare Workers AI** | `https://api.cloudflare.com/client/v4/accounts/{id}/ai/run` | **61 modeller** inkl. `@cf/meta/llama-3.3-70b-instruct-fp8-fast` (1.0s), `@cf/deepseek-r1-distill`, `@cf/meta/llama-4-scout`, `@cf/qwen2.5-coder`, `@cf/kimi-k2.7-code`, `@cf/glm-5.2` | 0.5-2s |
| **Arko Studio** | `https://arko.arcaelas.com/v3/messages` | Agent-baseret inference (stateless). `aid` + `content` + `stream:false` — 4.2s svar på "Say OK" | 2-6s |
| **Gemini** | `https://generativelanguage.googleapis.com/v1beta` | `models/gemini-3.1-flash-lite` (0.6s), `models/gemma-4-26b-a4b-it` (1.3s) | 0.6-1.3s |
| **Lokal Ollama** | `localhost:11434` | 10 lokale modeller | varierer |

### ⚠️ Delvist virkende — gratis, men begrænset

| Provider | Status | Begrænsning |
|---|---|---|
| **Gemini** (resten) | ❌ 429 quota / 503 high demand | Kun 2 modeller tilgængelige lige nu |
| **OllamaFreeAPI** | ❌ Kun `deepseek-r1` virker | Resten timer ud |

### ❌ Virker ikke

| Provider | Fejl | Årsag |
|---|---|---|
| **FreeModel.dev** (cc + api) | 200 men ToS-advarsel / 403 | Claude = "Access Denied — kun via officiel Claude Code client", GPT = 403 |
| **ZenMux** | 403 | Nøglen har ikke adgang |
| **Zenifra** | Ikke testet | — |
| **OpenRouter** | 402 | Ingen credits |
| **Sambanova** | 404 | Begge modeller findes ikke |

## Auth-strategi

**Nøgler opbevares KUN i auth profiles — aldrig i specs, aldrig i kode, aldrig i repoet.**

| Provider | Auth type | Status |
|---|---|---|
| OpenCode Go | Bearer token + User-Agent: `opencode/1.17.18` | ✅ Virker |
| Groq | Bearer token (auth profile key, IKKE runtime.json key) | ✅ Virker — runtime.json key var forkert |
| NVIDIA NIM | Bearer token | ✅ Virker — 120+ modeller |
| Cloudflare | Bearer token + account_id | ✅ Virker — 61 modeller |
| Arko | Bearer token + agent_id | ✅ Virker — `/v3/messages` |
| Gemini | API key query param | ✅ Virker — 2 modeller, resten quota |
| Ollama | Ingen (lokal) | ✅ Altid |
| DeepSeek | Bearer token | ✅ Virker (betalt, kun visible lane) |

**Single point of failure:** Ingen enkelt provider kan tage alt ned — alle er uafhængige.

## Endpoints & protokol (dokumenteret)

### OpenCode Go
- **Endpoint:** `https://opencode.ai/zen/v1/responses`
- **Format:** Responses API (`input` som array, ikke string)
- **Headers:** `Authorization: Bearer {key}`, `User-Agent: opencode/1.17.18`
- **Eksempel body:** `{"model": "big-pickle", "input": [{"role": "user", "content": "Say OK"}], "stream": false}`

### NVIDIA NIM
- **Endpoint:** `https://integrate.api.nvidia.com/v1/chat/completions`
- **Format:** Standard OpenAI chat completions
- **Model-navne:** `meta/llama-3.1-8b-instruct`, `mistralai/mistral-large`, `nvidia/nemotron-4-340b` (brug `/v1/models` for fuld liste)
- **Bemærk:** `nemotron-3-super-free` findes IKKE. Brug de 120+ bekræftede modeller.

### Cloudflare Workers AI
- **Endpoint:** `https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/{model}`
- **Format:** Cloudflare AI protokol (eget format, ikke OpenAI-kompatibelt)
- **Model-navne:** Skal være fuldt qualified: `@cf/meta/llama-3.3-70b-instruct-fp8-fast`, `@cf/kimi-k2.7-code`, `@cf/glm-5.2`
- **Headers:** `Authorization: Bearer {key}`, `Content-Type: application/json`

### Arko Studio
- **Endpoint:** `https://arko.arcaelas.com/v3/messages`
- **Format:** `{"aid": "{agent_id}", "content": "Besked", "max_tokens": 512, "stream": false}`
- **Auth:** `x-api-key: {key}` header
- **Token-forbrug:** Kræver tokens på kontoen — tjek balance jævnligt

## Arkitektur

### Lag 1 — Provider Registry (eksisterende, udvides)

`provider_router.json` opdateres med korrekte endpoints og modeller.
Auth profiles som source of truth — runtime.json indeholder kun referencer.

### Lag 2 — Model Discovery Daemon (ny)

Kører dagligt:
1. Scan `/v1/models` eller tilsvarende endpoint for hver provider
2. Sammenlign modeller med eksisterende registry
3. Test hver ny model med et minimalt prompt ("Say OK") — mål reachable, latency, output-tokens
4. **Indholdstjek:** Verificér at svaret indeholder forventet tekst — HTTP 200 er ikke nok (jf. FreeModel-lektionen)
5. Persistér opdateret model-liste
6. Emit event til Centralen

### Lag 3 — Task-based scoring

Hver model scores pr. opgavetype (coding, reasoning, classification, summarization, creative, fast_lookup).
Vægte: `is_free=0.5, task_match=0.0-1.0, latency=0.15, reliability=0.15, quality_score=0.1`

### Lag 4 — Centralen `models` cluster

Cluster: `models` med nerver:
- `model_registry` — live oversigt over alle tilgængelige modeller
- `model_discovery` — events når nye modeller opdages
- `model_health` — events når modeller bliver unreachable
- `model_quality` — events ved quality degradation
- `agent_pool` — dispatch og rotation på tværs af modeller

### Edge cases (15 stk.)

1. Provider nede → skip, log, prøv igen næste dag
2. Model timeout (>30s) → marker som `unreachable`, prøv igen om 1t
3. Rate limit → backoff, prøv senere
4. Auth expired → nudge Bjørn via Centralen
5. Model deprecated (404) → fjern fra registry, emit event
6. Same model på flere providers → dedup: gratis > betalt; latency tiebreaker
7. Provider skifter pris → re-scor ved næste daglige scan
8. Rollback trigger → backup før hver sync; auto-rollback hvis >50% modeller unreachable
9. Quality degradation over tid → daglig test fanger det; 3 dage i træk = auto-removal
10. Garbage output → model svarer men indhold er ikke "OK" → `quality_suspect`
11. Gammel model fjernet fra provider → næste daglige scan detekterer 404
12. Ny model opdaget → tilføjes til registry som `discovered` (observe-only indtil testet)
13. Free tier quota opbrugt → 429/402 → skip, prøv næste dag
14. Cloudflare model-navn-ændring → daemon fanger det ved `/models` diff
15. NVIDIA model-liste opdateres dagligt → daemon fanger det

## Implementeringsfaser

| Fase | Beskrivelse | Estimeret tid |
|---|---|---|
| 1 | Fix runtime.json nøgler (Groq, NVIDIA, Cloudflare, Arko) | 30min |
| 2 | Opdater model-navne i settings.py (Gemini, NVIDIA, Cloudflare) | 30min |
| 3 | OpenCode Go Responses API integration i cheap lane | 2t |
| 4 | NVIDIA NIM + Cloudflare + Arko integration i cheap lane | 3t |
| 5 | Model Discovery Daemon (scan, diff, test, persist, content check) | 4t |
| 6 | Task-based scoring + dedup-logik | 3t |
| 7 | Centralen cluster `models` (events + nudges) | 2t |
| 8 | Agent pool integration (dispatch, rotation, fallback) | 2t |
| 9 | Tests (unit + integration + edge cases) | 3t |
| 10 | Shadow-kørsel (observe-only, 24t data) | 1t + 24t |
| 11 | Flip til aktiv | 1t |

**Total udvikling: ~22t + 24t shadow**

## Forventet effekt

| Metric | Før | Efter |
|---|---|---|
| Gratis modeller i pool | ~2 | **~200** (6 OpenCode + 12 Groq + 120 NVIDIA + 61 Cloudflare + Arko + 2 Gemini + lokal ollama) |
| Deepseek belastning | 100% af agent-kald | <30% |
| Model discovery | Manuel | Automatisk, daglig |
| Udgået model detektion | Ingen | <24t |
| Provider diversity | 2 | **7 uafhængige kilder** |
| Centralen indsigt | Ingen | Live model registry + events |
