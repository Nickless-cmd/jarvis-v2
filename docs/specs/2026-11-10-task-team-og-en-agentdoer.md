---
status: til implementering
dato: 2026-11-10
version: 3
ejer: bjorn
forfatter: jarvis
review: Jarvis (self-review) → Claude (opus) ×2 → Codex ×2. Runde 1 dømte v1, runde 2 dømte v2.
         v3 er skrevet efter begge runder. Se §0.
---

# Spec: `Task` som eneste generelle agentdør — og team som tilstand, ikke som system

## 0. Ændringslog — hvad reviewene kostede

| Version | Dom | Hvad den kostede |
|---|---|---|
| v1 | **ikke klar** (Claude + Codex) | Prompten annoncerede `Task(team)`, som ikke fandtes. Motoren kunne ikke genbruges uændret. Race gav syntese over nul medlemmer. |
| v2 | **ikke klar** (Claude + Codex) | Fem blokerende fund, se nedenfor. Plus: forfatterens egen §15.2-beslutning byggede på en forkert præmis. |
| v3 | afventer review | Fem fund lukket med mekanisme, ikke med vilje. §15.2 vendt. |

**De fem fund fra runde 2, og hvor de nu lukkes:**

| # | Fund | Lukkes i |
|---|---|---|
| 1 | Syntesen går uden om `derive()` — intet mandat, ingen værktøjsliste, ingen deadline | §6.3 |
| 2 | `mandate_id` kolliderer: `canonical` indeholder ikke team, så N medlemmer får samme PRIMARY KEY | §5.2 |
| 3 | `provisioning` er en tilstand uden udgang: `_abandon()` er hårdt kodet til `GATHERING`, og `open_councils()` henter kun to statusser | §8.2 |
| 4 | `executor` afvises det forkerte sted — rollen er en etiket, `subagent_type` giver skriveret | §7.2 |
| 5 | R3 (tabt vækning) er et ønske uden mekanisme | §8.4 |

**Forfatterens egen fejl, rettet i v3:** v2's §15.2 hævdede at teamets alderstærskel kunne *arves* fra medlems-deadlines, fordi medlemmerne har samme udløb. Det holder ikke. `deadline_at` håndhæves **kun når agenten kalder et værktøj** (`agent_approval_gate.py:_mandate_verdict`), og der findes ingen sweep der udløber aktive assignments — `expire_due_queues()` rammer kun `status='queued'`. Et medlem der hænger inde i et LLM-kald bliver derfor aldrig terminalt, og teamet hænger evigt. Se §8.5.

---

## 1. Formål og succeskriterium

**Formål:** Der findes præcis **én** modelvendt vej til at starte agentarbejde: `Task`. Alle andre agentværktøjer er enten tilstande i `Task` eller pensioneret.

**Succeskriterium — målbart:**

1. `Task` er det eneste værktøj i den annoncerede flade der kan oprette en agent. `spawn_agent_task`, `relay_to_agent`, `scout_agent`, `cancel_agent`, `dispatch_code_mode_task` og `convene_agent_council` er alle i `RETIRED_AGENT_CREATION_TOOLS`.
2. Et team oprettes med `Task(team={...})`, og hvert medlem har et **gemt mandat** i `agent_assignment_mandates` — verificerbart med SQL, ikke med et løfte.
3. Et team af N medlemmer koster **ét** `Task`-kald i Jarvis' kontekst, ikke N.
4. Der findes ingen tilstand et team kan stå fast i uden at en sweep finder den.

---

## 2. Produktgrænse — hvad dette IKKE er

- **Ikke en ny motor.** Team er et mønster over `agent-contract-v1`. `agent_council.py` bliver motoren; den får ingen egen LLM-runtime og ingen ThreadPool.
- **Ikke skrivende teams i denne version.** Et teammedlem er læsende. Årsag i §7.2. Skrivende hold kræver en delt plan og en worktree-beslutning der ikke er taget.
- **Ikke en delt opgaveliste.** Størrelse og roller besluttes ved booking (§4). En skrivbar liste koster claim-konflikter og er først værd at betale når medlemmer skal omfordele arbejde undervejs.
- **Ikke en omdøbning af `agent_council.py`.** Historikken er mere værd end navnet.

---

## 3. Målt udgangspunkt (10/11-2026)

