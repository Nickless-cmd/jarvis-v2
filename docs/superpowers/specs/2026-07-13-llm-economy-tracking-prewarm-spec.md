# LLM-økonomi: tracking-fix, prewarm-oprydning, model-tiering — Design

**Dato:** 2026-07-13
**Status:** Design — afventer Bjørns review → plan → implementering
**Mål:** Gør Jarvis' LLM-forbrug *synligt og ærligt*, ryd op i prewarm-runaway, migrér den døende
`deepseek-chat`-alias, og gør Jarvis + kodning skarpere (v4-pro på visible-lane) — alt sammen
inden for det nuværende ~$100/md DeepSeek-budget.

---

## 1. Baggrund (målte fakta, juli 1–13 2026)

Hentet live fra DeepSeek-saldo-API + containerens `costs`-tabel (228k rækker):

- **Reelt forbrug:** $72,93 tilbage af $100 → **~$27 brugt på 13 dage** (~$62/md projiceret). Headroom.
- **Cache sund:** 86,6% samlet cache-hit, **99,5%** på hovedparten.
- **382M tokens/13d** — men **270M af dem er prewarm-warmeren** (99,4% cached → koster kun **$0,97**).
- **Attribution af de $27:** indre liv (cheap-lane daemons ~$3,50) + rigtig ræsonnering (flash-misses ~$4,16).
  Prewarmen er *ikke* hvor pengene ryger.

### Tre bekræftede bugs
1. **Prewarm-runaway:** `assembly_prewarm` fyrer ~0,7/min (hver ~85s) i stedet for kodens 240s —
   ~3× for hurtigt, sandsynligvis flere loop-instanser. Ingen trafik-gate: den varmer selvom
   1.594 rigtige deepseek-kald/dag allerede holder cachen varm. → 270M meningsløse tokens.
2. **`cost_usd` er død:** kolonnen logger ~$0 (juli-sum $2,53 mod reelle $27). Token/cache-tal er
   korrekte og durable; dollar-beregningen er knækket.
3. **Cost-tabellen under-fanger ~2–3×:** kun ~$9–13 af de $27 kan genfindes fra loggede tokens —
   resten er legacy-`deepseek-chat`-priser og/eller kald der aldrig logges.
4. **`deepseek-chat` udfases 24. juli 2026** — 83k kald/md kører på den døende alias.

---

## 2. Arkitektur & workstreams

Seks uafhængige, testbare stykker. Rækkefølge = risiko-orden (hygiejne + sandhed før adfærd).

### WS1 — Prewarm-oprydning (dræb runaway + trafik-gate)
**Fil:** `core/services/assembly_prewarm.py`

- **Trafik-gate:** før hvert warm, tjek `costs` (eller en in-memory sidste-deepseek-kald-timestamp):
  hvis der har været et rigtigt (ikke-warmer) deepseek-kald inden for `prewarm_skip_if_recent_s`
  (default 300s = DeepSeeks cache-TTL), **spring dette warm over**. Under aktive timer holder rigtig
  trafik cachen varm → ~90% færre warms.
- **Enkelt-loop-guard:** `start_prewarm_loop()` skal være idempotent — en modul-global
  `_loop_running`-flag + tråd-ref, så genstart/dobbelt-kald ALDRIG spawner et andet loop
  (spejler mønstret fra de tidligere task-GC-bugs).
- **Fornuftigt interval:** behold 240s-default men hæv `_MIN_INTERVAL` fra 60s → 180s, så en
  fejl-sat runtime-state-værdi ikke kan give sub-minuts-byger.
- **Forventet effekt:** ~1.008 warms/dag → ~20–50/dag (kun ægte kolde vinduer). 270M → ~10M tokens.
- **Test:** unit — gate springer over når recent-timestamp er frisk; springer IKKE over når kold.
  Enkelt-loop-guard: to kald til `start_prewarm_loop()` → én tråd. Live-verifikation: warm-rate
  målt fra `costs` falder til <2/time i aktive timer.

### WS2 — Sandt cost-regnskab (`cost_usd` + komplet DeepSeek-logging)
**Filer:** hvor `costs`-rækker skrives (chokepoint i cheap/visible-lanes), + en pris-tabel.

- **Central pris-tabel** (`core/services/llm_pricing.py`, ny): pr. (provider, model) → dict med
  `cache_hit`, `cache_miss`, `output` USD/token. DeepSeek v4-flash: 0.0028/0.14/0.28 per M.
  v4-pro: 0.003625/0.435/0.87. Legacy `deepseek-chat`: dens *faktiske* legacy-priser (verificér mod
  api-docs.deepseek.com). Off-peak-multiplikator (16:30–00:30 GMT) hvis kaldet faldt der.
