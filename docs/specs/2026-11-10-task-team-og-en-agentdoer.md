---
status: til implementering
dato: 2026-11-10
version: 2
ejer: bjorn
forfatter: jarvis
bygger på: 2026-10-07-agentorkestrering-og-subagenter.md (§5, §5.1, §6, §7)
review: Jarvis (self-review) → Claude (opus) → Codex. Begge eksterne reviews fandt
        blokerende fejl i v1; v2 er skrevet efter dem. Se §0.
---

# Spec: `Task` som eneste generelle agentdør — og team som tilstand, ikke som system

## 0. Ændringslog — hvad reviewene kostede

v1 blev sendt til to uafhængige reviews. Begge svarede **ikke klar**, og begge
fandt den samme blokerende fejl som forfatteren selv havde lavet i leverancen:
prompten annoncerede `Task` med et `team`-felt der ikke findes, så et kald ville
blive **stille ignoreret** og starte én almindelig agent. Det er værre end et
kapabilitetstab. **Rettet: løftet er fjernet fra prompten, målt med `grep`
(nul hits).**

Derudover er følgende rettet i v2:

| v1 påstod | Målt | Rettet i |
|---|---|---|
| "motoren røres ikke; kun én parameter, én kolonne, én gren" | `convene()` går uden om `derive()` og sender en fri `role` til `dispatch_agent` — intet mandat, ingen `allowed_tools`, ingen deadline, ingen worktree | §6, §9 |
| "et medlem kan ikke få bredere tilladelse end topniveauet" | Udækket. `role="executor"` giver `can-spawn`, og `max_fanout` håndhæves **kun** via et gemt mandat | §6 |
| "`max_fanout: 0` bevares" | Gælder kun børn af `Task`; team-medlemmer har intet mandat og dermed intet loft | §7 |
| R2: "findes ikke i dag" | `expire_due_queues()` findes, men rammer kun `queued`. Rådets række holder ingen kapacitet | §12 R2 |
| — (ikke fundet) | **Race:** `store.create()` gemmer `members_json='[]'`, og `advance()` kan nå at se `([], True)` → syntese af nul medlemmer | §8, §12 R0 |
| — (ikke fundet) | Team-idempotens udefineret: `derive()`'s `canonical` indeholder ikke `team`; replay sammenligner ikke `facts`/`team_name` | §5 |

## 1. Formål og succeskriterium

Jarvis skal have **én generel modelvendt indgang** til agentarbejde: `Task`.
Ingen parallel livscyklus, ingen anden generel oprettelsesvej.

`Task` skal kunne to ting, valgt ved bestilling:

| Tilstand | Hvad den er | Hvem bestemmer |
|---|---|---|
| `single` (standard) | Én opgave til én agent | Dagens `Task`, uændret |
| `team` | Et hold der løser **én** opgave sammen | Jarvis ved bestilling |

Et team er **ikke** en ny motor. Det er et mønster over den samme
assignment-motor, som spec 2026-10-07 §2 allerede beslutter.

**Succeskriterium.** Jarvis bestiller et team med ét `Task`-kald, får et
`team_id` og medlems-id'er straks, fortsætter sit eget arbejde, og modtager **ét**
samlet svar når syntesen er terminal. Et medlem der fejler, tæller som færdigt og
bliver **navngivet** i syntesen. `convene_agent_council` findes ikke længere i
hans værktøjsflade.

## 2. Produktgrænse

Efter denne ændring er der **to** oprettende værktøjer, ikke ét — og det skal
siges præcist:

- `Task` — den **generelle** dør til vilkårligt agentarbejde.
- `review_agent_work` — en **specialiseret** dør der kun kan oprette én læsende
  reviewer af et allerede afsluttet assignment. Den har også nul kald, men
  pensioneres ikke her (§11 punkt 4).

"Én dør" betyder i denne spec: én vej til vilkårligt agentarbejde.

`convene_agent_council` var den sidste *generelle* oprettelsesvej uden for
`Task`. Den er pensioneret (§10). **Konsekvens der skal siges højt:** indtil
§6 er bygget findes der ingen modelvendt vej til et råd. Det er acceptabelt fordi
den pensionerede vej havde **nul kald** i hele sin levetid (målt 10/11-2026), men
det er en bevidst fjernelse af kapacitet og skal stå i commit-beskeden.

## 3. Målt udgangspunkt (10/11-2026)

- `Task` er den eneste agentdør der bruges: **43 af 105** agent-kald. Med
  `wait_agents` (29) og `list_agents` (19) — opfølgning, ikke alternativer — er
  det **91 af 105 = 87 %**.
