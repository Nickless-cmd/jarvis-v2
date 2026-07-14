---
status: udkast v3 — live-testet, Bjørns retning 14. jul 2026
formål: Komplet provider/model management-system — auto-scanning, scoring,
 auto-opdatering, health-check på alle providers. Udvider agent-pool med
 bekræftede gratis modeller og giver Centralen livscyklus-styring.
kilder: Samtale Bjørn+Jarvis 14. jul, live API-tests (nøgle→model→svar),
 provider_router.json, settings.py, auth profiles, Groq+Gemini audit
revision: v3 — Groq key fix, Gemini model-opdatering, reelle tal
---

# Provider/Model Management System

## Problem

Jarvis' provider-landscape er statisk og manuelt vedligeholdt:
- `provider_router.json` har 16 providers, men model-lister er hardcodede og forældede
- OpenCode base URL var forkert (`/zen/v1` i stedet for `/zen/v1/responses`) → 403
- Groq brugte **forkert API-nøgle** i runtime.json → 403/401 (rigtig nøgle lå i auth profile)
- Gemini model-navne er udgået — `gemini-2.5-flash` findes ikke længere
- `gpt-oss:20b` (ollamafreeapi) eksisterer ikke → memory scoring fejler stille
- FreeModel.dev returnerer ToS-advarsel — ulovlig at bruge
- Ingen mekanisme detekterer nye modeller eller udgåede modeller
- Centralen har ingen indsigt i model-tilgængelighed eller -kvalitet
- Agent-poolen er reelt kun deepseek-flash + lokal ollama

## Fundne provider-status (live-testet 14. juli 2026)

### ✅ Virker — gratis

| Provider | Nøgle-status | Modeller der virker | Latency |
|---|---|---|---|
| **OpenCode Go** (`/zen/v1/responses`) | ✅ Auth profile | `big-pickle`, `deepseek-v4-flash-free`, `hy3-free`, `mimo-v2.5-free`, `nemotron-3-ultra-free`, `north-mini-code-free` | 1-7s |
| **Groq** (`api.groq.com`) | ✅ Nøgle i auth profile | `llama-3.1-8b-instant`, `llama-3.3-70b-versatile`, `qwen/qwen3-32b`, `qwen/qwen3.6-27b`, `meta-llama/llama-4-scout-17b-16e-instruct`, `allam-2-7b`, `openai/gpt-oss-20b`, `openai/gpt-oss-120b`, `openai/gpt-oss-safeguard-20b`, `deepseek-r1`, `llama-prompt-guard-2-22m`, `llama-prompt-guard-2-86m` | 0.1-0.4s |
| **Gemini** (`generativelanguage.googleapis.com`) | ✅ Api-nøgle | `gemini-3.1-flash-lite` (0.6s), `gemma-4-26b-a4b-it` (1.3s) | 0.6-1.3s |
| **Lokal Ollama** (`localhost:11434`) | ✅ Ingen nøgle | 10 lokale modeller | varierer |

### ❌ Virker ikke

| Provider | Fejl | Årsag |
|---|---|---|
| **FreeModel.dev** (cc + api) | 200 men ToS-advarsel / 403 | Claude = "Access Denied — kun via officiel Claude Code client", GPT = 403 |
| **ZenMux** (`zenmux.ai`) | 403 | Nøglen har ikke adgang |
| **Zenifra** (`ai.zenifra.com`) | Ikke testet | — |
| **Nvidia-NIM** | 404 | Model findes ikke |
| **Cloudflare** | 400 | Forkert model-navn |
| **Arko** | DNS-fejl | Navnetjeneste fejler |
| **OpenRouter** | 402 | Ingen credits |
| **Sambanova** | 404 | Model findes ikke |
| **OllamaFreeAPI** | Delvist nede | Kun `deepseek-r1` virker |

### 📡 Groq — specifikke detaljer

