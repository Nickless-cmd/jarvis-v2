# Mobile Push Notifications (FCM) — Design

Date: 2026-06-19
Status: Approved design — ready for implementation plan
Author: Claude (Opus 4.8) på baggrund af samtale med Bjørn
Sub-project: V2 delprojekt 1 af 4 (push → visuelt løft → device awareness → chatboble)

> Native push-notifikationer i selve Jarvis-companion-appen, leveret via Firebase
> Cloud Messaging (FCM) som **data-only** beskeder, så Google aldrig ser indhold.
> Bygger på det server-autoritative run-fundament (run_event_log).

---

## 1. Mål & ikke-mål

**Mål:** Telefonen modtager en native notifikation i Jarvis-appen — også når appen
er **helt lukket/dræbt** — for tre slags hændelser:

1. **Svar-klar** — et run blev færdigt mens brugeren ikke kiggede live.
2. **Proaktiv** — Jarvis tager selv initiativ (`initiative_queue`).
3. **Reminder** — planlagt påmindelse (`scheduled_tasks`).

Tap på notifikationen åbner den relevante samtale.

**Ikke-mål (bevidst udskudt):**
- Smart cross-device-routing (ude→mobil / hjemme→desktop) → delprojekt 3 (device awareness).
- Bubbles/overlay, batteri-optimerings-exemptions, Wear OS → senere V2-punkter.
- iOS (kun Android i denne fase).
- **Foreground service:** udskudt og *ikke nødvendig for push*. FCM vækker appen via
  Google Play Services selv når den er helt dræbt — uden en foreground service.
  Foreground-servicens eneste reelle værdi er kontinuerlig aktiv-stream-socket, og
  det dækker det server-autoritative run-fundament allerede (run overlever baggrund,
  klient re-abonnerer). Tages som separat polish-punkt hvis et konkret behov dukker op.

**Privatlivs-krav (spec §1.5 "ingen tredjepart"):** FCM-payloads er **data-only** —
de indeholder kun et vække-signal (`run_id`/`session_id`/`kind`), aldrig beskedtekst.
Appen henter det faktiske indhold fra **vores** server over HTTPS. Google ser at en
enhed blev vækket, aldrig hvad Jarvis skrev.

---

## 2. Arkitektur

```
Jarvis-server (container)                         Telefon (Android)
─────────────────────────                         ─────────────────────────
run færdig / initiative / reminder
   │
   ▼
push_dispatcher
   │  - suppression-tjek (run_event_log)
   │  - hent device_tokens pr. bruger
   ▼
fcm_gateway ──data-only──► FCM HTTP v1 (Google) ──► app vækkes (RNFirebase
   (OAuth fra service-account)                         messaging baggrunds-handler)
                                                          │
                                                          ▼
                                                  henter INDHOLD fra
                                                  /chat/sessions/{id} (HTTPS)
                                                          │
                                                          ▼
                                                  notifee viser native notifikation
                                                          │
                                                  tap → dyb-link → samtale
```

**Genbrug:** `run_event_log` (frame-loggen — udvides med let abonnent-sporing, se §5),
`notification_bridge`/`initiative_queue`/`scheduled_tasks` (eksisterende triggers).
`fcm_gateway` er parallel til det eksisterende `ntfy_gateway` (ntfy bevares urørt,
ikke længere den primære vej). FCM v1 OAuth bruger `google-auth` (allerede i ai-miljøet
— ingen ny server-dependency).

---

## 3. Komponenter

### Server (container)

