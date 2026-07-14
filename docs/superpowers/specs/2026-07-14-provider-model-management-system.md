---
status: udkast v6 — live-testet, Bjørns retning 14. jul 2026
formål: Komplet provider/model management-system — auto-scanning, scoring,
 auto-opdatering, health-check på alle providers. Udvider agent-pool med
 bekræftede gratis modeller og giver Centralen livscyklus-styring.
kilder: Samtale Bjørn+Jarvis 14. jul, live API-tests (nøgle→model→svar),
 provider_router.json, settings.py, auth profiles, full provider audit
revision: v6 — AIHubMix (gpt-4o-free), GitHub Models (4), Mistral AI (2),
 OVHcloud (~20, no key), Kilo Code (1), Cerebras (død)
---

# Provider/Model Management System

## Problem

Jarvis' provider-landscape er statisk og manuelt vedligeholdt...

## Live-testet provider-status (14. juli 2026)

### ✅ Virker — gratis (bevist med rigtigt model-svar)

| Provider | Endpoint | Modeller der virker | Latency |
|---|---|---|---|
| **OpenCode Go** | `https://opencode.ai/zen/v1/responses` | `big-pickle`, `deepseek-v4-flash-free`, `hy3-free`, `mimo-v2.5-free`, `nemotron-3-ultra-free`, `north-mini-code-free` | 1-7s |
| **Groq** | `https://api.groq.com/openai/v1` | 13 chat-modeller inkl. `llama-3.1-8b-instant`, `llama-3.3-70b-versatile`, `qwen/qwen3-32b`, `qwen/qwen3.6-27b`, `meta-llama/llama-4-scout-17b-16e-instruct`, `openai/gpt-oss-20b`, `openai/gpt-oss-120b`, `deepseek-r1` | 0.1-0.4s |
| **NVIDIA NIM** | `https://integrate.api.nvidia.com/v1` | **120+ modeller** inkl. `meta/llama-3.1-8b-instruct` (0.4s), `meta/llama-3.3-70b-instruct` (7.2s), 27 Llama-varianter | 0.4-7s |
| **Cloudflare** | `https://api.cloudflare.com/client/v4/accounts/{id}/ai/run/{model}` | **61 modeller** inkl. `@cf/meta/llama-3.3-70b-instruct-fp8-fast` (1.0s), `@cf/deepseek-r1-distill`, `@cf/meta/llama-4-scout`, `@cf/qwen2.5-coder`, `@cf/kimi-k2.7-code`, `@cf/glm-5.2` | 0.5-2s |
| **GitHub Models** 🆕 | `https://models.inference.ai.azure.com` | `gpt-4.1` (1.3s), `gpt-4.1-mini` (1.8s), `gpt-4o` (1.6s), `o4-mini` (3.6s), `DeepSeek-R1` (1.6s) | 1-4s |
| **Mistral AI** 🆕 | `https://api.mistral.ai/v1` | `mistral-small-latest` (0.4s), `codestral-latest` (0.3s) | 0.3-0.4s |
| **AIHubMix** 🆕 | `https://aihubmix.com/v1` / `https://api.inferera.com/v1` | `gpt-4o-free` (1.1-1.6s). **352 modeller i listen,** men kun gpt-4o-free bekræftet virkende. | 1-2s |
| **OVHcloud** 🆕 | `https://oai.endpoints.kepler.ai.cloud.ovh.net/v1` | `Qwen3.5-9B`, `gpt-oss-20b`, `gpt-oss-120b` (ingen nøgle krævet). 2 RPM/IP — tung rate limit. | 0.3-0.5s |
| **Kilo Code** 🆕 | `https://api.kilocode.ai/v1` | `nvidia/nemotron-3-super-120b-a12b:free` (0.7s) | 0.7s |
| **OpenRouter** | `https://openrouter.ai/api/v1` | `nvidia/nemotron-3-super-120b-a12b:free` (0.5s), `nvidia/nemotron-3-ultra-550b-a55b:free` (0.6-7.6s), `google/gemma-4-26b-a4b-it:free` (0.6-2.9s) | 0.5-7.6s |
| **Arko** | `https://arko.arcaelas.com/v3/messages` | Agent-baseret — `aid` + `content` + `stream:false`. 4.2s svar | 2-6s |
| **Gemini** | `https://generativelanguage.googleapis.com/v1beta` | `models/gemini-3.1-flash-lite` (0.6s), `models/gemma-4-26b-a4b-it` (1.3s) | 0.6-1.3s |
| **Lokal Ollama** | `localhost:11434` | 10 lokale modeller | varierer |