**Værktøjsfladen:**

| Måling | Tal |
|---|---|
| Agent-værktøjer i fladen | 16 |
| Faktisk brugt | 7 |
| `Task`' andel af agent-kald | 43 af 105 (**41 %**) |
| `Task` + `wait_agents` + `list_agents` | 91 af 105 (**87 %**) |
| Agent-kald som andel af ALLE værktøjskald | 105 af 19.541 (**0,5 %**) |
| `bash` som andel af alle kald | 13.106 (**67 %**) |

**Agenters varighed — 116 terminale assignments:**

| Percentil | Varighed |
|---|---|
| median | 0,5 min |
| p75 | 1,8 min |
| p90 | 3,8 min |
| p99 | 10,6 min |
| **maksimum** | **19,1 min** |
| over 30 min | **0 af 116** |
| over 45 min | **0 af 116** |

Deadline sættes per assignment: `now + 45 min` ved writes, ellers `now + 30 min` (`agent_task_facade.py:175`).

**Konsekvens for designet:** der er 11 minutters margin ved det værst observerede tilfælde. Deadline er ikke en knap ressource — men den er **ikke håndhævet for en hængende agent** (§8.5).

---

## 4. Kontrakten

```jsonc
{
  "description": "…",              // uændret
  "prompt": "…",                   // uændret — opgaven
  "subagent_type": "researcher",   // uændret i single; i team: medlemmernes standard
  "model": "…",                    // uændret
  "run_in_background": true,       // uændret
  "budget_tokens": 0,              // uændret — gælder PER MEDLEM
  "team": {                        // NYT — udeladt = single, som i dag
    "name": "råd vedr. dispatch-arkitektur",   // fri etiket, kun til mennesker
    "members": [
      {"role": "critic",     "task": "angrib forslaget"},
      {"role": "researcher", "task": "find hvad koden faktisk gør"},
      {"role": "planner",    "task": "foreslå rækkefølgen"}
    ]
  }
}
```

**Regler:**

1. `team` udeladt → nøjagtig som i dag. Ingen adfærdsændring for single.
2. `team.members` skal have **2–6** poster (`MIN_MEMBERS, MAX_MEMBERS` i `agent_council.py`). Størrelsen er et valg ved booking, ikke en fast liste.
3. `role` er **fri tekst**. Der findes ingen whitelist — den er en etiket på medlemmets opgave, ikke en port.
4. Hver `task` skal være **unik** inden for teamet. To identiske opgaver er ét svar talt to gange, og afvises.
5. `team.name` er en etiket til mennesker. **Grupperingen sker på `team_id`, ikke på navnet** (§5.1).
6. `facts` udeladt i denne version: `prompt` er det fælles faktagrundlag alle medlemmer får. Det er den eksisterende `council.topic`-semantik.

**Ukendte argumenter må ikke ignoreres stiltiende.** `Task(team=…)` mod en runtime uden feltet skal **afvises med en fejl**, ikke køre som en single-agent. Det var v1's fejl: `_exec_task` kaster ukendte argumenter væk, så et team-kald blev en helt almindelig agent uden ét ord om det.

---

## 5. Team-identitet og idempotens

### 5.1 `team_id` er nøglen, `team.name` er håndtaget

```python
team_id = "team-" + secrets.token_hex(8)
```

- `team_id` bærer `team-`-præfiks så det kan skelnes fra et `council-…` i logs.
- Navnet bruges **kun** til visning. To teams må hedde det samme.
- "Hvordan gik teamet?" besvares på `team_id`, aldrig på navn.

### 5.2 `mandate_id` — kollisionen der skal løses FØR noget andet

**Målt problem:** `derive()` udleder

```python
canonical = {"owner", "session", "parent_run", "parent_agent",
             "description", "prompt", "subagent_type", "model", "background"}
idem       = "task-" + sha256(json.dumps(canonical, sort_keys=True))[:32]
mandate_id = "mnd-" + sha256(idem)[:16]
```

`mandate_id` er `PRIMARY KEY` i `agent_assignment_mandates`. `canonical` indeholder **ikke** team og **ikke** medlemsindex. Derfor:

