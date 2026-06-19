# Intelligent Device Awareness — Design (V2 delprojekt 3)

**Dato:** 2026-06-19
**Status:** Godkendt design, klar til implementeringsplan
**Vision-reference:** `docs/superpowers/specs/2026-06-18-jarvis-mobile-companion-v2-vision.md` §4

## Mål

Jarvis ved hvilken enhed Bjørn er ved, og når han vil nå ham proaktivt
(svar-klar, reminder, initiativ) rammer han den rigtige enhed i stedet for at
sprede beskeden til alle. Presence er både infrastruktur (routing) og noget
Jarvis selv kan ræsonnere om (tone/timing/om han overhovedet afbryder).

## Bærende beslutninger (afklaret med Bjørn)

1. **Presence-model:** hybrid — aktivitets-recency er primær afgører; desktop-sleep
   og mobil-netværksskift er hints der skubber beslutningen.
2. **Routing-politik:** bedste enhed + eskalering ved manglende ack (ikke blast,
   ikke "kun én uden fallback").
3. **Desktop-rækkevidde:** nåbar mens appen kører (inkl. minimeret/tray); lukkes
   appen helt, ved presence at desktop er offline og ruter til mobil.
4. **Awareness:** både automatisk routing OG injektion i Jarvis' prompt-awareness.
5. **Arkitektur:** Tilgang A — poll-udvidet, in-memory presence i API-processen,
   genbrug af eksisterende desktop-poll + FCM. Ingen ny transport, ingen ny daemon.

## Hvad findes i dag (fundament)

- `core/services/push_dispatcher.py`: `_push_to_user` blæster FCM til ALLE mobil-tokens
  for en bruger. `on_run_done` (answer_ready), `on_initiative`, `on_reminder` går alle
  kun til mobil. Suppression via `run_event_log.was_consumed_or_active`.
- `core/services/device_tokens.py`: `device_tokens`-tabel m. `platform`-felt (kun
  'android' i brug); `register/list_for_user/delete`.
- Desktop (`jarvis-desk`): poller `GET /chat/active-runs` hvert ~1,5s; viser native
  "opgave færdig"-notifikation via Electron-broen (`window.jarvisDesk.notifyTaskDone`)
  for runs den selv følger. Ingen proaktiv push-kanal.
- Mobil: FCM data-only push live (foreground/baggrund/lukket).

Hul: ingen presence-model, ingen enheds-routing, ingen desktop proaktiv-kanal.

## Arkitektur — komponenter

### 1. `core/services/device_presence.py` (NY)

In-memory registry pr. bruger. Efemær (ingen DB) — enheder gen-pinger inden for
sekunder efter en API-restart.

```
_PRESENCE: dict[user_id, dict[device_key, DeviceState]]
```

`DeviceState` (dataclass):
- `device_key: str` — stabil pr. enhed (desktop: persistent install-id; mobil: FCM-token)
- `platform: str` — "desktop" | "mobile"
- `last_ping_at: float` — monotonic; heartbeat-friskhed
- `last_interaction_at: float` — monotonic; sidste ægte brugerhandling (send/åbn/klik)
- `foreground: bool` — app i fokus/foreground
- `awake: bool` — desktop ikke i sleep (mobil altid True)
- `network: str` — "home" | "away" | "unknown"

**Public API (alle under én lås, alle wrapped af kalderen):**
- `record_ping(user_id, device_key, platform, *, foreground, awake, network, interaction=False)`
  → opretter/opdaterer state; sætter `last_ping_at=now`; hvis `interaction` også
  `last_interaction_at=now`.
- `prune(user_id=None)` → fjern enheder hvor `last_ping_at` er ældre end
  `_PRESENCE_TTL_S` (desktop) hhv. behold mobil som FCM-reachable (se nedenfor).
- `rank(user_id) -> list[RankedDevice]` → nåbare enheder sorteret bedst-først.
- `summary(user_id) -> str` → menneske-læsbar linje til Jarvis-awareness.

**Reachability-regler:**
- Desktop er nåbar KUN hvis `last_ping_at` inden for `_DESKTOP_ONLINE_TTL_S` (12s;
  desktop pinger hvert ~5s).
- Mobil er nåbar via FCM hvis der findes et device_token (uanset foreground) — også
  hvis den ikke har pinget for nylig. Foreground-mobil er "stærkere nåbar".

**Scoring (i `rank`):** for hver nåbar enhed:
- `score = recency_weight(last_interaction_at)` — nyere interaktion = højere (lineært
  aftagende over `_RECENCY_HORIZON_S`, fx 600s).
- `+ FOREGROUND_BONUS` hvis `foreground`.
- desktop med `awake=False` → ekskluderes som kandidat (ikke bare straffes).
- mobil med `network=="away"` → `+ AWAY_MOBILE_BONUS` (du er ude → mobilen er hvor du er).
- desktop antages altid `network="home"`; intet hint-tillæg, men taber ikke til en
  baggrunds-mobil hjemme pga. foreground/recency.
