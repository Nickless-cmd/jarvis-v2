# Build plan — `Task(team)` mod den faktiske kode

**Kontrakt:** `docs/specs/2026-11-10-task-team-og-en-agentdoer.md` v5 (2026-11-10).
**Denne fil er arbejdsplanen, ikke kontrakten.** Spec'en siger *hvad der skal være sandt*; her står
*hvor i koden det sker, og hvordan vi ved det virker*. Er de to i konflikt, vinder spec'en.

**Målt udgangspunkt (10/11-2026), verificeret mod kilden i denne session:**

| Fil | Linjer | Hvad den ejer i dag |
|---|---|---|
| `core/runtime/db_agent_council.py` | 119 | Tabellen, `create()`, `set_members()`, `transition()`, `open_councils()` |
| `core/services/agent_council.py` | 267 | `convene()`, `advance()`, `_abandon()`, `synthesis_goal()`, `_wake_parent_on()` |
| `core/services/agent_task_facade.py` | 235 | `derive()`, `execute()`, `canonical`, `_BUDGET_DEFAULT` |
| `core/services/agent_contract_service.py` | 874 | `dispatch_agent()`, `supervise()` → `advance_councils()` |
| `core/runtime/db_agent_wait.py` | — | `register_wait()` — ingen unik nøgle |
| `core/tools/agent_contract_tools.py` | 482 | `_exec_task()` (kaster `team` væk), `Task`-skemaet |
| `core/tools/tool_scoping.py` | — | `RETIRED_AGENT_CREATION_TOOLS` (fem navne) |

**Eksisterende testdækning der skal genbruges, ikke genopfindes:**
`tests/test_agent_council.py` (337 linjer, 23 tests) · `tests/test_db_agent_council.py` ·
`tests/test_agent_task_facade.py` (164) · `tests/test_agent_contract_tools.py` (482) ·
`tests/test_db_agent_wait.py` · `tests/test_agent_orchestration.py`.

---

## Leverance 1 — R0: `PROVISIONING` og de tre statusser

**Hvorfor først:** dette er den ene fejl der kan give et svar uden grundlag. `create()` indsætter
rækken med `members_json='[]'`, og `advance()` kan nå at se `([], True)` → en syntese over nul
medlemmer.

**Ændringer:**

1. `db_agent_council.py` — `ensure_council_tables()`: tilføj kolonnerne `stalled_after_at` (TEXT,
   default `''`) og `synthesis_wake_registered_at` (TEXT, default `''`). Brug samme
   `ALTER TABLE`-mønster som `db_agent_deadlines.ensure_deadline_columns()` — kolonnerne skal kunne
   tilføjes til en eksisterende tabel uden at tabe data.
2. `db_agent_council.py` — tilføj `PROVISIONING = "provisioning"` og
   `OPEN_STATUSES = frozenset({PROVISIONING, GATHERING, SYNTHESIZING})`.
3. `db_agent_council.py` — `create()`: indsæt med `PROVISIONING`, ikke `GATHERING`.
4. `db_agent_council.py` — `set_members()`: efter `UPDATE members_json`, kald `transition()` fra
   `PROVISIONING` til `GATHERING`. Er rækken allerede `GATHERING` (en retry), skal det ikke fejle.
5. `db_agent_council.py` — `open_councils()`: brug `OPEN_STATUSES` i stedet for de to hårdkodede
   værdier. Byg `IN (?,?,?)` fra mængden, ikke en literal.
6. `agent_council.py` — `_abandon(owner, session, cid, started, frm)`: `frm` bliver en parameter.
   Kaldes med `PROVISIONING` når afvisningen sker før `set_members()`, ellers `GATHERING`.
7. `agent_council.py` — `advance()`: spring alt i `PROVISIONING` over (`continue`), så racen ikke
   kan give en syntese.

**Tests (skal fejle uden rettelsen):**
- `create()` returnerer `status == "provisioning"`.
- `advance()` på et team i `PROVISIONING` giver `[]` og opretter intet assignment.
- `set_members()` flytter `provisioning → gathering`.
- `_abandon(..., frm=PROVISIONING)` ender i `cancelled`, ikke i en fastlåst række.
- `OPEN_STATUSES` indeholder præcis tre statusser, og `open_councils()` finder alle tre.