- Kalder `derive_team()` `derive()` N gange med samme `prompt` og samme `description`, får alle N medlemmer **identisk `mandate_id`**.
- Resultat: medlem 2 fejler på PRIMARY KEY — eller bliver læst som en replay af medlem 1.
- Retter man det ved at give hvert medlem `idem = f"{idem}:m{i}"`, er `mandate_id` **stadig** `sha256(idem)[:16]` af det oprindelige idem hvis man ikke også ændrer den linje. To steder skal rettes, ikke ét.

**Afgørelse:** `derive()` får to nye parametre med bagudkompatible defaults:

```python
def derive(..., team_id: str = "", member_index: int = -1) -> dict:
```

og `canonical` udvides med `"team_id": team_id, "member_index": member_index`.

- Single-agent: begge defaults → `canonical` er byte-identisk med i dag → **samme idem og samme `mandate_id` som før**. Ingen replay brydes.
- Teammedlem: `team_id="team-…"`, `member_index=0..N-1` → unik `mandate_id` per medlem.
- Syntesen: `member_index=-1`, `team_id` sat → egen `mandate_id`.

**Accepttest:** to teams med identiske prompts skal give to forskellige `mandate_id`-sæt, og en single-agent med samme prompt skal give det id den ville fått før ændringen.

---

## 6. Autoritet: medlemmerne skal gennem `derive()`

### 6.1 Hvorfor dette er den vigtigste sektion

`max_fanout` og `deadline` håndhæves **kun gennem et gemt mandat** (`_mandate_verdict` læser `agent_assignment_mandates`). Et medlem uden mandat har:

- ingen værktøjs-whitelist → `allowed_tools` er tom
- ingen fan-out-spærring → `max_fanout` kan ikke læses, så den håndhæves ikke
- ingen deadline → intet at overskride
- intet worktree → ingen sti at holde sig inden for

Det var v1's og v2's centrale hul: motoren blev beskrevet som "genbrugt uændret", men `convene()` gik uden om hele autoritetslaget.

### 6.2 `derive_team()` — egen funktion, der kalder `derive()`

```python
def derive_team(*, owner, session, parent_run, parent_agent, description,
                prompt, subagent_type, model, run_in_background,
                budget_tokens, team_name, members) -> dict:
    team_id = "team-" + secrets.token_hex(8)
    validated = _validate_members(members)          # 2-6, unikke tasks, fri rolle
    derived = [
        derive(..., description=description, prompt=f"{prompt}\n\nDIN OPGAVE: {m['task']}",
               subagent_type=_member_type(subagent_type), model=model,
               run_in_background=run_in_background,
               budget_tokens=budget_tokens,
               team_id=team_id, member_index=i)
        for i, m in enumerate(validated)
    ]
    return {"team_id": team_id, "team_name": team_name, "members": derived}
```

**Hvorfor egen funktion og ikke en gren i `derive()`:** en gren ville gøre enhver ændring af single-agent-stien betinget af en team-tilstand. `derive()` skal forblive den ene, uforgrenede udledning af ét barns autoritet. `derive_team()` er en **løkke over den**, ikke en variant af den.

### 6.3 Syntesen skal også gennem `derive()`

**Målt problem:** `advance()` kalder `svc.dispatch_agent(...)` direkte (`agent_council.py:179-185`) med `role=c["synthesis_role"]`, uden `derive()`. Syntesen er dermed den N+1'te assignment med præcis det hul v1 blev afvist for. `synthesizer`-skabelonen har desuden `default_tool_policy: "none"` — altså nul værktøjer.

**Afgørelse:** `advance()` kalder **facade-laget**, ikke service-laget:

```python
mandate = derive(
    owner_user_id=owner, origin_session_id=session,
    parent_run_id=c["parent_run_id"], parent_agent_id=c["parent_agent_id"] or "jarvis",
    description=f"EMNE: {c['topic']}",
    prompt=synthesis_goal(c["topic"], outcomes),
    subagent_type="critic",            # læsende; syntesen får ingen skriveret
    model="", run_in_background=False,
    budget_tokens=c["budget_tokens"],
    team_id=c["team_id"], member_index=-1,
)
out = svc.dispatch_agent(**mandate, wake_parent=False)
```