- mobil ikke-foreground + ingen nylig ping → lav score, men forbliver i listen som
  sidste-udvejs FCM-kandidat.

`rank` returnerer `[RankedDevice(device_key, platform, score, reachable_via)]` hvor
`reachable_via` ∈ {"desktop_queue", "fcm"}.

Konstanter (modul-toppen, justerbare):
`_DESKTOP_ONLINE_TTL_S=12`, `_PRESENCE_TTL_S=120`, `_RECENCY_HORIZON_S=600`,
`FOREGROUND_BONUS=100`, `AWAY_MOBILE_BONUS=50`.

### 2. `core/services/proactive_router.py` (NY)

Erstatter `push_dispatcher`'s blanket-blast. `push_dispatcher` kalder ind her.

`route(user_id, payload: dict, kind: str) -> None`:
1. `ranked = device_presence.rank(user_id)`.
2. Tom liste → fald tilbage til `push_dispatcher._push_to_user` (FCM-blast alle
   mobil-tokens) — mister aldrig et signal.
3. Generér `notif_id` (uuid). Send til `ranked[0]` via dens kanal:
   - `reachable_via=="fcm"` → `push_dispatcher._fcm_send` til enhedens token (payload
     beriget med `notif_id`).
   - `reachable_via=="desktop_queue"` → `desktop_notifications.enqueue(user_id, {...})`.
4. Registrér pending-ack: `_PENDING[notif_id] = {user_id, payload, kind, remaining=ranked[1:],
   deadline=now+_ESCALATE_S}`.
5. `ack(notif_id)` → fjern fra `_PENDING` (annullér eskalering).
6. `sweep()` (kaldt periodisk, se nedenfor): for hver pending hvor `now>deadline` →
   pop næste fra `remaining`, send dertil, nulstil deadline; hvis `remaining` tom →
   fjern (eller én sidste FCM-blast hvis `kind` er højvigtig — answer_ready/reminder).

