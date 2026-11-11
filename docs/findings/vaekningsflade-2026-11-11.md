# Vækningsfladen — kortlægning 11/11-2026

Bestilling (Bjørn): én vækker (indbakken); andre kilder signalerer, indbakken vurderer og vækker.

## Målt (grep + læsning af hvert kaldested; AST-vagten i `tests/test_wake_gateway.py` måler det samme)

* **De «18 kaldesteder» er ikke 18 vækninger.** Af de nævnte filer er `workspace_context`,
  `autonomous_sessions` og `peak_varsel_daemon` KUN omtale i docstrings/kommentarer (ingen kode).
  `discord_gateway`, `dreaming_session`, `recurring_tasks` tæller to hver, men er hver ét kaldested
  (import + kald). Eksekverbare kaldesteder af `start_autonomous_run`: **13 filer**, plus
  `plugins.py` (ikke på listen) — og to filer starter runs via en ANDEN starter,
  `start_autonomous_stream_run`: `wakeup_dispatcher` og `agent_message_receipt`. Vagten dækker begge.
* **Præmissen «7 kopier af `_active_turn_blocks`» er forkert.** Den er defineret ÉT sted
  (`wakeup_dispatcher.py:118`); scheduled_tasks, agent_message_receipt, inbox_idle_waker,
  routine_dispatch og autonomous_side_task_dispatcher *importerer* den. `run_guard.py` og
  `routine_classification.py` omtaler den kun. Én definition er allerede sandt; en test låser det nu.
  (Det rigtige problem er at de 7 kaldere hver TOLKER svaret forskelligt — se nedenfor.)
* Indbakken kan bære det: `db_inbox.opret_eller_hent` er idempotent (dedup på `kilde_id`),
  `inbox_idle_waker` har allerede kandidat-regel, aktiv-guard, ét-spor-pr-post og rollback.

## Tabel

| Kilde | Vej i dag | Egen aktiv-guard | Gruppe |
|---|---|---|---|
| inbox_idle_waker | direkte (via `reserve_background_start`) | ja (fælles) | **waker** (den ene) |
| discord_gateway | direkte, tråd | nej (menneske skrev) | kanal-svar |
| telegram_gateway | direkte, tråd | nej | kanal-svar |
| routes/plugins.py (`/channel`) | direkte | nej | kanal-svar |
| scheduled_tasks (påmindelser) | direkte | ja (importeret) | vækning |
| recurring_tasks | via `dispatch_recurring` → legacy direkte | via run-guard i starter | vækning |
| dreaming_session | via `dispatch_system` → legacy direkte | nej | vækning |
| routine_trigger_adapters (heartbeat) | via `dispatch_system` → legacy direkte | nej | vækning |
| routine_dispatch | direkte | ja (importeret) | vækning |
| autonomous_side_task_dispatcher | direkte | ja (importeret) | vækning |
| wakeup_dispatcher | `start_autonomous_stream_run` | ja (definerer) | vækning |
| agent_message_receipt | `start_autonomous_stream_run` | ja (importeret) | vækning |
| jarvisx_processes (operator-wakeup) | direkte | nej, kun rate-limit | vækning |
| session_spawn (`start_session`-tool) | direkte | nej, rate-limit | vækning (Jarvis' eget valg) |
| visible_runs_memory (auto-continuation) | direkte efter sleep | eget re-check | vækning (fortsættelse) |

## Grænsen: vækning vs. kanal-svar

Test: **findes der et menneskes besked, som runnet er svar på, i samme øjeblik?**
Ja → kanal-svar: tidskritisk, og indbakkens «vent til intet kører» ville opsætte et svar til en
person der venter. Det er ikke en beslutning om at vække, men om at besvare. Nej → systemet
beslutter selv at starte et run → vækning, og SKAL gennem indbakkens vurdering.

**Tal: 3 kanal-svar, 11 reelle vækninger (+ waker selv = 15 filer med en starter).**
Af de oprindelige «18»: reelt 14 kaldested-filer ud over waker; 3 af de 18 var slet ingen kode.

## Hvad der er bygget (denne diff)

* `core/services/wake_gateway.py::anmod_om_vaekning(kilde, sag, tekst, …)` → `queued|deduped|rejected`
  + grund. Skriver en `vaekning`-post (ejer=jarvis, `kraever_handling=False`), starter intet,
  self-safe + logget. Dedup-nøgle = sagen.
* `inbox_state.KAN_DISPATCHES_KILDETYPER` + `inbox_idle_waker._er_moden/_dispatch_tekst`: waker kender
  `vaekning` og bruger postens tekst som direktiv.
* `tests/test_wake_gateway.py`: accept-tests + AST-vagt med ratchet (`TILLADT`), og en AST-test for
  at `_active_turn_blocks` kun defineres ét sted.

## IKKE gjort (bevidst)

Ingen af de 11 vækningskilder er migreret endnu. Hver har egen semantik der ikke kan flyttes
blindt: `recurring_tasks` bærer `task_id` og returværdi (`fire_count`), `scheduled_tasks` og
`routine_dispatch` vælger mål-session, `session_spawn` skal returnere en synkron kvittering til
tool-kalderen, `wakeup_dispatcher` skriver allerede selv en indbakke-post. Rækkefølge forslag:
1) dreaming/heartbeat (ingen returværdi), 2) operator-wakeup, 3) scheduled/routine/side-task
(samme session-valg som `_maal_session`), 4) recurring (kræver at waker kan bære `task_id`/origin),
5) wakeup_dispatcher/agent_message_receipt. `origin` (dream/heartbeat/…) går i dag tabt, da waker
altid bruger `origin="inbox"` — gatewayen bør bære det før migrering. Vagten kategoriserer dem som
`gaeld`; hver migration fjerner en linje i `TILLADT`.

