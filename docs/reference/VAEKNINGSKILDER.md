# Vækningskilder — hvad der kan starte et run for Jarvis

**Målt:** 11/11-2026, verificeret mod kilden (ikke mod hukommelsen).
**Status:** arkitekturen er under migrering. Der findes nu **to** veje: den gamle
(spredte kildetyper via `registrer_kilde`) og den nye (én indgang via
`wake_gateway`). Begge er aktive samtidig — se §4.

---

## 1. Den nye vej: én indgang (indført 11/11-2026)

`core/services/wake_gateway.py:70` — `anmod_om_vaekning(...)`

Kontrakten står i modulets docstring, linje 1: **kilderne SIGNALERER, indbakken
VURDERER og vækker.** En kilde starter aldrig selv et run. Den skriver kun en
anmodning af kildetypen `vaekning`, og indbakken afgør resten.

Posten bærer **aldrig** `kraever_handling` (den må ikke nægte en mutation i et
kørende run), og den er **moden i det øjeblik den skrives** — det er kildens
egen anmodning, ikke en tidsplan.

Migreret til gatewayen (målt 11/11-2026):

| Kilde | Sted |
|---|---|
| Planlagte opgaver | `core/services/scheduled_tasks.py:420` |
| Self-wakeup | `core/services/wakeup_dispatcher.py:369` |
| Agent fuldført | `core/services/agent_message_receipt.py:149` |
| Session-rutiner | `core/services/routine_dispatch.py:127` |
| Gentagende opgaver | `core/services/recurring_tasks.py:1074` |

**Ikke migreret endnu** — de skriver stadig deres egen kildetype direkte:
`ci_status_watch.py:313`, `decision_adherence_gate.py:332`,
`run_closure_gate.py:463` og `:792`, `scout_inbox_delivery.py:81`,
`self_wakeup.py:285`, `routine_runner.py:61`, `routine_diagnostics.py:85`,
`scheduled_inbox.py:58`, `restart_self_tools.py:467`.

---

## 2. Den gamle vej: den fælles skriver

`core/services/inbox_state.py:470` — `registrer_kilde(...)`

Idempotent per `(bruger, kildetype, kilde_id)`. Alle kilder — gamle som nye —
ender her. Kildetypen er en fri streng, men de to sæt nedenfor afgør hvad den
må.

---

## 3. Tre klasser af kildetyper

### 3a. Må starte et run — `KAN_DISPATCHES_KILDETYPER`
`core/services/inbox_state.py:130`

```
wakeup · afvist_run · ci_alarm · recurring · vaekning
```

Sættet siger **kun** «denne post må starte et run». Det rører ikke
gating-flaget. Sættet er stabilt uanset postens alder — det er nødvendigt, fordi
`kraever_handling` falder ved udløb (`_FRIST_DAGE`), og alle 148 `wakeup`-rækker
stod målt 13/10-2026 med `kraever_handling=0` alene fordi de var gamle.

### 3b. Må oprette, aldrig nægte en mutation — `IKKE_GATENDE_KILDETYPER`
`core/services/inbox_state.py:80`

```
daemon · heartbeat · recurring · approval · digest · proposal · decision ·
agent_result · scheduled · routine_event · background_attention ·
run_closure · genstart · dream
```

Grænsen er hele kontrakten: **kun det du selv har lovet kan blokere.** Husets
begivenheder informerer. Uden dette led kunne en post fra et afluttet run gate
det næste værktøjskald — den lammelse kostede 8,5 timer 12/10-2026.

### 3c. Den tredje klasse
Kan dispatche, men aldrig gate — defineret lige efter 3b i samme fil.
Se `_kilde_ejer_kan_loefte` (`inbox_state.py:455`).

### 3d. Modenhed — det afgørende led
`core/services/inbox_idle_waker.py:78` — `_er_moden(post, vaekninger=...)`

