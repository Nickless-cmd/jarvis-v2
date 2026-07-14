---
status: udkast v7 — live-testet, Bjørns retning 14. jul 2026
formål: Komplet provider/model management-system — auto-scanning, scoring,
 auto-opdatering, health-check på alle providers. Udvider agent-pool med
 bekræftede gratis modeller og giver Centralen livscyklus-styring.
kilder: Samtale Bjørn+Jarvis 14. jul, live API-tests (nøgle→model→svar),
 provider_router.json, settings.py, auth profiles, full provider audit
revision: v7 — Cerebras (User-Agent fix), TokenRouter (insufficient quota),
 Clinebot (16. provider, 5 modeller bekræftet), ~265 gratis
---

# Provider/Model Management System

## Problem

Jarvis' provider-landscape er statisk og manuelt vedligeholdt...

## Live-testet provider-status (14. juli 2026)

### ✅ Virker — gratis (bevist med rigtigt model-svar)

| Provider | Endpoint | Modeller der virker | Latency |
|---|---|---|---|
| **OpenCode Go** | `https://opencode.ai/zen/v1/responses` | `big-pickle`, `deepseek-v4-flash-free`, `hy3-free`, `mimo-v2.5-free`, `nemotron-3-ultra-free`, `north-mini-code-free` | 1-7s |
| **Groq** (fixet) | `https://api.groq.com/openai/v1` | 13 chat-modeller inkl. `llama-3.1-8b-instant`, `llama-3.3-70b-versatile`, `qwen/qwen3-32b`, `qwen/qwen3.6-27b`, `meta-llama/llama-4-scout`, `openai/gpt-oss-20b/120b`, `deepseek-r1` | 0.1-0.4s |
| **NVIDIA NIM** (fixet) | `https://integrate.api.nvidia.com/v1` | **120+ modeller** inkl. `meta/llama-3.1-8b-instruct` (0.4s), `meta/llama-3.3-70b-instruct` (7.2s), 27 Llama-varianter | 0.4-7s |
| **Cloudflare** (fixet) | `https://api.cloudflare.com/client/v4/accounts/{id}/ai/run/{model}` | **61 modeller** inkl. `@cf/meta/llama-3.3-70b-instruct-fp8-fast` (1.0s), `deepseek-r1-distill`, `llama-4-scout`, `qwen2.5-coder`, `kimi-k2.7-code`, `glm-5.2` | 0.5-2s |
| **Cerebras** (fixet) | `https://api.cerebras.ai/v1` | `llama-3.1-8b`, `gpt-oss-120b` (1.1s) | 1-2s |
| **Clinebot** 🆕 | `https://api.cline.bot/api/v1` | `minimax/minimax-m2.5` ($0.000002/kald), `deepseek/deepseek-chat` ($0.000022), `google/gemini-2.5-flash` (gratis), `openai/gpt-4o-mini` ($0.000003), `meta-llama/llama-3.3-70b-instruct` ($0.000028) | 1-4s |
| **GitHub Models** 🆕 | `https://models.inference.ai.azure.com` | `gpt-4.1` (1.3s), `gpt-4.1-mini` (1.8s), `gpt-4o` (1.6s), `o4-mini` (3.6s), `DeepSeek-R1` (1.6s) | 1-4s |
| **Mistral AI** 🆕 | `https://api.mistral.ai/v1` | `mistral-small-latest` (0.4s), `codestral-latest` (0.3s) | 0.3-0.4s |
| **AIHubMix** 🆕 | `https://aihubmix.com/v1` / `https://api.inferera.com/v1` | `gpt-4o-free` (1.1-1.6s). **352 modeller i listen,** men kun gpt-4o-free bekræftet. | 1-2s |
| **OVHcloud** 🆕 | `https://oai.endpoints.kepler.ai.cloud.ovh.net/v1` | `Qwen3.5-9B`, `gpt-oss-20b`, `gpt-oss-120b` (ingen nøgle). 2 RPM/IP — tung ratelimit. | 0.3-0.5s |
| **Kilo Code** 🆕 | `https://api.kilocode.ai/v1` | `nvidia/nemotron-3-super-120b-a12b:free` (0.7s) | 0.7s |
| **OpenRouter** | `https://openrouter.ai/api/v1` | `nvidia/nemotron-3-super-120b-a12b:free` (0.5s), `nvidia/nemotron-3-ultra-550b-a55b:free` (0.6-7.6s), `google/gemma-4-26b-a4b-it:free` (0.6-2.9s) | 0.5-7.6s |
| **Arko** | `https://arko.arcaelas.com/v3/messages` | Agent-baseret — 4.2s svar | 2-6s |
| **Gemini** | `https://generativelanguage.googleapis.com/v1beta` | `models/gemini-3.1-flash-lite` (0.6s), `models/gemma-4-26b-a4b-it` (1.3s) | 0.6-1.3s |
| **Lokal Ollama** | `localhost:11434` | 10 lokale modeller | varierer |

