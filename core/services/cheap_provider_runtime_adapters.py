from __future__ import annotations

# ── cheap_provider_runtime._adapters ─────────────────────────────────────────
# Provider dispatch + adapter layer, extracted from cheap_provider_runtime.py
# (Boy-Scout split, behavior-preserving). Holds: CheapProviderError, provider
# defaults/catalog, per-provider chat/stream adapters, HTTP helpers, tool-shape
# normalizers, text/cost extractors, token estimation, and the OFA/Arko circuit
# breakers. Selection/routing/quota logic lives in _selection.py. The public
# module `cheap_provider_runtime` re-exports every symbol here for import
# stability (blast-radius 45) and for monkeypatch seams (tests patch
# cheap_provider_runtime._execute_provider_chat / _http_json / httpx etc.).
import json
from datetime import UTC, datetime
from decimal import Decimal
from urllib import error as urllib_error
from urllib import parse as urllib_parse
from urllib import request as urllib_request
import httpx

from core.auth.profiles import get_provider_credentials, provider_has_real_credentials
from core.runtime.provider_router import resolve_provider_router_target


def _facade():
    # Resolve the public facade module lazily. Several primitives in this module
    # (provider dispatch, HTTP, credentials, provider-defaults) are monkeypatched
    # by tests via cheap_provider_runtime.<name>. When one adapter function calls
    # another such primitive, it must go through the facade so the patch takes
    # effect — exactly as it did when everything lived in one module.
    import core.services.cheap_provider_runtime as _f
    return _f


_DEFAULT_TIMEOUT_SECONDS = 30
_OPENAI_COMPATIBLE_PROVIDERS = {
    "groq",
    "nvidia-nim",
    "openrouter",
    "mistral",
    "sambanova",
    "opencode",
    "deepseek",
}

# Codex uses a distinct responses-based protocol via chatgpt.com/backend-api.
# NOT OpenAI-compatible — separate dispatch path.
_OPENAI_CODEX_PROVIDER = "openai-codex"

