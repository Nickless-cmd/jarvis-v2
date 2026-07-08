---
status: færdig
audited: 2026-07-08
ground_truth: superpowers artifact shipped (refs/symbols present in tree)
---
# Server-Authoritative Runs — Design (Stykke A)

Date: 2026-06-19
Status: Design — godkendt af Bjørn, klar til implementeringsplan
Forløber: A1-tee broadcast (live) + A3 detached-run (rullet tilbage, denne spec er A3 gjort rigtigt)

## Formål

En mobil-companion er ubrugelig hvis svar dør når man baggrunder appen — og man
baggrunder en telefon konstant. Ground truth (diagnostik 0.1.17, 2026-06-19):
mobilens "stream fejlede" er `error · http=200 · state=4 · software caused
connection abort` = **Android lukker selv SSE-socket'en ved baggrund/app-skift/
skærm-sleep.** Server-streamen er beviseligt sund (HTTPS curl: pings hver 5s,
max hul ≤6s, ét rent message_stop, fuld agentisk run til ende).

Med request-drevne runs (nuværende A1-tee) drives runnet af HTTP-forbindelsen,
så når socket'en kappes, dør runnet → intet svar. Denne spec gør runnet
**server-autoritativt**: det lever som en server-side baggrundsopgave,
uafhængigt af enhver forbindelse. Forbindelser bliver *abonnenter*.

Dette ene fundament løser tre ting på én gang:
1. **Baggrund-overlevelse** — runnet kører færdigt selvom mobilen mister forbindelsen.
2. **Bidirektionel realtime-sync** — enhver klient kan attache til et igangværende run i en session (desktop↔mobil begge veje).
3. **Fundament for FCM-push** (Stykke B, separat spec) — "intet klient attached → notificér".

## Scope

**I scope (Stykke A):** server-autoritative run-livscyklus + per-run event-log +
gen-abonnering fra offset + mobil-klient-reconnect + multi-klient-testharness +
flag-styring.

**Ikke i scope:** FCM-push (Stykke B — separat spec, kræver Firebase-projekt).
Android foreground service (ikke nødvendig når runnet overlever server-side).
Desktop-klient-ændringer (desktop får run-overlevelse gratis fra backend; dens
klient migreres evt. senere).

## Beslutninger (låst i brainstorm)

- **Blast radius:** backend-run-livscyklus bliver server-autoritativ for ALLE
  klienter (desktop+mobil+webchat), men **kun mobil-KLIENTEN ændres**. Desktop
  modtager byte-identiske v2-frames → urørt. (Option 1, et strikt subset af fuld
  migrering — døren til at migrere desktop-klienten senere står åben.)
