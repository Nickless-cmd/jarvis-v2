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

**Genbrug:** `run_event_log` (ved allerede om et run blev streamet til ende),
`notification_bridge`/`initiative_queue`/`scheduled_tasks` (eksisterende triggers).
`fcm_gateway` er parallel til det eksisterende `ntfy_gateway` (ntfy bevares urørt,
ikke længere den primære vej).

---

## 3. Komponenter

### Server (container)

| Fil | Ansvar |
|---|---|
| `core/services/fcm_gateway.py` *(ny)* | FCM HTTP v1 send. Mint OAuth-access-token fra service-account-nøglen (`fcm_service_account_path` i runtime.json), bygger data-only payload, POST til `https://fcm.googleapis.com/v1/projects/{fcm_project_id}/messages:send`. Returnerer (ok, fejl-kode). |
| `core/services/device_tokens.py` *(ny)* | DB-helpers mod ny tabel `device_tokens`: `register(user_id, token, platform)`, `list_for_user(user_id)`, `delete(token)`. Egen tabel for at undgå at røre db.py's 33k linjer. |
| `core/services/push_dispatcher.py` *(ny)* | Orkestrering: `on_run_done(run_id)`, `on_initiative(user_id, payload)`, `on_reminder(user_id, payload)`. Kører suppression-tjek, henter tokens, kalder `fcm_gateway`, rydder døde tokens op. |
| `apps/api/jarvis_api/routes/push.py` *(ny)* | `POST /push/register {token, platform}` (auth'ed → user_id fra token), `POST /push/unregister {token}`. |

**Wiring:**
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

---

## 4. Data-flow: svar-klar (primær)

1. Run kører server-autoritativt; `run_event_log` sporer om en levende klient
   streamer det til `message_stop`.
2. Run afslutter → `mark_done(run_id)`.
3. `push_dispatcher.on_run_done(run_id)`:
   - **Suppression:** blev runnet streamet til ende af en levende subscriber?
     `JA` → drop (brugeren så det live). `NEJ` → fortsæt.
   - Slå session→user op (`run_event_log.session_for_run` + session-ejer).
   - Hent `device_tokens` for brugeren.
   - Byg data-only payload `{kind: "answer_ready", session_id, run_id}`.
   - Send via `fcm_gateway` til hvert token.
4. Telefon vækkes → henter færdig besked fra `/chat/sessions/{id}` → notifee viser
   "Jarvis svarede" + uddrag.
5. Tap → dyb-link åbner samtalen.

**Proaktiv/reminder:** samme dispatcher, payload `kind: "initiative"` / `"reminder"`,
trigget af `initiative_queue` / `scheduled_tasks`.

---

## 5. Suppression (to lag)

- **Server-lag:** push kun hvis runnet *ikke* blev streamet til ende af en levende
  subscriber (genbruger `run_event_log`). Dækker "jeg sad og kiggede".
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

---

## 7. Test

**Server-unit:**
- `push_dispatcher` suppression: run streamet-til-ende → ingen send; ellers send (mock gateway).
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
