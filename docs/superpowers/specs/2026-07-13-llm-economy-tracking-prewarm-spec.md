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

### WS2 — Sandt cost-regnskab (`cost_usd` + komplet logging)
**Filer:** hvor `costs`-rækker skrives (chokepoint i cheap/visible-lanes), + en pris-tabel.

- **Central pris-tabel** (`core/services/llm_pricing.py`, ny): pr. (provider, model) → dict med
  `cache_hit`, `cache_miss`, `output` USD/token. DeepSeek v4-flash: 0.0028/0.14/0.28 per M.
  v4-pro: 0.003625/0.435/0.87. Legacy `deepseek-chat`: dens *faktiske* legacy-priser (verificér mod
  api-docs.deepseek.com). Off-peak-multiplikator (16:30–00:30 GMT) hvis kaldet faldt der.
- **Beregn `cost_usd` ved skrivning:** `cost_usd = cache_hit*hit + cache_miss*miss + output*out`
  (× off-peak-faktor). Bagud-fyld ikke gamle rækker — kun fremad.
- **Komplet logging:** audit ALLE deepseek-kaldssteder (grep efter deepseek-provider-kald) og sikr
  at HVERT kald skriver en `costs`-række. Reasoner/thinking-kald må ikke slippe uden om.
  Verifikations-mål: `sum(cost_usd)` for en periode ≈ DeepSeek-saldo-delta (±15%).
- **Test:** unit på pris-beregning (kendte tokens → kendt $). Reconciliation-test: en dags
  logget cost_usd matcher saldo-delta inden for tolerance.

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

### WS5 — Model-tiering: skarpere Jarvis (visible → v4-pro), bulk på flash
- **Visible/primary-lane → `deepseek-v4-pro`** (SWE-Bench 80,6% / LiveCodeBench 93,5 — mærkbart
  skarpere Jarvis). Lav-volumen → lille absolut merpris; passer i eksisterende $100.
- **Warmer + cheap-lane daemons + prewarm → bliver på `v4-flash`** (billig, 99% cache).
- Styres via runtime-state (per-lane model-map), ikke hardcode — så det kan rulles tilbage uden deploy.
- **Test:** lane→model-mapping enhedstestet; live: visible-svar bruger v4-pro (verificér via `costs.model`).
  Watch $/dag i `jc cost` i 1 uge efter flip; rul tilbage hvis det overstiger budget.

### WS6 — Off-peak/batch for ikke-realtids daemon-arbejde
- De ikke-realtids cheap-lane-job (refleksion, konsolidering, tests, teknisk-gæld-analyse) rutes til
  DeepSeek **off-peak** (16:30–00:30 GMT, 50–75% rabat) via en kø der udskyder ikke-hastende
  daemon-kald til vinduet. Realtid (visible/samtale) rammer aldrig køen.
- **Test:** kø udskyder korrekt; realtid omgår køen; off-peak-faktor afspejles i `cost_usd`.

### WS7 — Skær død vægt (abonnementer)
- **Cut GitHub Copilot Pro (90 kr)** — 2 kald i juli. **Cut ChatGPT (179 kr)** — ikke i loggen.
  Ingen kode; Bjørn afmelder. Spar 269 kr, nul tab. (GLM Coding Plan er UDE — ToS forbyder
  3.-parts/runtime-brug; kun coding-værktøjer.)

---

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
WS4 (deadline 24/7) og WS1 (runaway) først. Så WS2+WS3 (sandhed/synlighed). DERNÆST WS5 (tiering)
— for tallene skal være ærlige før vi tør flippe til Pro. WS6+WS7 sidst.