## Migrering af wakeup_dispatcher

`wakeup_dispatcher.dispatch_due_wakeups()` starter ikke længere selv et run. Efter push-nudge,
heartbeat-tick og `pick_wakeup_run_target(...)` kalder den ÉT `wake_gateway.anmod_om_vaekning(
kilde="wakeup_dispatcher", sag="wakeup:<id>", tekst=direktiv_for(record), session_id=<mål>,
task_id=<record>, permission_session=<bookingens samtale>, bruger_id=<record.user_id>)`.
`set_context`/`reset_context` og `start_autonomous_stream_run` er væk fra filen; den er fjernet
fra `TILLADT`.

**Kontraktændring for `dispatched`:** før = «et run startede NU». Nu = «vækningen er afleveret til
indbakken, som vurderer og vækker». `queued` og `deduped` giver begge `dispatched=True` (dedup er
allerede afleveret, ikke et nyt run). `rejected` giver skip med
`skip_reason="gateway_rejected: <grund>"`; en kastet undtagelse giver stadig `run_start_failed: …`.
`empty_prompt` er uændret. Det er en bevidst ændring, ikke et tab: «dispatched» siger intet om,
at et run kører.

**Aktiv-guarden** (`_active_turn_blocks`) kaldes ikke længere af dispatcheren. Funktionen er stadig
DEFINERET i `wakeup_dispatcher.py` (præcis én definition), og `inbox_idle_waker` importerer den
derfra og bærer nu guarden: den vækker først når intet kører i sessionen. Følge: en vækning der
fyrer midt i en tur får ikke længere `dispatch_skipped="user_active"` fra dispatcheren; den står i
indbakken og løftes, når turen er forbi.

**Kendt forskel:** dispatcheren sætter ikke længere workspace-konteksten (`workspace_name`,
`user_display_name`, `role`, `context_channel`) omkring runnet. Gatewayen bærer kun `bruger_id`,
så disse felter videregives ikke. Se om `inbox_idle_waker._start_run` selv sætter konteksten.

## Rettelse til rækkefølgen — målt 11/11-2026 (sen aften)

Den foreslåede rækkefølge ovenfor («1) dreaming/heartbeat — ingen returværdi») er
**forkert**, og kriteriet var det også. Returværdi er ikke det der afgør om en kilde
kan migreres. Det er **hvor runnet hører hjemme**.

**Målt:** `dreaming_session` kalder `start_autonomous_run(..., session_id=None,
origin="dream")` og `routine_trigger_adapters._legacy` kalder den med
`session_id=None, origin="heartbeat"`. Begge kører bevidst i deres EGEN silo.
`inbox_idle_waker._maal_session` falder tilbage til
`pick_wakeup_run_target(channel="app", ...)` → **ejerens app-samtale**.

Konsekvens hvis de blev migreret blindt: hver drømmesession og hvert
heartbeat-initiativ ville lande som et run i Bjørns desk-chat. Det er ikke «én
vækker», det er støj i hans samtale — og drømmen gør sig allerede synlig i
indbakken via `_registrer_dream_i_indbakken` (kildetype `dream`,
`IKKE_GATENDE_KILDETYPER`), så synligheden findes i forvejen ad en anden vej.

**Derfor:** dream og heartbeat migreres IKKE, medmindre vækkeren først kan starte et
run i kildens egen silo (`session_id=None`) for system-origins. Det er en ændring af
`_start_run`s kontrakt («session_id er PÅKRÆVET»), ikke en migrering.

**Rettes til:**

1. `scheduled_tasks` — har `target_session` og kanal-guard i forvejen. **Blokeret
   11/11:** `tests/test_scheduled_tasks.py::test_scheduled_run_kan_ikke_lande_i_discord`
   håndhæver den gamle kontrakt (monkeypatcher `start_autonomous_run`). Migrationen
   blev prøvet og rullet tilbage — den skal omskrives sammen med testen, ikke før.
2. `routine_dispatch`, `autonomous_side_task_dispatcher` — samme form som (1).
3. `session_spawn`, `visible_runs_memory`, `jarvisx_processes` — egne kontrakter
   (synkron kvittering / auto-continuation / operator-vækning).
4. dream, heartbeat — **ikke** vækninger. Se ovenfor.

## Forudsætningen er bygget (commit 9a9ce9baf)