- Agent-kald er **0,5 %** af alle værktøjskald (105 af 19.563). `bash` er 67 %.
- `convene_agent_council`, `review_agent_work`, `interrupt_agent`,
  `decide_agent_approval`: **0 kald** hver.
- `agent_council.convene` er allerede variabel: `MIN_MEMBERS, MAX_MEMBERS = 2, 6`,
  `role` er en fri streng, og to medlemmer med samme opgave afvises.
- `advance()` **kører i drift**, kaldt fra `agent_contract_service.py:748`.
- `agent_task_facade.derive()` sætter `max_fanout: 0`, `max_depth: 0` og en
  `deadline_at` på 30/45 min.

## 4. Kontrakten

```jsonc
{
  "description": "…",            // uændret
  "prompt": "…",                 // uændret — opgaven, i BEGGE tilstande
  "subagent_type": "researcher", // uændret; i team: standard for medlemmer
  "model": "…",                  // uændret
  "run_in_background": true,     // uændret
  "budget_tokens": 0,            // uændret
  "team": {                      // NYT — udeladt = single, som i dag
    "name": "råd vedr. dispatch-arkitektur",
    "facts": "målt: …; besluttet: …",   // valgfrit, fælles faktagrundlag
    "members": [
      {"role": "critic",     "task": "angrib forslaget"},
      {"role": "researcher", "task": "find hvad koden faktisk gør"},
      {"role": "planner",    "task": "foreslå rækkefølge"}
    ]
  }
}
```

**Regler, alle håndhævet i `derive()` før accept:**

1. `team` udeladt → `single`, adfærd uændret.
2. `prompt` er **opgaven** i begge tilstande. I team er det hvad holdet samlet
   skal svare på; `team.facts` er det fælles faktagrundlag. Et felt må ikke
   betyde to ting afhængigt af en anden parameter.
3. `members` skal være **2–6**, udledt af `MIN_MEMBERS`/`MAX_MEMBERS` — ikke
   gentaget som literal.
4. Hvert medlem kræver `role` og `task`, begge ikke-tomme.
5. To medlemmer må ikke have samme `task`.
6. `team` kan ikke kombineres med `run_in_background: false` (§11 punkt 2).
7. **`synthesis_role` er ikke et felt.** Syntesen er altid rollen
   `synthesizer` med `subagent_type` arvet fra topniveauet. v1 lod Jarvis vælge
   den; det gav en vej til at give syntesen `executor`-kapabilitet gennem
   bagdøren. Den er lukket.

## 5. Team-identitet og idempotens

| Felt | Ejer | Formål |
|---|---|---|
| `team_id` | runtime, genereret | Gruppering, historik, ventekontrakt |
| `team.name` | Jarvis, fri tekst | Læsbarhed. **Ikke** en nøgle |

Navnet må ikke være nøglen: to råd kan hedde det samme med ugers mellemrum, og
et idempotent genkald ville så returnere det forkerte teams svar.

**Idempotens (målt nødvendig — v1 havde den ikke).** `derive()`'s `canonical`
(`agent_task_facade.py:189-194`) indeholder i dag ikke `team`. Uden rettelse
giver to forskellige team med samme `prompt` **samme** `idempotency_key`, og det
andet kald returnerer det første teams svar. Derfor:

- `canonical` skal omfatte `team.name`, `team.facts` og de sorterede
  `(role, task)`-par.
- `convene()`'s replay-sammenligning skal ud over `topic` og `(role, task)` også
  sammenligne `facts` og `team_name` (`agent_council.py:83`).
- **Replay af et `cancelled` team må ikke svare `accepted`.** `_view()`
  (`agent_council.py:125`) gør det i dag. Det er en løgn om en accept der blev
  rullet tilbage.

Lageret er den eksisterende `agent_councils`-tabel. `council_id` **er**
`team_id`. Der tilføjes to kolonner: `team_name` og `team_facts`, begge
`DEFAULT ''` så eksisterende rækker læses uændret.

## 6. Autoritet: medlemmerne skal gennem `derive()`

Dette er v2's største ændring, og den er ikke kosmetisk.