Groq fejlede tidligere med 403/401. Årsag: **runtime.json brugte en forkert nøgle** (`gsk_0bDFcTz...`). 
Den korrekte nøgle ligger i auth profile (`gsk_cN2mhI...`) og blev testet med 13 chat-modeller, alle ✅ på 0.1-0.4s.

**Fix:** Opdater `runtime.json` til at bruge auth profile-nøglen i stedet for den hardcodede forkerte nøgle.

### 📡 Gemini — specifikke detaljer

Gemini API-nøgle (`AIzaSyD...`) er aktiv. Model-landskabet har ændret sig:

| Gammelt navn | Status | Nyt navn (hvis relevant) |
|---|---|---|
| `gemini-2.5-flash` | ❌ 404 — deprecated | `gemini-3.1-flash-lite` |
| `gemini-2.5-pro` | ❌ 429 — quota opbrugt | — |
| `gemini-2.0-flash` | ❌ 429 — quota opbrugt | — |
| `gemini-1.5-flash` | ❌ 404 — deprecated | — |
| `gemini-1.5-pro` | ❌ 404 — deprecated | — |
| `gemini-3.5-flash` | ⚠️ 503 — high demand | Prøv igen senere |
| **`gemini-3.1-flash-lite`** | ✅ **0.6s — virker** | — |
| **`gemma-4-26b-a4b-it`** | ✅ **1.3s — virker** | — |
| `gemini-3.1-flash-image` | ❌ 429 — quota | — |
| `gemini-3.1-flash-lite-image` | ❌ 429 — quota | — |

### 📡 FreeModel.dev — advarsel

FreeModel Claude-modeller returnerer HTTP 200 men indholdet er en ToS-advarsel:
> *"Access Denied: This service is restricted to authorized use through the official Claude Code client only."*

**Brug af FreeModel.dev udgør en ToS-violation og bør undgås.** GPT-modellerne på `api.freemodel.dev` giver 403.

## Auth-strategi

**Én primær OpenCode-nøgle** (fra auth profile) + **separate nøgler** til Gemini, Groq, DeepSeek.

**Single point of failure:** OpenCode-nøglen. Hvis den revokeres dør OpenCode-modellerne.
Mitigation:
- DeepSeek (visible lane) er uafhængig — samtaler med Bjørn påvirkes ikke
- Lokal Ollama er uafhængig — heartbeat/inner voice påvirkes ikke
- Groq er uafhængig (separat nøgle) — daemon-kald påvirkes ikke
- Gemini er uafhængig (separat nøgle)
- Agent-poolen falder tilbage til Groq + Ollama + Gemini hvis OpenCode dør

**Groq-key-fejl:** runtime.json brugte en forkert nøgle. Den korrekte nøgle ligger i auth profile.
Fix: Opdater runtime.json til at pege på auth profile-nøglen.

## Arkitektur

### Lag 1 — Provider Registry (eksisterende, udvides)

`provider_router.json` opdateres med korrekte endpoints og modeller:

| Provider ID | API endpoint | Format | Auth | Bekræftede gratis modeller |
|---|---|---|---|---|
| `opencode-go` | `https://opencode.ai/zen/v1/responses` | Responses API | OpenCode key | 6 |
| `groq` | `https://api.groq.com/openai/v1` | Chat completions | Groq key | 12 |
| `gemini` | `https://generativelanguage.googleapis.com/v1` | Gemini generateContent | Gemini key | 2 |
| `ollama` | `http://localhost:11434` | Chat completions | Ingen | 10 |

**OpenCode Go kræver:**
- **Endpoint:** `/responses` (IKKE `/chat/completions`)
- **Format:** `{"model": "...", "input": [{"role": "user", "content": "..."}]}`
- **Headers:** `Authorization: Bearer {key}`, `User-Agent: opencode/1.17.18`
- Chat completions virker også på 4 af 6 modeller

