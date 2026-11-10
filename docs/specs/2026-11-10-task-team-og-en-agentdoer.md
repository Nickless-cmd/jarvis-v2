---
status: til implementering
dato: 2026-11-10
version: 5
ejer: bjorn
forfatter: jarvis
review: Jarvis (self-review) → Claude (opus) ×2 → Codex ×2. Runde 1 dømte v1, runde 2 dømte v2,
         runde 3 dømte v3. v4 er skrevet efter runde 3, og alle fund er efterprøvet mod kilden
         af forfatteren selv. v5 tilføjer testmatrix, kanttilfælde og e2e-verifikation på Bjørns
         krav (10/11-2026). Se §0.
---

# Spec: `Task` som eneste generelle agentdør — og team som tilstand, ikke som system

## 0. Ændringslog — hvad reviewene kostede

**Runde 1 (v1 → v2).** Begge reviewere svarede *ikke klar*. Den blokerende fejl var forfatterens
egen: prompten annoncerede `Task` med `team`, men feltet fandtes ikke, og `_exec_task` kaster
ukendte argumenter væk — et kald ville stille have startet en helt almindelig agent. Rettet.
Derudover: motoren kunne ikke genbruges uændret (`convene()` gik uden om `derive()`), og en race
kunne oprette en syntese over nul medlemmer.

**Runde 2 (v2 → v3).** Begge svarede *ikke klar* med fem nye blokerende fund. Forfatterens egen
§15.2-beslutning byggede på en forkert præmis: `deadline_at` håndhæves **kun** når agenten kalder
et værktøj, og der findes ingen sweep for aktive assignments — så en "arvet" tærskel ville aldrig
fyre. Rettet i v3.

**Runde 3 (v3 → v4).** Begge svarede *ikke klar* igen. Fire af de fem fund var nu *delvist* lukket,
og runden afslørede at **spec'ens problem var genren, ikke detaljerne**: den blandede en kontrakt
(hvad der skal være sandt) med en implementeringsplan (hvordan koden ser ud). Kodeeksempler skrevet
i prosa er ikke kompilerede, og hvert af dem var angribeligt.

v4 gør derfor tre ting: **fjerner alle kodeeksempler der foregiver at være kode**, retter de
faktuelle påstande der var forkerte, og lukker de kontraktfejl der var ægte. Konkret:

| Fund | Status i v3 | Rettelse i v4 |
|---|---|---|
| Syntese-dispatch kunne ikke køre (`derive()` returnerer ikke identitetsfelter; `dispatch_agent()` tager ikke `run_in_background`) | DELVIST | §6.3 specificerer `execute()`-mønstret som kontrakt, ikke som kode |
| Værktøjsvagten slår på medlemmernes egne svar (`synthesis_goal()` indlejrer `summary` ordret) | ikke fundet | §6.4 — vagten må kun læse instruktionen |
| `canonical` udvidet ubetinget ændrer alle single-agent-hashes | DELVIST | §5.2 — nøglerne kun ved `team_id` |
| Team-retry starter et nyt team (tilfældigt `team_id`) | ikke fundet | §5.3 — deterministisk `team_id` |
| `register_wait` er ikke idempotent (nyt uuid hver gang) | DELVIST | §8.4 — unik nøgle + DONE-krav |
| `synthesizing` har ingen stall-kontrol | ikke fundet | §8.5 — alle åbne tilstande |
| `create()` hårdkoder `GATHERING` | DELVIST | §8.2 — skal starte i `PROVISIONING` |
| `RETIRED_AGENT_CREATION_TOOLS` indeholder fem **andre** navne end §10 påstod | ikke fundet | §10 — rettet til den faktiske liste |
| `stalled` vækker / vækker ikke (modsætning mellem §8.5 og §16) | ikke fundet | §8.5 — vækker, altid |
| §8.5's præmis om at en død proces aldrig bliver terminal | ikke fundet | §8.5 — præmissen var forkert, `reconcile_expired_leases` findes |

**Det der IKKE rettes, og hvorfor:** forfatteren holder fast i at `convene_agent_council` blev
pensioneret i samme leverance som spec'en (commit `0b87e7075`). Codex anbefalede tilbagerulning i
runde 1; forfatteren afviste det, fordi prompt-løftet blev fjernet i samme commit, så der ikke er
en løgn tilbage — kun et vindue uden rådsvej, og den vej havde nul kald.

**Runde 4 (v4 → v5) — ikke et review, et krav fra Bjørn.** v4 beskrev hvad der skal være sandt, men
sagde intet om *hvordan det bevises*. Otte accepttests er ikke en teststrategi: de siger hvad der
skal gælde, ikke hvilken fil der beviser det, hvilke kanttilfælde der kan vælte det, eller hvordan
man ser forskel på «grøn test» og «virker i drift». v5 tilføjer derfor tre ting:

- **§13** får en testmatrix: hver accepttest mappes til en konkret testfil og et konkret niveau
  (unit · service · e2e), med en note om hvad der allerede findes og hvad der skal skrives.
- **§13.5** tilføjer de kanttilfælde som accepttesterne ikke fanger, fordi de er *uden for* det
  normale forløb: nul medlemmer midt i provisioning, syv medlemmer, to supervisere samtidigt,
  genstart midt i et team, kapacitet der forsvinder mellem medlem 1 og 3.