At en kildetype **må** dispatche er ikke nok. Posten skal også være **moden**.
Kanonisk eksempel: en baggrunds-rutine har kildetypen `recurring` (som må
dispatche), men `_er_moden` svarer kun ja for de rutiner der er bundet til en
samtale (`recurring_tasks.session_id`). Uden den todeling ville alle levende
gentagende opgaver — inkl. den 4×daglige inspektion — begynde at vække runs.

Kandidatudvælgelsen: `kandidater()` i `inbox_idle_waker.py:133`.
Selve starten: `_start_run()` i samme fil, linje 273.

---

## 4. Kilderne, grupperet

### 4a. Indgående — dig
| Kanal | Sted |
|---|---|
| webchat / Desk | API-ruten, starter turen direkte |
| Discord DM | `core/services/discord_gateway.py:1483` |
| Telegram | `core/services/telegram_gateway.py` |
| JarvisX-processer | `apps/api/jarvis_api/routes/jarvisx_processes.py:596` |

### 4b. Uret — fyrer kun fordi heartbeat-tick tikker (15 min)
⚠️ **Afhængigheden er absolut:** står heartbeat-scheduleren stille, står **alle**
ur-baserede kilder stille. Se §6.

| Kilde | Sted | Bemærkning |
|---|---|---|
| Planlagte opgaver | `scheduled_tasks.py:420` → `scheduled_inbox.py:58` | kildetype `scheduled` |
| Gentagende opgaver | `recurring_tasks.py:1074` | kun **session**-rutiner vækker |
| Self-wakeup | `wakeup_dispatcher.py:369` | den største enkeltkilde |
| Poller-løkken | `scheduled_tasks.py:515` → `vaek_paa_aabne_poster` | den **generelle** vækker |

Periodiske jobs kører **inde i** heartbeat og vækker ikke selv:
chronicle 24 t · personality 4 t · weekly manifest 7 d · goal synthesis 7 d ·
quarterly arc 91 d.

### 4c. Huset — begivenheder der banker på
| Kilde | Sted | Kildetype |
|---|---|---|
| Agent fuldført | `agent_message_receipt.py:149` → `scout_inbox_delivery.py:81` | `agent_result` |
| Agent-vækning efter `wait_agents` | `agent_wake_intentions.py` → `visible_run_recovery_dispatcher.py` (egen tråd, 5 s kadence) | — |
| CI-alarm | `ci_status_watch.py:313` | `ci_alarm` |
| Drøm | `dreaming_session.py:354` | `dream` |
| Beslutnings-trigger | `decision_adherence_gate.py:332` | `decision` |
| Run-lukning | `run_closure_gate.py:463` og `:792` | `run_closure` |
| Baggrunds-opmærksomhed | `background_attention.py:157` | `background_attention` |
| Worktree-beslutning | `agent_contract_service.py:704` | `worktree_decision` |
| Afvist run | `run_guard.py:177` | `afvist_run` |
| Genstart | `restart_self_tools.py:467` | `genstart` |

### 4d. Selv-bestilt — dem Jarvis beder om
| Kilde | Sted |
|---|---|
| `start_session` (loft 10/time) | `core/services/session_spawn.py:50` |
| Side-opgave-vækker | `core/services/autonomous_side_task_dispatcher.py:180` |
| Session-rutiner | `core/services/routine_dispatch.py:127` |
| Runtime hooks | `core/services/runtime_hooks.py:71` (`origin=hook:<event>`) |
| Runtime-executive | `core/services/runtime_action_executor.py:338` |
| Autonomi-forslag | `core/services/autonomy_proposal_queue.py:566` og `:639` |
| Continuation | `core/services/visible_runs_memory.py:542` |

---

## 5. Værnene — tre karantæner

`core/services/wakeup_dispatcher.py`

| Konstant | Værdi | Linje | Betydning |
|---|---|---|---|
| `_ACTIVE_TURN_FRESH_S` | 120 s | 41 | en tur er i live |
| `_BRUGER_KARANTAENE_S` | 600 s | 46 | du skrev lige |
| `_JARVIS_KARANTAENE_S` | 300 s | 61 | jeg skrev lige |

