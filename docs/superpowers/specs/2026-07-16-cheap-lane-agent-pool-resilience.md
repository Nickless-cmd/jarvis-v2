# Cheap-lane + Agent-pool Resilience: "Den ubrydelige gratis-pool"

**Dato:** 2026-07-16
**Status:** Design — afventer Bjørns review
**Forfatter:** Claude (Opus 4.8) sammen med Bjørn

## Mål (én sætning)
Løfte Jarvis' gratis LLM-kraft markant ved at (a) auto-aktivere flere gratis-nøgle-konti,
(b) lære hver slots kvote og proaktivt rotere, og (c) lade cheap-lane-poolen overtage efter
ollama på alle ikke-visible runs — så det autonome loop kan køre uden at bryde og degradere
pænt til floor i værste fald.

## Kontekst / hvad findes allerede
Vi bygger PÅ eksisterende infrastruktur, ikke fra bunden:
- **`core/services/cheap_lane_balancer.py`** — taktisk lag. Har allerede `Slot(provider, model,
  auth_profile, rpm_limit, daily_limit)` + `SlotState(daily_use_count, daily_window_start,
  cooldown_until, breaker_level 0/1/2/3)`. Spreder trafik over slots; **reaktiv** daglig-kvote-
  læring fra 429. Slots læses i dag fra `provider_router.json`.
- **`core/services/central_router_adapt.py`** — strategisk/lært lag. `resolve_autonomous_model`
  (autonom→ollama, hard-guard mod betalt deepseek), lært præference + health-gate (`_HEALTH_FLOOR`).
- **`core/services/cheap_provider_runtime_selection.py`** — `execute_cheap_lane_via_pool`,
  `select_cheap_lane_target`, per-provider failover, `runtime.cheap_lane_exhausted`-event.
- **`core/services/cheap_provider_runtime_adapters.py`** — `CHEAP_PROVIDER_DEFAULTS` (30 providers),
  `provider_auth_ready`, `provider_runtime_defaults`.
- **Auth-profiler** — `~/.jarvis-v2/auth/profiles/<profil>/providers/<provider>/credentials.json`.
  I dag bruges kun `default`. `account2` (kærestens nøgler) er gemt men **inaktiv** (balanceren
  scanner ikke profiler → slots findes ikke).

**Ground truth (16.jul, testet):** ~14 providers virker på `default`, 9 arbejdsheste virker på
`account2` (groq/mistral/cohere/cerebras/huggingface/aihubmix/reka/requesty/opencode). gemini/
openrouter/cloudflare/ollamafreeapi = gyldige nøgler, kun forkert model-navn/base_url i config.

## Arbejdsdeling (Bjørns princip)
- **load_balancer = taktisk:** slot-health, cooldown, breaker, daglig-tæller, valg af næste sunde slot NU.
- **central router = strategisk/lært:** adaptiv kvote-model (hvad ER hver slots grænse?), prædiktiv
  fordeling, health-gate, lært præference. Fortæller balanceren HVORDAN den bør fordele over tid.

---

## Design

### WS1 — Multi-profil auto-aktivering (kernen i "starter automatisk")
**Krav (Bjørn):** drop en nøgle i en ny profil → den er live næste tick, ingen kode-deploy.

- Ny slot-kilde: udover `provider_router.json` **scanner balanceren `auth/profiles/*/providers/*/`**
  og danner en `Slot` pr. (provider, auth_profile) hvor `provider_auth_ready(provider, profil)`
  er True OG provideren er i `CHEAP_PROVIDER_DEFAULTS` med `routable=True`, `cost_class!=paid`.
- `slot_id` = `f"{provider}:{model}:{auth_profile}"` (auth_profile er ALLEREDE i `Slot` — minimal ændring).
- Keyless providers (pollinations/ovhcloud/ollamafreeapi/arko) danner én slot (profil "default").
- Resultat: `default` + `account2` (+ fremtidige `account3…`) bliver hver til selvstændige slots →
  ~2× (skalérbart til N×) kapacitet, fuldautomatisk når nøgler lander.
- **Værn:** en slot uden gyldig cred materialiseres aldrig (fail-closed). Scanning er cachet (TTL
  ~60s) så hot-path ikke rammer filsystemet hvert kald.

### WS2 — Adaptiv kvote-model (reaktiv → prædiktiv)
**Krav (Bjørn):** efter et par 429'ere skal systemet LÆRE hver slots kvote og proaktivt rotere,
så vi ikke konstant jagter døde/stale udbydere.

- Udvid `SlotState` med en **lært kvote-profil**: observeret `rpm_observed`, `daily_observed`,
  `last_429_at`, `429_count_window`, og en estimeret `reset_at` (fra `retry-after`-header når den
  findes, ellers heuristik: RPM=rullende 60s-vindue, daily=UTC-døgn).