CHEAP_PROVIDER_DEFAULTS: dict[str, dict[str, object]] = {
    # Phase A re-prioritization (2026-04-26): groq was hogging the chain
    # with priority=10 even though it's frequently rate-limited and in
    # cooldown. Spread load across nvidia-nim / openrouter / sambanova /
    # mistral first; let groq be a backup. Re-prioritize on observed
    # capacity, not historical assumption.
    "nvidia-nim": {
        "label": "NVIDIA NIM",
        "priority": 10,
        "base_url": "https://integrate.api.nvidia.com/v1",
        "auth_kind": "bearer",
        "protocol": "openai-chat",
        "models_endpoint": "/models",
        "rpm_limit": 40,
        "daily_limit": 500,
    },
    "openrouter": {
        "label": "OpenRouter",
        "priority": 20,
        "base_url": "https://openrouter.ai/api/v1",
        "auth_kind": "bearer",
        "protocol": "openai-chat",
        "models_endpoint": "/models",
        "rpm_limit": 20,
        "daily_limit": 100,
    },
    "sambanova": {
        "label": "SambaNova",
        "priority": 30,
        "base_url": "https://api.sambanova.ai/v1",
        "auth_kind": "bearer",
        "protocol": "openai-chat",
        "models_endpoint": "/models",
        "rpm_limit": 10,
        "daily_limit": 100,
    },
    "mistral": {
        "label": "Mistral",
        "priority": 40,
        "base_url": "https://api.mistral.ai/v1",
        "auth_kind": "bearer",
        "protocol": "openai-chat",
        "models_endpoint": "/models",
        "rpm_limit": 10,
        "daily_limit": 200,
    },
    "gemini": {
        "label": "Gemini",
        "priority": 50,
        # OpenAI-compat endpoint (2026-07-14 research): tool_calls virker out-of-the-box,
        # så gemini bliver en fuld tool-kapabel provider. gemini-2.5 er UDFASET (404 for
        # nye brugere) → -latest-aliaser tracker nyeste (Gemini 3.x) og udfases aldrig.
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "auth_kind": "bearer",
        "protocol": "openai-chat",
        "models_endpoint": "/models",
        "rpm_limit": 15,
        "daily_limit": 1000,
        "static_models": ["gemini-flash-latest", "gemini-flash-lite-latest", "gemini-pro-latest"],
    },
    "groq": {
        "label": "Groq",
        "priority": 60,
        "base_url": "https://api.groq.com/openai/v1",
        "auth_kind": "bearer",
        "protocol": "openai-chat",
        "models_endpoint": "/models",
        "rpm_limit": 30,
        "daily_limit": 10000,
    },
    "cloudflare": {
        "label": "Cloudflare Workers AI",
        "priority": 70,
        # OpenAI-compat endpoint (2026-07-14 research): tool_calls virker (CF fiksede lige
        # tool-call-IDs + finish_reason). account_id injiceres i base_url via provider_
        # router.json på containeren (per-konto, ikke i repoet). Fald-back-placeholder her.
        "base_url": "https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/v1",
        "auth_kind": "bearer",
        "protocol": "openai-chat",
        "models_endpoint": "/models",
        "rpm_limit": None,
        "daily_limit": None,
        "daily_neurons": 10000,
    },
    "ollamafreeapi": {
        "label": "OllamaFreeAPI",
        "priority": 95,
        "base_url": "",
        "auth_kind": "none",
        "protocol": "ollamafreeapi",
        "models_endpoint": "",
        "rpm_limit": None,
        "daily_limit": None,
    },
    "arko": {
        # Third-party agent platform (https://arko.arcaelas.com). Used as a
        # cheap-lane fallback alongside ollamafreeapi. Auth via API key
        # stored in runtime.json (arko_api_key + arko_cheap_agent_id) — not
        # via the auth_profile system. Priority 90 sits between OpenCode (80)
        # and OllamaFreeAPI (95): tried before OFA when Groq is rate-limited
        # but after the providers we trust most.
        "label": "Arko Studio",
        "priority": 90,
        "base_url": "https://arko.arcaelas.com",
        "auth_kind": "runtime-key",
        "protocol": "arko",
        "models_endpoint": "",
        "rpm_limit": None,
        "daily_limit": None,
        "static_models": ["jarvis-cheap-lane"],
    },
    "deepseek": {
        # Paid provider — Bjørn's $100 wallet, V4 Pro promo until 2026-05-31.
        # Auto prefix-caching on the server side (no params needed); cached
        # input tokens billed at lower rate. Keep system prompt prefix stable
        # for cache hits to actually land. Visible-lane only for now.
        "label": "DeepSeek",
        "priority": 5,
        "base_url": "https://api.deepseek.com/v1",
        "auth_kind": "bearer",
        "protocol": "openai-chat",
        "models_endpoint": "/models",
        "rpm_limit": None,
        "daily_limit": None,
        # deepseek-chat = compat-alias for v4-flash non-thinking mode.
        "static_models": ["deepseek-chat", "deepseek-v4-flash", "deepseek-v4-pro"],
        # routable=False (2026-07-14, Bjørn): deepseek er BETALT — hold den UDE af den
        # routbare cheap-pool så de gratis modeller tager al normal last ($0-mål).
        # Bevaret som nød-bund (cheap_lane_floor bruger base_url direkte) — kun brugt
        # hvis alle gratis providers er nede samtidig. Ude af regningen i normal drift.
        "routable": False,
    },
    "opencode": {
        "label": "OpenCode Zen",
        "priority": 80,
        "base_url": "https://opencode.ai/zen/v1",
        "auth_kind": "bearer",
        "protocol": "openai-chat",
        # No dynamic /models endpoint — models listed in static_models below.
        "models_endpoint": "",
        "rpm_limit": None,
        "daily_limit": None,
        # De faktiske gratis OpenCode Zen-modeller (verificeret via `opencode models`
        # på CheifOne, 14. jul). minimax-m2.5-free→mimo-v2.5-free og nemotron-3-super-
        # free→nemotron-3-ultra-free var UDFASET. Alle 6 verificeret $0.
        "static_models": [
            "big-pickle",
            "deepseek-v4-flash-free",
            "hy3-free",
            "mimo-v2.5-free",
            "nemotron-3-ultra-free",
            "north-mini-code-free",
        ],
    },
    "openai-codex": {
        "label": "OpenAI Codex (ChatGPT Plus OAuth)",
        "priority": 15,
        "base_url": "https://chatgpt.com/backend-api",
        "auth_kind": "oauth",
        "protocol": "openai-codex-responses",
        "models_endpoint": "",
        "rpm_limit": None,
        "daily_limit": None,
        "static_models": [
            "gpt-5.3-codex",
            "gpt-5.4",
        ],
        # routable=False (2026-07-14): Bjørn opsagde ChatGPT Plus → OAuth død, svarer
        # ikke (falder over til nvidia-nim). Ude af routbar pool så den ikke spilder
        # failover-forsøg. Gen-aktivér (fjern denne linje) hvis abonnementet kommer igen.
        "routable": False,
    },
    # --- Nye providers, live-verificeret 14. jul (Bjørns nøgler, ~/new_providers_.txt).
    # Alle OpenAI-compatible bearer. Modeller er de faktisk-bekræftede gratis.
    "cerebras": {
        "label": "Cerebras",
        "priority": 22,
        "base_url": "https://api.cerebras.ai/v1",
        "auth_kind": "bearer",
        "protocol": "openai-chat",
        "models_endpoint": "/models",
        "rpm_limit": 30,
        "daily_limit": 1000,
        # gemma-4-31b (non-reasoning) først = default-pick uden reasoning-overhead;
        # gpt-oss/glm er reasoning (brænder korte token-budgetter på tanke → tom content).
        "static_models": ["gemma-4-31b", "zai-glm-4.7", "gpt-oss-120b"],
    },
    "cline": {
        "label": "Cline",
        # Demoteret (2026-07-14): api.cline.bot returnerer ofte tom message (agentic
        # coding-værktøj, ikke ren OpenAI-chat). Bevaret som sidste-udvej fallback —
        # tomt svar → CheapProviderError → pool fail-over. NB: base /api/v1, ikke /v1.
        "priority": 92,
        "base_url": "https://api.cline.bot/api/v1",
        "auth_kind": "bearer",
        "protocol": "openai-chat",
        "models_endpoint": "",
        "rpm_limit": 20,
        "daily_limit": 200,
        "static_models": ["deepseek/deepseek-chat", "meta-llama/llama-3.3-70b-instruct"],
    },
    "aihubmix": {
        "label": "AIHubMix",
        "priority": 42,
        "base_url": "https://aihubmix.com/v1",
        "auth_kind": "bearer",
        "protocol": "openai-chat",
        "models_endpoint": "/models",
        "rpm_limit": 20,
        "daily_limit": 200,
        # KUN *-free — "auto" router til BETALT (403 balance). Se spec §1.
        "static_models": ["gpt-5.5-free", "coding-glm-5.2-free", "coding-minimax-m3-free"],
    },
    "requesty": {
        "label": "Requesty",
        "priority": 52,
        "base_url": "https://router.requesty.ai/v1",
        "auth_kind": "bearer",
        "protocol": "openai-chat",
        "models_endpoint": "/models",
        "rpm_limit": 20,
        "daily_limit": 200,
        "static_models": ["novita/tencent/hy3"],
    },
    # GitHub Models (14. jul research): 37 GRATIS modeller inkl. rigtige GPT-5/o3/o4-mini/
    # DeepSeek-R1. OpenAI-compat, tool_calls virker. Auth = github-copilot OAuth-token
    # (gho_, synket til container-auth). Rate: ~10 RPM / 50 RPD → premium-lejlighedsvis,
    # lav daily så proaktiv rotation flytter væk før udmattelse. Prioritet moderat-høj
    # (god kvalitet) men daily_limit=50 forhindrer den bliver arbejdshest.
    "github-models": {
        "label": "GitHub Models",
        "priority": 25,
        "base_url": "https://models.github.ai/inference",
        "auth_kind": "bearer",
        "protocol": "openai-chat",
        "models_endpoint": "",
        "rpm_limit": 10,
        "daily_limit": 50,
        "static_models": ["openai/gpt-5-mini", "openai/gpt-4o", "openai/o4-mini",
                          "deepseek/deepseek-r1", "meta/llama-3.3-70b-instruct"],
    },
    # OVHcloud AI Endpoints (14. jul research): EU/GDPR, ANONYM (ingen key, auth_kind=none).
    # 2 RPM anon → backup-lane. Model-navne m. UNDERSCORES. openai-compat.
    "ovhcloud": {
        "label": "OVHcloud AI Endpoints",
        "priority": 88,
        "base_url": "https://oai.endpoints.kepler.ai.cloud.ovh.net/v1",
        "auth_kind": "none",
        "protocol": "openai-chat",
        "models_endpoint": "/models",
        "rpm_limit": 2,
        "daily_limit": 100,
        "static_models": ["Meta-Llama-3_3-70B-Instruct", "Qwen3.5-9B"],
    },
    # Pollinations (15. jul, live-verificeret): ANONYM (ingen key, auth_kind=none),
    # openai-compat, TOOL-CAPABLE (tool_calls=1 testet med rigtigt tool-kald). Backed
    # af GPT-OSS. Anonymt eksponeres kun "openai-fast". base_url ender på /openai
    # (adapter poster /chat/completions). daily_limit=None → fuld headroom (linje 265),
    # ægte keyless $0-gulv. rpm konservativt sat.
    "pollinations": {
        "label": "Pollinations",
        "priority": 60,
        "base_url": "https://text.pollinations.ai/openai",
        "auth_kind": "none",
        "protocol": "openai-chat",
        "models_endpoint": "",
        "rpm_limit": 15,
        "daily_limit": None,
        "cost_class": "free",
        "static_models": ["openai-fast"],
    },
    # Kilo Gateway (15. jul, FreeLLMAPI-extraction + live-verificeret): OpenAI-compat
    # aggregator, ANONYM keyless på :free-routes (200 req/t/IP). 343 modeller; :free
    # tool-capable BEKRÆFTET (nemotron-3-super-120b/ultra-550b/cohere-north/openrouter
    # → tool_calls=1). base ender på /gateway/v1 (chat), model-liste på /gateway/models.
    # NB: :free-routes kan over tid skifte til paid (Kilos forbehold) + free-prompts
    # logges til træning → backup-tier, ikke primær. static_models = konservativt
    # verificeret-free-tool-capable-sæt.
    "kilo": {
        "label": "Kilo Gateway",
        "priority": 55,
        "base_url": "https://api.kilo.ai/api/gateway/v1",
        "auth_kind": "none",
        "protocol": "openai-chat",
        "models_endpoint": "",
        "rpm_limit": 30,
        "daily_limit": 2000,
        "cost_class": "free",
        "static_models": ["nvidia/nemotron-3-super-120b-a12b:free",
                          "nvidia/nemotron-3-ultra-550b-a55b:free",
                          "cohere/north-mini-code:free", "openrouter/free",
                          "tencent/hy3:free"],
    },
    # Z.ai / Zhipu GLM (15. jul, Bjørn-nøgle, live-verificeret): OpenAI-compat på
    # /paas/v4. glm-4.5-flash = ÆGTE GRATIS (ikke i /models-katalog men svarer $0;
    # de betalte glm-4.5/4.6/5.x gav 429 "insufficient balance" → fri/betalt-skel
    # bekræftet). Stærk GLM-4.5-model. Tool-capable men narrerer i auto-mode; fyrer
    # korrekt tool_calls med tool_choice forced (adapter sender auto → agent-lane får
    # tekst nogle runder, degraderer pænt). Fremragende til cheap lane/indre liv.
    # Nøgle (id.secret) gemt i CT105 auth-store — ALDRIG i repo.
    "zai": {
        "label": "Z.ai (Zhipu GLM)",
        # Deprioriteret 2026-07-18: ~92% "read operation timed out" over 24t (604 kald,
        # 555 fejl). Timeouts koster fuld failover-ventetid, så den skal bagerst i feltet
        # (registrets hidtil laveste var 95) — stadig tilgængelig som absolut sidste udvej.
        "priority": 96,
        "base_url": "https://api.z.ai/api/paas/v4",
        "auth_kind": "bearer",
        "protocol": "openai-chat",
        "models_endpoint": "",
        "rpm_limit": 30,
        "daily_limit": 1000,
        "cost_class": "free",
        "static_models": ["glm-4.5-flash"],
    },
    # HuggingFace Router (15. jul, Bjørns eksisterende hf_-token fundet lokalt):
    # OpenAI-compat `router.huggingface.co/v1`. STÆRK tool-capable (Llama-3.3-70B/
    # Qwen2.5-72B/DeepSeek-V3 → tool_calls=1 verificeret). CREDIT-METERET: gratis
    # månedlige credits, IKKE ubegrænset. Men konto = free + `canPay:False` (ingen
    # betalingsmetode) → NUL spend-risiko: løber credits tør → 402 (floor håndterer).
    # Derfor konservativt daily_limit så månedens credit ikke brændes på én dag.
    # fineGrained-token m. Inference-Providers-scope. Nøgle gemt CT105 — ALDRIG repo.
    "huggingface": {
        "label": "HuggingFace Router",
        "priority": 42,
        "base_url": "https://router.huggingface.co/v1",
        "auth_kind": "bearer",
        "protocol": "openai-chat",
        "models_endpoint": "/models",
        "rpm_limit": 10,
        "daily_limit": 40,
        "cost_class": "free",
        # 16. jul: udvidet fra 3→7 (Bjørn). Router har 123 modeller; disse er live-
        # verificeret PONG + non-reasoning (reasoning-modeller som Qwen3-32B brænder
        # token på tanke → tom content ved tight cap). DeepSeek-V4-Flash udeladt =
        # credits opbrugt på den route (HF er credit-meteret → daily=40 beskytter).
        "static_models": ["meta-llama/Llama-3.3-70B-Instruct",
                          "Qwen/Qwen2.5-72B-Instruct", "deepseek-ai/DeepSeek-V3",
                          "openai/gpt-oss-20b", "Qwen/Qwen2.5-Coder-32B-Instruct",
                          "microsoft/phi-4", "google/gemma-3-27b-it"],
    },
    # Reka (15. jul, Bjørn-nøgle): OpenAI-compat `api.reka.ai/v1`, bearer. reka-edge-2603
    # = ren tool-capable (tool_calls=1 verificeret; reka-flash-3 narrerer <reasoning>).
    # NB: IKKE $0 — $0.10/1M usage-based, kører på gratis trial-credits. Ingen billing-
    # API at verificere kort → Bjørn BEKRÆFTEDE ingen betalingsmetode → sikkert (ved tom
    # credit → 402, floor håndterer). Konservativt daily_limit så trial-credit ikke
    # brændes. Nøgle gemt CT105 — ALDRIG repo.
    "reka": {
        "label": "Reka",
        "priority": 50,
        "base_url": "https://api.reka.ai/v1",
        "auth_kind": "bearer",
        "protocol": "openai-chat",
        "models_endpoint": "/models",
        "rpm_limit": 10,
        "daily_limit": 40,
        "cost_class": "free",
        "static_models": ["reka-edge-2603"],
    },
    # BazaarLink (15. jul, Bjørn-nøgle): OpenAI-compat `bazaarlink.ai/api/v1`, bearer.
    # `auto:free` = ÆGTE perpetual gratis — 6/6 vedvarende kald cost=0 (BESTOD den
    # SiliconFlow-hærdede test: gratis BLIVER gratis, ingen trial-gate). Ærlig cost-
    # rapportering (betalt deepseek-v4-flash rapporterede cost=1.9e-05). CHAT-stærk,
    # TOOL-SVAG: med tools returnerer auto:free tom tekst → cheap lane/indre liv, ikke
    # agent-arbejdshest (agent-lane falder over til tool-capable). Nøgle CT105 — ALDRIG repo.
    "bazaarlink": {
        "label": "BazaarLink",
        "priority": 52,
        "base_url": "https://bazaarlink.ai/api/v1",
        "auth_kind": "bearer",
        "protocol": "openai-chat",
        "models_endpoint": "/models",
        "rpm_limit": 20,
        "daily_limit": 1000,
        "cost_class": "free",
        "static_models": ["auto:free"],
    },
    # SiliconFlow AFVIST 15. jul: så gratis ud i et lille trial-vindue (~8 kald), men
    # hård-gater derefter til 403 code=30001 "account balance insufficient" på ALLE
    # kald (selv max_tokens=100, efter pause). Kræver rigtig betaling for vedvarende
    # brug → ikke en $0-provider (som LLM7). Burst-test narrede først: trial-kvoten
    # holdt saldo=1 mens den varede. Ikke wired.
    # Copilot Pro (15. jul) — Bjørns betalte abonnement, delt i to efter multiplier:
    # copilot-free = 0x (inkluderet, nul premium-requests) → GRATIS, i cheap lane + pool.
    "copilot-free": {
        "label": "GitHub Copilot (free-tier)",
        "priority": 18,
        "base_url": "https://api.githubcopilot.com",
        "auth_kind": "bearer",
        "protocol": "openai-chat",
        "models_endpoint": "",
        "rpm_limit": 20,
        "daily_limit": 500,
        "cost_class": "free",
        "extra_headers": {"Editor-Version": "vscode/1.90.0",
                          "Copilot-Integration-Id": "vscode-chat"},
        "static_models": ["gpt-4o", "gpt-4.1", "gpt-5-mini"],
    },
    # copilot-premium = 1x+ (koster premium-requests) → BETALT, KUN agent pool, gated af
    # task.allow_paid ("rigtige opgaver"). Claude Opus/Sonnet, GPT-5.6, Gemini-3.
    "copilot-premium": {
        "label": "GitHub Copilot (premium)",
        "priority": 5,  # høj kvalitet — vælges FØRST når betalt er tilladt
        "base_url": "https://api.githubcopilot.com",
        "auth_kind": "bearer",
        "protocol": "openai-chat",
        "models_endpoint": "",
        "rpm_limit": 20,
        "daily_limit": 300,
        "cost_class": "paid",
        "extra_headers": {"Editor-Version": "vscode/1.90.0",
                          "Copilot-Integration-Id": "vscode-chat"},
        # Verificeret API-tilgængelige premium-modeller (opus-4.8/gpt-5.6 IKKE tilgængelig
        # via denne integration). claude-sonnet-5 = flagskib.
        "static_models": ["claude-sonnet-5", "claude-sonnet-4.6", "gpt-5.4",
                          "gemini-3.1-pro-preview"],
    },
    # AionLabs (16. jul, Bjørn-nøgle, free-tier konto): OpenAI-compat `api.aionlabs.ai/v1`,
    # bearer. Live-verificeret — /models svarer, chat-kald returnerede content="PONG" på
    # aion-2.0/2.5/3.0-mini. Modellerne er DeepSeek-V3.2/GLM-varianter TUNET til immersivt
    # roleplay/storytelling (reasoning:true, is_moderated:false, "mature/darker themes") —
    # IKKE rene assistent-modeller. De følger simple instrukser fint, men reasoning brænder
    # token på tanke → tight-cap-jobs kan give tom content (som cerebras/reka). Derfor
    # moderat prioritet: supplerende pool-medlem, ikke arbejdshest. Free-tier = kører på
    # gratis credits (pricing IKKE $0), så konservativ daily så credits ikke brændes.
    # Nøgle gemt CT105 auth-profil (default/providers/aionlabs) — ALDRIG i repo.
    "aionlabs": {
        "label": "AionLabs",
        "priority": 58,
        "base_url": "https://api.aionlabs.ai/v1",
        "auth_kind": "bearer",
        "protocol": "openai-chat",
        "models_endpoint": "/models",
        "rpm_limit": 15,
        "daily_limit": 100,
        "cost_class": "free",
        "static_models": ["aion-labs/aion-2.0", "aion-labs/aion-3.0-mini",
                          "aion-labs/aion-2.5"],
    },
    # FreeTheAi (16. jul, Bjørn-nøgle `sta_…`): OpenAI-compat gateway `api.freetheai.xyz/v1`,
    # ~54 modeller. Live-verificeret PONG på bbl/gpt-5.5-mini, bbl/grok-4.1-fast-non-reasoning,
    # olm/deepseek-v4-pro — 3 frontier-modeller vi IKKE har rent ellers. Resten er redundant
    # (kai/=kilo, opc/=opencode, glm/=zai, bbl/gemini=vores) eller ikke-chat (billede/lyd/TTS).
    #
    # TO hårde constraints → KUN agent-pool-reserve, ALDRIG den parallelle cheap-firehose:
    #   (1) DAGLIG Discord-`/checkin` låser HELE nøglen (ingen HTTP-endpoint → kan ikke auto-
    #       matiseres rent; Bjørn kører checkin manuelt). Down hver UTC-midnat til checkin.
    #   (2) concurrency=1 + 10 rpm → serialiseres; ubrugelig som parallel arbejdshest.
    # cost_class="paid" her = ROUTING-GATE, IKKE en billing-påstand (den er GRATIS, reel
    # cost=0). Det holder den ude af cheap lane (paid ekskluderes, L~413) + ude af zero-row
    # self-heal (gates free-only), men i agent-poolen via central_route(allow_paid=True).
    # priority 90 = bunden af agent-poolen: reserve, valgt kun når hoved-pool er tynd (Bjørn:
    # "aktivér hvis han løber tør for agenter"). Nøgle CT105 auth-profil — ALDRIG i repo.
    "freetheai": {
        "label": "FreeTheAi (Discord daily-checkin, agent-reserve)",
        "priority": 90,
        "base_url": "https://api.freetheai.xyz/v1",
        "auth_kind": "bearer",
        "protocol": "openai-chat",
        "models_endpoint": "/models",
        "rpm_limit": 10,
        "daily_limit": 300,
        "cost_class": "paid",  # routing-gate, ikke billing — se blok ovenfor
        "static_models": ["bbl/gpt-5.5-mini", "bbl/grok-4.1-fast-non-reasoning",
                          "olm/deepseek-v4-pro"],
    },
    # Cohere (16. jul, Bjørn trial-nøgle, research-sweep-vinder): OpenAI-compat endpoint
    # `api.cohere.ai/compatibility/v1`, bearer. VEDVARENDE gratis (ikke engangs-trial):
    # 1000 kald/MÅNED, 20 rpm, intet kort, US-hostet (intet privatlivs-problem). Trial-
    # nøgle = evaluering/non-commercial (fint til Jarvis' interne brug). Live-verificeret
    # PONG på command-r7b/command-a/command-r-plus. daily_limit=30 BESKYTTER månedskvoten
    # (1000/md ≈ 33/dag) så en travl dag ikke brænder hele måneden. Lav prioritet = sjælden
    # filler, ikke arbejdshest. Nøgle CT105 auth-profil — ALDRIG i repo.
    "cohere": {
        "label": "Cohere",
        "priority": 60,
        "base_url": "https://api.cohere.ai/compatibility/v1",
        "auth_kind": "bearer",
        "protocol": "openai-chat",
        "models_endpoint": "/models",
        "rpm_limit": 20,
        "daily_limit": 30,
        "cost_class": "free",
        "static_models": ["command-r7b-12-2024", "command-a-03-2025",
                          "command-r-plus-08-2024"],
    },
    # Alibaba Cloud Model Studio (16. jul, Bjørns workspace, Singapore/ap-southeast-1):
    # OpenAI-compat, bearer. Live-verificeret PONG: qwen-turbo/qwen-plus/qwen3.7-plus (97
    # chat-modeller incl. glm-5.2/kimi-k2.7/deepseek-v4). glm-5.2=reasoning (tom v. tight
    # cap) → udeladt. Free-tier = ENGANGS gratis token-kvote pr. model (~1M tok/model,
    # 90-dages udløb) → ENDELIG burst-kapacitet, ikke uendelig. daily_limit moderat så
    # kvoten ikke brændes på få dage. Kina-ejet (Singapore-hostet) — samme posture som zai
    # (også Kina) der allerede kører i cheap lane; ikke-følsom trafik.
    # COST: INGEN betalingsmetode på kontoen (bekræftet Bjørn 16.jul) → nul cost-risiko;
    # når gratis-kvoten er brugt/udløbet fejler kaldet pænt (credits-exhausted → cooldown →
    # roterer ud), ingen regning. Workspace-host = account-
    # scopet endpoint (ikke en secret; ubrugelig uden nøglen). Nøgle CT105 — ALDRIG repo.
    "alibaba": {
        "label": "Alibaba Model Studio (SG)",
        "priority": 32,
        "base_url": "https://ws-xmmuqa6plmcaheul.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1",
        "auth_kind": "bearer",
        "protocol": "openai-chat",
        "models_endpoint": "/models",
        "rpm_limit": 30,
        "daily_limit": 500,
        "cost_class": "free",
        "static_models": ["qwen-turbo", "qwen-plus", "qwen3.7-plus"],
    },
}