- `subagent_type="critic"` giver `writes=False`, `deadline_at=now+30min`, `allowed_tools` = read-only-sættet og et gemt mandat.
- Syntesen får dermed **mere** autoritet end i dag (en værktøjsliste og en deadline), ikke mindre — men stadig nul skriveret.
- `derive()` kan kaste `ValueError` hvis prompten kræver værktøjer syntesen ikke har. `synthesis_goal()` indeholder ingen værktøjsnavne i backticks, så det sker ikke i dag — men fejlen skal fanges og logges som en **synlig** fejl, ikke sluges (§8.4).

**Accepttest:** hver `synthesis_assignment_id` skal have en række i `agent_assignment_mandates` med `member_index = -1`.

---

## 7. Fan-out

### 7.1 Et teammedlem må ikke selv sprede sig

`derive()` sætter i dag `max_fanout: 0` og `max_depth: 0` for alle børn. Det er korrekt og skal bevares: et teammedlem der selv starter agenter giver en eksponentiel struktur ingen kan følge i Desk.

### 7.2 `executor` afvises i `derive()`, ikke i handleren

**Målt problem:** v2 afviste `role="executor"`. Men `role` er en **etiket** — `role = _ROLE.get(kind, kind)`, og `writes = kind in _WRITE_TYPES`. Det der giver skriveret er **`subagent_type`**, og den enum indeholder `"executor"`. Så `Task(subagent_type="executor", team={…})` ville give N skrivende agenter med hvert sit worktree, mens rollen hed noget andet.

**Afgørelse:** spærringen ligger i `derive()` som en mekanisk regel, ikke som en rolle-etiket:

```python
if team_id and kind in _WRITE_TYPES:
    raise ValueError(
        "et teammedlem kan ikke skrive: team er læsende i denne version. "
        "Brug en single Task(subagent_type='executor') for skrivende arbejde."
    )
```

- Den rammer **uanset** hvilken etiket rollen har.
- Den rammer i `derive()`, så den gælder for enhver kalder — også en fremtidig der ikke går gennem handleren.
- Den giver en fejl ved dispatch, ikke efter en kørsel. Samme princip som `ufuldstaendige_vaerktoejer`-vagten.

### 7.3 `_member_type()`

```python
def _member_type(top_level: str) -> str:
    kind = (top_level or "").strip().lower()
    if kind in _WRITE_TYPES:      # topniveauet bad om skrivning
        raise ValueError("team-medlemmer er læsende; se §7.2")
    return kind or "researcher"
```

En udeladt type bliver `researcher` — samme never-escalate-regel som `derive()` allerede bruger.

---

## 8. Livscyklus — og de tre måder et team kan hænge

### 8.1 Tilstande

```
provisioning ──► gathering ──► synthesizing ──► done
     │               │              │
     └───────────────┴──────────────┴──► cancelled
                                         stalled   (NY, se §8.5)
```

### 8.2 `provisioning` skal have en udgang — ellers er den en fælde

**Målt problem:** `store.create()` gemmer rådet med `members_json='[]'`. Kører `advance()` i det vindue, ser `_outcomes()` `([], True)` — og `0 != 0` er falsk, så syntesen oprettes over et tomt grundlag.

v2's svar var en `provisioning`-status. Men:

- `_abandon()` er hårdt kodet: `store.transition(cid, frm=store.GATHERING, to=store.CANCELLED)` → en `provisioning`-række kan **ikke** afbrydes.
- `open_councils()` henter `WHERE status IN (GATHERING, SYNTHESIZING)` → en `provisioning`-række bliver **aldrig** sweepet.

En tilstand ingen sweep finder, er en tilstand der hænger evigt.

**Afgørelse — tre mekaniske rettelser, alle nødvendige:**

1. **`open_councils()` henter alle ikke-terminale statusser**, udledt af en mængde snarere end to hårdt kodede konstanter:
   ```python
   OPEN_STATUSES = frozenset({PROVISIONING, GATHERING, SYNTHESIZING})
   ```
2. **`_abandon()` tager `frm` som parameter** i stedet for at gætte `GATHERING`.
3. **`advance()` springer `provisioning` over** i syntese-grenen (den må ikke producere noget), men **fejler den** hvis den er ældre end provisionerings-vinduet — se §8.5.

**Accepttest:** en council-række sat til `provisioning` med `members_json='[]'` skal (a) ikke producere en syntese, og (b) blive fundet af `open_councils()`.

### 8.3 Alt-eller-intet