- **§17** tilføjer e2e-verifikation efter husets mønster (`tests/e2e/`, `isolated_runtime`):
  seed → bestil et team → verificér at N assignments findes med N mandater → gør dem terminale →
  verificér at syntesen oprettes → verificér at parenten vågner. Plus den drift-verifikation der
  skal køre *efter* deploy, fordi en grøn unit-test ikke er bevis for den kørende proces.

---

## 1. Formål og succeskriterium

`Task` skal være den **eneste** måde at sætte agenter i verden på. Ikke én af fem. Alt andet
(subagents, teams, råd, review-kæder, workflows) er **tilstande eller mønstre over den samme
motor**, ikke separate systemer med hver sin livscyklus.

Et team er en tilstand af `Task`: `Task(..., team={...})`. Udelades `team`, er det en single-agent —
byte-identisk med i dag.

**Succeskriterier:**

1. Der findes præcis én modelvendt oprettelsesvej: `Task`. Alle andre navne er pensioneret og
   afvises i eksekveringsporten (§10).
2. Et `Task(team=…)` opretter N medlemmer + 1 syntese, alle med **gemt mandat** gennem `derive()`.
3. Intet teammedlem kan skrive filer (§7).
4. **Ingen tilstand kan hænge.** Enhver åben tilstand har en observerbar tærskel og en vej ud (§8).
5. Et gentaget `Task(team=…)` med samme input genoptager det eksisterende team — det starter
   ikke et nyt (§5.3).

---

## 2. Produktgrænse — hvad dette IKKE er

- **Ikke skrivende teams.** `executor` afvises i et team (§7.2). Arbejdshold med egne worktrees
  er udskudt (§15.5).
- **Ikke en delt, skrivbar opgaveliste.** Størrelse og roller besluttes ved booking. Er listen
  besluttet ved booking, skal den ikke være skrivbar — den skal være *synlig* (§15.6).
- **Ikke en ny LLM-runtime.** Motoren er `agent-contract-v1`. Team er et mønster over assignments.
- **Ikke en omdøbning af `agent_council.py`.** Historikken er mere værd end navnet (§15.4).

---

## 3. Målt udgangspunkt (10/11-2026)

- **16** agent-værktøjer i den modelvendte flade. **7** brugt. **9** aldrig kaldt.
- `Task` stod for **43 af 105** agent-kald. Med `wait_agents` + `list_agents` = **91 af 105 (87 %)**.
- **105 agent-kald ud af 19.541 værktøjskald = 0,5 %.** `bash` er 67 %.
- **116 terminale assignments:** median 0,5 min, p90 3,8 min, p99 10,6 min, **maksimum 19,1 min**.
  Nul har rørt 30-minutters-grænsen.
- To reviews startet samme sekund, afsluttet inden for 6 sekunder → **medlemmer kører parallelt**.

Tallene er grundlaget for §8.5's tærskler. De er målt, ikke gættet.

---

## 4. Kontrakten

`Task`-skemaet udvides med ét valgfrit felt. Alt andet er uændret.

```
team: {
  name:      string   # fri etiket, fx "råd vedr. dispatch-arkitektur"
  members:   [{ role: string, task: string }]   # 2–6
}
```

**Regler:**

- `members` kræver **unik `task`** per medlem. To medlemmer med samme opgave er ét svar talt
  flere gange, og afvises med begrundelse.
- `role` er **fri tekst** — ingen whitelist, ingen enum. Rollen er en etiket; autoritet kommer fra
  `subagent_type` (§7.2).
- `team.name` er **håndtaget**, ikke nøglen. Gruppering sker på `team_id` (§5.1).
- Udelades `team`, er adfærden byte-identisk med i dag.
- **`additionalProperties: false` skal sættes på `Task`-skemaet.** Uden den er reglen om at afvise
  ukendte argumenter kun en påstand: `_exec_task` læser kendte felter og ignorerer resten
  (`core/tools/agent_contract_tools.py:269`).

---

## 5. Team-identitet og idempotens

### 5.1 `team_id` er nøglen, `team.name` er håndtaget

`team_id` bærer `team-`-præfiks, så det kan skelnes fra et `council-`-id i logs. `team.name` er
fri tekst og kan kollidere mellem to teams — det er acceptabelt, fordi navnet aldrig er nøgle.

### 5.2 `canonical` udvides KUN når `team_id` er sat

`derive()`'s `canonical` er i dag ni nøgler (`core/services/agent_task_facade.py:189-195`).
Tilføjes `team_id` og `member_index` **ubetinget**, ændres `json.dumps(..., sort_keys=True)`, og
så får **alle single-agents nye idem- og mandat-id'er** — hvilket brækker enhver replay.

**Kontrakt:** nøglerne indgår kun i `canonical` når `team_id` er ikke-tom. For en single-agent er
hash-inputtet byte-identisk med i dag, og det skal en test bevise ved at sammenligne hashen før
og efter ændringen.

### 5.3 `team_id` udledes deterministisk — ikke tilfældigt

Et tilfældigt `team_id` gør retry farligt: et gentaget `Task(team=…)` efter et tabt svar ville
starte N **nye** agenter. `convene()` havde idempotens via `find_by_key`
(`core/services/agent_council.py:81-86`); den egenskab må ikke gå tabt.

