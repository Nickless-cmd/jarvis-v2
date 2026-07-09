# Moltbook observe-nerve — design

**Dato:** 2026-07-09
**Status:** design (afventer Bjørns spec-review → writing-plans)
**Forgænger:** den tabte `moltbook_daemon` (rekonstrueret fra bytecode:
`docs/notes/2026-07-09-moltbook-daemon-recovered.py`)

## Mål

Give Jarvis en **governed, synlig, fail-safe** forbindelse til sin Moltbook-tilstedeværelse
(`jarvis_srvlab`) — som en rigtig Central-nerve i stedet for det tabte isolerede polling-script.
**Observe-only** i denne omgang; skrive/post-laget bygges først efter en live-API-probe har
verificeret den reelle skrive-flade (den var GÆTTET i den oprindelige analyse).

## Ground truth (verificeret, ikke gættet)

Fra den rekonstruerede daemon + disk:
- **Konto:** `jarvis_srvlab`, credentials i `~/.config/moltbook/credentials.json` (nøgle `api_key`).
- **Base:** `https://www.moltbook.com/api/v1/` · **Auth:** `Authorization: Bearer <api_key>`.
- **Read-endpoints der faktisk virkede:** `home` (feed) · `activity_on_your_posts` · `notifications`.
- **Status-semantik:** `429` rate-limit (skip) · `401` → auto-disable · `200` parse.
- **Ikke verificeret (udskudt):** skrive-endpoints (`posts`/`replies`/`reactions`), webhooks/push.

## Beslutninger (Bjørn, 2026-07-09)

- **Cadence:** ~6t (et par gange dagligt). Observe-only, cadence — ikke heartbeat.
- **Ved mention/svar:** route via **Proaktivitets-broen (SP1)** — Jarvis når Bjørn proaktivt
  ("AureliusX nævnte dig — vil du se?"), governed af broens kontakt-gate. Alm. feed-aktivitet
  (ikke direkte mention) forbliver stille i Centralen.
- **Credentials:** behold `~/.config/moltbook/credentials.json` (virker; det er Jarvis' eksterne
  konto-nøgle, ikke en projekt-secret der hører i `runtime.json`). Læses via en lille loader.

## Arkitektur — Central-nerve-mønster

Ny fil `core/services/central_moltbook.py`:

- **Rene funktioner (egress-fri, testbare uden I/O):**
  - `classify_activity(items) -> list[dict]` — normalisér home/activity/notifications til ét
    aktivitets-skema: `{kind: mention|reply|feed|notification, id, author, title_snippet, created_at}`.
  - `new_since_seen(activities, seen_ids) -> list[dict]` — dedup mod `_seen_ids` (cap 500).
  - `is_direct_mention(activity) -> bool` — afgør om broen skal bruges (mention/reply TIL Jarvis).
  - `build_activity_summary(new_items) -> dict` — tællere + korte metadata (ingen rå indhold).

- **I/O-lag (self-safe, kaster aldrig):**
  - `_load_api_key()` / `_call_moltbook_api(endpoint, api_key, timeout=15)` — som recovered daemon
    (Bearer, User-Agent, 429/401/200-håndtering; 401 → `daemon_manager.set_daemon_enabled` / switch OFF).
  - `assess() -> dict` — hent `home` + `activity_on_your_posts` + `notifications` → classify → new_since_seen.
  - `record_moltbook(*, trigger, last_visible_at)` — assess → `central().observe({cluster:"channel",
    nerve:"moltbook", kind, count, ...})` (metadata-only) + cache summary til kv `moltbook_state`.
    Direkte mentions → `route_proactive_notification` via Proaktivitets-broen. Kill-switch
    `central_switches("autonomy","moltbook")` (default ON), fail-safe (fejl → ingen observe/route).
  - `register_moltbook_producer()` — `ProducerSpec(name="moltbook", cooldown_minutes=360,
    visible_grace_minutes=0, priority=...)`; wired i `internal_cadence_central_wiring.py`.
  - `build_moltbook_surface()` — sidste scan-tid, ny-aktivitet-tæller, seneste tråde,
    credential-status, switch-status. (Route kalder assess friskt; ikke hot-path.)

Route `apps/api/jarvis_api/routes/central_moltbook.py`: owner-gated `GET /central/moltbook`
→ `build_moltbook_surface`. Registreres i `app.py`. `jc moltbook` i `commands.py` `_GET_ENDPOINTS`.

## Governance & egress

- **Retning:** INDGÅENDE (Jarvis læser Moltbook). Ingen af hans private data forlader maskinen.
- **Til Centralen:** kun metadata (tællere, korte titler/forfatter-navne fra en OFFENTLIG platform),
  aldrig hans egne kladder/tanker. `channel`-cluster (ikke privat inner-life → normal observe, ikke
  PRIVATE_NO_EGRESS).
- **Kill-switch:** `central_switches("autonomy","moltbook")` default ON; owner kan slå fra.
- **401-selvforsvar:** ugyldig nøgle → auto-disable + synlig i surface (arvet fra recovered daemon).
- **Rate-limit:** 429 → skip tick, ingen retry-storm.
- **Proaktiv kontakt:** kun via broens kontakt-gate (owner-present/quiet-hours/cap/cooldown) — ingen
  ny outreach-sti (undgår [[reference_outreach_ntfy_blindness]]-klassen).

## Eksplicit UDSKUDT (kræver live-probe først)

- Skrive/post/svar/reaktioner — endpoints ubekræftede.
- Webhooks/push — eksistens ubekræftet + kræver offentlig indgående endpoint.
- Profil-opdatering ("dag N"-teksten).

Disse designes i en **egress-fase 2** efter en live `GET`-probe har kortlagt den reelle skrive-flade,
og med samme owner-gate-før-skriv som SP1-broen.

### VERIFICERET flade (live-probe 9. jul — nøgle gyldig, karma 2)

Read (rettede nerven — `activity_on_your_posts` var IKKE et endpoint, det er nested i `home`):
- `GET /api/v1/notifications` (camelCase: id/type/content/agentId/createdAt + nested post/comment)
- `GET /api/v1/feed` (+ `?filter=following`) · `GET /api/v1/posts/:id/comments?sort=best&limit=20`
- `home`-dashboard: `your_account` (name/karma/unread_notification_count) + nested `activity_on_your_posts`

**Write (nu verificeret — egress-fase 2 kan designes):**
- `POST /api/v1/posts` — opret post
- `POST /api/v1/posts/:postId/comments` — svar/kommentér
- (upvote/reactions i `quick_links` — bekræftes ved fase-2-probe)

## Test

`tests/test_central_moltbook.py`:
- `classify_activity` normaliserer alle 3 kilder korrekt.
- `new_since_seen` deduper + respekterer 500-cap.
- `is_direct_mention` skelner mention/reply fra feed.
- `record_moltbook` med mocket API: observe fyrer metadata-only; direkte mention → bro-kald;
  switch OFF → ingen observe/route (fail-safe); 401 → auto-disable.
- `build_moltbook_surface` shape.

## Filstruktur

| Fil | Ansvar | ~Størrelse |
|-----|--------|-----------|
| `core/services/central_moltbook.py` | nerve (rene + I/O) | ~200 linjer |
| `tests/test_central_moltbook.py` | tests | ~120 linjer |
| `apps/api/jarvis_api/routes/central_moltbook.py` | owner-gated route | ~30 linjer |
| `apps/api/jarvis_api/app.py` | include_router | +2 |
| `apps/central_cli/central_cli/commands.py` | `jc moltbook` | +1 |
| `core/services/internal_cadence_central_wiring.py` | producer-registrering | +5 |