Et team der ikke kan samles, skal ikke efterlade halve medlemmer. `_abandon()` afbryder de allerede startede medlemmer og lukker teamet som `cancelled`. Det er i dag korrekt — fejlen var kun `frm`-parameteren.

### 8.4 R3 — vækning der kan tabes, skal kunne gentages

**Målt problem:** `_wake_parent_on()` kaldes **efter** `transition(... to=SYNTHESIZING)` og sluger `ContractError`:

```python
except ContractError:
    logger.warning("ventekontrakt for raad %s kunne ikke registreres", ...)
```

Næste sweep forsøger ikke igen, fordi transitionen allerede er sket. Syntesen færdiggøres, men Jarvis vågner aldrig.

**Afgørelse:** vækning bliver en **selvstændig, idempotent handling**, ikke en sideeffekt af transitionen.

- Ny kolonne: `synthesis_wake_registered_at TEXT NOT NULL DEFAULT ''`.
- `advance()`'s `SYNTHESIZING`-gren kører **hver gang**, uanset syntesens status:
  ```python
  if not c["synthesis_wake_registered_at"] and c["synthesis_assignment_id"]:
      if _wake_parent_on(c, c["synthesis_assignment_id"]):
          store.mark_wake_registered(c["council_id"])
  ```
- `_wake_parent_on()` returnerer `bool` i stedet for at sluge fejlen. Fejlen **logges stadig** — men rækken forbliver tom, så næste sweep prøver igen.
- Fejlen bliver dermed selvhelbredende uden at skjule sin egen årsag: loggen har hvert forsøg, og kolonnen viser om det lykkedes.

**Accepttest:** en tvunget `ContractError` ved første forsøg skal give en tom `synthesis_wake_registered_at`, og næste `advance()` skal registrere vækningen.

### 8.5 Teamet skal have sin EGEN alderstærskel — og en sweep der håndhæver den

**Dette er rettelsen af v2's §15.2, som byggede på en forkert præmis.**

Målt: `deadline_at` håndhæves i `_mandate_verdict`, som kun kaldes **når agenten kalder et værktøj**. `expire_due_queues()` rammer kun `status='queued'`. Der findes **ingen** sweep der gør en aktiv, hængende assignment terminal.

Konsekvens: et medlem der hænger inde i et LLM-kald — eller en proces der døde midt i en kørsel — bliver aldrig terminalt. `_outcomes()` ser `all_terminal=False` for evigt, `advance()` `continue`r for evigt, og teamet hænger uden at nogen opdager det.

**Afgørelse:**

1. Teamet har en **egen** kolonne `stalled_after_at`, sat ved oprettelse til
   `max(medlems-deadlines) + SYNTHESIS_MARGIN`, hvor `SYNTHESIS_MARGIN = 15 min`.
   Begrundelse for marginen: syntesen er selv et assignment med egen 30-minutters deadline; teamet må ikke erklæres dødt mens syntesen kører.
2. `advance()` markerer teamet `stalled` når `now > stalled_after_at` og teamet stadig er i `gathering` eller `provisioning`.
3. `stalled` er en **observerbar** tilstand, ikke en tavs fejl: den vises i Desk og vækker parenten med navnet på de medlemmer der aldrig blev terminale.
4. Tærsklen er **afledt, ikke gættet** — den bygger på de målte deadlines i §3, ikke på et rundt tal som "2 timer".

**Hvorfor ikke bare lade deadline gælde:** fordi den ikke gælder. En regel der kun håndhæves ved værktøjskald kan ikke fange en agent der aldrig kalder et værktøj igen. Det er hele pointen.

---

## 9. Hvad genbruges, og hvad ændres

| Komponent | Status | Ændring |
|---|---|---|
| `agent_council.py` | **genbruges** | `convene()` → `convene_team()` med `team_id`; `advance()` gennem `derive()`; `_abandon()` får `frm`; vækning gøres gentagelig |
| `db_agent_council.py` | **ændres** | Nye kolonner: `team_id`, `team_name`, `stalled_after_at`, `synthesis_wake_registered_at`; `OPEN_STATUSES` |
| `agent_task_facade.py` | **ændres** | `derive()` får `team_id` + `member_index`; ny `derive_team()`; §7.2-spærring |
| `agent_contract_tools.py` | **ændres** | `team`-felt i skemaet; `team` med i `_exec_task`'s kendte argumenter |
| `agent_contract_handlers.py` | **ændres** | `_exec_task` grener til `derive_team()` |
| `agent_assignment_mandates` | **uændret skema** | Får flere rækker, ikke flere kolonner |
| `convene_agent_council` | **pensioneret** | Allerede fjernet 10/11 (§10) |