# Gen-udled openai-compat-sættet FRA protocol (15. jul) — den hardkodede liste
# (linje 35) gik glip af alle nye providers (cerebras/aihubmix/requesty/cline/
# github-models/ovhcloud/copilot-*) + gemini/cloudflare efter deres openai-compat-
# konvertering. Det gav "unsupported-provider" i balanceren OG deepseek-fallback i
# agent-step. Nu auto-inkluderes enhver protocol="openai-chat"-provider. deepseek
# beholdes (floor bruger den direkte selvom den er routable=False).
_OPENAI_COMPATIBLE_PROVIDERS = frozenset(
    p for p, _cfg in CHEAP_PROVIDER_DEFAULTS.items()
    if str(_cfg.get("protocol")) == "openai-chat"
) | {"deepseek"}


class CheapProviderError(RuntimeError):
    def __init__(
        self,
        *,
        provider: str,
        code: str,
        message: str,
        retry_after_seconds: int = 0,
        status_code: int | None = None,
    ) -> None:
        super().__init__(message)
        self.provider = provider
        self.code = code
        self.message = message
        self.retry_after_seconds = int(max(0, retry_after_seconds))
        self.status_code = status_code


def supported_cheap_providers() -> list[dict[str, object]]:
    return [
        {"provider": provider, **metadata}
        for provider, metadata in sorted(
            CHEAP_PROVIDER_DEFAULTS.items(),
            key=lambda item: int(item[1].get("priority") or 9999),
        )
    ]


