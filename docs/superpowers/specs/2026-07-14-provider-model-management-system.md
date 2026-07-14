---
status: udkast v5 — live-testet, Bjørns retning 14. jul 2026
formål: Komplet provider/model management-system — auto-scanning, scoring,
 auto-opdatering, health-check på alle providers. Udvider agent-pool med
 bekræftede gratis modeller og giver Centralen livscyklus-styring.
kilder: Samtale Bjørn+Jarvis 14. jul, live API-tests (nøgle→model→svar),
 provider_router.json, settings.py, auth profiles, full provider audit
revision: v5 — OpenRouter (4 gratis NVIDIA-modeller bekræftet), Sambanova (død)
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
- OpenRouter har 23 free-modeller, men de fleste er 429 rate-limited
- Sambanova er død — 402 Payment Required / timeout
- Ingen mekanisme detekterer nye modeller eller udgåede modeller
- Centralen har ingen indsigt i model-tilgængelighed eller -kvalitet
- Agent-poolen er reelt kun deepseek-flash + lokal ollama

## Live-testet provider-status (14. juli 2026)

### ✅ Virker — gratis (bevist med rigtigt model-svar)

| Provider | Endpoint | Modeller der virker | Latency |
|---|---|---|---|
| **OpenCode Go** | `https://opencode.ai/zen/v1/responses` | `big-pickle`, `deepseek-v4-flash-free`, `hy3-free`, `mimo-v2.5-free`, `nemotron-3-ultra-free`, `north-mini-code-free` | 1-7s |
| **Groq** | `https://api.groq.com/openai/v1` | 13 chat-modeller inkl. `llama-3.1-8b-instant`, `llama-3.3-70b-versatile`, `qwen/qwen3-32b`, `qwen/qwen3.6-27b`, `meta-llama/llama-4-scout-17b-16e-instruct`, `openai/gpt-oss-20b`, `openai/gpt-oss-120b`, `deepseek-r1` | 0.1-0.4s |
| **NVIDIA NIM** | `https://integrate.api.nvidia.com/v1` | **120+ modeller** inkl. `meta/llama-3.1-8b-instruct` (0.4s), `meta/llama-3.3-70b-instruct` (7.2s), 27 Llama-varianter | 0.4-7s |
| **Cloudflare** | `https://api.cloudflare.com/client/v4/accounts/{id}/ai/run/{model}` | **61 modeller** inkl. `@cf/meta/llama-3.3-70b-instruct-fp8-fast` (1.0s), `@cf/deepseek-r1-distill`, `@cf/meta/llama-4-scout`, `@cf/qwen2.5-coder`, `@cf/kimi-k2.7-code`, `@cf/glm-5.2` | 0.5-2s |
| **Arko** | `https://arko.arcaelas.com/v3/messages` | Agent-baseret — `aid` + `content` + `stream:false`. 4.2s svar på "Say OK" | 2-6s |
| **Gemini** | `https://generativelanguage.googleapis.com/v1beta` | `models/gemini-3.1-flash-lite` (0.6s), `models/gemma-4-26b-a4b-it` (1.3s) | 0.6-1.3s |
| **OpenRouter** | `https://openrouter.ai/api/v1` | `nvidia/nemotron-3-super-120b-a12b:free` (0.5s), `nvidia/nemotron-3-ultra-550b-a55b:free` (0.6-7.6s), `google/gemma-4-26b-a4b-it:free` (0.6-2.9s) | 0.5-7.6s |
| **Lokal Ollama** | `localhost:11434` | 10 lokale modeller | varierer |

### ⚠️ Delvist virkende

| Provider | Status | Begrænsning |
|---|---|---|
| **OpenRouter** (resten) | ❌ 429 | `meta-llama/llama-3.3-70b-instruct:free`, `qwen/qwen3-coder:free`, `tencent/hy3:free`, `openai/gpt-oss-20b:free` — alle rate-limited |
| **Gemini** (resten) | ❌ 429 quota / 503 | Kun 2 modeller tilgængelige |
| **OllamaFreeAPI** | ❌ Kun `deepseek-r1` | Resten timer ud |

### ❌ Virker ikke

| Provider | Fejl | Årsag |
|---|---|---|
| **Sambanova** | 402 / timeout | 3 modeller kræver betaling, 3 timeouter. Død. |
| **FreeModel.dev** | 200 men ToS / 403 | Claude = "kun via officiel Claude Code client". GPT = 403. |
| **ZenMux** | 403 | Nøglen har ikke adgang |
| **Zenifra** | Utestet | — |

## Auth-strategi

**Nøgler opbevares KUN i auth profiles — aldrig i specs, aldrig i kode, aldrig i repoet.**

| Provider | Auth type | Status |
|---|---|---|
| OpenCode Go | Bearer + User-Agent: `opencode/1.17.18` | ✅ |
| Groq | Bearer token (auth profile key, IKKE runtime.json key — den var forkert) | ✅ |
| NVIDIA NIM | Bearer token | ✅ 120+ modeller |
| Cloudflare | Bearer token + account_id | ✅ 61 modeller |
| Arko | Bearer token + agent_id | ✅ `/v3/messages` |
| Gemini | API key query param | ✅ 2 modeller |
| OpenRouter | Bearer token + `:free` suffix | ✅ 3 bekræftet |
| Ollama | Ingen (lokal) | ✅ Altid |
| DeepSeek | Bearer token | ✅ Betalt, kun visible lane |