**Kontrakt:** `team_id` udledes som en hash af teamets `canonical` (owner, session, parent_run,
description, prompt, `team.name`, og medlemmernes `role`+`task` i rækkefølge). Samme input →
samme `team_id` → `find_by_key` rammer den eksisterende række og svarer `replayed: true`.

`member_index` er medlemmets position i den bestilte liste og indgår i hvert medlems `canonical`,
så N medlemmer får N forskellige `mandate_id`. Uden den kolliderer de på PRIMARY KEY
(`core/runtime/db_agent_mandate.py:30`).

---

## 6. Autoritet: alle N+1 assignments gennem `derive()`

### 6.1 Hvorfor dette er den vigtigste sektion

Et gemt mandat er det eneste der håndhæver `max_fanout`, `max_depth`, værktøjsliste og deadline.
Går en assignment uden om `derive()`, har den **ingen** af delene — og `max_fanout: 0` bliver
virkningsløs, fordi den kun håndhæves gennem et gemt mandat.

### 6.2 `derive_team()` — egen funktion, der kalder `derive()` per medlem

Ikke en gren inde i `derive()`. Al validering (unikke tasks, 2–6 medlemmer, `executor`-afvisning)
sker **før første dispatch**, så et afvist team ikke efterlader halve medlemmer.

En `ValueError` fra `derive_team()` oversættes til `INVALID_SCOPE`, sådan som `execute()` gør
(`core/services/agent_task_facade.py:226-229`).

### 6.3 Syntesen dispatches gennem `execute()`-mønstret

v3 viste `svc.dispatch_agent(**mandate, wake_parent=False)`. Det kan ikke køre, og v4 gentager det
ikke som kode. **Kontrakten er:**

`derive()` returnerer `goal, description, role, expected_result, model, writes, workspace, target,
tool_policy, allowed_tools, budget_tokens, max_turns, deadline_at, idempotency_key,
run_in_background` **plus** en nested `mandate`. Identitetsfelterne (`owner_user_id`,
`origin_session_id`, `parent_run_id`, `parent_agent_id`) er **input**, ikke retur.

Det korrekte mønster er derfor præcis det `execute()` allerede bruger
(`core/services/agent_task_facade.py:230-236`): kald `derive(**fields)`, pop `mandate` og
`run_in_background` ud af planen, kald `dispatch_agent(..., mandate=mandate, **plan)` med
identitetsfelterne fra `fields`. Syntesen skal bruge **denne** vej — ikke en egen.

Syntesen dispatches med `subagent_type="critic"`. Den får dermed sit eget gemte mandat, sin egen
værktøjsliste og sin egen deadline — og nul skriveret.

### 6.4 Værktøjsvagten må ikke læse medlemmernes svar

`synthesis_goal()` indlejrer hvert medlems `summary` **ordret** (`core/services/agent_council.py:155`).
`derive()` kører `ufuldstaendige_vaerktoejer` på prompten, og regex'en
(`core/services/agent_task_requirements.py:22-27`) matcher `brug \`bash\``, `kør \`wt_write_file\``
og lignende.

**Konsekvens hvis uændret:** et medlem der skriver "kør `bash` …" får syntesen til at kaste
`ValueError` **deterministisk ved hvert supervisor-tick**. Teamet ender i `stalled`, og svaret går
tabt. Fejlen afhænger af medlemmernes frie tekst — den er ikke teoretisk.

**Kontrakt:** syntesens prompt har to dele — en **instruktion** (min tekst) og et **datagrundlag**
(medlemmernes citerede svar). `ufuldstaendige_vaerktoejer` må kun læse instruktionen. Grænsen skal
være eksplicit i koden, ikke implicit i teksten.

---

## 7. Fan-out

### 7.1 Et teammedlem må ikke selv sprede sig

`derive()` sætter `max_fanout: 0` og `max_depth: 0`. Fordi medlemmet har et gemt mandat, er det
håndhævet. Uden §6.2 ville det ikke være.

### 7.2 `executor` afvises i `derive()`, ikke i handleren

Rollen er en etiket. Det der giver skriveret er `writes = kind in _WRITE_TYPES`
(`core/services/agent_task_facade.py:164`), styret af **`subagent_type`**. Afvises `role="executor"`,
slipper man derfor igennem med `Task(subagent_type="executor", team={…})` — N skrivende agenter med
hvert sit worktree.

**Kontrakt:** spærringen ligger på `kind`, inde i `derive()`, og gælder uanset hvilket navn rollen har.

### 7.3 `_member_type()`

Medlemmernes `subagent_type` udledes af teamet, ikke af topniveauets `subagent_type`. Standard er
`researcher`; `critic`/`planner`/`watcher` tillades. `executor` afvises.

---

## 8. Livscyklus — og de fire måder et team kan hænge

### 8.1 Tilstande

```
PROVISIONING → GATHERING → SYNTHESIZING → DONE
      ↓            ↓             ↓
   CANCELLED    STALLED       STALLED
```

`OPEN_STATUSES = {PROVISIONING, GATHERING, SYNTHESIZING}`. `open_councils()` henter **denne mængde**,
ikke to hårdkodede værdier.

### 8.2 `create()` skal starte i `PROVISIONING`