- **Beregn `cost_usd` ved skrivning:** `cost_usd = cache_hit*hit + cache_miss*miss + output*out`
  (× off-peak-faktor). Bagud-fyld ikke gamle rækker — kun fremad.
- **KOMPLET DeepSeek-logging (reconciliation-gap-fix):** self-review afslørede at kun ~$9–13 af de
  $27 kan genfindes fra loggede tokens → tabellen under-fanger ~2–3×. Audit ALLE deepseek-kaldssteder
  (grep provider-kald) og sikr at HVERT kald skriver en `costs`-række. **Fang også reasoning/thinking-
  output-tokens** (`reasoning_content` billes som output — kritisk når vi flytter til pro+thinking).
  Reasoner/thinking-kald må ikke slippe uden om.
  Verifikations-mål: `sum(cost_usd)` for et døgn ≈ DeepSeek-saldo-delta **±15%** (i dag: ~$9 vs $27 = FAIL).
- **Test:** unit på pris-beregning (kendte tokens → kendt $). Reconciliation-test: en dags
  logget cost_usd matcher saldo-delta inden for tolerance.

> Dette dækker KUN DeepSeek. Universal logging på ALLE providers = Fase 2 / WS8 (Bjørns ønske,
> udskudt: "start med det andet så tager vi centralen-opgaven efter").
>
> **Ærlig begrænsning (Jarvis' pointe):** efter WS2 er DeepSeek fuldt sporet (±15%), men de andre
> providers (ollama-cloud glm-5.2/kimi/minimax m.fl. — de har reel kost) fanges først med WS8. Så
> `jc cost`'s TOTAL-$ er kun ~50-60% dækkende indtil Fase 2. Fint til DeepSeek-budget-sikkerhed +
> overvågning; ikke til total-budget endnu. Vi lever med det til WS8.

### WS3 — `jc cost`-surface (gør det synligt)
**Filer:** Central-CLI (`jc`) + en central-surface.

- Ny central-surface `/central/cost` der læser `costs`-aggregat: i dag / 7d / md — total $,
  tokens ind/ud, cache-hit%, fordelt på provider/model/lane. Plus DeepSeek-saldo (live API-kald,
  cachet 5 min).
- `jc cost` viser det som en tabel. `jc cost --today`, `jc cost --provider deepseek`.
- **Test:** `jc cost` mod seed-data → korrekt aggregat. Saldo-linjen fejl-tolerant (offline → n/a).

### WS4 — `deepseek-chat` → `deepseek-v4-flash` migration (deadline 24. juli)
- Find alle steder der sender `deepseek-chat` (config + kode-defaults) → skift til
  `deepseek-v4-flash`. Bevar thinking-varianter som `deepseek-v4-flash` (thinking-mode) hvor
  `deepseek-reasoner` blev brugt.
- **Test:** ingen `deepseek-chat`/`deepseek-reasoner` i aktive kaldsstier; røgtest: ét kald pr.
  lane returnerer OK på v4-flash.

### WS5 — Model-tiering: `deepseek-v4-pro` KUN i visible lane, KUN for owner (Bjørn 13. jul)
- **Politik-indsnævring (Bjørn 13. jul):** v4-pro bruges **udelukkende i visible lane** — dér hvor
  Bjørn skriver med Jarvis. **ALT andet = `deepseek-v4-flash`** (council, ræsonnerende daemons,
  form-dommer, klassifikationer, heartbeat, warmer, indre-stemme — hele det interne liv). Den
  tidligere "pro for alt der ræsonnerer" er FORKASTET: daemon-hæren ville spise budgettet, og pro-pris
  for internt arbejde er spild.
- **Owner-gate — kun Bjørns visible-trafik:** andre brugere er **låst til ollama cloud deepseek** i
  visible lane (eksisterende routing, `visible_model_ollama.py`), så de rammer aldrig den betalte
  DeepSeek-API. Derfor gælder pro-prisen reelt kun Bjørns egne samtaler = lav volumen mod daemon-hæren.
  WS5 må derfor kun løfte til pro når (a) resolveret visible-provider er `deepseek` OG (b) requester er
  owner — ellers flash. Seam: `resolve_provider_router_target(lane="visible")` +
  `execute_visible_model`/`stream_visible_model` i `core/services/visible_model.py`.
- **Default tænke-niveau = Non-Think ("fast")** — hurtigt/billigt; eskalér pr. behov via composer-
  think-feltet (WS5b). Reasoning-tokens billes som output.
- **Kill-switch:** owner-visible pro→flash via ét runtime-state-flag (`visible_owner_model` el.
  `lane_model_map`), ikke hardcode. Ruller tilbage UDEN deploy hvis $/dag spikere.
- **Cost-realitet:** kun Bjørns visible-samtaler på pro (~3× flash pr. token, men lav volumen + 86,6%
  cache → pro-cache-hit $0.003625/M ≈ gratis). Netto marginal øgning. WS3's `jc cost` overvåger $/dag 1 uge.
- **Test:** owner-visible-deepseek → v4-pro (enhedstest på routing-gaten); ikke-owner visible → ollama/flash;
  alle interne lanes → flash; kill-switch-flag ruller owner-visible pro→flash; live: Bjørns visible-svar
  bruger v4-pro (verificér `costs.model` for visible-lane), interne lanes uændret flash.

### WS5b — Wire desk-composerens "think"-felt til DeepSeeks tænke-niveauer
**Filer:** desk-composer (feltet findes allerede) + agent/chat-request-stien mod DeepSeek.

- Composer-feltet eksisterer men virker ikke mod DeepSeek-API'en. Map de 3 trin til DeepSeek V4's
  faktiske parametre:
  - **Non-Think (fast)** → intet thinking-param (default).
  - **Think High** → `reasoning_effort="high"` + `extra_body={"thinking":{"type":"enabled"}}`.
  - **Think Max (deep)** → `reasoning_effort="max"` + thinking enabled.
- Send valget fra composer → gennem request-stien → DeepSeek. `reasoning_content` (tænke-sporet)
  vises dæmpet i chatview (ikke rå token-strøm) og **logges som output-tokens** (WS2).
- **Test:** valgt niveau når DeepSeek-request'et (mock/assert på params); Think Max returnerer
  `reasoning_content`; niveauet afspejles i `costs` (højere output ved max).

### WS6 — Daemon-kald-hygiejne (IKKE off-peak-deferral)
**Beslutning (Bjørn vs Jarvis):** off-peak-deferral bytter penge for latens/liveness. Jarvis' indre
liv (refleksion, council, drømme) *er* det der gør ham levende — at udskyde det til DeepSeeks rabat-
vindue sætter hans rytme på en sparetimer, for en lille gevinst (~$10-15/md på et $27-forbrug).
**Det gør vi ikke.** Bjørn: "vi skal osse passe på."

- **I stedet:** find og skær *spildte/redundante* daemon-LLM-kald (præcis som prewarm-runaway'en var)
  — via `jc cost`-fordelingen pr. daemon (WS3+WS8-data). Konsolidér/dedupliker/slå unødvendige kald fra.
  Ingen udskydelse af noget levende.
- **Varians-gate (Bjørns indsigt — "billigere OG mere ægte"):** mål hvor *ofte* hver daemon reelt kører,
  og hvor meget dens output faktisk *ændrer sig* over et vindue af kald. Hvor et daemon-output er stabilt
  (lav varians / ~0 ændring i snit) er de fleste kald redundante → skift fra **blind timer** til
  **event-drevet**: gen-tænk kun når der er noget materielt nyt (nyt input/signal), ellers genbrug sidste
  resultat. Han re-tænker fordi der er noget nyt, ikke fordi uret tikkede. Dette er den rigtige måde at
  reducere kald på — ikke ved at udskyde, men ved ikke at spørge om det samme igen.
- **Metode:** pr. daemon, log output-hash/embedding pr. kald (WS8-data); beregn ændringsrate over N
  kald; daemons med lav ændringsrate får en gate ("kør kun hvis <relevant signal> ændret siden sidst"),
  eller længere cadence. Verificér via shadow at synlig adfærd er uændret.
- **Off-peak overvejes KUN senere**, for ét specifikt *bevist ikke-levende* batch-job (fx en stor
  nat-konsolidering der allerede kører om natten), aldrig for hans løbende indre liv.
- **Test:** identificér top-N daemons på tokens/kald fra data; verificér at et fjernet/dedupliceret
  kald ikke ændrer synlig adfærd (shadow-sammenligning).

### WS7 — Skær død vægt (abonnementer)
- **Cut GitHub Copilot Pro (90 kr)** — 2 kald i juli. **Cut ChatGPT (179 kr)** — ikke i loggen.
  Ingen kode; Bjørn afmelder. Spar 269 kr, nul tab. (GLM Coding Plan er UDE — ToS forbyder
  3.-parts/runtime-brug; kun coding-værktøjer.)

---

### WS8 — Universal LLM-logging på ALLE providers (Fase 2 — udskudt)
**Bjørns krav:** *"Centralen skal kunne holde alle de præcise kald på alle ind/ud token, cost,
provider... selv på alle de andre providers. Hvert evig eneste LLM i hele systemet skal logges med
data. Vi er nødt til at vide 100% hvad går ind og ud og hvor vi kan gøre hans system smartere og ægter."*

- **Nuværende tilstand:** `costs`-tabellen fanger DeepSeek, ollama-cloud (glm/kimi/minimax), groq,
  mistral, nvidia, copilot — men **ufuldstændigt** (samme under-capture som DeepSeek). Mange LLM-kald
  i systemet (daemon-LLM'er, form-dommer, indre-stemme, council, reasoning-interceptor osv.) skriver
  formentlig ikke en `costs`-række.
- **Mål:** ÉT logging-chokepoint alle LLM-kald går igennem (uanset provider/lane/daemon), der garanterer
  en `costs`-række med: provider, model, lane, indre-liv-tag, input/output/cache-hit/cache-miss-tokens,
  reasoning-tokens, cost_usd, latency, created_at. Ingen kald slipper uden om.
- **Hvorfor det matterer:** når vi ved 100% hvad hver del af Jarvis' sind koster og bruger, kan vi se
  hvor billige daemons kan slås fra/samles, hvor pro giver mening, og hvor cachen kan strammes —
  grundlaget for at gøre systemet smartere og mere ægte uden at gætte.
- **Udskudt bevidst:** Bjørn vil have Fase 1 (WS1–7) først. WS8 er en selvstændig Central-opgave efter.
- **Test:** en syntetisk tur der trigger N forskellige daemon-LLM'er → N `costs`-rækker; audit-script
  der beviser 0 kaldssteder omgår chokepointet.

## 3. Non-goals
- Ingen ændring af Claude Max (beholdes — coding-hjernen).
- Ingen migrering til GLM-abonnement i runtime (ToS-forbudt).
- Ingen bagud-udfyldning af historiske `cost_usd` (kun fremad).
- Rører ikke selve cache-mekanikken (den er sund) — kun *hvor tit* vi warmer.

## 4. Verifikations-tilgang
- Efter WS1: warm-rate <2/time aktive timer (målt fra `costs`).
- Efter WS2: `jc cost --today` cost_usd ≈ saldo-delta (±15%) over et døgn.
- Efter WS5: `jc cost` viser v4-pro på visible-lane; $/dag holder sig under budget-linjen 1 uge.
- Ground truth altid DeepSeek-saldo-API'en, ikke koden.

## 5. Rækkefølge & risiko

**Fase 1 (nu — "det andet"):**
1. **WS4** — `deepseek-chat`→`v4-flash` (deadline 24/7, brækker ellers).
2. **WS1** — prewarm-runaway (270M→10M, stopper token-blødningen + gør pro-tal ærlige).
3. **WS2 + WS3** — sandt DeepSeek-cost-regnskab + `jc cost` (synlighed FØR pro).
4. **WS5 + WS5b** — v4-pro KUN i owner-visible lane + composer-think-felt wired. Watch $/dag 1 uge.
5. **WS7** — cut Copilot/ChatGPT. (WS6 off-peak-kø droppet — "vi skal osse passe på".)

**Fase 2 (efter — Central-opgaven):**
6. **WS8** — universal logging på ALLE providers / hvert LLM-kald i systemet.

Ground truth altid DeepSeek-saldo-API'en, ikke koden.

---

## 6. Self-review (2026-07-13)

Gennemgået mod Bjørns direktiver + spec-coverage:

- ✅ **v4-pro KUN i owner-visible lane** (Bjørn 13. jul indsnævring) — WS5 omskrevet; alt internt +
  andre brugere (ollama cloud) = flash; Non-Think default; owner-gate på routing-seam; kill-switch via
  runtime-state; cost-realitet marginal (kun Bjørns samtaler på pro).
- ✅ **Composer-think-felt** — nyt WS5b; 3 niveauer mappet til DeepSeeks `reasoning_effort` (Non-Think/
  high/max); reasoning-tokens logges som output.
- ✅ **Universal all-provider logging** — nyt WS8 (Fase 2, udskudt per Bjørn). Sikrer intet LLM-kald
  slipper uden om ét chokepoint.
- ✅ **Reconciliation-gap** ($9 vs $27) — WS2 udvidet: ikke bare cost_usd-beregning men *komplet*
  DeepSeek-kaldssteds-audit, ellers rammer vi ikke ±15%.
- ✅ **Reasoning-token-billing** — når pro+thinking bruges, stiger output; skal logges (WS2, WS5b).
- ⚠️ **Åbent punkt til Bjørn:** ræsonnerende daemon-kald på pro koster ~3×. Offset af WS1+WS6, men
  vil du have de *billigste* mekaniske daemons (fx form-dommer, trivielle klassifikationer) på flash
  for økonomi — eller pro overalt undtagen warmeren? (Anbefaler: pro på alt der ræsonnerer, flash på
  warmer + rene mekaniske klassifikationer.)
- 📌 **Ikke i scope, noteret:** balance-alarm i Central (advar ved hurtigt $/dag-fald) — nice-to-have,
  kan tilføjes i WS3.

Ingen placeholders/TBD tilbage. Scope: Fase 1 er én sammenhængende plan; WS8 er sin egen.