**Review-port:** ja. Spørgsmålet til revieweren: *kan et team stadig få en syntese uden medlemmer —
ad hvilken som helst vej, inklusive genstart og to supervisere?*

---

## Leverance 2 — §5.2: betinget `canonical`

**Hvorfor:** tilføjes `team_id` og `member_index` ubetinget, får **alle** single-agents nye idem- og
mandat-id'er, og enhver replay brækker.

**Ændringer:**

1. `agent_task_facade.py` — `derive()` får to nye valgfrie parametre: `team_id: str = ""` og
   `member_index: int = 0`.
2. `derive()` — `canonical` udvides **kun** når `team_id` er ikke-tom:
   `canonical["team_id"] = team_id` og `canonical["member_index"] = member_index`.
   Er `team_id` tom, er `canonical` byte-identisk med i dag.
3. `derive()` — `idem` og `mandate_id` udledes uændret af `canonical`. Ingen anden ændring.

**Tests:**
- **Test 1 (accepttest):** gem hashen af `canonical` for et fast input **før** ændringen (som en
  literal streng i testen), og assert at den er identisk efter. At genberegne formlen to gange i
  samme kørsel beviser intet.
- Et team-medlem (`team_id` sat) får en **anden** `idem` end den samme agent uden `team_id`.

**Review-port:** ja. Fejl her brækker replay for alt eksisterende arbejde.

---

## Leverance 3 — §5.3: deterministisk `team_id`

**Hvorfor:** et tilfældigt `team_id` gør retry farligt — et gentaget kald efter et tabt svar starter
N nye agenter.

**Ændringer:**

1. `agent_task_facade.py` — ny funktion `derive_team_id(...)`: hash af owner, session, parent_run,
   description, prompt, `team.name`, og medlemmernes `role`+`task` **i bestilt rækkefølge**.
   Returnerer `"team-" + hex[:16]` (§15.3).
2. Rækkefølgen skal være den bestilte — ikke sorteret. En retry med ombyttede medlemmer skal give et
   nyt id, fordi det er et andet team.
3. `member_index` = medlemmets position i den bestilte liste (1-baseret).

**Tests:**
- **Test 3 (accepttest):** samme `Task(team=…)` to gange giver samme `team_id` og `replayed: true`.
- Ændret rækkefølge giver et nyt `team_id`.
- `team_id` starter med `team-` (kanttilfælde 18).

**Review-port:** ja.

---

## Leverance 4 — §6.2/§6.3: `derive_team()` og syntese gennem `execute()`

**Hvorfor:** et gemt mandat er det eneste der håndhæver `max_fanout`, `max_depth`, værktøjsliste og
deadline. Går en assignment uden om `derive()`, er `max_fanout: 0` virkningsløs.

**Ændringer:**

1. `agent_task_facade.py` — ny `_member_type(team_type: str) -> str`: standard `researcher`;
   `critic`/`planner`/`watcher` tillades; `executor` afvises med `ValueError`. Spærringen ligger på
   **kind**, ikke på rollenavnet (§7.2).
2. `agent_task_facade.py` — ny `derive_team(...)`: validerer **før** første dispatch (2–6 medlemmer,
   unikke `task`, tomt `team.name` afvises — kanttilfælde 7). Kalder `derive()` per medlem med
   `team_id` og `member_index`. Returnerer en liste af planer.
3. `agent_council.py` — `advance()`: syntesen dispatches gennem `derive()` + `dispatch_agent(mandate=…)`,
   præcis som `execute()` gør det (`derive` → pop `mandate` og `run_in_background` → `dispatch_agent`
   med identitetsfelterne fra input). `subagent_type="critic"` (§6.3).
4. Syntesen får dermed sit eget gemte mandat, egen værktøjsliste, egen deadline — og nul skriveret.

**Tests:**
- **Test 2 (accepttest):** 3 medlemmer → 3 forskellige `mandate_id`, alle `max_fanout: 0` og
  `max_depth: 0` i `agent_assignment_mandates`.
