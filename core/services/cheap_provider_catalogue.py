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
    # ── Tre udbydere tilføjet 26/9-2026 (Bjørns egne konti, nøgler i
    # runtime.json). Hver post er hvad der er MÅLT, ikke hvad siden lover.

    # ── tu-zi / «Kanin-API» (26/9-2026, Bjørns konto, intet betalingskort).
    # Samme NewAPI-gateway-familie som chinaapi: svarer med `x-new-api-version`
    # og `x-oneapi-request-id`, plus `x-tuzi-route-class`. 797 modeller.
    #
    # DEN GRATIS FLADE FINDES IKKE. 213 modeller står med `model_ratio: 0`, og
    # på chinaapi var fælden `quota_type: 1`; her er den et ANDET felt: kun ÉN
    # af de 213 har også `model_price: 0`, og den er ikke en tekstmodel. De
    # øvrige 212 har en fast pris pr. kald gemt i `model_price`. Derfor
    # `cost_class: paid` — der er intet gratis at hente.
    #
    # MÅLT at svare: claude-opus-4-5, gpt-5, gemini-2.5-flash,
    # claude-3-5-haiku-latest. `deepseek-v3` og `kimi-k2.6` gav tomt svar og
    # står derfor ikke her — kataloget lister kun det der HAR svaret.
    # ── fujcloud (26/9-2026, Bjørns konto). Fjerde NewAPI-gateway i rækken,
    # kørende i Vietnam — fejltekster kommer på vietnamesisk.
    #
    # NØGLEN SÅ ANDERLEDES UD, OG DET VAR IKKE ET FORMATPROBLEM. De to strenge
    # Bjørn først gav var `dashboard-access-tokens`, ikke API-nøgler; beviset
    # var at `/api/user/self` svarede «Thiếu header New-Api-User» — altså
    # manglende header, ikke ugyldigt token. Kontoen havde slet ingen API-nøgle
    # oprettet. Den rigtige er 48 tegn UDEN `sk-`-præfiks.
    #
    # INGEN GRATIS FLADE: 20 modeller i prislisten, 14 med `quota_type: 1`
    # (fast pris pr. kald) og 6 token-prisede — ingen med pris nul. Prislisten
    # kan læses uden nøgle på /api/pricing.
    #
    # MÅLT at svare (max_tokens=800): claude-opus-5, claude-sonnet-4-6,
    # deepseek-v4-flash, glm-5.3-flash, mimo-v2.6-flash. `mercury-2.5` gav tomt
    # og står derfor ikke her.
    #
    # BEMÆRK om de tre thinking-modeller: deepseek-v4-flash, glm-5.3-flash og
    # mimo-v2.6-flash bruger 76-514 tegn på `reasoning_content` FØR de svarer.
    # En probe med et lille `max_tokens` ser dem som døde. Det er ikke en
    # teori — jeg begik netop den fejl på chinaapis `gpt-5.5` samme aften.
    #
    # SALDO: kontoen kører sin EGEN valuta (`quota_display_type: CUSTOM`,
    # symbol ✦, 500.000 kvote = 1 ✦). Balancen er ~2.000 ✦. Hvad en ✦ er værd
    # i rigtige penge kunne ikke fastslås — topup-kursen er admin-only. Så
    # rækkevidden er kendt i ✦ og ukendt i kroner: ~30 kald til de dyre
    # (65 ✦) eller ~150 til de billige (13 ✦).
    "fujcloud": {
        "label": "fujcloud (gateway, VN)",
        "priority": 67,
        "base_url": "https://ai.fujcloud.com/v1",
        "auth_kind": "bearer",
        "protocol": "openai-chat",
        "models_endpoint": "/models",
        "rpm_limit": 10,
        "daily_limit": 100,
        "cost_class": "paid",
        "static_models": ["claude-sonnet-4-6", "deepseek-v4-flash",
                          "glm-5.3-flash", "mimo-v2.6-flash"],
    },
    # ── free.ai (26/9-2026). Nøgleløs, gratis, hurtig og værktøjs-dygtig —
    # og den eneste af aftenens otte der er ALLE fire dele på én gang.
    #
    # MODELLISTEN ER FIKTION. API'et melder 503 modeller, 465 af dem chat.
    # Målt: TO aliaser svarer — `qwen7b` og `qwen3-8b` — og begge peger på
    # SAMME bagvedliggende model, `Qwen/Qwen3-30B-A3B-Instruct`. Alle andre
    # svarer «'X' is not a model»: z-ai/glm-5.3-prime, qwen/qwen3.8-max-prime,
    # deepseek-r1, aion-labs/aion-3.5, qwen3-coder, mistral, llama3, gemma,
    # phi3. Samme slags løgn som airforces `tier: free`-felt, bare i
    # modelnavnene i stedet for i et flag.
    #
    # Derfor står der ÉN model her og ikke to: `qwen3-8b` ville være samme
    # backend under et andet navn, og en balancer der tror den har to veje har
    # ikke to veje.
    #
    # MÅLT: 345-365 ms svartid. 15 kald i træk → alle 200, intet loft observeret.
    # Værktøjskald VIRKER (`tool_calls: 1 get_weather` på en rigtig skema-test)
    # — det er ikke en selvfølge for en gratis 30B, og det er grunden til at
    # den er mere værd end de fleste nøgleløse.
    #
    # NØGLEN ER VALGFRI: kaldet svarer 200 UDEN auth. Vi sender den alligevel,
    # fordi den er Bjørns og kan bære en kvote vi ikke kan se. Den hører derfor
    # i `_PUBLIC_PROXY_PROVIDERS`: nøgleløs adgang betyder delt, anonym rute.
    "freeai": {
        "label": "free.ai (nøgleløs)",
        "priority": 44,
        "base_url": "https://api.free.ai/v1",
        "auth_kind": "bearer",
        "protocol": "openai-chat",
        "models_endpoint": "/models",
        "rpm_limit": 30,
        "daily_limit": 1000,
        "cost_class": "free",
        "static_models": ["qwen7b"],
    },
    # github-models PENSIONERET — GitHub lukkede tjenesten 30. JULI 2026.
    #
    # Det er ikke en slutning; det står i deres egen dokumentation
    # (docs.github.com/en/rest/models/inference): «As of July 30, 2026, GitHub
    # Models has been fully retired. The playground, model catalog, inference
    # API, and bring your own key (BYOK) are no longer available to any
    # customer.» De anbefaler Azure AI Foundry eller GitHub Copilot i stedet —
    # og Copilot kører allerede her som `copilot-free`.
    #
    # Registrets fem model-poster blev slaaet fra 19-08-2026, altsaa TRE UGER
    # EFTER lukningen. Den der slukkede dem reagerede paa fejl; han var ikke
    # aarsagen. Og ingen skrev hvorfor — derfor stod de som fem mystisk
    # slukkede modeller i en maaned.
    #
    # Jeg maalte mig frem til det samme FOER jeg slog det op, og maalingerne
    # staar nedenfor — ikke for at bevise noget der nu er dokumenteret, men
    # fordi de viser hvordan en lukket tjeneste SER UD udefra:
    #   models.github.ai svarer 200 med brødteksten «OK» paa HVER sti —
    #     ogsaa `/` og `/inference/chat/completions`.
    #
    #   DET ER IKKE NOEGLEN, OG IKKE ET FORAELDET MODEL-ID. Bjoern spurgte om
    #     det bare var nye modeller. Afgjort med tre kald til samme sti:
    #         gyldig noegle    200 "OK"
    #         UGYLDIG noegle   200 "OK"
    #         INGEN noegle     200 "OK"
    #     Endpointet autentificerer slet ikke. En levende API med et forkert
    #     model-id ville svare 400/404 med JSON; denne svarer det samme uanset
    #     hvem der spoerger.
    #
    #   OG DET ER IKKE OPSNAPPET TRAFIK. Jeg skrev foerst «bekraeftet fra to
    #     net», men CT105 og CheifOne gaar BEGGE gennem den samme pfSense —
    #     det var et svagere bevis end jeg paastod. Certifikatet afgoer det:
    #         CN = *.github.ai, Sectigo, gyldig 3/9 - 1/12 2026
    #     Samme CA som *.github.com. Det ER GitHubs egen server der svarer
    #     «OK». Vaertsnavnet vedligeholdes stadig; API'et er bare flyttet.
    #
    #   api.github.com/models svarer 404 med ÆGTE JSON — samme noegle, samme
    #     net. Vaerten autentificerer og ruter korrekt; der er bare ingen
    #     Models-API der.
    #
    #   Noeglens eneste scope er `read:user` (Models kraever `models:read`),
    #     men det er uden betydning naar endpointet ikke tjekker auth.
    #   models.inference.ai.azure.com — den oprindelige adresse — slaar ikke
    #     op laengere (NXDOMAIN).
    #   Nøglen FINDES og er gyldig (`gho_…` i default-profilen), saa det er
    #     ikke et auth-problem.
    #
    # Registret har fem model-poster, alle `lane=cheap` og alle slaaet FRA
    # 19-08-2026 i samme sekund. Det var ikke en ugepr&oslash;ve der fandt fem
    # d&aring;rlige modeller — det var migrationen. `visible_model_adapters`
    # siger det selv: «that was for the old models.github.ai free tier».
    #
    # Tjenesten er foldet ind i Copilot, og den kører allerede som
    # `copilot-free` (i puljen, verificeret). De modeller github-models ville
    # have tilføjet — o4-mini, deepseek-r1, llama-3.3-70b — er væk med den.
    #
    # Posten staar her uden `static_models` af historiske grunde; den kan ikke
    # komme i puljen, og det er rigtigt. Ikke wired.

    # ollamafreeapi IKKE BRUGBAR 27/9-2026 — de offentlige servere er nede.
    #
    # Den har sit eget adapter-modul (`core/runtime/ollamafreeapi_provider`)
    # og henter modellisten dynamisk: 10 modeller MED servere. Men et kald
    # fejler efter 136 sekunder med «All servers failed».
    #
    # Maalt paa serverne bag `llama3.2:3b` (4 stk) og `gpt-oss:20b` (1 stk):
    #   5.149.249.212:11434    timeout
    #   89.111.170.212:11434   timeout
    #   185.211.5.32:11434     connection refused paa 35 ms — vaerten lever,
    #                          porten er lukket
    # Samme resultat fra CT105 og fra CheifOne. Det er ikke vores firewall;
    # de offentlige Ollama-servere er vaek.
    #
    # Derfor har den hverken `static_models` her eller model-poster i
    # registret, og kommer aldrig i puljen. Registret siger stadig
    # `enabled: true`, hvilket faar den til at taelle med i «38 enabled» —
    # to tal der maaler forskellige ting. Se ogsaa modul-docstringen.
    # PEKPIK AFVIST 26/9-2026 — den ene model den tilbyder fejler på HVERT kald,
    # og kaldet trækker forbrug alligevel.
    #
    # `aiapiv2.pekpik.com/v1`, femte NewAPI-gateway i rækken
    # (`x-oneapi-request-id`, bag Cloudflare). Nøgle påkrævet. Token'et er
    # `free-daily-591`: gruppe «free», $1,00/$1,00, ser ud til at forny sig
    # dagligt.
    #
    # Katalogets ENESTE model er `gemini-2.5-flash`. MÅLT, tre kald:
    #   med værktøjs-skema  → `openai_error`, 0 tool_calls, tom content, 9.935 ms
    #   almindelig chat ×2  → `openai_error`, tom content, 9.051 og 8.436 ms
    #
    # Og det afgørende: forbruget gik 0 → 0,027 → 0,039 MENS alle tre kald
    # fejlede. En udbyder der fakturerer for fejl ville dræne den daglige
    # dollar uden at levere en eneste besvarelse — og gøre det tavst, fordi
    # fejlen ligner en almindelig provider-fejl i loggen.
    #
    # Prøves igen kun hvis nogen har set den svare. Ikke wired.
    # llm.kiwi AFVIST 26/9-2026 — fire af seks modeller kræver en Pro-plan, den
    # femte hænger, og den sjette kan ikke kalde værktøjer.
    #
    # `api.llm.kiwi/v1` (bemærk: `llm.kiwi/v1` giver 404). Modellisten er åben,
    # men KALD kræver nøglen — altså en krediteret udbyder, ikke en anonym
    # proxy. Seks modeller: auto, hrLLM, minimax-m3, minimax-m2.5,
    # nemotron-3-super, nemotron-3-ultra.
    #
    # MÅLT, hver model med et rigtigt værktøjs-skema:
    #   minimax-m3/m2.5, nemotron-3-super/ultra → «This model requires a Pro
    #     or VIP plan» (93-176 ms, afvist med det samme)
    #   hrLLM                                   → INTET svar, 90 s timeout
    #   auto                                    → svarer på almindelig chat,
    #     men 0 tool_calls og TOM content på værktøjs-testen (986 ms)
    #
    # `auto` fulgte heller ikke en triviel instruktion: på «Svar præcis: ok»
    # skrev den en forklaring af hvad ordet «ok» betyder.
    #
    # NB om nemotron-3-ultra: den er i forvejen kendt herfra for at FABRIKERE
    # filstier i explore-arbejde (se `agent_runtime_spawn`s kapabilitets-gulv),
    # så den ville være rutet udenom alligevel. Ikke wired.
    # api.navy AFVIST 26/9-2026 — gratis-planen er lukket for ALLE, ikke kun os.
    # Nøglen (`sk-navy-…`) er gyldig og kommer forbi auth; kaldet svarer derefter:
    #
    #   {"error":{"code":"insufficient_plan","type":"permission_error",
    #    "message":"The Free plan is temporarily paused for all users. You can
    #               purchase a plan at https://api.navy/dashboard/billing …"}}
    #
    # Ingen af de 144 modeller svarer — heller ikke de små. Katalogets liste ser
    # fristende ud (claude-opus-5.5, gpt-5.6, grok-4.7, gemini-3.8), og
    # `/v1/models` svarer 200 UDEN nøgle, så udbyderen ligner en åben
    # aggregator. Den er den ikke: modellisten er offentlig, adgangen er ikke.
    #
    # Samme familie som SiliconFlow-afvisningen nedenfor: gratis-fladen findes
    # på papiret og hård-gater i praksis. Forskellen er at navy siger det
    # ligeud i fejlteksten. Prøves igen kun hvis nogen har købt en plan.
    # Ikke wired.
    # AI Horde / stablehorde.net AFVIST 26/9-2026 — ægte gratis, men for langsom
    # og forkert slags modeller. Nøglen virker (`Nickless#539500`, 25 kudos,
    # concurrency 30), og det er et af de få steder der IKKE er en mellemhandler
    # med en regning: netværket er crowdsourced og betales i kudos.
    #
    # MÅLT ende til ende: indsendt job → 28 SEKUNDER til svar, købosition 31 ved
    # start. De øvrige udbydere svarer på 1-3 s. Kudos styrer prioriteten, og 25
    # er i bunden — under belastning bliver det værre, ikke bedre.
    #
    # Og svaret var ubrugeligt: en 3B-model der FORTSATTE teksten i stedet for
    # at svare («, men hvad? Det er jo den, vi»). Af de 29 tekstmodeller online
    # er de fleste roleplay-finetunes (Behemoth, Cydonia, Impish) — samme grund
    # som AionLabs er begrænset ovenfor.
    #
    # Teknisk er den heller ikke en `openai-chat`-post: API'et er asynkront
    # (POST /api/v2/generate/text/async → poll /status/{id}), så den kræver sin
    # egen protokol-adapter. Det kunne bære sig for arbejde hvor 30 s er ligegyldigt
    # — drømme, journal — men ikke for cheap-lane, og adapteren er sin egen opgave.
    # Ikke wired.
    # tu-zi / «Kanin-API» IKKE WIRED 26/9-2026 — kontoen er tom.
    #
    # Registreret, deployet og afprøvet i drift. Første kald svarede:
    #     {"error":{"message":"预扣费额度失败, 用户剩余额度: ＄0.075"}}
    # «forhåndsreservation mislykkedes, brugerens resterende saldo: $0,075».
    # En udbyder der fejler HVERT kald må ikke stå i puljen: balanceren ville
    # bruge et forsøg på den hver gang.
    #
    # Alt andet om den HOLDER, og det er derfor den står her frem for at være
    # slettet — fyldes kontoen op, er det én blok at wire igen:
    #
    #   base_url   https://api.tu-zi.com/v1     (OpenAI-kompatibel, bearer)
    #   nøgle      runtime.json → tuzi_api_key
    #   familie    tredje NewAPI-instans i rækken (x-new-api-version,
    #              x-oneapi-request-id, x-tuzi-route-class). 797 modeller.
    #   svarede    claude-opus-4-5, gpt-5, gemini-2.5-flash,
    #              claude-3-5-haiku-latest. deepseek-v3 og kimi-k2.6 gav tomt.
    #   cost_class paid — og fælden er et ANDET felt end på chinaapi: 213
    #              modeller har `model_ratio: 0`, men kun ÉN af dem har også
    #              `model_price: 0`, og den er ikke en tekstmodel. De øvrige
    #              212 har fast pris pr. kald i `model_price`. På chinaapi var
    #              fælden `quota_type: 1`. Samme software, to felter — hver
    #              konto skal måles for sig.
    #   port       hører i _PUBLIC_PROXY_PROVIDERS: en tredjepart ser prompten
    #              i klartekst uanset hvem der ejer kontoen.
    #
    # ── chinaapi-premium (26/9-2026): frontiermodellerne på Bjørns
    # chinaapi-konto, som EGEN post efter `copilot-premium`-mønstret — høj
    # prioritet, valgt FØRST når betalt er tilladt, og aldrig blandet ind i
    # det almindelige baggrundsarbejde.
    #
    # Bjørn: «lad os nu bruge det ordentligt». Det er dét den her adskillelse
    # er: de store modeller skal kunne vælges MED VILJE, ikke rammes af en
    # daemon der ledte efter noget billigt.
    #
    # Konto uden betalingskort — værst tænkelige er at kaldene begynder at
    # fejle, ikke en regning.
    #
    # PRIS, MÅLT: ét kald til claude-opus-5 med et 16-token-svar flyttede
    # `total_usage` 0,0988 → 0,3568. NB: tallet er et RULLENDE vindue, ikke en
    # kumulativ total — det faldt igen ved næste måling — så det duer som
    # størrelsesorden og ikke som forbrugsmåler. En rigtig samtale med
    # kontekst koster mange gange dette.
    #
    # `deepseek-v4-pro` er udeladt: den svarer ægte «available after topup».
    #
    # RETTET samme aften: jeg udelod ogsaa `gpt-5.5` med begrundelsen «svarede
    # tomt». Det var MIN maalefejl. Jeg proevede med `max_tokens: 16`, og paa en
    # thinking-model gaar hele budgettet til `reasoning_content` — `content`
    # bliver tom, og modellen ser doed ud. Med 800 tokens svarer den «ok».
    #
    # En probe paa 16 tokens kan ikke skelne «virker ikke» fra «taenker».
    # Samme faelde som Ollamas thinking-modeller, i ny forklaedning.
    "chinaapi-premium": {
        "label": "ChinaAPI (frontier, betalt)",
        "priority": 6,
        "base_url": "https://api.chinaapi.ai/v1",
        "auth_kind": "bearer",
        "protocol": "openai-chat",
        "models_endpoint": "/models",
        "rpm_limit": 10,
        "daily_limit": 100,
        "cost_class": "paid",
        "static_models": ["claude-opus-5", "claude-haiku-4-5", "kimi-k3",
                          "gemini-3.8-flash", "gpt-5.5"],
    },
    # nscale: rigtig udbyder, OpenAI-kompatibel, 23 modeller og INGEN gratis —
    # alle har pris. «Free» er $5 engangskredit, derefter pay-as-you-go. Ingen
    # /credits- eller /usage-flade (404), så forbruget kan ikke læses herfra;
    # kreditten løber tør uden varsel. Derfor `cost_class: paid`: den skal
    # gennem den samme port som de øvrige betalte, ikke glide med som gratis.
    # Billigst målt: Qwen3-4B $0,01/$0,03 pr. mio. — $5 rækker ~50 mio tokens.
    # gpt-oss-20b ($0,05/$0,20) svarede på et rigtigt kald.
    "nscale": {
        "label": "nscale (engangskredit)",
        "priority": 86,
        "base_url": "https://inference.api.nscale.com/v1",
        "auth_kind": "bearer",
        "protocol": "openai-chat",
        "models_endpoint": "/models",
        "rpm_limit": 20,
        "daily_limit": 200,
        "cost_class": "paid",
        "static_models": ["Qwen/Qwen3-4B", "openai/gpt-oss-20b"],
    },
    # airforce: free tier FINDES, men den er 1 request/MINUT (1.000/dag,
    # kun basic models). Verificeret konkret: 65 s ventetid → 200, kald igen
    # straks → `rate_limit_exceeded, limit: 1, retry_after 59s`.
    #
    # Mod vores ~440 kald/minut betyder det at den rate-limiteres i næsten
    # hvert forsøg. `rpm_limit: 1` er derfor ikke forsigtighed — det er det
    # ægte tal, og uden det ville balanceren brænde forsøg på den konstant.
    # Prioritet 95 = nederst: den er en reserve, ikke en bane.
    #
    # API'et melder 636 modeller og `tier: free` på de fleste — feltet LYVER:
    # de svarer 402 `paid_model_required`. Kun gpt-oss-20b svarede 200
    # (tre andre gav 429). Deres egen side: 28 free, 588 bag $9,99/md.
    "airforce": {
        "label": "airforce (1 RPM free tier)",
        "priority": 95,
        "base_url": "https://api.airforce/v1",
        "auth_kind": "bearer",
        "protocol": "openai-chat",
        "models_endpoint": "/models",
        "rpm_limit": 1,
        "daily_limit": 1000,
        "cost_class": "free",
        "static_models": ["gpt-oss-20b"],
    },
    # chinaapi: OneAPI/NewAPI-GATEWAY (x-oneapi-request-id, x-new-api-version)
    # — en mellemhandler der videresælger adgang. Ikke vores `agnes`-provider
    # (den peger på apihub.agnes-ai.com). Bjørns egen konto, oprettet 26/9,
    # saldo $1,9990, forbrug $0,0010 over 15 kald, unlimited quota.
    #
    # DEN FÆLDE DER GØR MODELLISTEN KORT: 45 af de 167 modeller står med
    # `model_ratio: 0`, men 38 af dem har `quota_type: 1` — fast pris pr.
    # kald, hvor ratio-feltet intet betyder. Kun `quota_type: 0` +
    # `billing_unit: tokens` er reelt gratis. `static_models` er derfor kun
    # de tre hvor `total_usage` er MÅLT til ikke at flytte sig.
    #
    # Frontiermodellerne svarer også (claude-opus-5, gpt-5.5, kimi-k3,
    # gemini-3.8-flash), men de koster, og cheap-lanen er ikke stedet:
    # «Cheap models may support Jarvis, not define him».
    #
    # PRIVATLIV: prompten går i klartekst gennem deres server uanset hvem der
    # ejer kontoen. Cheap-lanen kører på indhold fra `chat_messages`. Sagt
    # til Bjørn 26/9; hans beslutning.
    "chinaapi": {
        "label": "ChinaAPI (gateway)",
        "priority": 66,
        "base_url": "https://api.chinaapi.ai/v1",
        "auth_kind": "bearer",
        "protocol": "openai-chat",
        "models_endpoint": "/models",
        # Ingen rate-limit-headers set i fire kald i træk. 10 er et
        # konservativt gæt indtil et loft er målt — ikke et tal de har oplyst.
        "rpm_limit": 10,
        "daily_limit": 300,
        "cost_class": "free",
        "static_models": ["agnes-2.5-flash", "agnes-3.0-flash",
                          "stepaudio-3-chat-preview"],
    },
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
        # gemini-pro-latest fjernet 17/9-2026: gratis-kvoten for gemini-3.1-pro er
        # «limit: 0» på begge konti — Google har taget pro ud af gratis-planen.
        # Kaldet 12 gange i døgnet, 0 svar.
        "static_models": ["gemini-flash-latest", "gemini-flash-lite-latest"],
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
        "label": "OpenCode Zen (via klientens lokale server)",
        "priority": 80,
        # IKKE zen-endpointet. Et direkte POST til https://opencode.ai/zen/v1/
        # chat/completions giver 403 FreeTierError — «free tier can only be used
        # from within OpenCode». Gaten er hærdet: målt 27/9-2026 med et FRISK
        # session-id fra klient 1.18.32 gav stadig 403, hvor 17/9-tricket med
        # header-emulering virkede. Klienten selv kommer igennem, så den står som
        # mellemled på 127.0.0.1:4199 (systemd: scripts/opencode-serve.service),
        # og vi taler dens REST-API i stedet for OpenAI-formatet.
        "base_url": "http://127.0.0.1:4199",
        "auth_kind": "bearer",
        # Bevidst IKKE "openai-chat": _OPENAI_COMPATIBLE_PROVIDERS udledes af
        # protocol, og opencode skal have sin egen adapter-gren i stedet for den
        # direkte zen-sti (som ville give 403).
        "protocol": "opencode-server",
        # Ingen dynamisk /models-endpoint i OpenAI-forstand; klientens egen
        # `opencode models` kan liste dem, men den liste er kontobundet (se nedenfor).
        "models_endpoint": "",
        "rpm_limit": None,
        "daily_limit": None,
        # De gratis modeller der svarer fra CONTAINEREN med lanens nøgle
        # (målt 27/9-2026: alle 7 svarede PONG via `opencode run`).
        #
        # Listen er KONTOBUNDET, ikke bare tidsbundet. Bjørns snap-installation
        # viste longcat-2.5-preview-free, space-bunny-free og mimo-v2.6-flash-free
        # — ingen af dem findes her — og omvendt dukkede muse-spark-1.2 op her.
        # Tjek derfor med `opencode models`, og husk ikke listen.
        "static_models": [
            "big-pickle",
            "ling-3.0-flash-fin-free",
            "mimo-v2.5-free",
            "muse-spark-1.2-contributor-free",
            "muse-spark-1.3-contributor-free",
            "nemotron-3-ultra-free",
            "nemotron-3.5-lightning-free",
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
        # 27/9: gemma-4-31b svarer model-not-found og er væk fra /models.
        # /models viser qwen-3.8-27b og gpt-oss-120b, men begge konti svarer 402
        # på begge. Qwen kommer først i poolen efter et vellykket prøvekald.
        "static_models": ["gpt-oss-120b"],
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
        # 27/9: gpt-5.5-free gav 103 model-not-found i træk. coding-glm-5.3-free
        # svarede med både tekst og tool_call på default-profilen til $0.
        "static_models": ["coding-glm-5.3-free", "coding-glm-5.2-free", "coding-minimax-m3-free"],
    },
    "requesty": {
        "label": "Requesty",
        "priority": 52,
        "base_url": "https://router.requesty.ai/v1",
        "auth_kind": "bearer",
        "protocol": "openai-chat",
        "models_endpoint": "/models",
        # Gratis-planen (17/9-2026): 200 kald/døgn og kun ÉT samtidigt kald for en
        # organisation uden saldo («limit scales with your organization's balance»).
        # En hængende forespørgsel holder pladsen i minutter, så rpm holdes lavt.
        # Den gamle konto (og account2) svarede 402 selv på pris-0-modeller: de stod
        # ikke på gratis-planen. novita/tencent/hy3 var betalt. Prøvet én ad gangen:
        # laguna-*, ling-3.0-tiny og nemotron-3-nano findes ikke / 410.
        "rpm_limit": 4,
        "daily_limit": 180,
        "static_models": ["nvidia/nemotron-3-ultra-550b-a55b",
                          "nvidia/nemotron-3-super-120b-a12b",
                          "nvidia/nemotron-3.5-lightning-30b-a3b",
                          "mistral/leanstral-1-5",
                          "google/gemma-4-31b-it"],
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
        # 7/9-2026: `minimax-m3:cloud` er FJERNET. Den stod som gratis siden
        # 24. juli, men gatewayen svarer nu «this model requires a subscription
        # or extra usage» — det samme gør glm-5.2, kimi-k2.7-code og
        # deepseek-v4-*. Kun gemma4 er tilbage på free-tier. En model der
        # returnerer en abonnements-fejl er en død pool-plads, ikke en mulighed.
        "static_models": ["gemma4:31b-cloud"],
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
                          # Nex pro forsvandt fra Kilos live-katalog 27/9.
                          # Ling sante svarede med tekst og tool_call samme dag.
                          "inclusionai/ling-3.0-flash-sante:free",
                          "dots-studio/dots-3-note-preview:free",
                          "poolside/laguna-xs-2.1:free", "stepfun/step-3.7-flash:free",
                          "inclusionai/ling-3.0-flash-fin:free",
                          "nvidia/nemotron-3.5-lightning:free"],
        # tencent/hy3:free fjernet 17/9-2026: «does not exist» på gatewayen.
        # Udeladt 17/9: kilo-auto/free (26,7 s), glm-5.2:free (ingen tool-endpoint),
        # stealth/union-alpha (anonym udbyder bag «stealth» — ukendt hvem der får
        # prompterne), inkling-small (dagsloft).
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
        # 17/9-2026 igen 0 af 13 på to timer (timeouts + 1302 rate limit). Bjørn:
        # «giv zai længere pause». Mindst 2 t efter hver fejl i stedet for 5 min.
        "min_failure_cooldown_s": 7200,
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
    # Dahl (17/9-2026, Bjørn-nøgle i runtime.json som `dahl_api_key`):
    # OpenAI-compat `inference.dahl.global/v1`, bearer. Decentral GPU-pulje
    # («gonka»). MÅLT med nøglen samme dag, ikke læst på deres side:
    #   * /v1/models giver KUN 3 modeller.
    #   * zai-org/GLM-5.3-Flash: «pong» på 1,5 s, kalder værktøjer. Den bedste.
    #   * MiniMaxAI/MiniMax-M2.7: svarer (1,8 s) og kalder værktøjer, men lægger
    #     `<think>`-tekst i selve svaret.
    #   * deepseek-ai/DeepSeek-V4-Flash-0731: 429 «model_concurrency — Paid
    #     accounts are admitted first». Gratis-brugere får den KUN når der er
    #     plads. Den står med, fordi det er den Bjørn fik tilbudt; breakeren
    #     sætter den i karantæne når den 429'er.
    "dahl": {
        "label": "Dahl",
        "priority": 48,
        "base_url": "https://inference.dahl.global/v1",
        "auth_kind": "bearer",
        "protocol": "openai-chat",
        "models_endpoint": "/models",
        "rpm_limit": 20,
        "daily_limit": 2000,
        "cost_class": "free",
        "static_models": [
            "zai-org/GLM-5.3-Flash",
            "MiniMaxAI/MiniMax-M2.7",
            "deepseek-ai/DeepSeek-V4-Flash-0731",
        ],
    },
    # Token Harbor (17/9-2026, nøgle i runtime.json som `tokenharbor_api_key`,
    # kopieret fra repoets .env hvor Jarvis lagde den som
    # JARVIS_TOKENHARBOR_API_KEY). OpenAI-compat `tokenharbor.ai/v1` — IKKE
    # api.tokenharbor.ai (404). 35 modeller; kun `:free` er gratis. MÅLT:
    #   * deepseek-v4-flash:free    «pong» på 23-26 s, kalder værktøjer
    #   * deepseek-v4.1-flash:free  7-54 s, kalder værktøjer
    #   * mimo-v2.5:free            svarer (11 s) men kalder IKKE værktøjer —
    #                               udeladt, et agent-kald ville stå og vente.
    # Langsom: bagerst i køen (priority 72), redundans ikke arbejdshest.
    "tokenharbor": {
        "label": "Token Harbor",
        "priority": 72,
        "base_url": "https://tokenharbor.ai/v1",
        "auth_kind": "bearer",
        "protocol": "openai-chat",
        "models_endpoint": "/models",
        "rpm_limit": 10,
        "daily_limit": 500,
        "cost_class": "free",
        "static_models": [
            "deepseek-v4.1-flash:free",
            "deepseek-v4-flash:free",
        ],
    },
    # ── Fem nye nøgler (Bjørn 17/9-2026, alle i runtime.json). Endpoints fra hans
    # liste; MÅLT samme dag med ét «pong»-kald og ét værktøjskald pr. model. Kun
    # modeller der kaldte værktøjet korrekt er med.
    #
    # Inception (mercury): diffusion-model, den hurtigste vi har — 0,6-1,0 s med
    # værktøjskald. Gratis-kreditter, ikke ubegrænset.
    "inception": {
        "label": "Inception (Mercury)",
        "priority": 44,
        "base_url": "https://api.inceptionlabs.ai/v1",
        "auth_kind": "bearer",
        "protocol": "openai-chat",
        "models_endpoint": "/models",
        "rpm_limit": 20,
        "daily_limit": 500,
        "cost_class": "free",
        "static_models": ["mercury-2", "mercury-2.5"],
    },
    # Poolside: laguna-xs-2.1 kalder værktøjer på 0,8 s. laguna-s-2.1 svarede
    # «jeg har ikke adgang til et værktøj» med værktøjet foran sig → udeladt.
    "poolside": {
        "label": "Poolside",
        "priority": 46,
        "base_url": "https://inference.poolside.ai/v1",
        "auth_kind": "bearer",
        "protocol": "openai-chat",
        "models_endpoint": "/models",
        "rpm_limit": 20,
        "daily_limit": 500,
        "cost_class": "free",
        "static_models": ["poolside/laguna-xs-2.1"],
    },
    # ChatAnywhere: gratis-nøglen har DAGLIGE lofter pr. model (de mindste er de
    # rummeligste), så kun mini/nano + deepseek-v4-flash. gpt-5-mini kaldte også
    # værktøjer, men dens gratis-loft er lille. Alle fire: værktøjer på 1,6-2,7 s.
    "chatanywhere": {
        "label": "ChatAnywhere",
        "priority": 50,
        "base_url": "https://api.chatanywhere.tech/v1",
        "auth_kind": "bearer",
        "protocol": "openai-chat",
        "models_endpoint": "/models",
        "rpm_limit": 10,
        "daily_limit": 200,
        "cost_class": "free",
        "static_models": ["gpt-4.1-mini", "gpt-4o-mini", "gpt-4.1-nano", "deepseek-v4-flash"],
    },
    # Intern AI 书生 (Shanghai AI Lab): 10 RPM, nøglen gælder 6 måneder (udløber
    # ca. marts 2027). intern-latest skrev «Thinking Process» i svaret → udeladt.
    "internlm": {
        "label": "Intern AI",
        "priority": 56,
        "base_url": "https://chat.intern-ai.org.cn/api/v1",
        "auth_kind": "bearer",
        "protocol": "openai-chat",
        "models_endpoint": "/models",
        "rpm_limit": 8,
        "daily_limit": 500,
        "cost_class": "free",
        "static_models": ["intern-s2", "intern-s1-mini"],
    },
    # Agnes AI: gratis-brugere har et stramt rate limit (agnes-2.0-flash gav 429
    # under målingen). agnes-2.5-pro kræver saldo. 3.0-flash 6,8 s, 2.5-flash 15 s.
    "agnes": {
        "label": "Agnes AI",
        "priority": 64,
        "base_url": "https://apihub.agnes-ai.com/v1",
        "auth_kind": "bearer",
        "protocol": "openai-chat",
        "models_endpoint": "/models",
        "rpm_limit": 4,
        "daily_limit": 200,
        "cost_class": "free",
        "static_models": ["agnes-3.0-flash", "agnes-2.5-flash"],
    },
    # MegaNova (17/9-2026, nøgle i runtime.json som `meganova_api_key`): OpenAI-compat
    # api.meganova.ai/v1. Seks tekstmodeller er mærket «free», de fleste rollespil.
    # MÅLT: Mistral-Small-3.2-24B «pong» 0,5 s + værktøjskald 1,1 s. Udeladt:
    # manta-mini/flash (svarer, men kalder IKKE værktøjer), manta-pro og
    # GLM-4.7-Flash (403 «not available for your current tier»).
    "meganova": {
        "label": "MegaNova",
        "priority": 47,
        "base_url": "https://api.meganova.ai/v1",
        "auth_kind": "bearer",
        "protocol": "openai-chat",
        "models_endpoint": "/models",
        "rpm_limit": 10,
        "daily_limit": 500,
        "cost_class": "free",
        "static_models": ["mistralai/Mistral-Small-3.2-24B-Instruct-2506"],
    },
    # OrcaRouter: gratis-modellerne kræver en GitHub-konto koblet til
    # arbejdsområdet («a newly created GitHub account does not qualify»). Koblet
    # 17/9-2026; derefter værktøjskald MÅLT: deepseek-v4-flash-free 2,0 s,
    # hy3-free 2,1 s, glm-5.3-flash-free 6,6 s. Udeladt: orcarouter/free
    # («allowance is used up»), orcaverify (klassifikator, ikke chat),
    # stealth/union-alpha-free (anonym udbyder).
    "orcarouter": {
        "label": "OrcaRouter",
        "priority": 49,
        "base_url": "https://api.orcarouter.ai/v1",
        "auth_kind": "bearer",
        "protocol": "openai-chat",
        "models_endpoint": "/models",
        "rpm_limit": 10,
        "daily_limit": 500,
        "cost_class": "free",
        "static_models": ["deepseek/deepseek-v4-flash-free", "tencent/hy3-free",
                          "z-ai/glm-5.3-flash-free"],
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
        # claude-sonnet-4.6 + gemini-3.1-pro-preview fjernet 17/9-2026: «not
        # available for integrator» — ugeprøven slog dem fra 14/9, men kataloget
        # lagde dem ind igen.
        "static_models": ["claude-sonnet-5", "gpt-5.4"],
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