**Målt i v1's model:** `convene()` kalder `svc.dispatch_agent(role=<fri streng>,
…)` uden `mandate`, `tool_policy`, `allowed_tools`, `deadline_at` eller
`max_turns` (`agent_council.py:95-101`). Konsekvenserne:

- **Værktøjer** kommer fra skabelonens `default_tool_policy`, så en læsende
  rolle får `bash` i containeren — præcis det `derive()` bevidst fjerner
  (`_UDELADTE_TOOLS`).
- **`role="executor"` giver `can-spawn`** (`agent_runtime_base.py:789`), og det
  sæt indeholder `spawn_agent_task` (`:684`) — stadig en levende handler. Uden
  mandat findes ingen `max_fanout`-kontrol: den håndhæves kun for et gemt
  mandat og kun for navnet `Task` (`agent_approval_gate.py:154`, `:206`).
- **En `executor` i et team får `writes=False`** og intet worktree, men beholder
  `can-spawn` og container-`bash`. Det er den dårligste kombination: ingen
  isolering, men spredning.
- **Ingen deadline** — et hængende medlem udløber aldrig.
- `ufuldstaendige_vaerktoejer`-tjekket springes over.

**Derfor:** `role` er en **ren persona-etiket**. Den må aldrig vælge policy.

Den nye vej:

```
Task(team={…})
  → derive_team()  → N færdige dispatch-planer (samme form som derive() giver)
  → convene(plans=[…])  → dispatch_agent(**plan) pr. medlem
```

`convene()` tager **færdige planer** ind i stedet for selv at kalde
`dispatch_agent(role=…)`. `role` bruges derefter kun i `MEMBER_GOAL_HEAD` som
menneskelæsbar etiket. Dispatch-rollen er den udledte `_ROLE[kind]`.

**I v1 afvises `executor` i et team helt.** Et team er et læsende mønster indtil
videre. Skal et team skrive, kræver det en beslutning om worktrees og en delt
plan — ikke en bivirkning af at nogen skrev `executor` i en medlemsrolle.

## 7. Fan-out

`derive()` sætter `max_fanout: 0`. Det gælder **kun** børn af `Task`, fordi
loftet håndhæves via det gemte mandat. Team-medlemmer får i v2 deres eget mandat
gennem `derive_team()` og dermed samme loft — men det er en **konsekvens af §6**,
ikke noget der følger af sig selv.

Reglen står fast:

> Kun Jarvis' eget run kan bestille et team. Et team kan ikke bestille et
> undertema. Et medlem kan ikke spawne hjælpere.

`_room_for()` kontrollerer alle medlemmer før noget startes. Skal et medlem
senere kunne delegere, er det en udtrykkelig ændring af `max_fanout` med eget
loft — ikke en bivirkning.

## 8. Livscyklus — og racen der skal lukkes

```
Task(team={…})
   ├─ validering (2–6, unikke opgaver, kapacitet)  ── afvist ⇒ intet startet
   ├─ team_id oprettet, status = provisioning      ← NYT
   ├─ N assignments dispatchet
   ├─ medlemslisten gemt, status = gathering
   │     └─ svigter ét ⇒ de øvrige afbrydes, status = cancelled
   ▼
advance()  ← reconcile-sweepen
   │  KUN councils i gathering
   │  alle medlemmer terminale?  (fejl tæller som terminalt)
   ├─ nej ⇒ vent
   └─ ja  ⇒ syntese oprettes, status = synthesizing
                 └─ ventekontrakt på SYNTESEN, ikke på medlemmerne
   ▼