**Groq kræver:**
- **Endpoint:** `/chat/completions`
- **Format:** Standard OpenAI chat format
- **Key:** Skal hentes fra auth profile, IKKE runtime.json

**Gemini kræver:**
- **Endpoint:** `/{model}:generateContent?key={api_key}`
- **Format:** `{"contents": [{"role": "user", "parts": [{"text": "..."}]}]}`
- Model-navne skal opdateres — `gemini-2.5-flash` findes ikke længere

### Lag 2 — Model Discovery Daemon (ny)

Kører **dagligt** (1440 min cadence). For hver provider med `auto_discover: true`:

1. **Backup** `provider_router.json` → `provider_router.json.bak-{timestamp}`
2. **Hent model-liste** fra `/models` endpoint (eller `static_models` hvis ingen endpoint)
3. **Diff mod eksisterende registry** — nye modeller, fjernede modeller, ændrede priser
4. **Test hver model** med et minimalt prompt ("Say OK") — måling:
   - Reachable (ja/nej)
   - Latency (ms)
   - Output tokens/sek
   - **Indholdstjek**: Returnerer faktisk tekst, ikke bare HTTP 200 med tom body
   - **Garbage detection**: Svaret indeholder "OK" → `quality_pass=true`
5. **Persistér** opdateret model-liste til `provider_router.json`
6. **Emit event** til Centralen: `model.discovered`, `model.deprecated`, `model.unreachable`

**Vigtig læring fra FreeModel-test:** HTTP 200 betyder ikke at modellen virker.
Discovery daemon skal ALTID verificere at svaret indeholder forventet indhold,
ikke bare at HTTP status er ok.

**Edge cases:**
- Provider nede → skip, log, prøv igen næste dag
- Model timeout (>30s) → marker ... (resten uændret fra v2)

## Forventet effekt

| Metric | Før | Efter |
|---|---|---|
| Gratis modeller i pool | ~2 (groq free tier + lokal ollama) | 20+ (6 OpenCode + 12 Groq + 2 Gemini + lokal ollama) |
| Deepseek belastning | 100% af agent-kald | <30% (kun visible lane) |
| Model discovery | Manuel | Automatisk, daglig |
| Udgået model detektion | Ingen | <24t |
| Key management | Nøgler i runtime.json (nogle forkerte) | Auth profiles som source of truth |
| Centralen indsigt | Ingen | Live model registry + events |

## Blockers (skal løses før implementering)

1. **Groq key i runtime.json** — skal opdateres til auth profile-nøglen. Nuværende nøgle er forkert.
2. **Gemini model-navne** — `gemini-2.5-flash` skal udskiftes med `gemini-3.1-flash-lite` og `gemma-4-26b-a4b-it`
3. **FreeModel** — fjernes helt. ToS-violation og 403 på GPT-siden.

## Implementeringsfaser

| Fase | Beskrivelse | Estimeret tid | Afhængighed |
|---|---|---|---|
| 1 | Fix Groq key i runtime.json + opdater model-liste | 30min | Ingen |
| 2 | Fix Gemini model-navne i settings.py | 30min | Ingen |
| 3 | OpenCode Go Responses API integration i cheap lane | 2t | Fase 1+2 |
| 4 | Model Discovery Daemon (scan, diff, test, persist) | 4t | Fase 3 |
| 5 | Task-based scoring + dedup-logik | 3t | Fase 4 |
| 6 | Centralen cluster `models` (events + nudges) | 2t | Fase 4 |
| 7 | Agent pool integration (dispatch, rotation) | 2t | Fase 5+6 |
| 8 | Tests (unit + integration + edge cases) | 3t | Fase 3-7 |
| 9 | Shadow-kørsel (observe-only, 24t) | 1t + 24t | Fase 4-8 |
| 10 | Flip til aktiv | 1t | Fase 9 data |

**Total udvikling: ~17t + 24t shadow**