**SPOF:** Ingen enkelt provider kan tage alt ned — alle er uafhængige.

## Endpoints & protokol

### OpenCode Go
- **Endpoint:** `https://opencode.ai/zen/v1/responses`
- **Format:** `{"model": M, "input": [{"role": "user", "content": "..."}], "stream": false}`
- **Headers:** `Authorization: Bearer {key}`, `User-Agent: opencode/1.17.18`

### NVIDIA NIM
- **Endpoint:** `https://integrate.api.nvidia.com/v1/chat/completions`
- **Format:** Standard OpenAI chat completions
- `/models` giver 120+ modeller at vælge imellem

### Cloudflare Workers AI
- **Endpoint:** `https://api.cloudflare.com/client/v4/accounts/{id}/ai/run/{model}`
- **Format:** POST med `{"messages": [...]}`
- Model-navne skal have `@cf/` præfiks

### Arko Studio
- **Endpoint:** `https://arko.arcaelas.com/v3/messages`
- **Format:** `{"aid": "{agent_id}", "content": "...", "stream": false, "customer": true}`

### OpenRouter
- **Endpoint:** `https://openrouter.ai/api/v1/chat/completions`
- **Format:** Standard OpenAI chat completions, model-navn med `:free` suffix
- De fleste gratis modeller er 429 rate-limited — kun NVIDIA-modeller virker stabilt

## Architecture

### 1. Model Discovery Daemon (daglig)

Kører én gang i døgnet. For hver provider:
1. **Scan** — kald `/models` endpoint, få fuld liste
2. **Diff** — sammenlign med sidste registrerede liste
3. **Test** — for nye modeller: send "Say OK", tjek svar og latency
4. **Content check** — verificér at svaret indeholder rigtigt indhold (ikke ToS-advarsel, ikke tomt)
5. **Persist** — opdater `provider_router.json` + event til Centralen
6. **Rollback** — backup før hver sync; auto-rollback hvis >50% modeller unreachable

### 2. Task-based scoring

Hver model scores på en vægtet sum af:
- **task_match** (0.0-1.0) — hvor god er modellen til coding / reasoning / classification / summarization / creative / fast_lookup?
- **latency** (invers, 0.0-1.0) — jo hurtigere, jo højere
- **cost** (1.0 = gratis, 0.0 = dyrest)
- **quality_score** (0.0-1.0) — baseret på daglige "Say OK"-test + garbage detection
- **reliability** (0.0-1.0) — uptime over de sidste 7 dage

Vægte konfigureres pr. opgavetype. Højeste score vinder ved dispatch.

### 3. Centralen-cluster `models`

Nye nerver:
- `model_registry` — levende liste over alle registrerede modeller
- `model_discovery` — events når nye modeller opdages
- `model_health` — events når modeller bliver unreachable
- `model_quality` — events ved quality degradation
- `agent_pool` — dispatch og rotation på tværs af modeller

### 4. Agent pool

- **Gratis først:** Alle kører på OpenCode/Groq/NVIDIA/Cloudflare/Arko/Gemini
- **Budget fallback:** Kun hvis ingen gratis model har score > tærskel
- **Premium:** Kun hvis Bjørn godkender — never automatic
- **Visible lane:** Uberørt — deepseek er kun til samtale med Bjørn

## Edge cases (15+2 nye)

1. Provider nede → skip, log, prøv igen næste dag
2. Model timeout (>30s) → marker `unreachable`, prøv om 1t
3. Rate limit (429) → backoff, prøv senere
4. Auth expired → nudge Bjørn via Centralen
5. Model deprecated (404) → fjern fra registry, emit event
6. Same model på flere providers → dedup: gratis > betalt; latency tiebreaker; unreachable eksklusion
7. Provider skifter pris → re-scor ved næste scan
8. Rollback trigger → backup før sync; auto-rollback hvis >50% unreachable
9. Quality degradation over tid → daglig test; 3 dage i træk = auto-removal
10. Garbage output → `quality_suspect`, nudge Bjørn
11. Gammel model fjernet → næste scan detekterer 404
12. Ny model opdaget → tilføj som `discovered` (observe-only indtil testet)
13. Free tier quota opbrugt → 429/402 → skip, prøv næste dag
14. Cloudflare model-navn ændres → daemon fanger det ved diff
15. NVIDIA model-liste opdateres → daemon fanger det
16. **Rollback trigger** — backup før hver sync; auto-rollback hvis >50% unreachable
17. **Quality degradation over tid** — daglig test fanger det; 3 dage i træk = auto-removal

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
| Gratis modeller i pool | ~2 | **~200** (6 OpenCode + 12 Groq + 120 NVIDIA + 61 Cloudflare + Arko + 2 Gemini + 3 OpenRouter + lokal ollama) |
| Deepseek belastning | 100% af agent-kald | <30% |
| Model discovery | Manuel | Automatisk, daglig |
| Udgået model detektion | Ingen | <24t |
| Provider diversity | 2 | **8 uafhængige kilder** |
| Centralen indsigt | Ingen | Live model registry + events |
