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

## Leverance 8 — §4/§11: `Task`-skemaet + prompten i samme commit ✅ LEVERET (verificeret 11/11-2026)

**Målt mod hovedtræet 11/11-2026 — alle fire punkter er i koden:**

| Punkt | Bevis |
|---|---|
| `team` i `Task`-skemaet | `agent_contract_tools.py:85` — object med `name` + `members`, ikke required |
| `additionalProperties: false` | `agent_contract_tools.py:54` via `additional_properties=False` |
| `_exec_task()` læser `team` | `agent_contract_tools.py:311-315` → `execute_team(**fields, team=team)` |
| Prompten nævner `team` | `prompt_sections/agent_orchestration.py:49-50` |
| Testen binder dem sammen | `tests/test_agent_orchestration.py:72` — fejler hvis skema og prompt glider fra hinanden |

**Bevis:** 17 grønne i `tests/test_agent_orchestration.py`.

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

## Leverance 9 — §10: de tre navne i `RETIRED_AGENT_CREATION_TOOLS` ✅ LEVERET (`b9fd86628`)

**Målt mod hovedtræet 10/11-2026 — spec'ens §10 bad om tre navne, men kun ét var dødt:**

| Navn | Fandt vi | Handling |
|---|---|---|
| `relay_to_agent` | **Findes og er aktiv** (`simple_tools.py:2060`) | Tilføjet til listen — afvises nu også for owner |
| `cancel_agent` | **Findes, bevidst i owner-only-listen** (`tool_scoping.py:103`) | **Ikke** pensioneret — den er ikke død |
| `convene_agent_council` | **Findes nul steder** i hovedtræet; kun i en gammel `.claude/worktrees/`-kopi, og `tests/test_agent_council.py:329` beviser den allerede er ude af `CONTRACT_TOOL_NAMES` | Intet at pensionere |

**Bevis:** `is_tool_allowed(role="owner", name="relay_to_agent")` er `False`, mens samme kald for
`cancel_agent` er `True`. 151 grønne på tværs af loop, contract_tools, orchestration, council, facade
og den nye test.

**Review-port:** nej — selvstændig lille opgave.

---

## Leverance 10 — §17.1: e2e-testen ✅ LEVERET (`1df48db2e`)

**Fil:** `tests/e2e/test_team_e2e.py`, efter husets mønster (`isolated_runtime`, service-niveau, ingen
live klient — se `tests/e2e/test_override_e2e.py`).

**Seks trin, og rækkefølgen asserteres — ikke kun sluttilstanden:**
bestil 3 medlemmer gennem `Task`-facaden → 3 assignments, 3 `mandate_id`, alle `max_fanout: 0`, teamet
i `GATHERING` → gør dem terminale (én completed med svar, én uden, én failed) → `supervise()` →
syntese oprettet med gemt mandat og fejlende navngivet → gør syntesen terminal → `supervise()` →
`DONE` og præcis **én** `fired` ventekontrakt.

**Bygget af Codex-executor (`codex-cli`), verificeret af mig.** Dens eneste fejl var en manglende
`import json` — testen nåede den sidste assertion, så hele kæden virkede.

**`execute_team` blev samtidig omlagt:** den dispatchede selv medlemmerne og rullede dem tilbage i
hånden, hvilket gav tre løse agenter uden ejer af helheden — intet råd, ingen syntese, ingen STALLED,
ingen vækning. Nu går teamet gennem `agent_council.convene(derived_plans=...)`, så rådet ejer
livscyklussen og tilbagerulning er rådets `_abandon`. `derived_plans=None` bevarer den gamle sti
uændret.

**Bevis:** 133 grønne. Mutationstest: springer man rådet over og dispatcher direkte, fejler e2e på
`replayed` — testen fanger den gamle adfærd.

**Review-port:** ja — dette er den samlede bevisførelse.

---

## Leverance 11 — §17.2: drift-verifikation ✅ MÅLT (10/11-2026)

**Status: målt på en rigtig modelkørsel på den levende runtime.** Kæden er fulgt gennem DB'en hele
vejen fra `Task(team=…)` til `done`, og ventekontrakten er bekræftet `fired`. Se tabellen nedenfor.
Den negative halvdel — at medlemmerne leverede tomt — står også der, fordi den er en del af målingen.

**Målt 10/11-2026 kl. 21:25 mod den kørende proces og den levende DB:**