**Vigtigt — Cloudflare-workaround:** OpenCode Go, Cerebras (og sandsynligvis flere) kræver en `User-Agent` header (fx `opencode/1.17.18`) for at komme igennem Cloudflare-gate. Uden den: 403 error code 1010. Bør være standard header på alle cheap lane-kald.

**Clinebot særligt:** Returnerer svar indpakket i `{"success": true, "data": {...}}` — lidt anderledes end standard OpenAI format. Dokumentationen fremhæver `minimax/minimax-m2.5` som eksplicit test-model.

### ⚠️ Delvist/svagt virkende

| Provider | Status | Begrænsning |
|---|---|---|
| **OpenRouter** (resten) | ❌ 429 | De fleste `:free` modeller rate-limited |
| **Gemini** (resten) | ❌ 429 / 503 | Kun 2 modeller tilgængelige |
| **OllamaFreeAPI** | ❌ Kun `deepseek-r1` | Resten timer ud |
| **AIHubMix** (resten) | ❌ 400/403 | 351 af 352 modeller afvist |
| **OVHcloud** | ❌ 429 | 2 RPM — hurtigt opbrugt |

### ❌ Virker ikke

| Provider | Fejl | Årsag |
|---|---|---|
| **TokenRouter** 🆕 | 200 med `insufficient_user_quota` | Kontoen har $0 — fri-modellen kræver stadig positiv konto |
| **Sambanova** | 402 / timeout | 3 modeller kræver betaling, 3 timeouter. Død. |
| **FreeModel.dev** | 200 ToS / 403 | Claude = "kun via officiel Claude Code client". GPT = 403. |
| **ZenMux** | 403 | Nøglen har ikke adgang |
| **Zenifra** | Utestet | — |

## Samlet workforce

| Kilde | Modeller | Pris | Rate limits |
|---|---|---|---|
| **OpenCode Go** | 6 | Gratis | ~30 rpm |
| **Groq** | 13 | Gratis | ~30 rpm |
| **NVIDIA NIM** | 120+ | Gratis | ~100 rpm |
| **Cloudflare** | 61 | Gratis | ~50 rpm |
| **Cerebras** 🆕 | 2 | Gratis | ~20 rpm |
| **Clinebot** 🆕 | 5 | <$0.00003/kald | ~30 rpm |
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
| **I alt** | **~265 gratis** | **$0** | **>300 rpm kombineret** |

## Forventet effekt

| Metric | Før | Efter |
|---|---|---|
| Gratis modeller i pool | ~2 | **~265** |
| Deepseek belastning | 100% af agent-kald | <20% |
| Provider diversity | 2 | **16 uafhængige kilder** |
| Rate limit redundans | Ingen | >300 rpm kombineret |
| Centralen indsigt | Ingen | Live model registry + events |