- **Mekanisme:** in-memory event-log **pr. run_id** (ikke pr. session — det var
  A3's fejl der gav buffer-kollision mellem overlappende runs). `--workers 1` →
  in-memory delt på tværs af alle endpoints + baggrundstråde i api-processen.
- **Retention:** behold kun seneste run pr. session + auto-prune. En afsluttet
  log skal kun leve længe nok til en igangværende reconnect; DB har det endelige svar.

## Arkitektur & komponenter

### 1. `core/services/run_event_log.py` (ny — den rette primitiv)

In-memory, append-only, offset-indekseret log pr. run_id. Tråd-sikker (Lock).

```
create(run_id, session_id) -> None          # registrér ny log
append(run_id, frame: str) -> None          # tilføj v2-frame, opdatér last_append_at
mark_done(run_id) -> None                    # terminal → abonnenter stopper
read(run_id, from_idx: int) -> (frames: list[str], done: bool)
active_run_for_session(session_id) -> str | None   # seneste ikke-done run for sessionen
is_live(run_id) -> bool                      # ikke done + frisk append (<20s)
live_run_ids() -> list[str]                  # til /chat/active-runs (afløser per-session-buffer)
prune() -> None                              # behold seneste run/session, drop ældre afsluttede
```

Intern state: `{run_id: {session_id, frames: list[str], done: bool, last_append_at: float, created_at: float}}`.
Hård cap: `_MAX_FRAMES = 4000` pr. run (runaway-værn). `_LIVE_IDLE_S = 20.0`
(pings hver ~5s holder live under tool-runder).

### 2. `core/services/visible_runs_sections/detached_run.py` (omskrives fra A3)

`start_user_run_detached(*, message, session_id, approval_mode, thinking_mode,
force_user_id, tool_scope, provider_override, model_override, eff_model,
eff_provider, lane) -> str` (returnerer run_id).

- Genererer run_id; `run_event_log.create(run_id, session_id)` synkront FØR retur.
- Spawner baggrundstråd (copy_context for ContextVars) der:
  kører `_stream_visible_run(run, force_user_id, tool_scope)` gennem
  `translate_to_v2(...)`; for hvert frame `run_event_log.append(run_id, frame)`;
  i `finally`: `gen.aclose()` (→ `_stream_visible_run`'s finally → `unregister_visible_run`)
  + `run_event_log.mark_done(run_id)`.
- Ingen per-session begin/end → ingen kollision mellem overlappende runs.
- Beholder backend-guarden "ét aktivt run pr. session" (klienten blokerer send
  mens serveren arbejder; ingen nudge-swallow).

### 3. Endpoints (`apps/api/jarvis_api/routes/chat.py` + `chat_stream_v2.py`)

- `POST /chat/stream/v2` — starter detached run; returnerer StreamingResponse der
  abonnerer på run-loggen fra offset 0 + haler til done. **Byte-identiske frames
  som i dag** (golden-frame-verificeret) → desktop urørt.
- `GET /chat/runs/{run_id}/subscribe?from=N` (ny) — gen-abonnér fra offset N. SSE.
  Catch-up fra N + live-hale til done. 404 hvis run_id ukendt/pruned.
- `GET /chat/sessions/{id}/live` (ny) — slår sessionens aktive run op
  (`active_run_for_session`) og streamer det fra offset 0 (cross-device +
  foreground-attach). 204 hvis intet aktivt run.
- `GET /chat/active-runs` — afledt af `run_event_log.live_run_ids()` mappet til
  session_ids (afløser run_follow.live_sessions).

### 4. Mobil-klient (kun mobil)

- `streamClient.startStream`: spor offset (frame-tæller) + run_id (fra
  message_start/system_event:run).
- På drop før message_stop (inkl. `software caused connection abort`):
  auto-reconnect til `/chat/runs/{run_id}/subscribe?from=<offset>` med eksponentiel
  backoff (max ~5 forsøg). Vis "genforbinder…" i stedet for "stream fejlede".
  Falder tilbage til `sessions.select` hvis 404 eller forsøg opbrugt.
- `followSession`/resubscribe-hjælper genbruger samme reducer (byte-identiske frames).
- Foreground-resume: hvis `/chat/active-runs` viser sessionen aktiv, attach via
  `/chat/sessions/{id}/live`.
- Behold server-bevidst send-blok (composer = stop mens serveren arbejder).

## Dataflow

1. Send → `POST /chat/stream/v2` → `start_user_run_detached` → baggrundstråd kører
   → frames appendes til `run_event_log[run_id]` → respons-stream abonnerer fra 0.
2. Mobil baggrunder → socket kappes → respons-stream stopper, **baggrundstråd kører videre**.
3. Mobil vender tilbage → `subscribe?from=<offset>` → frames siden offset + live-hale → sømløst.
4. Run færdigt → `mark_done` → alle abonnenter får message_stop; svaret persisteret i DB.
5. Cross-device: desktop starter run → mobil kalder `/sessions/{id}/live` → attach.

## Fejlhåndtering

- **api-genstart midt i run:** in-memory-log + tråd dør → run interrupted (DB har
  delvist svar). Reconnect får 404 → fallback til `sessions.select`. Sjældent (`--workers 1`).
- **Ukendt/pruned run_id ved subscribe** → 404 → DB-fallback.
- **Hurtige/gentagne sends:** hvert send = eget run + egen log (ingen kollision).
  Backend-guard + klient-send-blok serialiserer.
- **Append/tee-fejl:** try/except-indkapslet; må aldrig vælte runnet eller afsenderens stream.
- **Flag OFF:** `server_authoritative_runs=false` i runtime.json → falder tilbage
  til A1-tee direkte stream (nuværende stabile adfærd), uden ny deploy.

## Test & udrulning (eksplicit imod A3-fejlen "verificeret med kun curl")

1. **Unit:** `tests/test_run_event_log.py` (append/read/offset/done/liveness/prune/cap),
   `tests/test_detached_run.py` (fresh tee, fejl→mark_done, aclose→unregister).
2. **Multi-klient integrationstest** (`tests/test_server_authoritative_runs.py`):
   (a) start run, (b) abonnér fra 0, (c) drop midt i, (d) gen-abonnér fra N,
   (e) hævd ingen huller + fuldført, (f) **golden-frame: byte-identiske frames vs.
   direkte sti** (desktop-kompat).
3. **Skygge-verifikation FØR live:** kør harness mod lokal api-instans til grønt;
   derefter deploy bag flag + on-device-smoke.
4. **Flag-rollout:** `server_authoritative_runs` i runtime.json. Deploy med flag
   OFF (nul adfærdsændring), verificér desktop uændret, flip ON, verificér mobil
   overlever baggrund. Kan slås fra øjeblikkeligt hvis noget overrasker.

## Leverancer

- Desktop urørt + verificeret uændret (golden-frame + flag-OFF-baseline).
- Mobil: svar overlever baggrund (auto-reconnect fra offset).
- Bidirektionel realtime-sync (desktop↔mobil via `/sessions/{id}/live`).
- Fundament klar til FCM-push (Stykke B).
- Zombie-slot kureret ved roden (unregister kører altid via aclose i finally).

## Ikke-mål

- FCM-push (Stykke B).
- Foreground service.
- Desktop-klient-migrering (kan følge senere; backend understøtter det allerede).
- Multi-worker/Redis-backed log (unødvendig med `--workers 1`; kan opgraderes ved skalering).