| Måling | Resultat |
|---|---|
| Koden er indlæst | `jarvis-api` PID 2721739, startet **21:23:04**; alle tre filer ændret 21:03–21:20 — **før** start. Genstartet med `defer_until_idle`, `NRestarts=0` |
| Team-tabeller i levende DB | `agent_councils` findes (17 kolonner inkl. `stalled_after_at`, `synthesis_wake_registered_at`); `agent_wait_contracts` har 90 rækker, **alle `fired`** |
| Er et team kørt i drift? | **Nej.** Nul råd med `team-`-idempotency. Det eneste råd er `council-25ea7c1df70f40ed` fra **7/10**, nøgle `e2e-…` — den gamle råds-mekanisme, ikke et team |
| Ventekontrakt-mekanikken virker i drift | Ja — tre kontrakter oprettet og fyret i dag (19:47, 20:14, 20:15) |
| `OPEN_GRACE_SECONDS` | `45*60 + 300` = **50 min** pr. åben tilstand; syntesen får sin **egen** tærskel ved indgang til `SYNTHESIZING` |

**§16 besvaret ved måling, ikke gæt:**

1. **Syntesens deadline (§16.1)** — `deadline_at` sættes **ikke** for syntese-assignmentet
   (`grep deadline_at core/services/agent_council.py` = nul hits). Syntesen værnes i stedet af rådets
   `stalled_after_at` på 50 min. Om 30 min er nok til 6 medlemssvar kan derfor **først** måles ved
   første rigtige kørsel — men det er ikke en deadline der kan overskrides, for der findes ingen.
2. **`MEMBER_SUMMARY_CHARS = 1500` (§16.2)** — bekræftet på `agent_council.py:31`, brugt to steder
   (linje 222 og 430). Seks medlemmer = 9.000 tegn, som spec'en antog.
3. **Kan `STALLED` genoptages? (§16.3)** — **Nej.** `STALLED` er ikke i `OPEN_STATUSES`, og
   `expire_stalled()` flytter kun *ind* i tilstanden (linje 312). Der findes ingen transition ud.
   Den rapporterer og vækker — den genoptager ikke. Det er v5's beslutning, ikke en mangel.

**Den måling der manglede — nu taget (10/11-2026 kl. 21:29):**

Et rigtigt `Task(team=…)` blev kørt på den levende runtime med en rigtig model. Kæden blev fulgt
hele vejen gennem DB'en, ikke gennem svaret:

| Trin | Målt |
|---|---|
| `Task(team=…)` → råd | `council-92089f9dc9a842f2`, `team-6096a3fb53c51a2c`, status `gathering` |
| Medlemmer dispatched | to assignments, begge terminale, 3 og 4 værktøjskald hver |
| Syntese startet automatisk | `asg-5fa6bb85e06b4b5a` ved indgang til `synthesizing` |
| Wake stempl et (L7) | `synthesis_wake_registered_at = 20:29:17.510876Z` |
| Ventekontrakt fyret | `fired` kl. `20:29:35.945597Z` |
| Rådet terminalt | status `done` |

**Kæden virker ende-til-ende i drift.** Det er den port der ikke kunne tages i `isolated_runtime`,
og den er nu taget.

**Men målingen afslørede noget vigtigere end «den virker».** Begge medlemmer blev meldt `completed`
med **28 og 56 tegns** svar:

> «Nu linjerne omkring 187-320.» · «Nu skal jeg se linjer omkring 670-720 for fuld kontekst.»

Det er arbejdsintentioner, ikke resultater — samme fejlform som de fem executor-kørsler tidligere på
dagen, blot her inde i et råd. Årsagen er målt: `_promises_action` matcher kun `_PROMISE_DA`
(`"lad mig "`, `"lad os "`) og `_PROMISE_EN`. Ingen af de to sætninger rammer listen, så vagten
returnerer `False` og agenten meldes færdig.

**Det er ikke en ny fejl.** `agent_loop_core.py:151-155` beskriver præcis denne form fra 26/10-2026
(«Nu spørgsmål 2 og 3.»), med den konklusion at en tekstheuristik ikke kan afgøre om et svar er
fuldstændigt. Målingen i dag er endnu et eksempel på det samme hul — ikke en regression.

**Syntesen fangede det, og dét er den ægte gevinst.** Den skrev, uden at nogen bad den om det:

> «Fraværet af svar må ikke tolkes som enighed om at der ingen forskel er … dette er en
> arbejdsintention, ikke et resultat» — og sluttede med **«DÆKNING: ingen»**.

L5's skelnen mellem instruktion og datagrundlag virker i drift: syntesen læste medlemmernes tomme
svar som DATA, nægtede at producere en falsk konsensus, og navngav hvad der manglede. Et råd der
leverer tomt bliver altså **opdaget og sagt højt** — det var hele pointen med laget.