`_ESCALATE_S=180` (justerbar). `sweep()` planlægges per-pending via `threading.Timer`
(samme mønster som `push_dispatcher`'s eksisterende 5s-grace-timer): når `route`
registrerer en pending, armes en `Timer(_ESCALATE_S, _escalate, [notif_id])`; `ack`
annullerer timeren. Ingen global poll-loop, ingen ny daemon. `_escalate` sender til
næste enhed og armer en ny timer hvis `remaining` ikke er tom.

Suppression: for `kind=="answer_ready"` bevares det eksisterende
`was_consumed_or_active`-tjek (hvis en klient aktivt ser runnet, ingen push overhovedet).
Tjekket sker i `push_dispatcher.on_run_done` FØR `route` kaldes (uændret placering).

### 3. `core/services/desktop_notifications.py` (NY)

Per-bruger in-memory kø (efemær).

```
_QUEUE: dict[user_id, list[dict]]   # {notif_id, kind, title, body, session_id, ts}
```

- `enqueue(user_id, item)` → append.
- `drain(user_id) -> list[dict]` → returnér + ryd (desktop poller og kvitterer ved
  visning via separat ack; drain fjerner fra køen så den ikke gen-leveres).
- `prune()` → drop items ældre end `_DESKTOP_NOTIF_TTL_S` (fx 300s) der aldrig blev
  drained (desktop gik offline).

### 4. `apps/api/jarvis_api/routes/presence.py` (NY)

Alle bruger-scoped via `_current_user` (samme mønster som `routes/push.py`).
- `POST /presence/ping` body `{device_key, platform, foreground, awake, network, interaction?}`
  → `device_presence.record_ping(...)` → `{"ok": true}`.
- `GET /notifications/pending` → `desktop_notifications.drain(uid)` →
  `{"items": [...]}`.
- `POST /notifications/ack` body `{notif_id}` → `proactive_router.ack(notif_id)` →
  `{"ok": true}`.

### 5. Klient-wiring

**Desktop (`jarvis-desk`):**
- Presence-ping hvert ~5s mens app kører (egen let interval; ikke koblet til 1,5s
  run-pollen). `foreground` via `window.focus`/`blur`, `awake` via Electron
  `powerMonitor` `suspend`→False / `resume`→True (main-proces → IPC → renderer-state),
  `interaction=true` sættes på næste ping efter send/klik. `device_key` = persistent
  install-id gemt i app-settings (genereres ved første start hvis fraværende).
- Notif-poll: piggyback på den eksisterende 1,5s `active-runs`-poll → kald også
  `GET /notifications/pending`; for hvert item → vis native OS-notifikation via en
  generaliseret bro: `window.jarvisDesk.notify({kind, title, body, sessionId})`
  (refaktorér `notifyTaskDone` til at delegere hertil — bevar bagudkompatibilitet).
  Ved visning → `POST /notifications/ack {notif_id}`; ved klik → nav til `sessionId`
  + samme ack (idempotent).

**Mobil:**
- Presence-ping ved `AppState`-skift (active/background) + `NetInfo`-skift
  (wifi→`network="home"`, cellular→`"away"`, andet→`"unknown"`) + periodisk hvert ~30s
  mens foreground. `device_key` = FCM-token (haves allerede). `interaction=true` ved
  app-åbning/besked-send.
- FCM-payload bærer nu `notif_id`; ved visning (notifee) → `POST /notifications/ack`.

### 6. Jarvis-awareness — `prompt_contract`

Ny sektion "device-presence", DYNAMISK indhold → placeres BAGEST i prompten
(cache-stabilitets-reglen). Læser `device_presence.summary(uid)`:
- Eksempel aktiv: "Bjørn er aktiv ved desktop (i fokus). Mobil: baggrund, hjemme-wifi."
- Eksempel ude: "Bjørn ser ud til at være ude — mobil i forgrund på mobildata. Desktop offline."
- Eksempel ingen: "Ingen aktiv enhed lige nu (sidst set mobil for ~2t siden)."
Killswitch-gatet (fx `device_awareness_enabled`), best-effort, fanger alle exceptions
— må ALDRIG bryde den synlige prompt.

## Dataflow (svar-klar eksempel)

1. Detached run færdigt → `push_dispatcher.on_run_done(run_id)`.
2. `was_consumed_or_active`? Ja → stop (en klient så det live). Nej → fortsæt.
3. `proactive_router.route(owner, {kind:answer_ready, session_id, run_id}, "answer_ready")`.
4. `rank` → fx `[desktop(score 240, desktop_queue), mobile(score 90, fcm)]`.
5. Enqueue til desktop-kø; registrér pending m. `remaining=[mobile]`, deadline +180s.
6. Desktop-poll henter item → viser OS-notif → `ack` → pending fjernet. FÆRDIG.
   Eller: desktop ser den aldrig (Bjørn gik) → efter 180s `sweep` → FCM til mobil.

## Fejlhåndtering

- Alle `device_presence`/`proactive_router`/`desktop_notifications`-kald er wrapped
  hos kalderen → bryder aldrig chat eller push.
- Tom/ukendt presence → fald tilbage til nuværende FCM-blast (eksisterende adfærd).
- API-restart midt i eskalering: `_PENDING` tabes, men signalet ligger i DB
  (run/reminder), og gen-levering er idempotent via `notif_id` (klienten de-dup'er på id).
- Stale enheder + udrainede desktop-notifs TTL-prunes.
- `powerMonitor` ikke tilgængelig (ældre Electron/OS) → `awake` defaulter True
  (degraderer til ren recency-routing).

## Privacy

- Presence er strengt per-bruger (`_current_user`-scoped); ingen ser andres enheder.
- `network` er kun en grov wifi/cellular-klassifikation ("home"/"away"/"unknown") —
  INGEN SSID, IP eller geolokation gemmes. Matcher multiuser-security-northstar
  (tool-adgang ≠ data-adgang; GDPR-bevidst).

## Testplan

- **Unit `device_presence`:** table-driven scoring/rank med falsk monotonic-ur:
  recency-vægtning, foreground-bonus, sleep-eksklusion, away-mobil-bonus,
  reachability (desktop online-TTL vs mobil-FCM-fallback), prune.
- **Unit `proactive_router`:** fake clock + fake presence → bedste-enhed-valg,
  eskalering ved manglende ack, ack annullerer, tom-presence-fallback, suppression.
- **Unit `desktop_notifications`:** enqueue/drain/prune (drain rydder, TTL-prune).
- **Integration (FastAPI TestClient):** `/presence/ping`, `/notifications/pending`,
  `/notifications/ack` — bruger-scoping + happy path.
- **Klient:** jest (mobil AppState/NetInfo→ping-payload, FCM notif_id→ack); vitest
  (desktop ping-loop, notif-poll→bro-kald, ack ved visning/klik).

## Filer (dekomponering — én ansvar hver)

- `core/services/device_presence.py` — NY (registry + scoring + summary)
- `core/services/proactive_router.py` — NY (routing + eskalering + pending-ack)
- `core/services/desktop_notifications.py` — NY (per-bruger kø)
- `apps/api/jarvis_api/routes/presence.py` — NY (3 endpoints)
- `core/services/push_dispatcher.py` — MOD (kald `proactive_router.route` i stedet for
  direkte `_push_to_user`; behold `_push_to_user`/`_fcm_send` som kanal-primitiver)
- `core/services/prompt_contract.py` — MOD (device-presence-sektion, bagest)
- `apps/jarvis-desk/...` — MOD (presence-ping, notif-poll, powerMonitor, bro-`notify`)
- `apps/mobile/...` — MOD (presence-ping på AppState/NetInfo, FCM notif_id→ack)

## Ikke i scope (YAGNI)

- Desktop nåbar når app er HELT lukket (kræver separat altid-kørende daemon + auto-start
  + OS-tilladelser pr. platform) — bevidst fravalgt.
- WebSocket-presence — fravalgt til fordel for poll-udvidet.
- Geolokation/SSID-baseret hjemme-detektion — kun grov wifi/cellular.