Kontrolfunktionerne: `_bruger_skrev_for_nylig` (:64),
`_jarvis_skrev_for_nylig` (:71), `_nylig_rolle_i_session` (:84),
`_active_turn_blocks` (:118). Dispatch: `dispatch_due_wakeups` (:264).

Det er derfor de fleste wakeups står med
`dispatch_skipped: session_har_levende_run` — målt 21 i nat.

Informerende poster (`kraever_handling=0`) starter **aldrig** et run. De venter
på at nogen kigger.

---

## 6. Afhængigheden der kan lamme alt

**Målt 11/11-2026 kl. 18:54–20:25:** `heartbeat_runtime_state` stod med
`scheduler_active = 1`, `scheduler_health = "active"`, `next_tick_at` løbende
frem — men `heartbeat_runtime_ticks` fik **ikke én række** i 71 minutter.
Flaget påstod liv, ingen målte livet.

Konsekvensen er ikke kosmetisk: netværkshelbreddet måles i tick-loopet, så da
scheduleren stoppede, stoppede målingen med den. Den røde post (`16954`) blev
hængende i `resolved = 0` — ikke fordi netværket var rødt, men fordi ingen
kiggede efter.

Dette er **anden gang** samme fejlform. `heartbeat_scheduler.py:50–56` siger det
selv om stilstanden 2/9-2026: «`scheduler_active` stod på true hele vejen
igennem, mens intet slag faldt.» Fixet dengang gjorde stilstanden *læsbar* — det
forhindrede den ikke.

Spor: `side-5e69324fce`. `is_running()` og `iterations()` findes allerede i
`heartbeat_scheduler.py:57–72`, bygget præcis til at skelne «tråden er væk» fra
«tråden kører men slaget falder ikke».

---

## 7. Fælder

- **`resolved = 0` betyder ikke «uløst problem».** Målt 11/11-2026: 10 uløste
  poster, kun **1** var `error`. De ni andre var `info`-støj. Filtrér på
  `severity`, aldrig på `resolved` alene.
- **`origin` gemmes ikke i `visible_runs`.** Kilden kan ikke læses tilbage fra
  run-tabellen.
- **`start_autonomous_run` er ikke længere den eneste vej.** Den findes stadig
  (`visible_runs_memory.py:542`, `discord_gateway.py:1483`,
  `session_spawn.py:120`, `inbox_idle_waker.py:355`,
  `autonomous_side_task_dispatcher.py:180`, `dreaming_session.py:432`,
  `jarvisx_processes.py:596`, `routine_trigger_adapters.py:244`), men nye kilder
  bør gå gennem `wake_gateway`.
- **Vækkeren bruger den AKTUELLE workspace.** `vaek_paa_aabne_poster` kalder
  `bruger_for_workspace(current_workspace_name())` — en post for Michelles
  workspace vågner ikke fra Bjørns kontekst. Ægte begrænsning, ikke rettet.

---

## 8. Målt fordeling i drift (11/11-2026)

1.023 poster i `inbox_items` fordelt på 18 kildetyper:

```
wakeup 498 · decision 179 · agent_result 51 · scheduled 47 · run_closure 47 ·
dream 44 · recurring 41 · genstart 39 · background_attention 26 ·
worktree_decision 24 · afvist_run 20 · job 13 · routine_event 6 ·
agent_smith 6 · test 4 · proposal 1 · daemon 1 · ci_alarm 1
```

**Den største kilde er mine egne self-wakeups** — 498, mere end alt andet
tilsammen. Næststørst er beslutnings-triggerne (179), og først derefter dine
bookede opgaver (47).

⚠️ `agent_smith` (6 poster) er ikke kortlagt i koden som en egen vækningskilde.
Den står som åben undren — ikke gættet her.