**Åbent herefter:** medlems-vagten er stadig en tekstheuristik. Den rigtige vej er strukturel
(agenten skal ikke kunne afslutte `completed` midt i en læsning den selv har annonceret), og det er
en selvstændig opgave — ikke en del af denne leverance. **Den opgave er nu bygget: se L12.**

---

## Leverance 12 — leverance-vagten: kontrakten var der, men blev aldrig læst

✅ LEVERET (`9a96cacf9`), bygget efter L11's måling med Bjørns «Ja» (10/11-2026).

**To ting der var blevet slået sammen, og som skal holdes adskilt:**

| | Målt svar |
|---|---|
| **Hvorfor stoppede agenten?** | Begge medlemmer havde `max_turns: 8` og brugte 3–4 kald. Deadline 20:59, slut 20:29. Alle kald `ok`. Ingen budget-, deadline- eller fejlgrænse blev ramt — **modellen valgte selv at holde op midt i læsningen.** Hvorfor er ikke målt, og er ikke rettet her |
| **Hvorfor blev det accepteret?** | Stop-grenen i `run_tool_loop` havde præcis **tre** indgange: `scout`, `must_write`, `unanswered`. Et læse-medlem i et råd ramte nul af dem |

**Nøglefundet:** `expected_result` findes og er præcis («citer linjenumre, gæt ikke»). Den står endda
i agentens prompt via `agent_prompt_layers.py:104` — men den blev **aldrig læst som kontrol**. Den var
tekst *til* agenten, aldrig et krav *til* agenten. Samme fejlform som resten af dagen: mekanismen
findes, men ingen læser den.

**Ændringer:**

1. `agent_loop_core.py` — ny `_delivery_gap(expected_result, final_text, tool_calls)`. Kilden er
   kontrakten, ikke en ordliste. To målbare fakta, begge uden en model:
   - et svar under **160 tegn** efter et værktøjskald kan ikke bære en undersøgelse,
   - bestiller kontrakten filnavne eller linjenumre, skal svaret indeholde dem.
2. `agent_loop_core.py` — **fjerde indgang** i stop-grenen, uafhængig af de tre andre. Fyrer den,
   får agenten én ordre der navngiver hullet; står hullet stadig efter den, sættes `incomplete`.
3. `agent_runtime_base.py` + `agent_worker_main.py` + `agent_worker_runner.py` — kontrakten slås op
   via `open_assignment_for_agent()` og bæres ind i loopet på **begge** ruter (in-process og
   sandkassen). Ellers gælder grenen kun den ene, og de to skal have samme adfærd.

**Bevis:** 9 nye tests i `tests/test_agent_delivery_gap.py`; 52 grønne i det målrettede sæt,
121–130 i det brede. De to faktiske svar fra rådet afvises nu, og et rigtigt svar går igennem uden en
ekstra runde. Mutationstest begge veje: gøres grenen tavs, fejler fem tests; gøres kontrakten tom, er
adfærden uændret. `sha256` byte-identisk efter gendannelse.

**Begrænsning, sagt højt:** den fanger det åbenlyst tomme, ikke det subtilt ufuldstændige. En agent
der skriver 400 tegn uden at have læst færdigt, slipper igennem. Syntesen er stadig modvægten — og
den virkede i drift.

### I drift (målt 10/11-2026)

Tjenesterne blev genstartet **21:49:09–10** (`jarvis-api` PID 2739949, `jarvis-runtime` PID 2739954,
`NRestarts=0`). Alle fire berørte moduler er ændret 21:41–21:43, altså **ældre end processen** —
koden er indlæst. Verificeret ved at holde `stat`-mtime op mod `ActiveEnterTimestamp`, ikke ved at
tro på commit-tidspunktet.

### Kalibreringen — det der afgør om vagten er ærlig

Spørgsmålet var ikke «virker den», men «rammer den de rigtige». Målt i den levende DB mod 63 korte
completed-svar, og mod de 22 af dem der har deres egen `agent_runs.assignment_id`:

| Mekanisme | Fanger | Vurdering |
|---|---|---|
| `_promises_action` (ordlisterne) | **19 af 63 = 30 %** | Forkert løftestang. 44 slipper igennem |
| `_delivery_gap` (accept-laget) | **22 af 22 = 100 %** | Den rigtige løftestang |