| Fil | Ansvar |
|---|---|
| `core/services/fcm_gateway.py` *(ny)* | FCM HTTP v1 send. Mint OAuth-access-token fra service-account-nøglen (`fcm_service_account_path` i runtime.json), bygger data-only payload, POST til `https://fcm.googleapis.com/v1/projects/{fcm_project_id}/messages:send`. Returnerer (ok, fejl-kode). |
| `core/services/device_tokens.py` *(ny)* | DB-helpers mod ny tabel `device_tokens`: `register(user_id, token, platform)`, `list_for_user(user_id)`, `delete(token)`. Egen tabel for at undgå at røre db.py's 33k linjer. |
| `core/services/push_dispatcher.py` *(ny)* | Orkestrering: `on_run_done(run_id)`, `on_initiative(user_id, payload)`, `on_reminder(user_id, payload)`. Kører suppression-tjek, henter tokens, kalder `fcm_gateway`, rydder døde tokens op. |
| `apps/api/jarvis_api/routes/push.py` *(ny)* | `POST /push/register {token, platform}` (auth'ed → user_id fra token), `POST /push/unregister {token}`. |
| `core/services/run_event_log.py` *(udvid)* | Let abonnent-sporing til suppression-signalet (se §5): `subscriber_opened(run_id)` / `subscriber_closed(run_id)` (tæller), `mark_consumed(run_id)` (sat når en subscriber yielder done-framen), `was_consumed_or_active(run_id) -> bool`. |
| `core/services/chat_sessions.py` *(udvid)* | `get_session_owner(session_id) -> str \| None` — slår ejer op via seneste besked-stempel (`user_id`); bruges af dispatcher til at vælge tokens. |

**Wiring:**
- `_subscribe`/`/runs/{id}/subscribe`/`/sessions/{id}/live`-generatorerne kalder `subscriber_opened` ved start + `subscriber_closed` i `finally`, og `mark_consumed` når de yielder `message_stop`.
- `core/services/visible_runs_sections/detached_run.py` `_consume` finally (efter `mark_done`) → `push_dispatcher.on_run_done(run_id)` (best-effort, try/except, må aldrig bryde runnet).
- `initiative_queue` udgivelse → `on_initiative`.
- `scheduled_tasks` reminder-fyring → `on_reminder`.

**DB-skema (`device_tokens`):**
```sql
CREATE TABLE IF NOT EXISTS device_tokens (
    token       TEXT PRIMARY KEY,
    user_id     TEXT NOT NULL,
    platform    TEXT NOT NULL DEFAULT 'android',
    updated_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_device_tokens_user ON device_tokens(user_id);
```

### Mobil (app — `.worktrees/jarvis-mobile-companion-v1/apps/mobile`)

| Modul | Ansvar |
|---|---|
| `@react-native-firebase/messaging` | FCM-token + data-only baggrunds-/forgrunds-handler. `google-services.json` ligger i `android/app/` (gitignored). |
| `notifee` | Viser den native notifikation; håndterer tap → dyb-link. |
| `src/lib/push.ts` *(ny)* | `registerForPush()` efter login (hent token → `POST /push/register`, lyt på token-rotation → re-registrér), `onMessage`/`setBackgroundMessageHandler` (data-only → hent indhold fra `/chat/sessions/{id}` → vis via notifee), tap → naviger til samtale. Suppression: vis ikke banner hvis appen er i forgrunden på præcis den samtale. |

**Native rebuild kræves:** `@react-native-firebase/*` + `notifee` er native moduler →
APK skal genbygges (gradle: google-services-plugin + firebase-bom; `setBackgroundMessageHandler`
registreres i `index.js` uden for komponent-træet). Ikke en JS-only ændring.

---

## 4. Data-flow: svar-klar (primær)

1. Run kører server-autoritativt; abonnerende HTTP-generatorer registrerer sig via
   `subscriber_opened`/`subscriber_closed`, og sætter `mark_consumed` når de yielder
   `message_stop`.
2. Run afslutter → `mark_done(run_id)` → `push_dispatcher.on_run_done(run_id)`.
3. `on_run_done` planlægger et tjek efter `PUSH_GRACE_S` (~5s — giver en levende
   klient tid til at dræne de sidste frames til `message_stop`), og afgør så:
   - **Suppression:** `run_event_log.was_consumed_or_active(run_id)` → `True` (nogen
     så/ser det live) → drop. `False` (alle subscribere var droppet, fx baggrundet)
     → fortsæt.
   - Slå ejer op: `session_for_run(run_id)` → `chat_sessions.get_session_owner(sid)`.
   - Hent `device_tokens` for brugeren.
   - Byg data-only payload `{kind: "answer_ready", session_id, run_id}` (`priority: high`).
   - Send via `fcm_gateway` til hvert token.
4. Telefon vækkes → henter færdig besked fra `/chat/sessions/{id}` → notifee viser
   "Jarvis svarede" + uddrag.
5. Tap → dyb-link åbner samtalen.

**Proaktiv/reminder:** samme dispatcher, payload `kind: "initiative"` / `"reminder"`,
trigget af `initiative_queue` / `scheduled_tasks`.

---

## 5. Suppression (to lag)

- **Server-lag:** `on_run_done` venter `PUSH_GRACE_S` (~5s) og pusher kun hvis
  `was_consumed_or_active(run_id)` er `False` — dvs. ingen levende subscriber så
  runnet til ende. Grace-vinduet undgår et kapløb hvor en mobil i forgrunden lige
  er ved at dræne de sidste frames. Dækker "jeg sad og kiggede" (desktop/mobil/webchat).
- **Klient-lag:** appen viser ikke banner hvis den er i forgrunden på præcis den
  samtale data-only-beskeden gælder (beskeden er der live). Serveren pusher signalet;
  appen beslutter visning.

---

## 6. Fejl-håndtering

| Situation | Adfærd |
|---|---|
| FCM svarer `UNREGISTERED`/`INVALID_ARGUMENT` på et token | Slet tokenet fra `device_tokens` (selv-oprydning). |
| FCM-send net/auth-fejl | Log + ét retry; bryder aldrig runnet (alt i try/except). |
| Tilladelse nægtet på telefonen | Graceful — ingen push, in-app virker stadig. |
| Token-registrering fejler | Prøv igen ved næste app-åbning. |
| Service-account mangler/ugyldig | `fcm_gateway.is_configured()` → False; dispatcher no-op'er stille. |

**Kendt forbehold (data-only leverings-pålidelighed):** data-only FCM-beskeder skal sendes
med `AndroidConfig.priority = HIGH` for at vække en app i baggrund/doze. Selv da kan
aggressive OEM-batteri-managers (Xiaomi/Huawei/OnePlus) forsinke/droppe wake når appen er
*helt dræbt* — det er præcis det batteri-exemption-flow der er udskudt til et senere V2-punkt
(spec §7). På standard-Android (inkl. Bjørns enhed) er high-priority data-only pålideligt nok.

---

## 7. Test

**Server-unit:**
- `run_event_log` abonnent-sporing: `subscriber_opened`/`closed` tæller korrekt; `mark_consumed` + `was_consumed_or_active` (aktiv subscriber → True; consumed → True; ingen af delene → False).
- `push_dispatcher` suppression: `was_consumed_or_active=True` → ingen send; `False` → send (mock gateway). Ejer-opslag via `get_session_owner`.
- `device_tokens` CRUD: register (upsert), list_for_user, delete.
- `fcm_gateway`: payload-form er data-only (ingen `notification`-felt, kun `data`); mock FCM-HTTP for 200 + UNREGISTERED-oprydning.
- `routes/push.py`: register/unregister scoper til auth'ed user_id.

**Mobil-unit:** `push.ts` token-registrering + data-only→hent→vis-flow (mock messaging + notifee).

**Ende-til-ende (manuel, det endelige bevis):** send en ægte data-only besked til
Bjørns telefon-token, verificér native notifikation + tap → korrekt samtale, med
appen (a) i forgrunden, (b) i baggrunden, (c) helt lukket.

---

## 8. Konfiguration (allerede på plads)

- `runtime.json`: `fcm_project_id = "jarvis-companion-58e5c"`, `fcm_service_account_path = ~/.jarvis-v2/config/fcm-service-account.json` (chmod 600).
- Mobil: `google-services.json` i `android/app/` (gitignored).
- Sender ID / project number: `184612871089`.

---

*Godkendt sektion-for-sektion af Bjørn 2026-06-19. Næste: implementerings-plan via writing-plans.*