`db_agent_council.create()` hårdkoder `GATHERING` (`core/runtime/db_agent_council.py:73`). Det er
racen: rækken findes med `members_json='[]'`, og `advance()` kan nå at se `([], True)` → syntese
over nul medlemmer.

**Kontrakt:** `create()` indsætter i `PROVISIONING`. `set_members()` er den der transitionerer til
`GATHERING`, når alle medlemmer er skrevet. `advance()` springer alt i `PROVISIONING` over.

### 8.3 Alt-eller-intet

Afvises medlem *i*, køres `_abandon()`, og rådet går til `CANCELLED`. `_abandon()` tager `frm` som
**parameter** — i dag er den hårdkodet til `GATHERING` (`core/services/agent_council.py:121`), så
enhver afvisning fra `PROVISIONING` ville fejle på statusskiftet og efterlade teamet fast.

### 8.4 R3 — vækning der kan tabes, skal kunne gentages

`_wake_parent_on()` kaldes efter skiftet til `SYNTHESIZING`, og en `ContractError` **logges og
sluges** (`core/services/agent_council.py:189-215`). Næste sweep forsøger ikke igen: syntesen
fuldføres, men parenten vågner aldrig.

**Kontrakt:**

- Kolonne `synthesis_wake_registered_at` på `agent_councils`.
- Registreringen kører igen ved hvert sweep indtil den lykkes.
- **`register_wait()` skal være idempotent.** I dag laver den `wait-{uuid4}` hver gang
  (`core/runtime/db_agent_wait.py:111`) og har ingen unik nøgle på (parent_run_id, assignment_ids).
  Et crash mellem registrering og `mark_wake_registered` giver derfor en **dobbelt vækning**.
  Der skal være en unik nøgle, så gentaget registrering rammer samme kontrakt.
- **`DONE` kræver `synthesis_wake_registered_at` sat** (eller at `parent_run_id` er tom). Ellers
  flytter `SYNTHESIZING → DONE` rådet ud af `OPEN_STATUSES`, og der kommer aldrig et nyt forsøg.
- Mangler `parent_run_id`, returnerer `_wake_parent_on()` **succes** (der er ingen at vække), så
  løkken ikke kører evigt på en betingelse der aldrig kan opfyldes.

### 8.5 Alle åbne tilstande skal have en tærskel — og `STALLED` vækker parenten

v3 gav kun `GATHERING` og `PROVISIONING` en tærskel. En syntese der hænger i et LLM-kald ville
derfor stå i `SYNTHESIZING` uden ende — samme fejlform som medlemmerne, og det bryder §1's
succeskriterium 4.

**Kontrakt:**

- `stalled_after_at` sættes ved indgang til **enhver** åben tilstand, ikke kun `GATHERING`.
- For `SYNTHESIZING` er tærsklen **syntesens egen start + dens deadline + margin** — ikke teamets.
  En syntese kan starte ved `max(medlems-deadlines)` og har selv 30 min; en fælles tærskel ville
  erklære et levende team dødt.
- `STALLED` **vækker parenten**. Det er hele pointen: ellers er det en tavs tilstand, og svaret går
  tabt uden at nogen ser det.
- En sweep finder forfaldne teams i `OPEN_STATUSES` og sætter dem i `STALLED`.

**Præmis rettet:** v3 skrev at "en proces der døde midt i en kørsel aldrig bliver terminal". Det er
forkert — `reconcile_expired_leases` (`core/runtime/db_agent_lease.py:251-320`) sætter et forsøg med
udløbet lease i kø igen eller markerer det `failed`. Det uopdagede tilfælde er et medlem der
**hænger, mens processen lever** — og det er præcis hvad tærsklen skal fange.

---

## 9. Hvad genbruges, og hvad ændres

**Motoren røres — det er ikke en påstand om det modsatte.** v1 hævdede "én parameter, én kolonne,
én gren". Det var forkert. Der skal:

- **2 nye funktioner:** `derive_team()`, `_member_type()`.
- **4 kolonner:** `team_id`, `member_index`, `stalled_after_at`, `synthesis_wake_registered_at`.
- **5 rettelser i livscyklussen:** `create()` starter i `PROVISIONING`; `set_members()` transitionerer;
  `_abandon(frm)`; `OPEN_STATUSES`; `DONE`-kravet.
- **2 rettelser i kontrakten:** `canonical` udvides betinget; `register_wait` bliver idempotent.
- **1 rettelse i vagten:** den må ikke læse medlemmernes citater.

`_exec_task` ligger i `core/tools/agent_contract_tools.py:269` — ikke i `agent_contract_handlers.py`,
som v3 påstod.

---

## 10. Pensionering — hvad der faktisk er sandt

`RETIRED_AGENT_CREATION_TOOLS` (`core/tools/tool_scoping.py:31-37`) indeholder i dag:
`scout_agent`, `spawn_agent_task`, `dispatch_code_mode_task`, `dispatch_to_claude_code`, `task`.

Den er håndhævet tre steder: trukket fra alle scopes, afvist i `is_tool_allowed()`, og
`load_more_tools` kan ikke genoplive den.

**v3 påstod at listen indeholdt seks andre navne. Det var forkert.** Konkret:

