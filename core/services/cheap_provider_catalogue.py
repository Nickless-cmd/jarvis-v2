"""Kataloget over cheap-lane-udbydere — hvem findes, hvad koster de, hvad virker.

Hver post er en MÅLING, ikke en gengivelse af udbyderens markedsføring. Derfor
står afviste udbydere også her med grunden: SiliconFlow så gratis ud i et
trial-vindue og hård-gatede bagefter, ModelScope kræver real-name. Uden den
historik ville nogen prøve dem igen om tre måneder.

`static_models` er dem vi har set svare. En model der står på udbyderens liste
men returnerer 402 eller tom tekst hører ikke til her.

Boy-Scout-udskillelse 7/9-2026: `cheap_provider_runtime_adapters` var 2.051
linjer, hvoraf kataloget alene var 628. Dicten re-eksporteres derfra, så
eksisterende kaldere og tests virker uændret.
"""
from __future__ import annotations

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
            # north-mini-code-free udgik 19. aug 2026 ("Model … is not supported" —
            # rapporteret som auth-rejected, hvilket sendte fejlsøgningen efter nøgler
            # frem for efter modeller). /models viser 6 gratis; disse to er nye.
            "nemotron-3.5-lightning-free",
            "laguna-s-2.1-free",
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
        # zai-glm-4.7 fjernet 19. aug 2026: Cerebras svarer `model_archived_error`
        # ("archived and unavailable for the organization") på begge auth-profiler.
        # Verificeret mod /v1/models — kontoen tilbyder nu KUN gemma-4-31b + gpt-oss-120b.
        "static_models": ["gemma-4-31b", "gpt-oss-120b"],
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
        # TØMT 19. aug 2026: GitHub retirer hele tjenesten. Alle fem modeller svarer
        # HTTP 410 med `github_models_retirement_brownout` — "temporarily unavailable as
        # part of a scheduled retirement brownout". En brownout er en varslet nedlukning,
        # ikke en driftsforstyrrelse: der er ingen model at skifte til hos denne udbyder.
        # Beholdt som tom entry (ikke slettet), så en genopstået tjeneste kun kræver at
        # listen fyldes igen — og så historikken i git forklarer hvorfor den er tom.
        "static_models": [],
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
    # account2's EGEN ollama-cloud free-tier-konto (24. jul, Bjørn): en separat
    # ollama-server på VPN-gateway-hosten 10.0.0.26 proxy'er til
    # ollama.com med account2's konto → adskilt gratis cloud-kvote fra den lokale
    # `ollama` (ejerens konto, visible-lane, i _EXCLUDED_PROVIDERS). Kaldet er et
    # ALM. LAN-kald til 10.0.0.26 (auth_kind=none, egress=home) — account2-
    # adskillelsen sker inde i ollama-serveren, ikke i vores egress. static_models
    # = KUN de cloud-modeller free-tier faktisk kan (verificeret 24. jul); de øvrige
    # (glm-5.2/kimi-k2.7-code/deepseek-v4-*) kræver subscription → udeladt så de ikke
    # bliver døde pool-slots.
    "ollama-a2": {
        "label": "Ollama Cloud (account2 free tier)",
        "priority": 90,
        # ADRESSEN FLYTTET 7/9-2026: stod på 10.0.0.45, som ikke svarer — hverken
        # ping eller ARP. 1.063 kald på syv døgn, ALLE med
        # «[Errno 113] No route to host», 0,0 % success. Gatewayen fandtes ved at
        # scanne LAN for port 11434: den ligger på 10.0.0.26 og har præcis de to
        # konfigurerede modeller. Verificeret med et rigtigt kald — svarer «klar»
        # OG returnerer tool_calls, så den duer til agent-arbejde.
        "base_url": "http://10.0.0.26:11434",
        "auth_kind": "none",
        "protocol": "ollama",
        "models_endpoint": "/api/tags",
        "rpm_limit": 6,
        "daily_limit": 200,
        "cost_class": "free",
        "static_models": ["gemma4:31b-cloud", "minimax-m3:cloud"],
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
    # LLM7.io (7/9-2026, nøgle i runtime.json som `llm7_api_key`): OpenAI-compat
    # `api.llm7.io/v1`, bearer. Nævnt i denne fil siden juli som «en $0-provider
    # (som LLM7)» — kendt god, aldrig tilsluttet.
    #
    # MÅLT med nøglen: listen returnerer 46 modeller, men **kun 3 af 36
    # tekst-modeller svarer faktisk**. 31 giver 402 «Insufficient balance»
    # (claude-opus-5, gpt-6-astra, deepseek-v4-*, glm-5.3-flash m.fl. — de står
    # på listen, men er betalte). Læs derfor ALDRIG static_models ud af
    # /v1/models her; de skal måles.
    #
    # To fælder fundet ved målingen:
    #   * `gpt-oss` svarer 200 med TOM tekst. Værre end en fejl i en lane —
    #     det ligner succes. Udeladt med vilje.
    #   * `mistral-Nemo` findes ikke (400). Det fulde navn
    #     `mistral-Nemo-Instruct-2407` virker — men KUN uden tools (400 med).
    #
    # Tools verificeret på codestral-latest og minimax-m2.7 (ét tool_call hver).
    # Anonymt: 10 RPM / 60 kald i timen; nøglen fordobler.
    #
    # Hvad den reelt tilføjer: REDUNDANS, ikke nye evner — codestral-latest har
    # vi via mistral, og minimax-m2.7 findes på xkiro. En anden vej til de samme
    # modeller er stadig værd at have når en udbyder falder ud.
    "llm7": {
        "label": "LLM7.io",
        "priority": 54,
        "base_url": "https://api.llm7.io/v1",
        "auth_kind": "bearer",
        "protocol": "openai-chat",
        "models_endpoint": "/models",
        "rpm_limit": 10,
        "daily_limit": 500,
        "cost_class": "free",
        "static_models": [
            "codestral-latest",
            "minimax-m2.7",
            "mistral-Nemo-Instruct-2407",
        ],
    },
    # xkiro (7/9-2026, Bjørn-nøgle i runtime.json som `xkiro_api_key`):
    # OpenAI-compat `api.xkiro.com/v1`, bearer. MÅLT med nøglen, ikke læst på
    # deres side:
    #   * `/v1/usage` svarer med free_tokens.limit_per_day = 5.000.000 — altså
    #     5 mio. tokens PR. DØGN, ikke pr. måned.
    #   * DeepSeek-modellerne har IKKE `:free` i navnet, men trækker alligevel
    #     fra gratis-puljen: efter fire testkald stod wallet stadig på præcis
    #     5.000000 USD og `used_today` var steget. Bjørns antagelse holdt.
    #   * 112 modeller, heraf 25 med `:free` (qwen + minimax).
    #
    # FÆLDE: udbyderen svarer **403 uden en User-Agent**. Pythons standard
    # `Python-urllib/3.x` afvises. Cheap-lane sætter allerede
    # `jarvis-v2/cheap-lane` på hvert kald, så det virker her — men en ny
    # klient uden UA vil fejle med noget der ligner et nøgleproblem.
    #
    # static_models er bevidst de `:free`-mærkede: de er utvetydigt gratis.
    # DeepSeek-modellerne trækker fra samme pulje, men uden `:free` i navnet er
    # der intet der lover det bliver ved, og de hører til i den synlige bane.
    "xkiro": {
        "label": "xkiro",
        "priority": 50,
        "base_url": "https://api.xkiro.com/v1",
        "auth_kind": "bearer",
        "protocol": "openai-chat",
        "models_endpoint": "/models",
        "rpm_limit": 20,
        "daily_limit": 1000,
        "cost_class": "free",
        "static_models": [
            "qwen/qwen3.5-flash:free",
            "qwen/qwen3.6-35b-a3b:free",
            "qwen/qwen3-coder-plus:free",
            "minimax/minimax-m2.5-highspeed:free",
        ],
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
        # aion-2.5 udgik 19. aug 2026 ("Unknown model", rapporteret som http-400 →
        # klassificeret transient, så slottet blev ved med at komme tilbage). /models
        # viser 4; aion-3.0 er efterfølgeren.
        "static_models": ["aion-labs/aion-2.0", "aion-labs/aion-3.0-mini",
                          "aion-labs/aion-3.0"],
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