def provider_runtime_defaults(provider: str) -> dict[str, object]:
    return dict(CHEAP_PROVIDER_DEFAULTS.get(str(provider or "").strip(), {}))


def provider_cost_class(provider: str) -> str:
    """'free' (default) eller 'paid'. Betalte providers (copilot-premium) må KUN
    vælges når en task eksplicit tillader det (task.allow_paid) — 'rigtige opgaver'."""
    return str((CHEAP_PROVIDER_DEFAULTS.get(str(provider or "").strip()) or {})
               .get("cost_class") or "free")


def is_routable_provider(provider: str) -> bool:
    """False = provideren må IKKE vælges i normal routing (kun evt. som nød-bund).
    Bruges til at holde betalte providers (deepseek) ude af den gratis cheap-pool.
    Default True — kun eksplicit routable=False udelukker."""
    cfg = CHEAP_PROVIDER_DEFAULTS.get(str(provider or "").strip())
    return bool((cfg or {}).get("routable", True))


def provider_auth_ready(*, provider: str, auth_profile: str) -> bool:
    normalized_provider = str(provider or "").strip()
    # Tom profil → "default" (16.jul): candidate-byggeren giver auth_profile='' for providere
    # der ikke er i provider-router-registret (kun i CHEAP_PROVIDER_DEFAULTS static_models,
    # jf. Phase D). _require_credentials normaliserer ALLEREDE ''→'default' ved dispatch, så
    # readiness SKAL gøre det samme — ellers markeres en fungerende provider (nøgle under
    # 'default') som ikke-klar og vælges aldrig. Ingen default-nøgle → get_provider_credentials
    # returnerer None → stadig False. Rent additivt.
    profile = (str(auth_profile or "").strip()) or "default"
    if normalized_provider not in CHEAP_PROVIDER_DEFAULTS:
        return False
    if normalized_provider == "ollamafreeapi":
        return True
    # auth_kind=none (fx OVHcloud anon): ingen nøgle nødvendig — altid "ready".
    if str((CHEAP_PROVIDER_DEFAULTS.get(normalized_provider) or {}).get("auth_kind")) == "none":
        return True
    if normalized_provider == "arko":
        # Arko's credentials live in runtime.json, not in auth profiles.
        from core.runtime.arko_provider import is_configured as arko_is_configured
        return arko_is_configured()
    if normalized_provider == _OPENAI_CODEX_PROVIDER:
        # Codex uses OAuth tokens imported from ~/.codex/auth.json.
        # Check that the auth profile exists and has usable credentials.
        from core.auth.openai_oauth import get_openai_bearer_token
        try:
            token = get_openai_bearer_token(profile=profile, auto_reimport=False)
            return bool(token)
        except Exception:
            return False
    credentials = get_provider_credentials(profile=profile, provider=normalized_provider)
    if not credentials:
        return False
    if normalized_provider == "cloudflare":
        return bool(
            str(credentials.get("api_key") or "").strip()
            and str(credentials.get("account_id") or "").strip()
        )
    return provider_has_real_credentials(profile=profile, provider=normalized_provider)


def list_provider_models(
    *,
    provider: str,
    auth_profile: str = "",
    base_url: str = "",
) -> dict[str, object]:
    normalized_provider = str(provider or "").strip()
    defaults = _facade().provider_runtime_defaults(normalized_provider)
    profile = str(auth_profile or "").strip()
    root = str(base_url or defaults.get("base_url") or "").strip()
    if not normalized_provider:
        return _listing_surface(
            provider="",
            auth_profile=profile,
            status="missing-provider",
            source="missing-provider",
            models=[],
        )
    if normalized_provider not in CHEAP_PROVIDER_DEFAULTS:
        return _listing_surface(
            provider=normalized_provider,
            auth_profile=profile,
            status="unsupported-provider",
            source="unsupported-provider",
            models=[],
        )
    if not provider_auth_ready(provider=normalized_provider, auth_profile=profile):
        return _listing_surface(
            provider=normalized_provider,
            auth_profile=profile,
            status="auth-not-ready",
            source="provider-live",
            models=[],
            base_url=root,
        )
    try:
        if normalized_provider in _OPENAI_COMPATIBLE_PROVIDERS:
            models = _list_openai_compatible_models(
                provider=normalized_provider,
                auth_profile=profile,
                base_url=root,
            )
        elif normalized_provider == "ollamafreeapi":
            models = _list_ollamafreeapi_models()
        elif normalized_provider == "gemini":
            models = _list_gemini_models(auth_profile=profile, base_url=root)
        elif normalized_provider == "cloudflare":
            models = _list_cloudflare_models(auth_profile=profile, base_url=root)
        elif normalized_provider == _OPENAI_CODEX_PROVIDER:
            from core.services.cheap_provider_runtime_streaming import (
                _list_openai_codex_models,
            )
            models = _list_openai_codex_models()
        else:
            models = []
    except CheapProviderError as exc:
        return _listing_surface(
            provider=normalized_provider,
            auth_profile=profile,
            status=exc.code,
            source="provider-live",
            models=[],
            base_url=root,
        )
    return _listing_surface(
        provider=normalized_provider,
        auth_profile=profile,
        status="ready" if models else "unavailable",
        source="provider-live",
        models=models,
        base_url=root,
    )


def _flatten_messages_to_text(messages: list[dict] | None) -> str:
    """Collapse a chat-message list to a single prompt string.

    Used when a tool-carrying caller (which builds a ``messages`` transcript)
    lands on a text-only provider adapter. Self-safe: returns "" on junk.
    """
    if not messages:
        return ""
    parts: list[str] = []
    for m in messages:
        if not isinstance(m, dict):
            continue
        role = str(m.get("role") or "")
        content = m.get("content")
        if content is None:
            continue
        text = str(content).strip()
        if not text:
            continue
        parts.append(f"[{role}] {text}" if role else text)
    return "\n\n".join(parts)


def _resolve_egress_proxy(*, provider: str, auth_profile: str) -> str | None:
    """Task 8b: resolve the egress proxy URL for a (provider, auth_profile) slot.

    Gated behind the ``cheap_pool_multiprofile_enabled`` flag: flag OFF -> always
    None (no proxy, unchanged home-IP behavior). Flag ON -> map the slot's egress
    to its proxy; the leak guard inside ``_resolve_proxy`` raises if a non-home
    egress has no configured endpoint (never silently uses the home IP).

    Symbols are resolved through the selection module at call time so tests that
    monkeypatch ``_flag_multiprofile`` / ``_resolve_proxy`` there take effect.
    """
    from core.services import cheap_provider_runtime_selection as _sel
    if not _sel._flag_multiprofile():
        return None
    from core.services.egress_routing import resolve_egress
    egress = resolve_egress(provider, auth_profile)
    return _sel._resolve_proxy(egress)


def _execute_provider_chat(
    *,
    provider: str,
    model: str,
    auth_profile: str,
    base_url: str,
    message: str | None = None,
    messages: list[dict] | None = None,
    tools: list[dict] | None = None,
) -> dict[str, object]:
    """Dispatch a single chat turn to the right provider adapter.

    Axis 3 (agent-freedom): ``tools`` + ``messages`` are optional. Only the
    OpenAI-compatible adapters honour tool calling; every other provider
    silently ignores ``tools`` and falls back to plain text (so passing a
    tools array is always safe — a non-tool provider degrades to text-only,
    exactly as before). ``messages`` lets a caller carry a running
    tool-call transcript; when omitted the legacy single-``message`` path
    is preserved untouched for backward compatibility.
    """
    # Dispatch targets are resolved through the public facade so tests that
    # monkeypatch cheap_provider_runtime._execute_*_chat still take effect
    # (they patch the facade attribute; the original single-module code saw
    # the patch naturally). The Codex adapter additionally lives in the
    # streaming submodule and is only reachable via the facade re-export.
    _f = _facade()
    if provider in _OPENAI_COMPATIBLE_PROVIDERS:
        return _f._execute_openai_compatible_chat(
            provider=provider,
            model=model,
            auth_profile=auth_profile,
            base_url=base_url,
            message=message,
            messages=messages,
            tools=tools,
        )
    # Text-only adapters below don't accept messages/tools. Coerce a running
    # transcript down to a single string so a tool-carrying caller still
    # degrades gracefully (text-only) instead of crashing on message=None.
    if message is None:
        message = _flatten_messages_to_text(messages)
    if provider == "gemini":
        return _f._execute_gemini_chat(
            model=model,
            auth_profile=auth_profile,
            base_url=base_url,
            message=message,
        )
    if provider == "cloudflare":
        return _f._execute_cloudflare_chat(
            model=model,
            auth_profile=auth_profile,
            base_url=base_url,
            message=message,
        )
    if provider == "ollamafreeapi":
        return _f._execute_ollamafreeapi_chat(
            model=model,
            message=message,
        )
    if provider == "ollama":
        return _f._execute_local_ollama_chat(
            model=model,
            base_url=base_url,
            message=message,
        )
    if provider == "arko":
        return _f._execute_arko_chat(message=message)
    if provider == _OPENAI_CODEX_PROVIDER:
        return _f._execute_openai_codex_chat(
            model=model,
            auth_profile=auth_profile,
            base_url=base_url,
            message=message,
        )
    raise CheapProviderError(
        provider=provider,
        code="unsupported-provider",
        message=f"cheap provider not supported: {provider}",
    )