- `convene_agent_council` er fjernet fra katalog, handlers og scopes i commit `0b87e7075` — men den
  står **ikke** i `RETIRED_AGENT_CREATION_TOOLS`. Den kan derfor ikke genoplives via
  `load_more_tools`, men den er heller ikke beskyttet af porten.
- `relay_to_agent` og `cancel_agent` står stadig som annoncerede agent-værktøjer i
  `core/tools/copilot_tool_pruning.py:360`. `cancel_agent` er slet ikke et værktøj, men en funktion
  i `agent_runtime_spawn` som Central-UI'et kalder (`apps/api/jarvis_api/routes/central.py:167`) —
  en navnekollision der får et internt funktionskald til at se ud som en modelvendt dør.

**Kontrakt:** de to tilføjes til `RETIRED_AGENT_CREATION_TOOLS`, og `convene_agent_council` med.
Det er en selvstændig lille opgave — ikke en del af team-implementeringen.

---

## 11. Prompten må ikke love feltet før det findes

`core/services/prompt_sections/agent_orchestration.py` beskriver værktøjsfladen. Feltet `team` må
**ikke** nævnes der før `Task`-skemaet har det. Et løfte i prompten om et felt der ikke findes er
ikke en kosmetisk fejl: `_exec_task` kaster ukendte argumenter væk, så kaldet ville stille starte en
almindelig agent.

Ændringen sker i **samme commit** som skemaet. En test skal bevise at prompten kun nævner værktøjer
og felter der faktisk findes.

---

## 12. Risici

**R0 — syntese over nul medlemmer.** Lukket af §8.2. **Skal ind først:** den er den eneste fejl der
kan producere et svar uden grundlag.

**R1 — teamet hænger evigt.** Lukket af §8.5, forudsat at tærsklen gælder **alle** åbne tilstande.

**R2 — teamets række holder ingen kapacitet.** Kapacitet tælles som åbne assignments
(`core/runtime/db_agent_deadlines.py:88-104`). At markere et team `failed` frigiver derfor intet —
medlemmerne skal selv terminale. v1's påstand om at "én kolonne" løste dette var fejldiagnosticeret.

**R3 — vækning tabes.** Lukket af §8.4.

**R4 — medlemmernes tekst dræber syntesen.** Lukket af §6.4.

**R5 — `STALLED` er en tavs tilstand.** Lukket af §8.5: den vækker.

---

## 13. Testmatrix — hver accepttest har en fil og et niveau

Otte accepttests er ikke en strategi. Tabellen nedenfor mapper hver test til **hvor** den hører
hjemme, **hvilket niveau** den beviser noget på, og **om den findes i dag**. Niveau er ikke
kosmetik: en unit-test beviser en funktion, en service-test beviser samspillet mellem funktioner i
en isoleret runtime, og kun en e2e-test beviser at kæden hænger sammen fra modelkald til vækning.

| # | Accepttest | Fil | Niveau | Findes |
|---|---|---|---|---|
| 1 | Byte-identisk single-agent-hash | `tests/test_agent_task_facade.py` | unit | Nej — tilføjes |
| 2 | N medlemmer → N forskellige `mandate_id`, alle `max_fanout: 0` | `tests/test_agent_council.py` | service | Delvist (3-medlems-råd findes; mandat-assert tilføjes) |
| 3 | Retry giver `replayed: true` og samme `team_id` | `tests/test_agent_council.py` | service | Delvist (idempotens findes for råd; team-vej tilføjes) |
| 4 | `executor` afvises uanset rollenavn | `tests/test_agent_task_facade.py` | unit | Nej — tilføjes |
| 5 | Medlemscitat ("kør `bash`") dræber ikke syntesen | `tests/test_agent_council.py` | service | Nej — tilføjes |
| 6 | Syntese der aldrig bliver terminal → `STALLED` + vækning | `tests/test_agent_council.py` | service | Nej — tilføjes |
| 7 | Dobbelt `register_wait` giver én kontrakt | `tests/test_db_agent_wait.py` | unit | Nej — tilføjes |
| 8 | Prompten nævner intet felt `Task` ikke har | `tests/test_agent_orchestration.py` | unit | Ja (`test_agent_orchestration.py:58`) — udvides med `team` |

**Supplerende tests der ikke er accepttests, men som skal med i samme leverance:**

| Test | Fil | Hvorfor |
|---|---|---|
| `create()` starter i `PROVISIONING` og `advance()` springer den over | `tests/test_db_agent_council.py` | R0 — den ene fejl der kan give et svar uden grundlag |
| `_abandon(frm)` virker fra `PROVISIONING` | `tests/test_agent_council.py` | Ellers efterlades et team fast ved første afvisning |
| `OPEN_STATUSES` dækker alle tre åbne tilstande | `tests/test_db_agent_council.py` | En hårdkodet toerliste er præcis v3's fejl |
| `stalled_after_at` sættes ved **hver** indgang til en åben tilstand | `tests/test_agent_council.py` | §8.5 — ikke kun `GATHERING` |
| `DONE` nægtes når `synthesis_wake_registered_at` mangler og `parent_run_id` er sat | `tests/test_agent_council.py` | §8.4 — ellers forsvinder teamet fra `OPEN_STATUSES` uden vækning |
| `_wake_parent_on()` svarer succes når `parent_run_id` er tom | `tests/test_agent_council.py` | Ellers kører løkken evigt på en betingelse der aldrig kan opfyldes |
| `derive_team()` validerer **før** første dispatch | `tests/test_agent_task_facade.py` | §6.2 — et afvist team må ikke efterlade halve medlemmer |
| `additionalProperties: false` afviser et ukendt felt | `tests/test_agent_contract_tools.py` | §4 — uden den er reglen kun en påstand |
| `relay_to_agent`, `cancel_agent`, `convene_agent_council` i `RETIRED_AGENT_CREATION_TOOLS` | `tests/test_copilot_tool_pruning.py` | §10 — selvstændig lille opgave |

