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