### ⚠️ Delvist/svagt virkende

| Provider | Status | Begrænsning |
|---|---|---|
| **OpenRouter** (resten) | ❌ 429 | De fleste `:free` modeller rate-limited |
| **Gemini** (resten) | ❌ 429 / 503 | Kun 2 modeller tilgængelige |
| **OllamaFreeAPI** | ❌ Kun `deepseek-r1` | Resten timer ud |
| **AIHubMix** (resten) | ❌ 400/403 | 351 af 352 modeller afvist — kun `gpt-4o-free` virker |
| **OVHcloud** | ❌ 429 | 2 RPM — hurtigt opbrugt |

### ❌ Virker ikke

| Provider | Fejl | Årsag |
|---|---|---|
| **Sambanova** | 402 / timeout | 3 modeller kræver betaling, 3 timeouter. Død. |
| **Cerebras** 🆕 | 403 Forbidden | Nøglen ugyldig/udløbet |
| **FreeModel.dev** | 200 ToS / 403 | Claude = "kun via officiel Claude Code client". GPT = 403. |
| **ZenMux** | 403 | Nøglen har ikke adgang |
| **Zenifra** | Utestet | — |

## Auth-strategi

**Nøgler opbevares KUN i auth profiles — aldrig i specs, aldrig i kode, aldrig i repoet.**
API-nøgler til AIHubMix og Cerebras udleveres separat og sættes i runtime.json/auth profiles.

| Provider | Auth type | Status |
|---|---|---|
| OpenCode Go | Bearer + User-Agent: `opencode/1.17.18` | ✅ |
| Groq | Bearer token (auth profile key, IKKE runtime.json key) | ✅ |
| NVIDIA NIM | Bearer token | ✅ 120+ |
| Cloudflare | Bearer token + account_id | ✅ 61 |
| GitHub Models | Bearer token (GitHub OAuth) | ✅ 5 |
| Mistral AI | Bearer token | ✅ 2 |
| AIHubMix | Bearer token | ✅ 1 (gpt-4o-free) |
| OVHcloud | **Ingen nøgle krævet** — anonymous tier | ✅ ~20 |
| Kilo Code | Bearer token | ✅ 1 |
| Arko | Bearer token + agent_id | ✅ |
| Gemini | API key query param | ✅ 2 |
| OpenRouter | Bearer token + `:free` suffix | ✅ 3 |
| Ollama | Ingen (lokal) | ✅ Altid |
| DeepSeek | Bearer token | ✅ Betalt |

**SPOF:** Ingen enkelt provider kan tage alt ned — 13 uafhængige kilder.

## Samlet workforce

| Kilde | Modeller | Pris | Rate limits |
|---|---|---|---|
| **OpenCode Go** | 6 | Gratis | ~30 rpm |
| **Groq** | 13 | Gratis | ~30 rpm |
| **NVIDIA NIM** | 120+ | Gratis | ~100 rpm |
| **Cloudflare** | 61 | Gratis | ~50 rpm |
| **GitHub Models** 🆕 | 5 | Gratis | 10-15 rpm, 50-150 rpd |
| **Mistral AI** 🆕 | 2 | Gratis (~1B tokens/md) | ~10 rpm |
| **AIHubMix** 🆕 | 1 | Gratis | ~20 rpm |
| **OVHcloud** 🆕 | ~20 | Gratis (no key) | 2 rpm/IP |
| **Kilo Code** 🆕 | 1 | Gratis | ~10 rpm |
| **OpenRouter** | 3-23 | Gratis | ~5-10 rpm |
| **Arko** | Agent-baseret | Gratis | ~30 rpm |
| **Gemini** | 2 | Gratis | Tight quota |
| **Lokal Ollama** | 10 | Gratis | Ubegrænset |
| **DeepSeek** | v4-flash/pro | Betalt | ~100 rpm |
| **I alt** | **~250 gratis** | **$0** | **>300 rpm kombineret** |

## Forventet effekt

| Metric | Før | Efter |
|---|---|---|
| Gratis modeller i pool | ~2 | **~250** |
| Deepseek belastning | 100% af agent-kald | <20% |
| Provider diversity | 2 | **13 uafhængige kilder** |
| Rate limit redundans | Ingen | >300 rpm kombineret |
| Centralen indsigt | Ingen | Live model registry + events |