**Regel for hele matrixen:** hver række skal kunne fejle. En test der er grøn fordi dens assertion
matcher alt — fx `assert result` på et svar der altid er sandt — beviser intet og tæller ikke.
Test 1 er den vigtigste af slagsen: den skal sammenligne en **gemt hash-værdi** fra før ændringen,
ikke genberegne den samme formel to gange i samme kørsel.

---

## 13.5 Kanttilfælde — det der ligger uden for det normale forløb

Accepttesterne dækker det forventede forløb. Nedenstående kan vælte det, og de er ikke dækket af
nogen af testene ovenfor.

**Provisionering og race**

1. **Nul medlemmer midt i provisioning.** `create()` har indsat rækken, `set_members()` er ikke
   kørt, og `advance()` ser den. Skal springes over — ikke give en syntese. (§8.2)
2. **To supervisere samtidigt.** `supervise()` kører i både api og runtime. Begge ser samme team i
   `GATHERING`, begge forsøger at oprette syntesen. `transition()` er en CAS — den ene skal tabe,
   og der må ikke oprettes to syntese-assignments.
3. **Genstart midt i et team.** Processen dør efter medlem 2 af 4 er dispatchet. Ved genstart skal
   teamet stadig være i `PROVISIONING` eller `GATHERING` (ikke `DONE`), og `advance()` skal kunne
   fortsætte. `members_json` må ikke indeholde medlemmer der aldrig blev accepteret.
4. **Kapacitet forsvinder mellem medlem 1 og 3.** `_room_for()` tjekker før dispatch, men et andet
   team kan tage pladserne undervejs. Medlem 3 afvises med `CAPACITY` → `_abandon()` → `CANCELLED`.
   Testen i dag (`test_a_failing_dispatch_midway_stops_the_started_members_and_cancels_the_council`)
   dækker dette for råd; team-vejen skal have samme garanti.

**Grænser**

5. **Syv medlemmer.** `MAX_MEMBERS = 6`. Syv skal afvises **før** første dispatch, ikke efter seks
   er startet.
6. **Ét medlem.** `MIN_MEMBERS = 2`. Ét medlem er ikke et team — det er en almindelig `Task`, og
   skal afvises med en henvisning til det, ikke med en generisk fejl.
7. **Tomt `team.name`.** Navnet er en etiket, ikke en nøgle. Skal det afvises, eller må det være
   tomt? Kontrakten i §4 siger fri etiket — men et tomt navn gør teamet uskelneligt i Desk. **Valg:
   afvises**, fordi navnet er det eneste mennesket ser, og et tomt navn gør `team_id` til den eneste
   identitet. Begrundelsen skal stå i fejlmeddelelsen.
8. **To medlemmer med samme `task`.** Afvises (§4). Men hvad med samme `role` og forskellig `task`?
   Tillades — rollen er en etiket, og to kritikere med forskellige angrebsvinkler er netop pointen.

**Medlemmernes udfald**

9. **Et medlem fejler, resten lykkes.** Syntesen oprettes og skal **navngive** den fejlende (§8.1).
   Dette er allerede testet for råd — team-vejen skal arve garantien, ikke genopfinde den.
10. **Alle medlemmer fejler.** Syntesen oprettes stadig, men med et grundlag der udelukkende er
    fejl. Skal den oprettes? **Valg: ja** — den kan stadig sige hvad der mangler, og et svar om at
    intet kunne hentes er mere værd end stilhed. Men syntesen skal ikke kunne påstå enighed.
11. **Et medlem svarer med tomt `summary`.** `synthesis_goal()` skelner allerede mellem "svarede" og
    "blev afsluttet uden brugbart svar". Team-vejen skal bevare den skelnen.
12. **Syntesen fejler.** Teamet skal gå til `DONE` (syntesen er terminal) — ikke blive hængende. Men
    parenten skal have udfaldet, ikke kun en tom vækning.

**Vækning**

13. **`register_wait` kaldes to gange efter crash.** Skal ramme samme kontrakt (§8.4). Uden unik
    nøgle får parenten to vækninger for ét svar.
14. **`parent_run_id` er tom** (fx et team startet fra en baggrundsjobb uden synligt run). Ingen
    vækning er mulig — `_wake_parent_on()` skal svare succes, ikke fejle i det uendelige.
15. **Brugeren stopper parentens run mens teamet kører.** `block_wakes_for_run` spærrer vækningen;
    resultatet skal lande i inbox. Teamet må ikke gå i `STALLED` af den grund — det er en bevidst
    spærring, ikke en hængning.

**Dataintegritet**