- `Task(subagent_type="executor", team={…})` afvises (§7.2, test 4).
- 7 medlemmer afvises før første dispatch; 1 medlem afvises med henvisning til almindelig `Task`.
- To medlemmer med samme `task` afvises; samme `role` med forskellig `task` tillades.
- Syntesen har et gemt mandat (slå op i `agent_assignment_mandates`).

**Review-port:** ja — dette er autoritetsgrænsen.

---

## Leverance 5 — §6.4: vagten må ikke læse medlemmernes citater

**Hvorfor:** `synthesis_goal()` indlejrer medlemssvar ordret. Skriver et medlem "kør `bash`", matcher
`ufuldstaendige_vaerktoejer` det og kaster `ValueError` **ved hvert tick**. Teamet ender i `stalled`.

**Ændringer:**

1. `agent_council.py` — `synthesis_goal()` returnerer to dele, adskilt eksplicit: `instruktion` og
   `datagrundlag`. Grænsen skal være i koden (fx en tuple eller to navngivne felter), ikke implicit i
   teksten.
2. `agent_task_facade.py` — `derive()` (eller den nye `derive_team()`) kører
   `ufuldstaendige_vaerktoejer` **kun** på instruktionen når det er en syntese. Tilføj en eksplicit
   parameter (fx `guard_text: str | None`) frem for at gætte ud fra indholdet.

**Tests:**
- **Test 5 (accepttest):** et medlem svarer "kør `bash` og læs filen" → syntesen oprettes stadig.
- En syntese-instuktion der **selv** kræver et værktøj den ikke har, afvises stadig.

**Review-port:** nej — lille, men testen skal fejle uden rettelsen.

---

## Leverance 6 — §8.5: tærskel for alle åbne tilstande + `STALLED` vækker

**Ændringer:**

1. `db_agent_council.py` — tilføj `STALLED = "stalled"`. `OPEN_STATUSES` er uændret (STALLED er ikke
   åben — den er terminal-for-sweepen, men skal stadig kunne ses).
2. `stalled_after_at` sættes ved indgang til **enhver** åben tilstand: `PROVISIONING` (ved create),
   `GATHERING` (ved set_members), `SYNTHESIZING` (ved transition).
3. For `SYNTHESIZING` er tærsklen syntesens **egen** start + dens deadline + margin — ikke teamets.
4. Ny `expire_stalled()` (eller en gren i `advance()`): find teams i `OPEN_STATUSES` med
   `stalled_after_at < now()`, sæt `STALLED`, og **væk parenten**.
5. `agent_contract_service.supervise()` kalder den — den kører allerede `advance_councils()`.

**Tests:**
- **Test 6 (accepttest):** en syntese der aldrig bliver terminal → `STALLED` + vækning.
- `stalled_after_at` er sat i alle tre åbne tilstande, ikke kun `GATHERING`.
- Et team i `STALLED` vækker parenten præcis én gang.

**Review-port:** ja.

---

## Leverance 7 — §8.4: idempotent `register_wait` + `DONE`-kravet

**Ændringer:**

1. `db_agent_wait.py` — `register_wait()`: før den indsætter, slå op på
   `(parent_run_id, assignment_ids_json, condition)`. Findes kontrakten, returnér den i stedet for at
   lave et nyt uuid. Tilføj en unik index der håndhæver det i DB'en, ikke kun i Python.
2. `agent_council.py` — `_wake_parent_on()`: skriv `synthesis_wake_registered_at` når registreringen
   lykkes. Svarer **succes** når `parent_run_id` er tom (der er ingen at vække) — ellers kører løkken
   evigt på en betingelse der aldrig kan opfyldes.
3. `advance()` — `SYNTHESIZING → DONE` kræver at `synthesis_wake_registered_at` er sat, eller at
   `parent_run_id` er tom. Ellers bliver teamet i `SYNTHESIZING` og forsøger igen næste sweep.
4. Registreringen kører igen ved hvert sweep indtil den lykkes.