**Motoren røres — det er ikke en påstand om det modsatte.** v1 hævdede "én parameter, én kolonne, én gren". Det var forkert: der skal fire kolonner, to nye funktioner og tre rettelser i livscyklussen til.

---

## 10. Pensionering af `convene_agent_council` — allerede udført

Fjernet fra `agent_contract_tools.py`, `agent_contract_handlers.py`, `tool_scoping.py`, `tool_catalog.py` og `agent_orchestration.py`. Nul modelvendte hits i `core/` og `apps/`. 70 tests grønne i de tre berørte filer. `CAPABILITIES.md` regenereret.

**Codex anbefalede at rulle pensioneringen tilbage** fordi `Task(team)` endnu ikke findes. Det er ikke gjort: prompt-løftet er fjernet, så der er ingen løgn tilbage — kun et vindue uden rådsvej, og den vej havde **nul** kald. Bjørns beslutning var at den døde kode skulle ud.

**Vinduet lukkes af §14's rækkefølge.** Indtil `team`-feltet findes, kan Jarvis ikke samle et råd. Det er et bevidst fravalg, ikke en forglemmelse.

---

## 11. Prompten må ikke love feltet før det findes

**Målt fejl i v1, lavet af forfatteren selv i samme leverance:** `agent_orchestration.py` blev ændret til at nævne `` `Task` med `team` ``, mens `team`-feltet ikke fandtes. Et sådant kald ville blive **stille ignoreret** — `_exec_task` kaster ukendte argumenter væk — og starte én helt almindelig agent.

**Regel:** prompt-teksten ændres i **samme commit** som feltet, aldrig før. Indtil da er `team` fraværende fra `orchestrator_section()`, og `test_agent_orchestration.py` vogter det (backtick-navne i prompten skal være annoncerede værktøjer eller eksplicit undtagne parameternavne).

---

## 12. Risici

| # | Risiko | Håndtering |
|---|---|---|
| **R0** | **Race:** `store.create()` gemmer `members_json='[]'`, `advance()` kan se `([], True)` → syntese over nul medlemmer | `provisioning`-status + `open_councils()` dækker den + `advance()` springer den over (§8.2). **Skal ind først.** |
| **R1** | Medlem uden mandat → `max_fanout` håndhæves ikke | §6: alle medlemmer gennem `derive()`; accepttest kræver en mandat-række per medlem |
| **R2** | **Fejldiagnosticeret i v2.** Rådets række holder ingen kapacitet — kapacitet tælles som åbne assignments, så at markere et team `failed` frigiver intet | Teamet får `stalled` som **observation** (§8.5), ikke som kapacitetsfrigivelse. R2 løses ikke ved at fejle teamet |
| **R3** | Vækning tabes permanent | §8.4: `synthesis_wake_registered_at` + gentagelig registrering |
| **R4** | `mandate_id`-kollision | §5.2: `team_id` + `member_index` i `canonical` |
| **R5** | `executor` i team giver N skrivende agenter | §7.2: mekanisk spærring i `derive()` |
| **R6** | Et team der hænger, opdages aldrig | §8.5: egen `stalled_after_at` + sweep, fordi `deadline_at` ikke håndhæves for en hængende agent |
| **R7** | Teamet bliver endnu et system ingen læser — som det autonome council der blev fjernet 15/9 med begrundelsen *"hvilken effekt har det uden du læser det"* | Syntesen vækker parenten (§8.4), og resultatet lander i Jarvis' inbox. **Et team uden en læser er ikke færdigt.** |

---

## 13. Accepttests