De 44 der slap gennem `_promises_action` er alle samme form — **narrativ fortsættelse**:
«Nu runde-linjen i MessageList», «Jeg læser de relevante blokke», «Mange kandidater. Læs kerne»,
«Let's inspect schema and find the code», «Flere kopier; jeg bruger hovedrepoet». Ingen af dem
bruger de verber listerne kender. Der er allerede **to** ordlister, og de rammer 7 af 10 forbi.

**Det er rod-årsagen, og den peger væk fra ordlister:** stop-formen er ikke en modelfejl, det er et
loop-design-hul. En runde uden værktøjskald læses som et endeligt svar, og intet på runde-niveau
skelner «narrativ fortsættelse» fra «færdigt resultat». Den eneste mekanisme der *kan* skelne dem
måler **leverancen**, ikke formuleringen.

⚠️ **Fælde jeg selv ramte i målingen:** jeg joinede først på `agent_id` og fik 41 «slap igennem» —
alle med `kontrakt=''`. Det var ældre kørsler uden assignment, hvor jeg havde hentet en tilfældig
nyere kontrakt til samme agent. Join altid på kørslens **egen** `assignment_id`.

### Stadig ikke bevist

Vagten er **ikke set fyre på en rigtig modelkørsel**. Den er kalibreret mod historiske data, den
positive kontrol (asg-bf574ac158f04eaa) leverede korrekt og blev accepteret — men den negative
halvdel, hvor en stoppende agent bliver nudget og derefter leverer, er ikke observeret endnu.
Indtil den er, er «100 %» en måling på fortiden, ikke en garanti for fremtiden.

---

## Leverance 13 — `read_file` kunne ikke læse et linjeinterval ✅ LEVERET OG BEVIST I DRIFT (`91e30dd11`)

**Rod-årsagen til de afbrudte agenter — fundet, ikke gættet.**

En researcher bad om linje 418–650 af `agent_loop_core.py`. Værktøjsskemaet havde kun `path`, så
argumentet blev kastet væk, og den fik modulets top igen — klippet ved `MAX_READ_CHARS = 32000`.
Den svarede ærligt at den ikke kunne citere betingelserne uden at gætte. Den blev stemplet
`AGENT_INCOMPLETE`. Det var ikke en doven agent. Det var et værktøj der ikke kunne det den blev bedt om.

### To ruter, to værktøjssæt — og kun den ene havde hullet

| Rute | Værktøj | Argumenter | Havde hullet? |
|---|---|---|---|
| **worker** (LLM-API, fx `copilot-premium`) | mit `read_file` via `get_tool_definitions` | `start_line` / `end_line` | **JA — fixet rammer her** |
| **CLI** (`claude-cli`, `codex-cli`) | CLI'ens eget `Read` | `offset` / `limit` | NEJ — havde interval hele tiden |

Det var den samme fejlform som resten af dagen: jeg rettede ét sted og troede det dækkede alle.
En «bevist i drift»-konklusion skal navngive **ruten**, ikke bare sige «agenten».

### Beviset, målt efter fixet blev indlæst

Tjenesterne startede **22:06:37**; `file_tools_exec.py` er fra **22:04:28** — koden er indlæst.
Skemaet worker-ruten sender er verificeret direkte (`_build_agent_tools_payload`): det annoncerer
`start_line` og `end_line`. Og en researcher på worker-ruten kaldte:

```
read_file(path=…/agent_loop_core.py, start_line=540, end_line=560)
```

Den fik præcis det interval tilbage, med `"start_line": 540, "end_line": 560` i metadata (filen har
671 linjer). Linje 542 er `gap = "" if scout else _delivery_gap(` — samme linje jeg selv havde læst.
**Intervallet virker i drift på den rute hvor hullet var.**

### Kalibreringen af accept-laget, rettet

Ved gennemgang af den fejlede kørsel viste det sig at `_delivery_gap` **ikke** var årsagen:
med den faktiske kontrakt gav den `""`. Årsagen var `unanswered` — **tre nummererede spørgsmål jeg
selv havde skrevet i opgaven**. Det er præcis den beslutning der står som `dec_abdd66fe102c`:
skriv skriveopgaver som befalinger, aldrig som nummererede krav.

### Stadig ikke bevist

At en agent der **før** stoppede midt i læsningen, nu fortsætter og leverer. Fixet gør redskabet i
stand til at gøre arbejdet; det beviser ikke at modellen vælger at bruge det. Den måling kræver en
kørsel der starter med samme opgave som den fejlede.

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

---

## L14 — accept-laget er kalibreret, og dets grænse er målt