`inbox_items.origin` (TEXT NOT NULL DEFAULT '') + `origin` gennem
`anmod_om_vaekning` og `inbox_idle_waker._start_run`. Gatewayen falder tilbage til
`kilde`, så «hvem vækkede mig» altid kan besvares. Uden dette tabte HVER migrering
sin herkomst i det tavse: wakeren skrev altid `origin="inbox"`.

## Målt 11/11-2026 (aften) — hvad der faktisk mangler, og hvorfor

Tre kilder er migreret: `wakeup_dispatcher` (9edc428d6), `scheduled_tasks`
(35657c3e2), `recurring_tasks` (fb89d5af5). Forudsætningen `inbox_items.origin`
blev bygget først (9a9ce9baf), fordi vækkeren ellers skrev `origin="inbox"` for alt.

### routine_dispatch — BLOKERET, ikke glemt

Den ser ud som en ren kandidat (bærer allerede `session_id` og `task_id=run_id`),
men den bærer fire ting gatewayen ikke tager imod:

    start_autonomous_run(
        ..., max_tool_calls=int(permission["max_tool_calls"]),
        max_seconds=float(permission["max_seconds"]),
        tool_scope=str(definition["capability_scope"]),
        completion_callback=completed,     # afregner claimet via _settle_session_run
    )

`completed` er ikke kosmetisk: den kalder `_settle_session_run`, som frigiver
`db_routines.claim_run`-leased og skriver `session_dispatched`-eventet. Migrerer
man uden den, hænger claimet til leasen udløber, og rutinen ser aldrig afregnet ud.

**Konsekvens:** `anmod_om_vaekning` skal kunne bære budget (`max_tool_calls`,
`max_seconds`), `tool_scope` og en completion-callback FØR denne kilde kan flyttes.
Det er en kontrakt-udvidelse, ikke en omskrivning af kaldestedet.

### De øvrige, med deres egen grund

| Kilde | Dom | Grund |
|---|---|---|
| `dreaming_session` | migreres IKKE | kører bevidst `session_id=None` i egen silo; `_maal_session` falder tilbage til ejerens app-samtale, så en blind migrering flytter hver drøm ind i Bjørns desk-chat |
| `routine_trigger_adapters` | migreres IKKE | `origin="heartbeat"`, samme silo-problem |
| `autonomous_side_task_dispatcher` | BLOKERET | bærer `max_tool_calls`, `max_seconds`, `started_callback`, `completion_callback` |
| `session_spawn` | ikke en vækning | et værktøj jeg kalder for at starte et run i en navngiven session — hører i `kanal` |
| `jarvisx_processes` | ikke en vækning | API-rute der vækker fra UI med egen rate-limit — `kanal`-lignende |
| `visible_runs_memory` | uafklaret | continuation-run efter et run; ikke undersøgt |

**Netto:** af de syv er to ikke vækninger, to skal ikke migreres, to er blokeret på
samme kontrakt-udvidelse, og én er uafklaret. Den næste rigtige bid er derfor
kontrakt-udvidelsen — ikke endnu en kildemigrering.

## Kontrakt-udvidelsen: budgettet er baaret, callbacken er ikke (11/11-2026, sen aften)

**Løst — `15841aa85`.** `max_tool_calls`, `max_seconds` og `tool_scope` er nu
tre kolonner i `inbox_items` (32 i alt) og baeres hele vejen:
gateway → post → waker → starter. `0` betyder «intet loft» og er en gyldig
vaerdi, ikke en manglende; wakeren sender derfor kun feltet videre naar kilden
faktisk satte en graense. Bevis: `test_budget_naar_hele_vejen_til_starteren`
fejler paa kode uden videresendelsen i wakeren — maalt, ikke antaget.

**Ikke løst — callbacken, og grunden er maalt.** `completion_callback` er en
proces-lokal Python-funktion. Den kan ikke serialiseres i en DB-post, saa den
kan ikke baeres gennem indbakken som de tre felter.

Det afgoerende spoergsmaal er HVOR vaekningen sker. Maalt:
`vaek_paa_aabne_poster` kaldes kun fra `scheduled_tasks` (samme proces som
bookingen), mens `routine_dispatch` kaldes fra `routine_runner` — en poller i
runtime-processen. En in-memory registrering noeglet paa postens `kilde_id`
virker derfor for `scheduled_tasks`, men IKKE for `routine_dispatch`: den
bookes i én proces og vaekkes i en anden.

**Konsekvensen er konkret:** `_SESSION_LEASE_SECONDS = 900`, og leasen fornyes
ikke. Uden `completed`-callbacken staar `db_routines.claim_run`-claimet i op
til 15 minutter efter hvert rutine-run, og `session_dispatched`-eventet
skrives aldrig. Rutinen ser ikke afregnet ud, selv om den er faerdig.

**Naeste skridt er derfor ikke en registrering, men en beslutning:** enten
(a) en cross-process afregning — `routine_runner` poller selv sine aabne
claims og afregner dem, saa callbacken bliver overfloedig, eller (b) en
DB-baaret afregnings-post som wakeren skriver naar runnet slutter. (a) er
husets moenster: tilstanden ligger allerede i `db_routines`, og en poller der
laeser sin egen sandhed er staerkere end en closure der skal overleve en
procesgraense.