16. **`mandate_id`-kollision.** To medlemmer med identisk `canonical` (samme rolle, samme task) ville
    give samme `mandate_id` og kollidere på PRIMARY KEY. `member_index` i `canonical` forhindrer det
    (§5.3) — men rækkefølgen skal være **den bestilte**, ikke en sorteret, ellers får en retry med
    ombyttede medlemmer nye id'er.
17. **DB låst under `set_members()`.** `database is locked (5)` er målt i huset. Transitionen fra
    `PROVISIONING` til `GATHERING` skal enten lykkes eller fejle synligt — ikke efterlade teamet i
    `PROVISIONING` uden at nogen ved det.
18. **`team_id` kolliderer med et `council_id`.** Umuligt med `team-`-præfiks (§15.3), men testen
    skal bevise at præfikset faktisk sættes — ikke kun at det står i spec'en.

---

## 14. Rækkefølge — ikke til forhandling

Hvert trin er en **selvstændig leverance**: den har filer, en test der skal grønnes, og en review-port
før det næste trin starter. Rækkefølgen er ikke kosmetisk — trin 1 lukker den ene fejl der kan give
et svar uden grundlag, og trin 2 skal være på plads før nogen idempotens kan testes, fordi en ændret
`canonical` giver nye id'er til alt.

| # | Leverance | Filer | Test der skal grønnes | Review-port |
|---|---|---|---|---|
| 1 | **R0:** `PROVISIONING`, `create()`, `set_members()`, `_abandon(frm)`, `OPEN_STATUSES` | `core/runtime/db_agent_council.py`, `core/services/agent_council.py`, `tests/test_db_agent_council.py`, `tests/test_agent_council.py` | `create()` starter i `PROVISIONING`; `advance()` springer den over; `_abandon` virker fra `PROVISIONING`; `OPEN_STATUSES` dækker tre tilstande | Ja — dette er den ene fejl der giver et svar uden grundlag |
| 2 | **§5.2:** betinget `canonical` | `core/services/agent_task_facade.py`, `tests/test_agent_task_facade.py` | Test 1: gemt hash fra før ændringen er byte-identisk | Ja — brækker replay hvis den er forkert |
| 3 | **§5.3:** deterministisk `team_id` + `member_index` | `core/services/agent_task_facade.py`, `core/services/agent_council.py` | Test 3: retry giver samme `team_id`; test 2: N medlemmer → N `mandate_id` | Ja |
| 4 | **§6.2/§6.3:** `derive_team()`, syntese gennem `execute()`-mønstret | `core/services/agent_task_facade.py`, `core/services/agent_council.py` | Test 2 fuldt; syntesen har gemt mandat med `max_fanout: 0` | Ja — dette er autoritetsgrænsen |
| 5 | **§6.4:** vagten læser kun instruktionen | `core/services/agent_council.py`, `core/services/agent_task_requirements.py` | Test 5: medlemscitat "kør `bash`" giver stadig syntese | Nej — lille, men testen skal fejle uden rettelsen |
| 6 | **§8.5:** tærskel for alle åbne tilstande + `STALLED` vækker | `core/runtime/db_agent_council.py`, `core/services/agent_council.py` | Test 6: syntese der aldrig bliver terminal → `STALLED` + vækning | Ja |
| 7 | **§8.4:** idempotent `register_wait` + `DONE`-kravet | `core/runtime/db_agent_wait.py`, `core/services/agent_council.py`, `tests/test_db_agent_wait.py` | Test 7: to kald → én kontrakt; `DONE` nægtes uden registrering | Ja |
| 8 | **§4/§11:** `Task`-skemaet + `additionalProperties: false` + prompten | `core/tools/agent_contract_tools.py`, `core/services/prompt_sections/agent_orchestration.py`, `tests/test_agent_orchestration.py` | Test 8: prompten nævner intet felt `Task` ikke har; ukendt felt afvises | Ja — samme commit, ellers lyver prompten |
| 9 | **§10:** de tre navne i `RETIRED_AGENT_CREATION_TOOLS` | `core/tools/tool_scoping.py`, `tests/test_copilot_tool_pruning.py` | Navnene er i listen og afvises af `is_tool_allowed()` | Nej — selvstændig lille opgave |
| 10 | **§17.1:** e2e-testen | `tests/e2e/test_team_e2e.py` | Hele kæden: bestil → 3 mandater → terminale → syntese → `DONE` → én `fired` kontrakt | Ja — dette er den samlede bevisførelse |
| 11 | **§17.2:** drift-verifikation | `jarvis.db`, journal på CT105 | De fem målinger i §17.2 taget på kørende runtime | Ja — og dette er den **eneste** port der beviser at det virker |

**Regel for review-portene:** en port er ikke «læs koden igennem». Den er en uafhængig reviewer der
får kravet (rækken ovenfor), den faktiske diff, og den grønne test — og som skal svare *godkendt* eller
*navngive hvad der mangler*. Er porten ikke bestået, starter næste trin ikke. Det er den samme
`review_agent_work`-mekanisme huset allerede har.

**Undtagelse, og den skal siges højt:** trin 11 kan ikke køres af en agent i en isoleret runtime. Den
kræver en rigtig kørsel på CT105 med en rigtig model. Indtil den er taget, er status «implementeret,
ikke verificeret i drift» — og det er en anden status end «færdig».