1. **Single uændret:** en `Task` uden `team` giver byte-identisk `idempotency_key` og `mandate_id` som før ændringen.
2. **Mandat per medlem:** `Task(team={members: 3})` giver 3 rækker i `agent_assignment_mandates` med distinkte `mandate_id` og `member_index` 0,1,2.
3. **Ingen skrivning:** `Task(subagent_type="executor", team={…})` afvises med `ValueError` **før** dispatch.
4. **Ingen tom syntese:** en council i `provisioning` med `members_json='[]'` producerer ingen syntese og findes af `open_councils()`.
5. **Vækning gentages:** tvunget `ContractError` → tom `synthesis_wake_registered_at` → næste `advance()` registrerer.
6. **Stalled:** et team hvis medlem aldrig bliver terminalt markeres `stalled` efter `max(deadlines) + 15 min`.
7. **Syntese har mandat:** hver `synthesis_assignment_id` har en mandat-række med `member_index = -1`.
8. **Én dør:** `Task` er det eneste annoncerede værktøj der kan oprette en agent; de seks pensionerede navne er i `RETIRED_AGENT_CREATION_TOOLS`.
9. **Prompten lover intet:** `orchestrator_section()` indeholder ikke `team` før feltet findes.

---

## 14. Rækkefølge — ikke til forhandling

1. **R0 — race-guarden.** `provisioning` + `OPEN_STATUSES` + `_abandon(frm)` + `advance()`-skip. Den er den eneste fejl der kan producere et svar uden grundlag.
2. **§5.2 — `mandate_id`.** Uden den kan intet team med mere end ét medlem oprettes.
3. **§6 — `derive_team()` og syntese gennem `derive()`.**
4. **§7.2 — skrive-spærringen i `derive()`.**
5. **§8.4 + §8.5 — vækning og `stalled`.**
6. **§4 — `team`-feltet i skemaet, og `team` i prompten i SAMME commit.**
7. **Desk — `AgentDispatchPane` (38 linjer i dag) viser den plan der faktisk dispatches.**

Punkt 1–5 kan bygges og testes uden at `team`-feltet findes. Punkt 6 er den eneste der ændrer den modelvendte flade, og den kommer sidst fordi alt andet skal stå, før nogen kan kalde den.

---

## 15. Afgjorte punkter

### 15.1 `derive_team()` er en egen funktion, der kalder `derive()`
Ikke en gren i `derive()`. En gren ville gøre single-agent-stien betinget af en team-tilstand.

### 15.2 Teamet har sin egen alderstærskel — afledt, og håndhævet af en sweep
**v2's svar var forkert.** Det hævdede at tærsklen kunne arves fra medlems-deadlines, fordi medlemmerne har samme udløb. Målt: `deadline_at` håndhæves kun ved værktøjskald, og der findes ingen sweep for aktive assignments. Et hængende medlem bliver aldrig terminalt.

v3's svar: `stalled_after_at = max(medlems-deadlines) + 15 min`, håndhævet af `advance()` selv, med `stalled` som observerbar tilstand. Tallet er afledt af de målte deadlines (§3), ikke gættet — men det er **håndhævet**, hvilket er forskellen.

### 15.3 `team_id` bærer `team-`-prefiks
Gratis, og gør et team skelneligt fra et council-id i logs.

### 15.4 `agent_council.py` omdøbes ikke nu
Historikken er mere værd end navnet. En funktionel ændring skal ikke gøres uskelnelig fra en kosmetisk.

### 15.5 Skrivende teams er udskudt
Et teammedlem er læsende i denne version (§7.2). Skrivende hold kræver en delt plan og en worktree-beslutning der ikke er taget. Worktree-isoleringen blokerer ikke i sig selv en delt liste — listen er en tabel, ikke en fil — men et medlem kan i dag kun skrive til tre tabeller, og alle tre er per-barn. Det er den næste beslutning, ikke denne.

---

## 16. Åbent — og hvad der afgør det

**Intet blokerende.** De fem fund fra runde 2 er lukket med mekanisme. Det ene åbne punkt er afhængigt af en måling vi ikke har:

**Skal `stalled` vække parenten, eller kun vises i Desk?**
Argumentet for vækning: et team der hænger, er præcis det Jarvis skal vide. Argumentet imod: et team der hænger, er ikke et svar — det er en fejl, og Jarvis har allerede en inbox der viser fejl.

**Afgørelse:** det vises i Desk og tælles i `inbox` som en post — men det vækker **ikke** et nyt run. Vækning er forbeholdt syntesen, som er det eneste der bærer et svar. Et team der hænger, skal ikke kunne starte en tur uden indhold. Det er samme lære som 15/9.