syntese terminal ⇒ status = done ⇒ Jarvis vakt ét sted med ét svar
```

**R0 — racen (fundet af begge reviewere, ikke af forfatteren).**
`store.create()` gemmer rådet som `gathering` med `members_json='[]'`
(`db_agent_council.py:68-74`), og `set_members` kaldes først når alle N
dispatches er færdige (`agent_council.py:108`). Kører `advance()` i det vindue,
giver `_outcomes(owner, [])` → `([], True)`, og tjekket
`len(outcomes) != len(c["members"])` bliver `0 != 0` → **falsk**. Syntesen
oprettes med nul medlemmer, rådet skifter til `synthesizing`, og `_abandon`
bagefter fejler stille fordi `GATHERING→CANCELLED` returnerer `False`.

Vinduet er reelt: hver dispatch går gennem routing, fork-planlægning og
worktree-oprettelse, og `advance()` kan køre fra begge processer.

**Lukket ved:** en ny status `provisioning` (oprettet, ingen medlemmer endnu).
`advance()` rører **kun** `gathering`. Det er en eksplicit tilstand i stedet for
en tom liste der tilfældigvis ser terminal ud.

## 9. Hvad genbruges, og hvad ændres

| Del | Status |
|---|---|
| `advance()` / supervisor | Genbruges, **+ guard mod `provisioning`** |
| `_validate()` — 2–6, fri rolle, unik opgave | Genbruges uændret |
| `_room_for()` — kapacitet før start | Genbruges uændret |
| `_abandon()` — intet halvt team | Genbruges, men skal **logge** når overgangen returnerer `False` |
| `_wake_parent_on()` — vækning på syntesen | Genbruges, **+ retry** (§12 R3) |
| `synthesis_goal()` | Genbruges uændret |
| `agent_councils`-tabellen | Genbruges, **+ `team_name`, `team_facts`, status `provisioning`** |
| `convene()` | **Ændres:** tager færdige planer ind; `role` bliver etiket |
| `derive()` | **Ny gren** `derive_team()` → N planer |
| `Task`-skemaet | **Nyt felt**: `team` |
| `convene_agent_council` som værktøj | **Pensioneret** |

Netto: motoren **røres** — på fire punkter, alle nødvendige. v1's påstand om
"én parameter, én kolonne, én gren" var forkert.

## 10. Pensionering af `convene_agent_council` — udført

Fjernet fra alle modelvendte flader. **Målt 10/11-2026:**
`grep -rn "convene_agent_council" --include="*.py" core/ apps/` giver **nul**
hits.

| Fil | Handling |
|---|---|
| `core/tools/agent_contract_tools.py` | Definition, handler, `CONTRACT_TOOL_NAMES`, `_NEW_ONLY` |
| `core/tools/agent_contract_handlers.py` | Import og map-entry |
| `core/tools/tool_scoping.py` | Tre lister |
| `core/services/tool_catalog.py` | `("Agenter", […])` |
| `core/services/prompt_sections/agent_orchestration.py` | Council-mønstret fjernet fra prompten |
| `tests/test_agent_contract_tools.py`, `test_agent_orchestration.py`, `test_agent_council.py` | Opdateret; `agent_council.convene` testes direkte |

Motoren (`agent_council.py`, `db_agent_council.py`) står. De genererede
referencer `docs/reference/CAPABILITIES.md` og
`docs/reference/api/core.tools.01.md` skrives af repoets hooks og forsvinder ved
næste regenerering — de må ikke rettes i hånden.

## 11. Bevidste fravalg

1. **Ingen skrivbar delt opgaveliste.** Holdets sammensætning — og dermed
   opgavefordelingen — besluttes ved bestilling. En liste der ikke kan ændres,
   behøver ikke være skrivbar, kun **synlig**. En skrivbar liste koster
   claim-konflikter, forældede claims og rækkefølgeafhængigheder.
2. **`team` + `run_in_background: false` afvises.** En synkron venten på et helt
   team binder Jarvis' tur mens N medlemmer plus en syntese kører.
3. **Ingen team-hukommelse på tværs af kørsler.** `team_id` grupperer én kørsel.
4. **`review_agent_work` pensioneres ikke her.** Den er en specialiseret dør, ikke
   en generel.
5. **`executor` i team afvises i v1** (§6).
6. **`synthesis_role` er ikke et felt** (§4 regel 7).

## 12. Risici

**R0 — race mellem `convene` og `advance`.** Syntese af nul medlemmer. Lukket
ved `provisioning`-tilstanden (§8). **Blokerende hvis ikke lukket.**

**R1 — kapabilitetstab i vinduet.** Indtil §6 er bygget findes ingen rådsvej.
Afbødet ved at den gamle vej havde nul kald. Byg §6 og §10's efterladenskaber i
**samme** leverance fremover.

**R2 — fejldiagnosticeret i v1.** Rådets række holder **ingen** kapacitet;
kapacitet tælles som åbne assignments (`db_agent_contract.py:843-853`). At sætte
council-status til `failed` frigiver derfor intet. De tre reelle måder et team
kan hænge på:

- (a) et medlem står `active`/`waiting` uden deadline — fordi team-medlemmer i
  dag ikke får `derive()`'s `deadline_at`;
- (b) syntesen kan ikke accepteres (kapacitet) og prøves igen hver tick, mens
  rådet står i `gathering`;
- (c) syntesen accepteres men bliver aldrig terminal.

Alle tre løses i §6 (deadline pr. medlem) plus en alderstærskel på teamet selv.
**Tærsklen skal arves fra `derive()`'s deadline (30/45 min), ikke gættes til
2 timer.**

**R3 — vækning kan tabes permanent.** `_wake_parent_on()` kaldes efter
`transition()` til `synthesizing`, og en `ContractError` **logges og sluges**
(`agent_council.py:189-215`). Næste sweep forsøger ikke registreringen igen.
Syntesen færdiggøres, men Jarvis vågner aldrig. Kræver: registreringen skal
kunne gentages, eller fejlen skal gøre rådet synligt i tilstanden.

**R4 — `cancel_agent`-navnekollision.** Står som annonceret agentværktøj i
`copilot_tool_pruning.py:360`, men er en **funktion** i `agent_runtime_spawn` som
Central-UI'et kalder. Ikke rettet her; samme fejlklasse som R1 i
pensionsarbejdet: et internt funktionsnavn der ser ud som en dør.

## 13. Accepttests

Eksisterende 1–9 fra v1, plus de huller reviewene fandt:

1. `Task` uden `team` → identisk adfærd (regressionstest).
2. `Task(team)` med 2 og med 6 medlemmer → accepteret, `team_id` returneret.
3. 1 eller 7 medlemmer → `INVALID_SCOPE`, **intet** startet.
4. To medlemmer med samme `task` → `INVALID_SCOPE`, intet startet.
5. Kapacitet utilstrækkelig → afvist før start; `count_open_assignments` uændret.
6. Eet medlem fejler → syntesen navngiver det, teamet bliver `done`.
7. `convene_agent_council` findes ikke i nogen scope, i `load_more_tools`, i
   `tool_catalog` eller i prompten; `grep` giver nul hits i `core/`+`apps/`.
8. `team_name` og `team_facts` overlever genstart og kan læses tilbage på `team_id`.
9. **R0-race:** `advance()` kaldt midt i `convene` (monkeypatch `dispatch_agent`
   så den kalder `advance`) må ikke give en syntese med 0 medlemmer.
10. **Tilladelser:** hvert medlems `allowed_tools` er lig `derive()`'s sæt —
    uden `bash` og uden `spawn_agent_task` — og der findes et gemt mandat med
    `max_fanout=0` og en `deadline_at`.
11. **Roller:** `role="executor"` i et medlem afvises; syntesen kan ikke få
    `executor`-kapabilitet.
12. **Prompt mod skema:** hver parameter prompten nævner findes i skemaet. En
    test der fanger næste gang nogen skriver et felt ind i prompten før det
    findes.
13. **Idempotens:** samme `Task(team)` to gange giver samme `team_id` og ingen
    ekstra assignments; forskellige team med samme `prompt` giver **forskellige**
    id'er; replay af et `cancelled` team svarer ikke `accepted`.
14. **Delvis fejl:** når medlem 3 fejler, er medlem 1–2 afbrudt og
    `count_open_assignments` tilbage på udgangspunktet.
15. **Syntese-fejl:** en ikke-kapacitetsfejl i syntese-dispatch må ikke give et
    evigt loop, og det skal være defineret hvad Jarvis får hvis syntesen selv fejler.
16. **Migration:** en eksisterende tabel uden `team_name`/`team_facts` migreres
    korrekt og læses uændret.

## 14. Implementeringsrækkefølge

1. `team_name` + `team_facts`-kolonner, status `provisioning` (migration,
   bagudkompatibel).
2. **R0-guard** i `advance()` — før noget andet, ellers bygger vi oven på racen.
3. `derive_team()` → N planer gennem den eksisterende `derive()`-logik.
4. `convene(plans=…)`: tag planer ind, `role` som etiket, `synthesis_role` låst.
5. `Task`-skemaets `team`-felt + prompt-sætningen — **i samme commit som 3–4**,
   så prompten aldrig lover noget der ikke findes.
6. Idempotens (§5): `canonical` + replay-sammenligning + `cancelled`-svar.
7. R2/R3-værn: deadline pr. medlem, alderstærskel, gentagelig vækning.
8. `AgentDispatchPane`: vis team-planen den faktisk dispatcher.

## 15. Åbne punkter

1. **§6:** skal `derive_team()` være en egen funktion, eller en gren i
   `derive()`? Egen funktion er renere, men duplikerer valideringen.
2. **§12 R2:** alderstærsklen arves fra `derive()`'s deadline — men et team har
   N medlemmer med hver sin deadline. Er teamets tærskel `max(deadlines) + syntese`?
3. **§5:** skal `team_id` være et prefiks (`team-…`) så det kan skelnes fra et
   `council_id` i logs?
4. **§9:** bør `agent_council.py` omdøbes til `agent_team.py`, når det nu er den
   offentlige flade? Omdøbning koster git-historik.