def _execute_openai_compatible_chat(
    *,
    provider: str,
    model: str,
    auth_profile: str,
    base_url: str,
    message: str | None = None,
    messages: list[dict] | None = None,
    tools: list[dict] | None = None,
    temperature: float | None = None,
    top_p: float | None = None,
    extra_body: dict | None = None,
) -> dict[str, object]:
    # Resolve monkeypatchable primitives through the facade (see _facade()).
    _f = _facade()
    credentials = _f._require_credentials(profile=auth_profile, provider=provider)
    root = str(base_url or _f.provider_runtime_defaults(provider).get("base_url") or "").rstrip("/")
    _api_key = str(credentials.get('api_key') or '').strip()
    headers: dict[str, str] = {}
    if _api_key:  # auth_kind=none (OVHcloud anon) → ingen Authorization-header
        headers["Authorization"] = f"Bearer {_api_key}"
    # Provider-specifikke ekstra-headers (fx Copilot kræver Editor-Version +
    # Copilot-Integration-Id for at api.githubcopilot.com accepterer kaldet).
    _extra_h = (CHEAP_PROVIDER_DEFAULTS.get(provider) or {}).get("extra_headers")
    if isinstance(_extra_h, dict):
        headers.update({str(k): str(v) for k, v in _extra_h.items()})
    if messages is None:
        if message is None:
            raise ValueError("Either 'messages' or 'message' must be provided")
        messages = [{"role": "user", "content": message}]
    payload: dict[str, object] = {
        "model": model,
        "messages": messages,
        "stream": False,
        # Without an explicit max_tokens, OpenCode/MiniMax defaults to ~512
        # which truncates Jarvis mid-sentence (observed cutoff at "**Capability"
        # after exactly 549 output tokens). 4096 is generous enough for any
        # single visible reply without burning the free quota.
        "max_tokens": 4096,
    }
    # Send-grænse-normalisering: deepseek-chat/reasoner-aliaserne udfases 2026-07-24.
    # Enhver upstream-sti der stadig vælger dem (fx classification-default =
    # static_models[0]) omskrives transparent til v4-flash + tilsvarende thinking-param,
    # så adfærden bevares (chat=non-thinking, reasoner=thinking) uden det døende alias.
    # Ligger FØR extra_body-merge, så en eksplicit caller-thinking vinder over dette.
    if provider == "deepseek" and model in ("deepseek-chat", "deepseek-reasoner"):
        payload["thinking"] = (
            {"type": "disabled"} if model == "deepseek-chat" else {"type": "enabled"}
        )
        model = "deepseek-v4-flash"          # reassign så cost-logging labeler ærligt
        payload["model"] = model
    # Lag 10 Phase 1 (2026-05-12): caller may pass modulated values.
    # When None, omit from payload so server-side defaults apply (cheap-lane
    # callers don't pass them; only visible-lane wrappers do).
    if temperature is not None:
        payload["temperature"] = float(temperature)
    if top_p is not None:
        payload["top_p"] = float(top_p)
    if tools:
        payload["tools"] = _normalize_tools_for_openai_chat(tools)
    if extra_body:
        payload.update(extra_body)
    # GPT-5/o-series (reasoning) afviser 'max_tokens' → brug 'max_completion_tokens'.
    _mname = str(model).split("/")[-1]
    if any(_mname.startswith(p) for p in ("gpt-5", "o1", "o3", "o4")) and "max_tokens" in payload:
        payload["max_completion_tokens"] = payload.pop("max_tokens")
    # Task 8b: account2 egress-proxy. Gated behind the multiprofile flag — when
    # OFF, proxy stays None (unchanged, home-IP behavior). When ON, a non-default
    # profile is routed through its egress proxy; _resolve_proxy hard-raises on a
    # missing endpoint rather than leaking account2 over the home IP.
    # v6bind (2026-07-23): when the flag is on and this slot is eligible (account2
    # profile + provider on the allowlist, e.g. groq), bind the connection to a
    # native-IPv6 source address in our HE /64 INSTEAD of the he6 proxy hop. When
    # None (default), the existing multiprofile proxy path is byte-identical.
    from core.services.egress_routing import resolve_v6bind_source as _rv6
    _v6src = _rv6(provider, auth_profile)
    proxy = None if _v6src else _resolve_egress_proxy(provider=provider, auth_profile=auth_profile)
    _proxy_kw = {"proxy": proxy} if proxy else {}
    if provider == "groq":
        _egress_kw = {"source_address": _v6src} if _v6src else _proxy_kw
        data, _headers = _f._http_json_httpx(
            f"{root}/chat/completions",
            payload=payload,
            headers=headers,
            provider=provider,
            **_egress_kw,
        )
    else:
        data, _headers = _f._http_json(
            f"{root}/chat/completions",
            payload=payload,
            headers=headers,
            provider=provider,
            **_proxy_kw,
        )
    _first_choice = (data.get("choices") or [{}])[0] or {}
    first_msg = _first_choice.get("message") or {}
    tool_calls = list(first_msg.get("tool_calls") or [])
    # Fase 4 Task S: deepseek (and other reasoning-capable openai-compat
    # providers) expose the model's reasoning trace on
    # choices[0].message.reasoning_content — plumb it through additively so
    # /v1/agent/step can forward+pair it across tool rounds. Absent on
    # providers that don't support it -> "" (unchanged behavior).
    reasoning_content = str(first_msg.get("reasoning_content") or "")
    # Tool-only responses (no assistant text) are valid when tools are in
    # play — don't raise empty-response in that case.
    if tool_calls:
        try:
            text = _extract_openai_compatible_text(provider=provider, data=data)
        except CheapProviderError:
            text = ""
    else:
        text = _extract_openai_compatible_text(provider=provider, data=data)
    usage = data.get("usage") or {}
    prompt_estimate = sum(len(str(m.get("content", ""))) for m in messages) // 4
    # Deepseek (and a few other openai-compat providers) report cache hit/miss
    # split inside usage. Plumb through so cost calc and observability can
    # distinguish — Deepseek charges ~50x less for cache hits ($0.0028/M vs
    # $0.14/M on v4-flash). If absent, downstream pricing falls back to
    # treating all input as cache miss.
    cache_hit = int(usage.get("prompt_cache_hit_tokens") or 0)
    cache_miss = int(usage.get("prompt_cache_miss_tokens") or 0)
    enriched_usage = dict(usage)
    if provider == "deepseek":
        enriched_usage.setdefault("prompt_cache_hit_tokens", cache_hit)
        enriched_usage.setdefault("prompt_cache_miss_tokens", cache_miss)
        enriched_usage.setdefault("model", model)
    return {
        "text": text,
        "tool_calls": tool_calls,
        "reasoning_content": reasoning_content,
        "input_tokens": int(
            usage.get("prompt_tokens")
            or usage.get("input_tokens")
            or prompt_estimate
        ),
        "output_tokens": int(
            usage.get("completion_tokens")
            or usage.get("output_tokens")
            or _estimate_tokens(text)
        ),
        "cache_hit_tokens": cache_hit,
        "cache_miss_tokens": cache_miss,
        "cost_usd": float(_estimate_cheap_cost(provider=provider, usage=enriched_usage)),
        "finish_reason": str(_first_choice.get("finish_reason") or ""),
    }


def deepseek_request_for_thinking_mode(model: str, thinking_mode: str) -> tuple[str, dict]:
    """Map composer thinking_mode -> (model, extra_body) WITHOUT the deprecated aliases
    (deepseek-chat/reasoner die 2026-07-24). DeepSeek V4 toggles thinking via request params:
      - fast -> non-thinking:  extra_body={"thinking":{"type":"disabled"}}
      - think -> high:         reasoning_effort="high" + thinking enabled
      - deep -> max:           reasoning_effort="max"  + thinking enabled
      - deepseek-v4-pro:       always thinking, cannot disable -> (model, {})
    """
    mode = (thinking_mode or "think").strip().lower()
    m = (model or "").strip()
    if m in ("deepseek-chat", "deepseek-reasoner"):
        m = "deepseek-v4-flash"
    if m == "deepseek-v4-pro":
        return m, {}
    if mode == "fast":
        return m, {"thinking": {"type": "disabled"}}
    if mode == "deep":
        return m, {"reasoning_effort": "max", "thinking": {"type": "enabled"}}
    return m, {"reasoning_effort": "high", "thinking": {"type": "enabled"}}


def deepseek_model_for_thinking_mode(model: str, thinking_mode: str) -> str:
    """Backward-compat: return only the model (never the deprecated alias)."""
    return deepseek_request_for_thinking_mode(model, thinking_mode)[0]


_DSML_OPEN = "<｜｜DSML｜｜tool_calls>"
_DSML_CLOSE = "</｜｜DSML｜｜tool_calls>"


def _strip_dsml_leak(buffer: str, in_block: bool) -> tuple[str, str, bool]:
    """Strip Deepseek thinking-mode tool_call DSL from streaming content.

    Deepseek v4-pro can spill its internal tool_call DSL — wrapped in
    ``<｜｜DSML｜｜tool_calls>...</｜｜DSML｜｜tool_calls>`` (U+FF5C fullwidth
    bars) — into delta.content alongside the proper structured tool_calls
    array. Without this filter the user sees raw special-token markup,
    AND any tool arguments embedded there (which has previously included
    secrets the model planned to use). Strip the entire block; structured
    tool_calls.tool_calls path is unaffected.

    Returns ``(safe_chunk, remaining_buffer, in_block)``.

    The remaining_buffer holds either:
    - in_block=False: the tail that *might* be the start of a DSML opener
      we haven't fully matched yet (so we don't emit it prematurely).
    - in_block=True: bytes we're still skipping until the closer arrives.
    """
    safe: list[str] = []
    while buffer:
        if in_block:
            close_idx = buffer.find(_DSML_CLOSE)
            if close_idx == -1:
                # We're still inside the block; no close yet. Keep buffer
                # but cap it so a never-closing block doesn't grow unbounded.
                if len(buffer) > 8192:
                    buffer = buffer[-1024:]
                return "".join(safe), buffer, in_block
            buffer = buffer[close_idx + len(_DSML_CLOSE):]
            in_block = False
            continue
        # Not in block — find next opener
        open_idx = buffer.find(_DSML_OPEN)
        if open_idx == -1:
            # No full opener. But the buffer's tail could still be a partial
            # opener mid-stream (e.g. ends with "<｜｜D"). Hold back any tail
            # that *could* be a prefix of the opener to avoid emitting "<｜"
            # before deciding.
            tail_keep = 0
            for k in range(1, min(len(_DSML_OPEN), len(buffer)) + 1):
                if _DSML_OPEN.startswith(buffer[-k:]):
                    tail_keep = k
            if tail_keep:
                safe.append(buffer[:-tail_keep])
                return "".join(safe), buffer[-tail_keep:], in_block
            safe.append(buffer)
            return "".join(safe), "", in_block
        # Emit prefix before the opener, then enter block
        if open_idx > 0:
            safe.append(buffer[:open_idx])
        buffer = buffer[open_idx + len(_DSML_OPEN):]
        in_block = True
    return "".join(safe), "", in_block