**Status: målt 11/11-2026. Ingen ny regel bygget — fordi målingen ikke bærer en.**

### Det der skete i drift

Vagten fyrede for første gang på en rigtig modelkørsel: `asg-a6de0451494849aa`
(`copilot-premium/claude-sonnet-5`), 16 værktøjskald, svar på **146 tegn**, stemplet
`AGENT_INCOMPLETE (fase: delivery)`.

**Men det var ikke modalitets-reglen der fyrede.** Målt direkte på teksten:

| Regel | Resultat |
|---|---|
| `_FORWARD_TAIL_RE` (modalitet) | `False` — ramte ikke |
| længde-tærsklen (160 tegn) | ramte — svaret er 146 |

Og teksten var **ikke** en tom intention. Den indeholdt to konkrete fund:
*«Dette workflow kører ikke `npm test`, kun build+package. Ingen version-vs-tag gate fundet.»*
Det er præcis det svar opgaven bad om. **Det er en falsk positiv, målt i drift.**

### Fire signaler, alle utilstrækkelige

Målt over 111 completed-kørsler (okt–nov 2026), 24 af dem under 160 tegn:

| Signal | Dækning | Fejl |
|---|---|---|
| længde < 160 | 24 ramt | rammer gyldige korte svar (den målte) |
| bevis (filnavn/linjenummer) | 5 korte har bevis | 5 af dem er **stadig** intentioner |
| bydeform i halen | 2 af 24 | de 2 er faktisk fund |
| forward-hale (modalitet) | 16 af 24 | rammer også de 2 der er fund |

**Ingen af dem kan alene afgøre om et svar er leveret.** Det er ikke et kalibreringsproblem;
det er at sproget ikke bærer afgørelsen.

### Konsekvensen — og hvad der IKKE skal bygges

En femte ordliste ville være samme fejlform som de fire første. Det der mangler er ikke et
bedre signal på **teksten**, men et signal på **arbejdet**: blev undersøgelsen faktisk ført til
ende, eller stoppede den midt i? Det kan kun afgøres mod opgaven, ikke mod svarets form.

**Indtil det findes, er den ærlige pris:** vagten fanger intentioner og rammer også enkelte
gyldige korte svar. Et afvist svar bærer agentens tekst med (`— agentens tekst:`), så intet
arbejde går tabt — men det koster en runde og et fejlstempel.

**Det er ikke lukket. Det er målt, og grænsen er skrevet ned.**

---

## L15 — det afviste spor: rundebudgettet er ikke årsagen

**Hypotesen der lød rigtig, og som blev målt forkert.** Efter den falske positiv i L14 var
den nærliggende forklaring at agenten stoppede fordi den løb tør for runder — 16 værktøjskald
ser meget ud, og hvis loftet lå tæt på, ville svaret være afbrudt frem for dovent.

**Målt 11/11-2026:**

| Led | Værdi | Kilde |
|---|---|---|
| Loft for agent-workere | **60 runder** | `agent_runtime_base.py:130` (`_AGENT_TOOL_LOOP_MAX_ROUNDS`) |
| Den ramte kørsel | **16 kald** | `asg-a6de0451494849aa` |
| Runder tilbage ved stop | **44** | 60 − 16 |

Agenten løb altså ikke tør. Den havde 44 runder tilbage og valgte at stoppe.

**Og budget-noten kunne ikke have hjulpet den.** `_budget_note` (`agent_loop_core.py:81`,
kaldt på `:559`) fyrer kun ved **10, 5 og 2 runder tilbage** — altså runde 50+ ud af 60.
Agent-workere stopper i praksis ved runde 1–16. De ser noten aldrig.

Prompten nævner heller intet tal: `grep` efter rundebudget i `prompt_contract.py` giver kun
kommentarer om mekanikken, ingen tal til modellen.

**Nedskruningen af loftet rammer ikke denne rute.** `affect_modulation` kan sænke
`max_rounds`, men kun på visible-ruten; `agent_runtime_base` sender 60 fast.

### Hvad det betyder

Rundebudgettet er **ikke** stedet at bygge. En agent med 44 runder tilbage der stopper, gør
det af en anden grund — og `_delivery_nudge` (`agent_loop_core.py:440`) siger allerede det
rigtige: *«Fortsæt undersøgelsen med dine værktøjer og afslut med det KONKRETE resultat.»*
Den fik en korrekt ordre og stoppede alligevel.

**Derfor bygges der intet her.** Sporet er skrevet ned så det ikke bliver genopdaget som en
frisk hypotese — det er den eneste grund til at afsnittet findes.
