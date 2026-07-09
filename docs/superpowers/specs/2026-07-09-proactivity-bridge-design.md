# Proaktivitets-broen — design

**Dato:** 2026-07-09
**Status:** Godkendt (design)
**Sub-projekt:** 1 af 2 (Agent Smith = repetitions-/selv-lighed-kritiker er #2, bygges bagefter).

## Baggrund

Jarvis' egen read-only-diagnose (9. jul): hans indre spørgsmål, initiativer og undren når **aldrig** Bjørn. Infrastrukturen findes stort set — men **broen** mellem hans indre lag og Bjørns opmærksomhed er ikke bygget. Fragmenterne bliver i mørket (buffer/DB), og `notify_user`/`route_proactive_notification` kaldes aldrig med dem.

Kobler til [[reference_outreach_ntfy_blindness]]: sidste gang outreach fejlede fordi (a) det blev sendt via en uovervåget ntfy-kanal og (b) kontakt-gaten læste Jarvis' EGNE autonome runs som "bruger aktiv". Begge fejl skal undgås her.

## Mål

En rute der samler Jarvis' fragmenter → prioriterer → gennem en presence-bevidst contact-gate → når over overfladen som en besked til Bjørn (Discord/webchat). **Hybrid** overflade-model, **live-governed fra dag ét** (ingen skygge-periode — men hård governance + øjeblikkelig kill-switch + fuld observabilitet i stedet).

## Beslutninger (fra brainstorm)

- **Overflade-model = hybrid:** event-drevet for det presserende (ét kritisk item straks), digest for resten ("mens du var væk"-batch).
- **Live-governed fra dag ét:** sender fra start, men hårdt gated (daily-cap 3, cooldown 2t, presence-gate, quiet-hours). Ingen shadow-periode; i stedet gør vi governance robust + hver beslutning observerbar.
- **Tilgang A:** ÉN cadence-producer med to interne grene (urgent + digest), delt contact-gate + caps → én governance-flade.
- **Kill-switch default ON** (Bjørn valgte live), men flip OFF = øjeblikkelig tavshed.
- **Genbrug, byg ikke om:** hele nedstrøms-stakken findes allerede.

## Ground truth (verificeret 9. jul — read-only map)

- **`proactivity`-cluster** findes (`central_catalog.py:111`) men har INGEN aktiv cadence-producer der fodrer det med owner-rettet indhold. Nerver: verification (gate) + observables (pressure_threshold, action_router, longing_signal, initiative_queue, …).
- **Fragment-kilder** (producerer, men lander i DB/buffer, ikke hos Bjørn):
  - `initiative_queue.get_pending_initiatives()` (`initiative_queue.py:196`) — `runtime_initiatives`-tabel, felter incl. focus/priority/status/detected_at. Live, ikke overfladet.
  - `existential_wonder_daemon` (`existential_wonder_daemon.py:45`) — genererer 1 spørgsmål, skriver til private_brain + `_wonder_buffer` + eventbus `existential_wonder.generated`. **Ikke registreret som producer** (forældreløs).
  - `inner_voice_daemon` (`inner_voice_daemon.py:101`) — har cadence-producer; detekterer initiativer → `push_initiative` til initiative_queue.
- **Levering (findes, virker):**
  - `route_proactive_notification(user_id, notification_type, payload, importance, *, _skip_quiet)` (`notification_router.py:181`) → resolver kanal, quiet-hours-gated, → Discord/webchat.
  - `discord_gateway.send_dm_to_user(recipient_discord_id, text)` (`discord_gateway.py:409`).
  - `is_quiet_hours(prefs, now_hm)` (`notification_router.py:87`) — kun tidsbaseret (default 23:00–07:00).
- **Caps/cooldown findes:** `action_router._MAX_PROACTIVE_PER_DAY=3`, `_PROACTIVE_COOLDOWN_HOURS=2` (`action_router.py:42-43`, settings-backed) + `_proactive_messages_today()`.
- **Governance-mønstre til genbrug:** `central_switches.is_enabled/set_enabled`, `ProducerSpec` + cadence, `central().observe({cluster, nerve, …})` (self-safe).

## Arkitektur

Ét nyt modul + minimal wiring. Alt tungt findes allerede.

### `core/services/proactivity_bridge.py` (nyt)

Rene, enkelt-ansvars-funktioner (hver unit-testet):

- **`collect_candidates() -> list[dict]`** — læs de eksisterende kilder (egress-frit): pending initiatives (`get_pending_initiatives`), seneste existential wonder (`get_latest_wonder`/buffer), inner-voice-båret initiativ. Normalisér til `{kind, text, priority, source, source_id, ts}`. Self-safe → `[]` ved fejl. **Skriver intet.**
- **`classify(candidate) -> "urgent" | "normal"`** — urgent = priority "high" ELLER kind in {kritisk impuls}; ellers normal. Ren funktion.
- **`select(candidates) -> {"urgent": [...], "normal": [...]}`** — dedup (source_id), sortér efter (priority, friskhed), cap listelængder (fx normal ≤ 5).
- **`should_reach_owner(*, urgent: bool, now, prefs, last_owner_visible_at, sent_today, last_sent_at) -> tuple[bool, str]`** — **contact-gaten** (ren, testbar; ingen I/O — kalderen henter signalerne):
  - **Bjørn reelt fraværende:** `now - last_owner_visible_at >= _AWAY_MIN` (digest) — hvor `last_owner_visible_at` er ÆGTE bruger-synlig-aktivitet (IKKE autonome runs). Urgent tillader kortere/ingen away-krav.
  - **Quiet-hours:** `is_quiet_hours(prefs)` blokerer normal; urgent/kritisk kan `_skip_quiet` KUN hvis eksplicit kritisk.
  - **Daily-cap:** `sent_today < _MAX_PROACTIVE_PER_DAY`.
  - **Cooldown:** `now - last_sent_at >= _PROACTIVE_COOLDOWN_HOURS`.
  - Returnér `(ok, reason)` — reason bruges til observe ved suppression.
- **`build_digest(normal) -> str`** — "Mens du var væk:"-format, kort, prioriteret, ≤ N items.
- **`build_urgent(item) -> str`** — enkelt-item-format.
- **`run_proactivity_bridge_tick(*, trigger, last_visible_at) -> dict`** — cadence run_fn (orkestrering, self-safe):
  1. Kill-switch: `central_switches.is_enabled("autonomy","proactivity_bridge")` (default ON). OFF → observe "disabled", return.
  2. Hent presence + prefs + caps-tællere (ægte signaler).
  3. `collect_candidates()` → `select()`.
  4. **Urgent-gren:** hvis urgent-item + `should_reach_owner(urgent=True)` → send ÉT via `route_proactive_notification(type="reach_out", importance="high")` → observe `bridge_surfaced`.
  5. **Digest-gren:** ellers hvis normal-items + `should_reach_owner(urgent=False)` → `build_digest` → send (importance="normal") → observe `bridge_surfaced`.
  6. **Ellers:** `central().observe({cluster:"proactivity", nerve:"bridge_suppressed", reason})` — synlig, ikke sendt.
  7. Efter send: opdatér cap-tæller + last_sent (genbrug action_routers state hvis muligt, ellers eget kv).
- **`register_proactivity_bridge_producer()`** — `ProducerSpec(name="proactivity_bridge", cooldown_minutes=10, visible_grace_minutes=15, run_fn=run_proactivity_bridge_tick, priority=12)`.
- **`build_proactivity_bridge_surface() -> dict`** — read-only: seneste surfaced/suppressed-beslutninger + aktuelle kandidater + switch-status.

### Wiring (minimal)

- `internal_cadence_central_wiring.py`: self-safe blok der kalder `register_proactivity_bridge_producer()`.
- Ny route `apps/api/jarvis_api/routes/central_proactivity.py`: owner-gated `GET /central/proactivity` → `build_proactivity_bridge_surface()`.
- `apps/central_cli/central_cli/commands.py`: `"proactivity": "/central/proactivity"` → `jc proactivity`.

## Data-flow

```
cadence-tick (10 min, visible_grace 15) → run_proactivity_bridge_tick
  → kill-switch? → collect_candidates (initiative_queue + wonder + inner-voice)
  → select (urgent/normal) → should_reach_owner (presence + quiet + cap + cooldown)
    → urgent+ok  → route_proactive_notification(high) → Discord/webchat → observe surfaced
    → digest+ok  → build_digest → route_proactive_notification(normal) → observe surfaced
    → ellers     → observe suppressed (reason)
→ /central/proactivity + jc proactivity (surfaced/suppressed + kandidater + switch)
```

## Fejlhåndtering

- Hele modulet self-safe: enhver kilde-/central-/leverings-fejl → fanget, observeret som fejl-note, aldrig crash i cadence-hot-path (paritet med de andre inner-life-daemoner).
- Kill-switch fail-safe: hvis switch-læsning fejler → behandl som ON? Nej — **fail-CLOSED for afsendelse** (hellere tavs end spam): switch-fejl → suppress + observe. (Modsat gate_enforce, fordi her er "gør intet" den sikre tilstand.)
- Levering fejler → observe `delivery_failed` + tæl IKKE som brugt cap (så en ægte besked ikke tabes til cap'en pga. en transient fejl).

## Test

`tests/test_proactivity_bridge.py` — rene funktioner på fixtures:
- `should_reach_owner`: fraværende+under-cap+ikke-quiet → (True); tilstede → (False, "owner_present"); quiet+normal → (False, "quiet_hours"); cap-ramt → (False, "daily_cap"); cooldown → (False, "cooldown"); urgent+quiet → (True) kun hvis kritisk.
- `classify`/`select`: urgent vs normal, dedup på source_id, cap på listelængde.
- `build_digest`/`build_urgent`: indeholder item-teksten, kort, ingen tomme.
- `run_proactivity_bridge_tick`: kill-switch OFF → intet sendt (route ikke kaldt); switch-læsnings-fejl → suppress (fail-closed); self-safe når en kilde kaster.
- presence-gaten bruger ÆGTE owner-visible-signal (mock injiceret), ikke autonome runs.

## Filer

- **Ny:** `core/services/proactivity_bridge.py` + `tests/test_proactivity_bridge.py`; `apps/api/jarvis_api/routes/central_proactivity.py`.
- **Ændr:** `core/services/internal_cadence_central_wiring.py` (registrér producer); API-app router-registrering; `apps/central_cli/central_cli/commands.py` (`_GET_ENDPOINTS`).

## Scope-grænse

SP1 = broen: collect → select → contact-gate → route (hybrid, live-governed) + observabilitet + kill-switch. Den bygger IKKE nye fragment-generatorer (bruger de eksisterende), aktiverer IKKE longing/pressure-akkumulatoren (separat), og bygger IKKE Agent Smith (SP2). Existential_wonder er forældreløs — broen LÆSER dens buffer/DB; at give den sin egen cadence-producer er valgfrit follow-up (noteres, ikke i scope).

## Deploy

Rører runtime (ny cadence-producer + route + CLI). Fuld suite (~20 min) + container-deploy (`git pull` ff/merge + `sudo systemctl restart jarvis-runtime jarvis-api` på `bs@10.0.0.39`, begge). Kill-switch default ON → live straks efter deploy; kan flippes OFF øjeblikkeligt hvis den spammer. Lander på `main`.