def _execute_gemini_chat(
    *,
    model: str,
    auth_profile: str,
    base_url: str,
    message: str,
) -> dict[str, object]:
    credentials = _facade()._require_credentials(profile=auth_profile, provider="gemini")
    api_key = str(credentials.get("api_key") or "").strip()
    root = str(base_url or _facade().provider_runtime_defaults("gemini").get("base_url") or "").rstrip("/")
    safe_model = urllib_parse.quote(model, safe="")
    url = f"{root}/models/{safe_model}:generateContent?key={urllib_parse.quote(api_key, safe='')}"
    data, _headers = _facade()._http_json(
        url,
        payload={"contents": [{"parts": [{"text": message}]}]},
        headers={},
        provider="gemini",
    )
    text = _extract_gemini_text(data)
    usage = data.get("usageMetadata") or {}
    return {
        "text": text,
        "output_tokens": int(usage.get("candidatesTokenCount") or _estimate_tokens(text)),
        "cost_usd": 0.0,
    }


def _execute_cloudflare_chat(
    *,
    model: str,
    auth_profile: str,
    base_url: str,
    message: str,
) -> dict[str, object]:
    credentials = _facade()._require_credentials(profile=auth_profile, provider="cloudflare")
    api_key = str(credentials.get("api_key") or "").strip()
    account_id = str(credentials.get("account_id") or "").strip()
    root = str(base_url or _facade().provider_runtime_defaults("cloudflare").get("base_url") or "").rstrip("/")
    encoded_model = urllib_parse.quote(model, safe="@/-")
    url = f"{root}/accounts/{account_id}/ai/run/{encoded_model}"
    data, _headers = _facade()._http_json(
        url,
        payload={"messages": [{"role": "user", "content": message}]},
        headers={"Authorization": f"Bearer {api_key}"},
        provider="cloudflare",
    )
    text = _extract_cloudflare_text(data)
    return {
        "text": text,
        "output_tokens": _estimate_tokens(text),
        "cost_usd": 0.0,
    }


def _list_openai_compatible_models(
    *,
    provider: str,
    auth_profile: str,
    base_url: str,
) -> list[dict[str, object]]:
    credentials = _facade()._require_credentials(profile=auth_profile, provider=provider)
    root = str(base_url or _facade().provider_runtime_defaults(provider).get("base_url") or "").rstrip("/")
    data, _headers = _facade()._http_json(
        f"{root}/models",
        headers={"Authorization": f"Bearer {str(credentials.get('api_key') or '').strip()}"},
        provider=provider,
        method="GET",
    )
    models = data.get("data") or []
    return [
        {
            "id": str(item.get("id") or "").strip(),
            "label": str(item.get("id") or item.get("name") or "").strip(),
        }
        for item in models
        if isinstance(item, dict) and str(item.get("id") or "").strip()
    ]


def _list_gemini_models(*, auth_profile: str, base_url: str) -> list[dict[str, object]]:
    credentials = _facade()._require_credentials(profile=auth_profile, provider="gemini")
    api_key = str(credentials.get("api_key") or "").strip()
    root = str(base_url or _facade().provider_runtime_defaults("gemini").get("base_url") or "").rstrip("/")
    url = f"{root}/models?key={urllib_parse.quote(api_key, safe='')}"
    data, _headers = _facade()._http_json(url, headers={}, provider="gemini", method="GET")
    models = data.get("models") or []
    return [
        {
            "id": str(item.get("name") or "").replace("models/", "").strip(),
            "label": str(item.get("displayName") or item.get("name") or "").strip(),
        }
        for item in models
        if isinstance(item, dict) and str(item.get("name") or "").strip()
    ]


def _list_cloudflare_models(*, auth_profile: str, base_url: str) -> list[dict[str, object]]:
    credentials = _facade()._require_credentials(profile=auth_profile, provider="cloudflare")
    api_key = str(credentials.get("api_key") or "").strip()
    account_id = str(credentials.get("account_id") or "").strip()
    root = str(base_url or _facade().provider_runtime_defaults("cloudflare").get("base_url") or "").rstrip("/")
    url = f"{root}/accounts/{account_id}/ai/models/search"
    data, _headers = _facade()._http_json(
        url,
        headers={"Authorization": f"Bearer {api_key}"},
        provider="cloudflare",
        method="GET",
    )
    results = data.get("result") or data.get("models") or []
    return [
        {
            "id": str(item.get("id") or item.get("name") or item.get("model") or "").strip(),
            "label": str(item.get("name") or item.get("id") or item.get("model") or "").strip(),
        }
        for item in results
        if isinstance(item, dict)
        and str(item.get("id") or item.get("name") or item.get("model") or "").strip()
    ]


def _list_ollamafreeapi_models() -> list[dict[str, object]]:
    from core.runtime.ollamafreeapi_provider import list_ollamafreeapi_models

    return [{"id": model, "label": model} for model in list_ollamafreeapi_models()]


# ── OllamaFreeAPI circuit breaker — LØFTET til den delte per-provider breaker ──
# Spec §11.2: de tidligere ofa/arko-specifikke breakers er nu BAKKET af den delte
# per-provider store (provider_circuit_breaker.pp_*), keyed på provider_id="ollamafreeapi".
# Vi bevarer ofa's historiske adfærd (3 fejl i træk → åben 5 min) via pp_configure.
_OFA_CB_THRESHOLD = 3            # open after 3 consecutive fails (bevaret)
_OFA_CB_OPEN_DURATION_S = 300.0  # stay open 5 minutes (bevaret)
_OFA_PROVIDER_ID = "ollamafreeapi"


def _ofa_circuit_open() -> bool:
    from core.services import provider_circuit_breaker as _cb
    _cb.pp_configure(_OFA_PROVIDER_ID, threshold=_OFA_CB_THRESHOLD,
                     cooldown_s=_OFA_CB_OPEN_DURATION_S)
    return _cb.pp_is_open(_OFA_PROVIDER_ID)


def _ofa_circuit_record_failure() -> None:
    from core.services import provider_circuit_breaker as _cb
    _cb.pp_configure(_OFA_PROVIDER_ID, threshold=_OFA_CB_THRESHOLD,
                     cooldown_s=_OFA_CB_OPEN_DURATION_S)
    _cb.pp_record_failure(_OFA_PROVIDER_ID)


def _ofa_circuit_record_success() -> None:
    from core.services import provider_circuit_breaker as _cb
    _cb.pp_record_success(_OFA_PROVIDER_ID)


def _execute_ollamafreeapi_chat(
    *,
    model: str,
    message: str,
) -> dict[str, object]:
    from core.runtime.ollamafreeapi_provider import call_ollamafreeapi

    if _ofa_circuit_open():
        raise CheapProviderError(
            provider="ollamafreeapi",
            code="circuit-open",
            message=(
                f"ollamafreeapi circuit breaker open (after "
                f"{_OFA_CB_THRESHOLD}+ consecutive failures, retrying in "
                f"{int(_OFA_CB_OPEN_DURATION_S/60)}m)"
            ),
        )

    try:
        data = call_ollamafreeapi(model=model, prompt=message, timeout=_DEFAULT_TIMEOUT_SECONDS)
    except Exception as exc:
        _ofa_circuit_record_failure()
        raise CheapProviderError(
            provider="ollamafreeapi",
            code="provider-error",
            message=str(exc),
        ) from exc
    _ofa_circuit_record_success()
    text = str((data.get("message") or {}).get("content") or "").strip()
    return {
        "text": text,
        "output_tokens": _estimate_tokens(text),
        "cost_usd": 0.0,
    }


# ── Arko circuit breaker — LØFTET til den delte per-provider breaker ──────────
# Spec §11.2: bakket af den delte per-provider store, keyed provider_id="arko".
# Bevarer arko's historiske adfærd (3 fejl i træk → åben 3 min) via pp_configure.
_ARKO_CB_THRESHOLD = 3          # consecutive failures before opening (bevaret)
_ARKO_CB_OPEN_DURATION_S = 180  # stay open for 3 minutes (bevaret)
_ARKO_PROVIDER_ID = "arko"


def _arko_circuit_open() -> bool:
    from core.services import provider_circuit_breaker as _cb
    _cb.pp_configure(_ARKO_PROVIDER_ID, threshold=_ARKO_CB_THRESHOLD,
                     cooldown_s=float(_ARKO_CB_OPEN_DURATION_S))
    return _cb.pp_is_open(_ARKO_PROVIDER_ID)


def _arko_circuit_record_failure() -> None:
    from core.services import provider_circuit_breaker as _cb
    _cb.pp_configure(_ARKO_PROVIDER_ID, threshold=_ARKO_CB_THRESHOLD,
                     cooldown_s=float(_ARKO_CB_OPEN_DURATION_S))
    _cb.pp_record_failure(_ARKO_PROVIDER_ID)


def _arko_circuit_record_success() -> None:
    from core.services import provider_circuit_breaker as _cb
    _cb.pp_record_success(_ARKO_PROVIDER_ID)