- **Prædiktiv gate (central router):** før en slot vælges, beregn `predicted_available =
  daily_observed - daily_use_count > margin` OG `rpm_window_room > 0`. Slots uden hovedrum
  **springes over proaktivt** (ikke prøves-og-fejles).
- **Læring:** hver 429 opdaterer `daily_observed = min(nuværende estimat, daily_use_count)` →
  konvergerer mod den reelle grænse over få hændelser. Kendte config-grænser
  (`CHEAP_PROVIDER_DEFAULTS[x].daily_limit/rpm_limit`) er startgæt; observation overstyrer.
- **Anti-jag:** en slot der har fejlet N gange inden for M minutter får eskalerende breaker
  (eksisterende `breaker_level` 5min→15min→1h) OG markeres `stale` → central router afprioriterer
  den til næste døgn-reset. Ingen konstant genforsøg på døde udbydere.

### WS3 — ollama → cheap-lane fallback (rygraden)
**Krav (Bjørn):** cheap-lane overtager efter ollama på autonome runs; gælder ALLE ikke-visible kald.

- `resolve_autonomous_model` (allerede: autonom→ollama `deepseek-v4-flash:cloud`) suppleres med en
  **eksekverings-fallback**: når ollama-kaldet fejler (kvote/timeout/5xx) i den autonome/daemon-
  eksekvering → kald `execute_cheap_lane_via_pool` (roterende gratis-slots via WS1/WS2) → floor.
- **Visible lane RØRES IKKE** (Bjørn Q1): dine egne chats forbliver ren deepseek (betalt kvalitet),
  ingen cheap-fallback. Fallback gælder autonome runs, agent-pool, daemoner, relevance, indre-liv.
- Genbrug den fikse `pick_failover_target` (nu ollama, ikke betalt deepseek) hvor relevant.

### WS4 — Agent-pool deler samme sunde pool
- `agent_pool_router` / dispatch-agenter trækker fra **samme slot-registry + cooldown/kvote-model**
  som cheap-lane → arver robusthed + auto-aktivering gratis. Ingen separat pool-logik.
- Bevar eksisterende agent-floor (keyless gratis, jf. tidligere fix) som nederste sikkerhed.

### WS5 — Config-fixes (gratis kapacitet, ingen nøgler)
Rene katalog/base_url-rettelser der låser gyldige-men-fejlkonfigurerede providers op:
- **gemini** — korrekt nuværende model-navn (fx `gemini-2.0-flash-exp`); nøgle (`AQ.`-format) er gyldig.
- **openrouter** — pålidelig `:free`-model (fx en verificeret gratis-model, ikke den der 404'er).
- **cloudflare** — byg URL med `account_id` (creds har `api_key` + `account_id`).
- **ollamafreeapi** — ret base_url (`/chat/completions` malformed i dag).
- Verificér hver med et rigtigt inferens-kald (samme harness som 16.jul-testen).

### WS6 — Rotation-politik (Bjørn Q2: priority + cooldown)
- Vælg højeste-priority sunde slot; rotér KUN væk ved fejl/kvote/cooldown.
- **Round-robin inden for samme priority-tier** for at sprede kvote-brug jævnt mellem ligeværdige
  slots (fx groq:default og groq:account2).

## Ikke-mål (YAGNI)
- Ingen cheap-fallback på visible lane.
- Ingen betalt-provider i baggrund (deepseek KUN visible — allerede håndhævet).
- Ingen ny UI; observabilitet via eksisterende Central-nerver + `/cheap-balancer-state`.

## Acceptance ("loopet der ikke bryder")
1. Med ≥2 profiler aktive: dræb (cooldown) alle slots for én provider → autonome runs fortsætter
   på andre providers uden fejl.
2. Simulér 429 på en slot N gange → central router afprioriterer den proaktivt; ingen gentagne
   forsøg på den døde slot i cooldown-vinduet.
3. ollama-kvote tømt → autonomt run completer via cheap-lane (ikke `failed`).
4. Drop en ny profils nøgle → den bliver valgt inden for TTL uden genstart.
5. Visible lane uændret (deepseek) under alt ovenstående.
6. `record_cost` viser $0 for de gratis fallbacks; ingen betalt-lane-pres.

## Test-strategi
- Unit: slot-scanning (WS1), kvote-læring/prædiktiv gate (WS2), fallback-kæde (WS3) — alle med
  mockede provider-svar (429/timeout/ok). Følg `test_<modul>.py`-konvention.
- Integration: acceptance-scenarier 1-6 mod isoleret runtime.
- Live-verifikation: config-fixes (WS5) mod containeren; provider-sweep som 16.jul.

## Risici
- **Filsystem-scan hot-path** → cache med TTL (WS1).
- **Fejllært kvote for lav** → observation bruger `min()` og re-læres efter døgn-reset; kendt
  config-grænse som floor.
- **Deploy-divergens** (container ≠ HEAD) → følg kirurgisk deploy-ritual (commit→push origin→
  reset --hard→genstart), verificér HEAD.