**Tests:**
- **Test 7 (accepttest):** to kald med samme `(parent_run, assignments)` giver **én** kontrakt.
- `DONE` nægtes når registreringen mangler og `parent_run_id` er sat.
- Tom `parent_run_id` → `_wake_parent_on()` svarer succes og teamet kan gå til `DONE`.

**Review-port:** ja.

---

## Leverance 8 — §4/§11: `Task`-skemaet + prompten i samme commit

**Ændringer:**

1. `agent_contract_tools.py` — `Task`-skemaet: tilføj `team` (object med `name` og `members`), sæt
   `additionalProperties: false` på `Task`'s `parameters`. `team` er **ikke** required.
2. `agent_contract_tools.py` — `_exec_task()`: læs `team` og send det videre til facaden. I dag
   læses fem felter og resten kastes.
3. `prompt_sections/agent_orchestration.py` — nævn `team` **først når skemaet har det**, i samme
   commit. Et løfte om et felt der ikke findes er den fejl der startede hele runden (§0, runde 1).
4. `tests/test_agent_orchestration.py` — udvid `test_agent_orchestration.py:58` til også at dække
   `team`, så testen fanger næste gang nogen skriver et felt ind i prompten før skemaet.

**Tests:**
- **Test 8 (accepttest):** prompten nævner intet felt `Task` ikke har.
- Et ukendt felt på `Task` afvises (`additionalProperties: false`) i stedet for at blive ignoreret.
- `team` udeladt → byte-identisk adfærd med i dag.

**Review-port:** ja — samme commit, ellers lyver prompten.

---

## Leverance 9 — §10: de tre navne i `RETIRED_AGENT_CREATION_TOOLS`

**Ændringer:** `tool_scoping.py` — tilføj `relay_to_agent`, `cancel_agent` og `convene_agent_council`
til `RETIRED_AGENT_CREATION_TOOLS`. Listen har i dag fem navne (`scout_agent`, `spawn_agent_task`,
`dispatch_code_mode_task`, `dispatch_to_claude_code`, `task`) — det er **fem**, ikke tre, og spec'ens
§10 er rettet til at sige det.

**Tests:** navnene er i listen, `is_tool_allowed()` afviser dem, og `load_more_tools` kan ikke
genoplive dem.

**Review-port:** nej — selvstændig lille opgave.

---

## Leverance 10 — §17.1: e2e-testen

**Fil:** `tests/e2e/test_team_e2e.py`, efter husets mønster (`isolated_runtime`, service-niveau, ingen
live klient — se `tests/e2e/test_override_e2e.py`).

**Seks trin, og rækkefølgen asserteres — ikke kun sluttilstanden:**
bestil 3 medlemmer gennem `Task`-facaden → 3 assignments, 3 `mandate_id`, alle `max_fanout: 0`, teamet
i `GATHERING` → gør dem terminale (én completed med svar, én uden, én failed) → `supervise()` →
syntese oprettet med gemt mandat og fejlende navngivet → gør syntesen terminal → `supervise()` →
`DONE` og præcis **én** `fired` ventekontrakt.

**Review-port:** ja — dette er den samlede bevisførelse.

---

## Leverance 11 — §17.2: drift-verifikation (kan ikke gøres af en agent)

Fem målinger på CT105 efter deploy. Indtil de er taget, er status «implementeret, ikke verificeret i
drift» — en anden status end «færdig». Målingerne står i spec'ens §17.2.

---

## Arbejdsform for agent-kørslen

Hver leverance køres som **én `Task`** med `subagent_type="executor"` mod repoet, med:

- **kravet** = leverancens række i §14 plus dens afsnit i spec'en,
- **beviset** = den grønne test (ikke en beskrivelse af hvad der blev gjort),
- **review-porten** = `review_agent_work` med kravet som `requirements`.

Mellem leverancerne læses **diffen**, ikke agentens konklusion. En leverance der melder «færdig» uden
en grøn test er ikke færdig.

**Rækkefølgen må ikke ændres:** leverance 2 ændrer id-genereringen for alt efterfølgende, og
leverance 1 lukker den ene fejl der kan give et svar uden grundlag.