def _execute_arko_chat(*, message: str) -> dict[str, object]:
    from core.runtime.arko_provider import call_arko

    if _arko_circuit_open():
        raise CheapProviderError(
            provider="arko",
            code="circuit-open",
            message=(
                f"arko circuit breaker open (after {_ARKO_CB_THRESHOLD}+ "
                f"consecutive failures, retrying in "
                f"{int(_ARKO_CB_OPEN_DURATION_S/60)}m)"
            ),
        )

    try:
        data = call_arko(prompt=message, timeout=_DEFAULT_TIMEOUT_SECONDS)
    except Exception as exc:
        _arko_circuit_record_failure()
        raise CheapProviderError(
            provider="arko",
            code="provider-error",
            message=str(exc),
        ) from exc
    _arko_circuit_record_success()
    text = str((data.get("message") or {}).get("content") or "").strip()
    return {
        "text": text,
        "output_tokens": _estimate_tokens(text),
        "cost_usd": 0.0,
    }


def _normalize_tools_for_openai_chat(tools: list[dict] | None) -> list[dict] | None:
    """Normalize tool defs to OpenAI Chat Completions format.

    Some tools in our registry are registered in Anthropic shape:
        {"name": "...", "description": "...", "input_schema": {...}}
    OpenAI Chat Completions (and Deepseek/Groq/etc.) require:
        {"type":"function", "function":{"name":"...","description":"...","parameters":{...}}}

    Without this conversion, deepseek rejects the request with HTTP 400
    "missing field type" on the offending tool. Run on every tool list
    before dispatching to /chat/completions.
    """
    if not tools:
        return None
    out: list[dict] = []
    seen_names: set[str] = set()

    def _add(tool: dict, name: str) -> None:
        # Deepseek (og strict OpenAI-compat) afviser med
        # "Tool names must be unique" hvis samme function-navn
        # registreres flere gange. Vores tool-registry har 3 dubletter
        # (process_list, goal_create, goal_list). Drop første-vinder —
        # bedre at miste en duplikat end at tabe hele turn'en.
        if not name or name in seen_names:
            return
        seen_names.add(name)
        out.append(tool)

    for t in tools:
        if not isinstance(t, dict):
            continue
        # Already Chat-Completions-shaped
        if t.get("type") == "function" and isinstance(t.get("function"), dict):
            _add(t, str((t.get("function") or {}).get("name") or ""))
            continue
        # Anthropic shape → convert
        if "input_schema" in t and "name" in t:
            _add(
                {
                    "type": "function",
                    "function": {
                        "name": str(t.get("name") or ""),
                        "description": str(t.get("description") or ""),
                        "parameters": t.get("input_schema") or {"type": "object", "properties": {}},
                    },
                },
                str(t.get("name") or ""),
            )
            continue
        # Bare-name shape (rare) — wrap minimally
        if "name" in t:
            _add(
                {
                    "type": "function",
                    "function": {
                        "name": str(t.get("name") or ""),
                        "description": str(t.get("description") or ""),
                        "parameters": t.get("parameters") or t.get("input_schema") or {"type": "object", "properties": {}},
                    },
                },
                str(t.get("name") or ""),
            )
    return out or None


_OLLAMA_LOCAL_TIMEOUT_SECONDS = 120


def _execute_local_ollama_chat(
    *, model: str, base_url: str, message: str
) -> dict[str, object]:
    """Call the local Ollama instance with a specific model.

    Added 2026-05-14 to support per-model selection from the public-safe
    cheap-lane pool (vs. _execute_public_safe_local_ollama which picks
    via resolve_provider_router_target and only respects lane=local).

    Uses a 120s timeout (vs the 30s default) because cloud-passthrough
    models on local Ollama can be slow on first call / cold start, and
    counterfactual prompts are longer than the typical heartbeat probe.
    """
    url = str(base_url or "http://127.0.0.1:11434").rstrip("/")
    payload = {
        "model": str(model or "").strip(),
        "messages": [{"role": "user", "content": message}],
        "stream": False,
    }
    try:
        # Use urllib directly with extended timeout — _http_json is locked
        # to _DEFAULT_TIMEOUT_SECONDS and shared by many providers.
        body = json.dumps(payload).encode("utf-8")
        req = urllib_request.Request(
            f"{url}/api/chat",
            data=body,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": "jarvis-v2/cheap-lane",
            },
            method="POST",
        )
        with urllib_request.urlopen(req, timeout=_OLLAMA_LOCAL_TIMEOUT_SECONDS) as response:
            data = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        raise CheapProviderError(
            provider="ollama", code="request-failed", message=str(exc)
        )
    text = str((data.get("message") or {}).get("content") or "").strip()
    return {
        "lane": "cheap",
        "provider": "ollama",
        "model": model,
        "status": "completed",
        "execution_mode": "public-safe-local-ollama",
        "source": "cheap-provider-runtime",
        "text": text,
        "input_tokens": _estimate_tokens(message),
        "output_tokens": _estimate_tokens(text),
        "cost_usd": 0.0,
    }


def _execute_public_safe_local_ollama(*, message: str) -> dict[str, object]:
    target = resolve_provider_router_target(lane="local")
    if not bool(target.get("active")) or str(target.get("provider") or "").strip() != "ollama":
        raise RuntimeError("public-safe local fallback unavailable")
    base_url = str(target.get("base_url") or "http://127.0.0.1:11434").rstrip("/")
    payload = {
        "model": str(target.get("model") or "").strip(),
        "messages": [{"role": "user", "content": message}],
        "stream": False,
    }
    data, _headers = _facade()._http_json(
        f"{base_url}/api/chat",
        payload=payload,
        headers={},
        provider="ollama",
    )
    text = str((data.get("message") or {}).get("content") or "").strip()
    return {
        "lane": "local",
        "provider": "ollama",
        "model": str(target.get("model") or "").strip(),
        "status": "completed",
        "execution_mode": "public-safe-local-fallback",
        "source": "cheap-provider-runtime",
        "text": text,
        "input_tokens": _estimate_tokens(message),
        "output_tokens": _estimate_tokens(text),
        "cost_usd": 0.0,
    }


def _require_credentials(*, profile: str, provider: str) -> dict[str, object]:
    # Tom/whitespace profil → "default" (aldrig kald _profile_dir("") som rejser
    # "Profile name must be a simple non-empty identifier"). Cheap-lane-selection kan
    # give tom auth_profile for keyless providers (kilo/pollinations) — normalisering
    # her gør at en evt. gemt token (kilo's JWT under "default") stadig hentes.
    profile = (str(profile or "").strip()) or "default"
    # auth_kind=none (Pollinations/OVHcloud/kilo anon) kræver INGEN credential-entry —
    # returnér tom dict så adapteren udelader Authorization-headeren (linje ~650).
    # try/except: enhver profil-fejl → {} (kør anonymt), aldrig crash i cheap-lane.
    if str((CHEAP_PROVIDER_DEFAULTS.get(provider) or {}).get("auth_kind")) == "none":
        try:
            return dict(get_provider_credentials(profile=profile, provider=provider) or {})
        except Exception:
            return {}
    credentials = get_provider_credentials(profile=profile, provider=provider)
    if not credentials:
        raise CheapProviderError(
            provider=provider,
            code="auth-not-ready",
            message=f"{provider} credentials missing for profile {profile}",
        )
    api_key = str(credentials.get("api_key") or "").strip()
    if provider == "cloudflare":
        if not api_key or not str(credentials.get("account_id") or "").strip():
            raise CheapProviderError(
                provider=provider,
                code="auth-not-ready",
                message="cloudflare requires api_key and account_id",
            )
    elif not api_key:
        # auth_kind=none (OVHcloud anon) kræver ingen nøgle.
        if str((CHEAP_PROVIDER_DEFAULTS.get(provider) or {}).get("auth_kind")) == "none":
            return credentials
        raise CheapProviderError(
            provider=provider,
            code="auth-not-ready",
            message=f"{provider} api_key missing for profile {profile}",
        )
    return credentials


def _http_json(
    url: str,
    *,
    provider: str,
    method: str = "POST",
    payload: dict[str, object] | None = None,
    headers: dict[str, str] | None = None,
    proxy: str | None = None,
) -> tuple[dict[str, object], dict[str, str]]:
    request_headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "jarvis-v2/cheap-lane",
        **(headers or {}),
    }
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib_request.Request(
        url,
        data=body,
        headers=request_headers,
        method=method,
    )
    # Task 8b: account2 egress-proxy. When set, route this single request through
    # the proxy (http+https) via a dedicated opener; None -> direct (home IP).
    _opener = (
        urllib_request.build_opener(
            urllib_request.ProxyHandler({"http": proxy, "https": proxy})
        ).open
        if proxy
        else urllib_request.urlopen
    )
    try:
        with _opener(req, timeout=_DEFAULT_TIMEOUT_SECONDS) as response:
            raw_headers = {key.lower(): value for key, value in response.headers.items()}
            data = json.loads(response.read().decode("utf-8"))
        return data, raw_headers
    except urllib_error.HTTPError as exc:
        body_text = exc.read().decode("utf-8", errors="replace")
        retry_after = int(exc.headers.get("Retry-After", "0") or 0)
        code = _classify_http_error(provider=provider, status_code=exc.code, body=body_text)
        if code == "checkin-required":
            _notify_checkin_required(provider)
        raise CheapProviderError(
            provider=provider,
            code=code,
            message=body_text[:500] or f"HTTP {exc.code}",
            retry_after_seconds=retry_after,
            status_code=exc.code,
        )
    except urllib_error.URLError as exc:
        raise CheapProviderError(
            provider=provider,
            code="unreachable",
            message=str(exc.reason),
        )
    except Exception as exc:
        raise CheapProviderError(
            provider=provider,
            code="request-failed",
            message=str(exc),
        )