---

## 15. Afgjorte punkter

**15.1** `derive_team()` er en egen funktion, der kalder `derive()` — ikke en gren i `derive()`.
**15.2** Teamet har **sin egen** alderstærskel, afledt og håndhævet af en sweep. Den kan ikke arves
fra medlems-deadlines: `deadline_at` håndhæves kun ved værktøjskald.
**15.3** `team_id` bærer `team-`-præfiks.
**15.4** `agent_council.py` omdøbes ikke nu.
**15.5** Skrivende teams er udskudt. Worktree-isoleringen blokerer ikke en delt liste (listen er en
tabel, ikke en fil), men et medlem kan i dag kun skrive til tre per-barn-tabeller, og der findes
intet sted at sige "jeg tager del 2".
**15.6** Listen er **synlig, ikke skrivbar**. Størrelsen besluttes ved booking; en skrivbar liste
koster claim-konflikter og rækkefølge, og den pris betales kun når arbejdet er dynamisk.

---

## 16. Åbent — og hvad der afgør det

1. **Syntesens deadline.** Er `critic`-standardens 30 min nok til at læse 6 medlemssvar à 1.500 tegn?
   Måles ved første kørsel, ikke gættes.
2. **`MEMBER_SUMMARY_CHARS = 1500`.** Seks medlemmer = 9.000 tegn citat i syntesens prompt. Det er
   under alle grænser, men det er også 9.000 tegn der aldrig kan caches. Måles.
3. **Om `STALLED` skal kunne genoptages** eller kun rapporteres. v4 rapporterer og vækker; genoptagelse
   er en ny beslutning.

---

## 17. E2E-verifikation — forskellen på «grøn test» og «virker»

Husets mønster for e2e er service-niveau i `tests/e2e/` med `isolated_runtime`-fixturen: seed →
handling → verificér tilstand → udfald, uden en live model eller klient (se
`tests/e2e/test_override_e2e.py`). Team-kæden skal have samme behandling, fordi dens fejlform er
**tavshed**: et team der hænger, svarer ikke med en fejl — det svarer slet ikke.

### 17.1 E2E-testen (skal køre i CI)

`tests/e2e/test_team_e2e.py` — én sammenhængende kørsel gennem den ægte service-kæde:

1. **Bestil** et team med 3 medlemmer gennem `Task`-facaden (ikke gennem `convene`).
2. **Verificér** at der findes 3 assignments, 3 forskellige `mandate_id`, alle med `max_fanout: 0`,
   og at teamet står i `GATHERING` — ikke `PROVISIONING`.
3. **Gør** medlemmerne terminale (én `completed` med svar, én `completed` uden, én `failed`).
4. **Kør** `supervise()` én gang. **Verificér** at syntesen er oprettet, at den har et gemt mandat,
   og at dens prompt navngiver den fejlende.
5. **Gør** syntesen terminal. **Kør** `supervise()` igen. **Verificér** at teamet er `DONE` og at
   der findes præcis **én** ventekontrakt der er `fired`.
6. **Verificér negativt:** at der ikke blev oprettet mere end ét syntese-assignment, og at intet
   medlem fik `max_fanout > 0`.

Testen skal fejle hvis nogen af de seks trin giver det rigtige svar af den forkerte grund — fx hvis
syntesen oprettes fordi `advance()` sprang `PROVISIONING` over i stedet for fordi medlemmerne var
terminale. Derfor asserteres **rækkefølgen**, ikke kun sluttilstanden.

### 17.2 Drift-verifikation (skal køre efter deploy — ikke i CI)

En grøn e2e-test beviser at koden kan, ikke at processen gør. Efter deploy af §14's trin skal disse
målinger tages på den kørende runtime, og resultatet skal skrives i §0 med tal:

| Måling | Hvor | Bevis for |
|---|---|---|
| `SELECT status, COUNT(*) FROM agent_councils GROUP BY status` | `jarvis.db` | At intet team står fast i `PROVISIONING` |
| Antal teams med `stalled_after_at < now()` og status i `OPEN_STATUSES` | `jarvis.db` | At sweepen faktisk fanger forfaldne teams |
| `SELECT COUNT(*) FROM agent_wait_contracts WHERE status='fired'` før/efter et team | `jarvis.db` | At vækningen fyrer præcis én gang |
| Antal `mandate_id` per team i `agent_assignment_mandates` | `jarvis.db` | At N medlemmer giver N mandater — i drift, ikke kun i test |
| `journalctl -u jarvis-runtime` for `raad kunne ikke avanceres` | CT105 | At supervisor-løkken ikke fejler tavst |

**Kravet for at kalde leverancen færdig:** mindst ét rigtigt team skal have kørt gennem
`Task(team=…)` i drift, og de fem målinger skal være taget. Indtil da er status «implementeret,
ikke verificeret i drift» — og det er en anden status end «færdig».

### 17.3 Hvad e2e ikke kan bevise

E2e-testen kører i en isoleret runtime. Den kan ikke bevise at vækningen når **Bjørns** session, at
Desk viser teamet, eller at en rigtig model leverer et brugbart medlemssvar. De tre ting kræver en
rigtig kørsel, og de hører i §17.2 — ikke i CI.

---