def _http_json_httpx(
    url: str,
    *,
    provider: str,
    payload: dict[str, object] | None = None,
    headers: dict[str, str] | None = None,
    proxy: str | None = None,
    source_address: str | None = None,
) -> tuple[dict[str, object], dict[str, str]]:
    request_headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "jarvis-v2/cheap-lane",
        **(headers or {}),
    }
    # Task 8b: account2 egress-proxy (httpx 0.28 kwarg is `proxy=`, not `proxies=`).
    # None -> direct (home IP).
    _client_kwargs: dict[str, object] = {
        "timeout": _DEFAULT_TIMEOUT_SECONDS,
        "follow_redirects": True,
    }
    # v6bind (2026-07-23): bind the outbound connection to a specific local source
    # address (account2 native-IPv6 egress in our HE /64) — the httpx equivalent of
    # `curl --interface <v6addr>`. Mutually exclusive with a proxy; when set it
    # replaces the he6 proxy hop so the connection egresses natively from CT105.
    if source_address:
        _client_kwargs["transport"] = httpx.HTTPTransport(local_address=source_address)
    elif proxy:
        _client_kwargs["proxy"] = proxy
    try:
        with httpx.Client(**_client_kwargs) as client:
            response = client.post(
                url,
                json=payload,
                headers=request_headers,
            )
            raw_headers = {key.lower(): value for key, value in response.headers.items()}
            response.raise_for_status()
            data = response.json()
        return data, raw_headers
    except httpx.HTTPStatusError as exc:
        body_text = exc.response.text
        retry_after = int(exc.response.headers.get("Retry-After", "0") or 0)
        code = _classify_http_error(
            provider=provider,
            status_code=exc.response.status_code,
            body=body_text,
        )
        if code == "checkin-required":
            _notify_checkin_required(provider)
        raise CheapProviderError(
            provider=provider,
            code=code,
            message=body_text[:500] or f"HTTP {exc.response.status_code}",
            retry_after_seconds=retry_after,
            status_code=exc.response.status_code,
        )
    except httpx.RequestError as exc:
        raise CheapProviderError(
            provider=provider,
            code="unreachable",
            message=str(exc),
        )
    except Exception as exc:
        raise CheapProviderError(
            provider=provider,
            code="request-failed",
            message=str(exc),
        )


def _classify_http_error(*, provider: str, status_code: int, body: str) -> str:
    lowered = str(body or "").lower()
    # FreeTheAi-checkin-gate (16.jul): nøglen låses HELT hver UTC-dag indtil Bjørn kører
    # Discord-/checkin. Body-baseret (uafhængig af status-kode) så vi altid fanger den →
    # distinkt kode så dispatch-stien kan nudge Jarvis (han beder Bjørn om /checkin).
    if "daily_checkin_required" in lowered or "check-in required" in lowered or "checkin required" in lowered:
        return "checkin-required"
    if status_code == 402:
        return "credits-exhausted"
    if status_code == 404:
        if "no endpoints found" in lowered or "endpoint" in lowered:
            return "model-unavailable"
        return "model-not-found"
    if status_code == 401:
        return "auth-rejected"
    if status_code == 403:
        if "error code: 1010" in lowered or "access denied" in lowered or "forbidden" in lowered:
            return "provider-blocked"
        return "auth-rejected"
    if status_code == 429:
        if "quota" in lowered or "daily" in lowered or "insufficient credits" in lowered:
            return "quota-exhausted"
        return "rate-limited"
    if status_code >= 500:
        return "provider-error"
    return f"http-{status_code}"


def _default_failure_cooldown_seconds(code: str) -> int:
    normalized = str(code or "").strip()
    if normalized == "rate-limited":
        return 300
    if normalized in {"quota-exhausted", "credits-exhausted"}:
        return 3600
    if normalized in {"provider-blocked", "provider-error"}:
        return 1800
    if normalized in {"model-not-found", "model-unavailable"}:
        return 900
    if normalized == "checkin-required":
        # Låst til næste Discord-/checkin (per UTC-dag). 30 min → self-heal genopliver
        # den auto ~30 min efter Bjørn har checket ind, uden at hamre imens.
        return 1800
    return 300


def _notify_checkin_required(provider: str) -> None:
    """Læg en nudge i Jarvis' awareness når en checkin-gated provider (FreeTheAi) er låst,
    så HAN kan huske at bede Bjørn køre /checkin. Dedup pr. UTC-dag (én nudge/dag, uanset
    hvor mange kald/self-heal-probes der rammer låsen). Self-safe — aldrig crash i dispatch."""
    try:
        from datetime import UTC, datetime
        from core.services import nudge_broend
        today = datetime.now(UTC).date().isoformat()
        src = f"{provider}_checkin"
        for n in nudge_broend.list_pending(limit=50):
            if n.get("source") == src and str(n.get("created_at") or "").startswith(today):
                return  # allerede nudget i dag
        nudge_broend.push(
            source=src, kind="provider_checkin", importance="normal",
            message=(f"{provider} er låst i dag — den kræver Bjørns daglige Discord-/checkin. "
                     f"Hvis du får brug for dens modeller (gpt-5.5-mini/grok-4.1-fast/"
                     f"deepseek-v4-pro), så bed Bjørn køre /checkin på deres server."),
        )
    except Exception:
        logger.debug("checkin-nudge fejlede", exc_info=True)


def _extract_openai_compatible_text(*, provider: str, data: dict[str, object]) -> str:
    choices = data.get("choices") or []
    for item in choices:
        if not isinstance(item, dict):
            continue
        message = item.get("message") or {}
        content = message.get("content")
        if isinstance(content, str) and content.strip():
            return content.strip()
        if isinstance(content, list):
            parts = [
                str(part.get("text") or "").strip()
                for part in content
                if isinstance(part, dict) and str(part.get("text") or "").strip()
            ]
            if parts:
                return "\n".join(parts).strip()
    raise CheapProviderError(
        provider=provider,
        code="empty-response",
        message="provider returned no assistant text",
    )


def _extract_gemini_text(data: dict[str, object]) -> str:
    candidates = data.get("candidates") or []
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        content = candidate.get("content") or {}
        parts = content.get("parts") or []
        texts = [
            str(part.get("text") or "").strip()
            for part in parts
            if isinstance(part, dict) and str(part.get("text") or "").strip()
        ]
        if texts:
            return "\n".join(texts).strip()
    raise CheapProviderError(
        provider="gemini",
        code="empty-response",
        message="gemini returned no candidate text",
    )


def _extract_cloudflare_text(data: dict[str, object]) -> str:
    result = data.get("result") or {}
    if isinstance(result, dict):
        response = str(result.get("response") or "").strip()
        if response:
            return response
        messages = result.get("messages") or []
        for item in messages:
            if not isinstance(item, dict):
                continue
            content = str(item.get("content") or "").strip()
            if content:
                return content
    raise CheapProviderError(
        provider="cloudflare",
        code="empty-response",
        message="cloudflare returned no text response",
    )


def _listing_surface(
    *,
    provider: str,
    auth_profile: str,
    status: str,
    source: str,
    models: list[dict[str, object]],
    base_url: str = "",
) -> dict[str, object]:
    return {
        "provider": provider,
        "auth_profile": auth_profile,
        "source": source,
        "status": status,
        "base_url": base_url,
        "models": models,
    }


# DeepSeek pricing (per 1M tokens, USD). Source: https://api-docs.deepseek.com/
# Pulled 2026-05-07. v4-pro has a 75% promo until 2026-05-31 15:59 UTC — after
# that the full price kicks in. v4-flash flat priced; cache-hit ~50x cheaper
# than cache-miss. Update if Deepseek changes pricing.
_DEEPSEEK_PROMO_END_ISO = "2026-05-31T15:59:00+00:00"

_DEEPSEEK_PRICES_PER_M: dict[str, dict[str, Decimal]] = {
    "deepseek-v4-flash": {
        "cache_hit": Decimal("0.0028"),
        "cache_miss": Decimal("0.14"),
        "output": Decimal("0.28"),
    },
    "deepseek-v4-pro_promo": {
        "cache_hit": Decimal("0.003625"),
        "cache_miss": Decimal("0.435"),
        "output": Decimal("0.87"),
    },
    "deepseek-v4-pro_full": {
        "cache_hit": Decimal("0.0145"),
        "cache_miss": Decimal("1.74"),
        "output": Decimal("3.48"),
    },
}


def _deepseek_price_table(model: str) -> dict[str, Decimal] | None:
    if model == "deepseek-v4-flash":
        return _DEEPSEEK_PRICES_PER_M["deepseek-v4-flash"]
    if model == "deepseek-v4-pro":
        from datetime import datetime, timezone
        promo_end = datetime.fromisoformat(_DEEPSEEK_PROMO_END_ISO)
        in_promo = datetime.now(timezone.utc) < promo_end
        key = "deepseek-v4-pro_promo" if in_promo else "deepseek-v4-pro_full"
        return _DEEPSEEK_PRICES_PER_M[key]
    return None


def _estimate_deepseek_cost(usage: dict[str, object]) -> Decimal:
    model = str(usage.get("model") or "").strip()
    table = _deepseek_price_table(model)
    if table is None:
        return Decimal("0")
    prompt_total = Decimal(str(usage.get("prompt_tokens") or 0))
    cache_hit = Decimal(str(usage.get("prompt_cache_hit_tokens") or 0))
    cache_miss = Decimal(str(usage.get("prompt_cache_miss_tokens") or 0))
    # If the API didn't split it, treat all prompt tokens as cache miss
    # (conservative — tracks higher cost rather than under-reporting).
    if cache_hit == 0 and cache_miss == 0:
        cache_miss = prompt_total
    output = Decimal(str(usage.get("completion_tokens") or usage.get("output_tokens") or 0))
    million = Decimal("1000000")
    cost = (
        cache_hit * table["cache_hit"]
        + cache_miss * table["cache_miss"]
        + output * table["output"]
    ) / million
    return cost


def _estimate_cheap_cost(*, provider: str, usage: dict[str, object]) -> Decimal:
    if provider == "deepseek":
        return _estimate_deepseek_cost(usage)
    # Free-tier cheap providers are tracked primarily by quota rather than spend.
    if provider != "openrouter":
        return Decimal("0")
    prompt_tokens = Decimal(str(usage.get("prompt_tokens") or usage.get("input_tokens") or 0))
    completion_tokens = Decimal(str(usage.get("completion_tokens") or usage.get("output_tokens") or 0))
    return (prompt_tokens + completion_tokens) * Decimal("0")


def _estimate_tokens(text: str) -> int:
    normalized = " ".join((text or "").split())
    if not normalized:
        return 1
    return max(1, len(normalized) // 4)
