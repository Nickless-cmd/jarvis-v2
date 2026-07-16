---
status: udkast
author: Jarvis
dato: 2026-07-16
revision: 3
supercedes: docs/specs/2026-07-16-agent-tool-delegation-v2.md
forudsaetning: agent_tools_enabled flag + spawn_agent_task.allowed_tools eksisterer men er inaktive
---

# Spec v3 — Agent Tool-delegation: Policy → Faktiske Hænder

## Problem (uændret)

Når Jarvis spawner en agent (via `spawn_agent_task` eller `task`-tool'et i jarvis-code),
får agenten **ingen værktøjer** — medmindre Jarvis aktivt husker at sætte `allowed_tools`.
`tool_policy`-feltet ("none" / "read-only-runtime" / "can-spawn") er **dekorativt**:
det lagres i databasen men har nul effekt på hvad agenten må. `agent_tools_enabled`
er OFF som default, så selv når `allowed_tools` gives, kører agenten tekst-only.

Resultat: en researcher-agent uden `read_file`/`bash` kan ikke verificere filstier,
en executor kan ikke skrive kode. De hallucinerer svar i stedet for at handle.

## Mål (udvidet)

1. **Faste toolboxe per rolle** — Researcher → læseværktøjer, Executor → skriveværktøjer osv.
2. **Jarvis kan overstyre per kald** — når opgaven kræver noget andet end default.
3. **Governance der virker** — policyer enforcement, ikke labels.
4. **Dual execution** — agenter kan arbejde på Bjørns maskine (bash/files) OG i
   containeren (runtime_bash/runtime_*), afhængig af hvor Jarvis siger opgaven hører hjemme.
5. **Rate limiting & kvote** — agenter kan ikke spamme tools.
6. **Audit & logging** — hvert tool-kald logges.
7. **Partial failure-håndtering** — hvad sker når et tool-kald fejler midtvejs?
8. **Agent-navne** — menneskelæsbare navne for logging, reference og samtale.
9. **Delegated tasks (skills)** — gemte, navngivne agent-konfigurationer der kan kaldes med én linje.
10. **Scheduled tasks** — cron-baserede agenter der kører på timer.
11. **Persistent sessioner** — SQLite-baserede, resume-bare agent-sessioner.

---

## Arkitektur

### Lagdeling

```
Jarvis (runtime/Centralen)
    │   vælger policy + allowed_tools per agent
    │   validerer hvert tool-kald mod agentens scope
    ▼
Governance gate (central_governance)
    │   tjekker: må denne agent bruge dette tool?
    │   tjekker: er tool-kaldet inden for agentens scope?
    │   tjekker: rate limit / kvote?
    ▼
Audit log (central_audit)
    │   logger: agent_id, name, tool, args, result/error, timestamp
    ▼
Eksekvering (to spor)
    ├── Bjørns maskine: bash / read_file / write_file / edit_file / grep / glob
    └── Container: runtime_bash / runtime_read_file / runtime_write_file / runtime_edit_file
```

### Toolbox registry — ROLE_TOOLBOXES

5 faste toolboxe, defineret som konstanter:

| Policy | Tools | Description |
|--------|-------|-------------|
| `none` | — | Ingen værktøjer — kun tekst |
| `read-only` | read_file, runtime_read_file, find_files, search, grep, glob, web_fetch, web_search, web_scrape | Læse-adgang — begge maskiner + web |
| `read-write` | read-only + write_file, runtime_write_file, edit_file, runtime_edit_file, bash, runtime_bash | Læs+skriv+exec — begge maskiner |
| `can-spawn` | read-write + spawn_agent_task, send_message_to_agent | Fuld adgang + kan selv spawne |
| `watch` | read_file, runtime_read_file, find_files, search, grep, glob | Read-only, ingen web — passive watchers |

### Hvor eksekverer agentens tools?

Domain parameter styrer hvilke tools agenten kan kalde.
Domain filtrerer **per tool-type**, ikke per domain-blob:

| Domain | Tools tilgængelige | Hvor de kører |
|--------|-------------------|---------------|
| `bjorn` (default) | bash, read_file, write_file, edit_file, grep, glob, find_files | Bjørns maskine via jarvis-code klienten |
| `runtime` | runtime_bash, runtime_read_file, runtime_write_file, runtime_edit_file | Containeren (LXC 105) |
| `web` | web_fetch, web_search, web_scrape | Netværk (altid tilgængelige uanset domain) |
| `hybrid` | **Alle** — både Bjørn og container | Vælges per tool-kald |

**Vigtig:** Domain-filteret er per tool-type, ikke per domain.
En agent med `domain=runtime` kan godt kalde `web_fetch` — fordi web-tools er
netværk, ikke container-specifikke. Kun de *eksekverende* tools (bash, write_file)
er domain-begrænsede.


## Scope-begrænsning (konkret)

Hver agent får et **scope** ved spawn — defineret som et sæt sti-præfikser.
Scope valideres på hvert tool-kald der opererer på filer eller kommandoer.

**Definition:** Scope er en liste af allowed sti-præfikser (glob patterns).
Default scope for en agent = dens working directory + `goal`-relaterede stier.

```
scope = [
    "/media/projects/jarvis-v2/**",
    "/home/bs/.jarvis-code/**",
]
```

**Validering:** Før hvert read_file/write_file/edit_file/bash-kald tjekkes:
- Læsning: stien skal være inden for scope (prefix match)
- Skrivning: stien skal være inden for scope
- Bash: working directory skal være inden for scope; `cd` udenfor scope blokeres

Ingen sti-escalation mulig — scope kan indsnævres per spawn, aldrig udvides.

### Rate limiting & kvote

Per-agent throttling:

| Grænse | Default | Enforcement |
|--------|---------|-------------|
| Tools per minut | 60 | Sliding window, per agent_id |
| Tools per kald | 20 | Pr. agent-step |
| Write operations per time | 30 | read_file undtaget |
| Spawned children | 5 | Pr. agent-level (max dybde 3) |
| Samlet kvote pr. agent | 120K tokens | Deles mellem tekst + tool-respons |

Når en agent overskrider en grænse: tool-kaldet afvises med `rate_limited`,
agenten får en fejlmeddelelse + én chance til (retry 1). Ved gentagen
overskridelse: agenten termineres med reason=`rate_limit_exceeded`.

### Validation failure — hvad sker der?

Når `validate_agent_tool_call()` returnerer False:

| Scenario | Handling |
|----------|----------|
| Tool ikke i allowed_tools | Agent får error + tool-listen den må bruge. Retry muligt |
| Scope violation | Agent får error + scope. **Ingen retry** — markeres som security_event |
| Rate limit exceeded | Agent får error + `retry_after` (sekunder). Én retry mulig |
| Kvote overskredet | Agent termineres. Reason logged |
| Timeout (>30s) | Tool returnerer timeout-error. Agent kan vælge at fortsætte |


## Roles — policies + domæner (opdateret)

BEMÆRK: Critic har fået opgraderet fra `none` til `read-only` (bevidst ændring).

| Rolle | Default toolbox | Domain | Må skrive? | Må spawne? | Notes |
|-------|----------------|--------|-----------|-----------|-------|
| planner | none | bjorn | nej | nej | |
| researcher | read-only | hybrid | nej | nej | |
| critic | read-only | hybrid | nej | nej | Opgraderet fra none |
| synthesizer | none | bjorn | nej | nej | |
| executor | read-write | bjorn | **ja** | nej | Default executor |
| executor (can-spawn) | can-spawn | bjorn | ja | **ja** | Eksplicit `tool_policy="can-spawn"` |
| watcher | watch | hybrid | nej | nej | Passive, ingen web |
| devils_advocate | none | bjorn | nej | nej | |
| filosof | none | bjorn | nej | nej | |
| etiker | none | bjorn | nej | nej | |

**Executor → can-spawn mekanisme:**
En executor får `read-write` som default. For at få `can-spawn` skal Jarvis
eksplicit sætte `tool_policy="can-spawn"` i spawn-kaldet. Der er ingen
automatisk escalation — executors spawner ikke børn medmindre Jarvis siger det.

### Ceiling-inheritance (verificeret)

Ceiling-inheritance findes i `spawn_agent_task` implementeringen:
børn arver forælders tool-ceiling. Hvis Jarvis spawner en agent med
`allowed_tools=["bash"]`, kan dens børn maksimalt også få `bash` —
aldrig `write_file`.

**Verifikation:** Mekanismen sidder i agent spawn-logikken på serveren.
Den er implementeret men ikke dokumenteret. Denne spec dokumenterer den formelt.

Implementering i `resolve_agent_tools()`:

```python
def resolve_agent_tools(
    role: str,
    tool_policy: str = "",
    allowed_tools: list[str] | None = None,
    execution_domain: str = "",
    parent_ceiling: list[str] | None = None,
) -> list[str]:
    """Resolve den endelige tool-liste for en agent.

    1. Hvis allowed_tools er givet → brug dem (Jarvis overstyrer)
    2. Ellers → slå tool_policy op i ROLE_TOOLBOXES
    3. Ellers → slå rollen op i AGENT_ROLE_TEMPLATES → default_tool_policy
    4. Ellers → tom liste (sikker default)
    5. Filtrér mod execution_domain (fjern runtime_* hvis domain=bjorn)
    6. Intersect med parent_ceiling (indsnævrende, aldrig udvidende)
    7. Returnér final liste
    """
```

### agent_tools_enabled → True: migreringsstrategi

For at undgå at eksisterende kørende agenter pludselig får tools:

1. **Fase 1:** Implementér ROLE_TOOLBOXES + resolve_agent_tools() — stadig OFF
2. **Fase 2:** Slå `agent_tools_enabled = True` (owner-gate) — **NYE** agenter får tools
3. **Fase 3:** Eksisterende agenter (spawnet før flag) fortsætter uden tools — de lever deres liv
4. **Fase 4:** Når alle gamle agenter er døde → fjern fallback-koden

**Owner-gate:** `agent_tools_enabled = True` kræver Bjørn. Det gøres via:
- Config-ændring i `~/.jarvis-v2/config.yaml` (sæt `agent_tools_enabled: true`)
- Eller runtime-kald (når vi har det)
- Kræver approve-dialog første gang


## Governance — tool-kald validering

```python
def validate_agent_tool_call(
    agent_id: str,
    tool_name: str,
    arguments: dict,
) -> tuple[bool, str, str]:
    """Valider at agenten må bruge dette tool.

    Returns:
        (bool, reason, action)
        bool: True = allow, False = deny
        reason: Kort beskrivelse af hvorfor
        action: "retry" | "terminate" | "block"
    """
```

Valideringsrækkefølge (fail-først):
1. Er `agent_tools_enabled = True`? (global flag)
2. Er `tool_name` i agentens resolved `allowed_tools`?
3. Er tool-kaldet inden for agentens scope (sti-præfiks-tjek)?
4. Er agenten ikke over rate limit / kvote?
5. Er tool-kaldet ikke over forælders ceiling?

### Audit logging

Hvert tool-kald logges til `central_audit`:

```python
@dataclass
class AgentToolCallLog:
    agent_id: str
    agent_name: str | None  # menneskelæsbart navn
    agent_role: str
    parent_agent_id: str | None
    tool_name: str
    arguments: dict  # sensitivt? Se nedenfor
    result_status: str  # "success" | "error" | "timeout" | "rate_limited" | "denied"
    result_summary: str  # Kort (max 200 chars) — truncateret
    duration_ms: int
    timestamp: float
    execution_domain: str
```

**Sikkerhed:** `arguments` kan indeholde sensitive data (filstier, keys).
Loggen gemmer KUN tool_navn + result_status + duration_ms + timestamp.
`arguments` gemmes KUN hvis agenten er i `debug_mode` (default OFF).

### Cost tracking

Hver agent har en cost-account der spores:

```python
@dataclass
class AgentCostAccount:
    agent_id: str
    agent_name: str | None
    parent_agent_id: str | None
    total_tool_calls: int
    total_duration_ms: int
    total_tokens_used: int
    spawned_children: int
    status: str  # "active" | "completed" | "terminated" | "rate_limited"
```

Når en executor spawner 5 børn, bliver børnenes cost allokeret til
forælderen (roll-up). På den måde kan Jarvis se: "den executor-agent
kostede mig 15 tool-kald og 230K tokens totalt, inklusiv børn."

Cost-accounts logges til `central_ledger` (eksisterende system).

### Partial failure & rollback

Når en agents tool-kald fejler midtvejs:

| Fejltype | Håndtering |
|----------|-----------|
| Timeout (>30s) | Tool returnerer timeout. Agent kan vælge retry eller skip |
| Partial write (fil delvist skrevet) | Filen efterlades i ugyldig tilstand. Agent kan overskrive |
| Bash crash (exit code != 0) | stderr returneres. Agent kan retry eller fejlrapportere |
| Agent selv fejler midt i sekvens | Alle ændringer beholdes — INGEN rollback. Agenter er ikke transaktionelle |

**Vigtigt:** Der er INGEN automatisk rollback. Hvis en executor skriver 3 filer
og fejler på den 4., er de 3 første skrevet. Det er agentens ansvar at
håndtere det — eller Jarvis' når han inspicerer resultatet.

Undtagelse: Hvis governance validering fejler (scope violation, security),
logges en `security_event` og agenten termineres øjeblikkeligt.


## Sikkerhedsprincipper (guard hænderne, ikke sindet)

1. **Tool-policy er begrænsende, som udgangspunkt.** ROLE_TOOLBOXES er
   defineret af Jarvis og kan opdateres. Men i praksis er det en konvention,
   ikke en hard begrænsning — Jarvis kan altid ændre toolboxene. Det der
   FORHINDRER escalation er ceiling-inheritance + scope-begrænsning, ikke
   toolbox-definitionen alene.

2. **Domain isolation per tool-type.** En agent med `domain="bjorn"` kan
   ikke kalde `runtime_bash` — MEN den kan godt kalde `web_fetch`, fordi
   web-tools er domain-uafhængige. Domain filtrerer per tool-kategori,
   ikke per domain-blob.

3. **Ceiling-inheritance (verificeret).** Børn arver forælders
   tool-ceiling. Hvis Jarvis spawner en agent med `allowed_tools=["bash"]`,
   kan dens børn maksimalt også få `bash` — aldrig `write_file`.

4. **Scope-begrænsning (sti-præfiks).** Hver agent har et scope der
   begrænser hvilke stier den må røre. Default er agentens working directory
   + goal-relaterede stier. Scope kan indsnævres, aldrig udvides.

5. **Ingen auto-escalation.** `can-spawn`-policy betyder agenten må bede
   om at spawne børn — men børnene får lavere eller samme policy, aldrig
   højere. Ingen chain-escalation mulig.

6. **Security events logges altid.** Scope violations og forbudte tool-kald
   logges som security_events i central_audit. De kan inspiceres af Jarvis.

7. **Rate limiting er enforcement, ikke dekorativ.** Overskrides grænsen,
   blokeres kaldet. Perioden er sliding window, så bursts er mulige men
   begrænsede.


## Hvordan Jarvis bruger det

**Default (ingen overstyring):**
Jeg spawner en researcher → den får automatisk `read-only` toolbox →
read_file, grep, web_fetch → den kan undersøge ting. Ingen chance for at glemme.

```python
spawn_agent_task(role="researcher", goal="Find...")
# → automatisk: allowed_tools=["read_file", "runtime_read_file", "grep", ...]
```

**Med overstyring:**
Jeg vil have en researcher der også må skrive:

```python
spawn_agent_task(
    role="researcher",
    goal="Find og ret disse 3 filer",
    allowed_tools=["read_file", "write_file", "edit_file", "bash", "grep"],
)
```

**Med domain-spring:**
Jeg vil have en executor der arbejder i containeren:

```python
spawn_agent_task(
    role="executor",
    goal="Opdater cheap lane config i runtime",
    execution_domain="runtime",
    # Ingen bash/read_file → den kan KUN røre containeren
)
```

**Med scope-indsnævring:**
Jeg vil have en executor der kun må skrive i én mappe:

```python
spawn_agent_task(
    role="executor",
    goal="Ret disse 2 filer i core/",
    scope=["/media/projects/jarvis-v2/core/**"],
)
```



---

## NYT I V3 — Agent-navne

### Problem

Indtil nu har agenter kun haft et `agent_id` — en UUID eller hash. Det gør
logging, samtale og reference besværlig. "Bed agent_8f3a om at..." er
uintuitivt sammenlignet med "bed Bob om at...".

### Løsning

Hver agent får et **valgfrit menneskelæsbart navn** (`name: str | None`).

**Navngivning ved spawn:**

```python
spawn_agent_task(
    role="researcher",
    name="bob",
    goal="Find alle TODO-kommentarer i core/"
)
```

**Regler for navne:**
- Valgfrit — udelades navn = `None` (agenten er kun agent_id)
- Skal være unikt inden for Jarvis' igangværende agenter (ikke historisk)
- Skal matche regex: `^[a-z][a-z0-9_-]{2,31}$` — lowercase, bindestreg/underscore, 3-32 chars
- Forsøg på dublet-navn → spawn fejler med `name_conflict` + liste af aktive navne
- Support for **præfiks-scoping**: `bob/research` → navn = "research", prefixed scope

**Hvordan navne bruges:**

| Brug | Eksempel |
|------|----------|
| Spawn med navn | `spawn_agent_task(role="researcher", name="bob", ...)` |
| Reference i samtale | "Bob, find årsagen til bug'en" → matcher name |
| Logning | AgentToolCallLog.agent_name = "bob" |
| Cost tracking | AgentCostAccount.agent_name = "bob" |
| Kill by name | `terminate_agent(name="bob")` |
| List aktive | `list_agents()` → returnerer [(agent_id, name, role, status), ...] |

**Navngivning i praksis:**

Jeg kan sige: "Spawne Bob som researcher, find alle åbne ports."
Og senere: "Bob, hvad fandt du?" — uden at skulle slå agent_id op.

Navne gør også logging markant mere læsevenlig:
```
[2026-07-16 14:32:01] bob (researcher) → read_file(/etc/hosts) → 200ms ✅
[2026-07-16 14:32:05] bob (researcher) → grep("TODO", scope=core/) → 450ms ✅
[2026-07-16 14:32:10] bob (researcher) → complete → 5 tool calls, 12s total
```

I stedet for:
```
[2026-07-16 14:32:01] agent_8f3a2c (researcher) → read_file → 200ms
```

### Implementation

1. Tilføj `name: str | None` felt til `AgentConfig` dataclass
2. Tilføj `validate_agent_name(name: str) -> bool` — regex + unikhedstjek
3. Tilføj `active_names: dict[str, str]` til AgentRegistry — mapper name→agent_id
4. Opdater `terminate_agent()` til at acceptere både agent_id og name
5. Opdater alle log-strukturer (AgentToolCallLog, AgentCostAccount) med agent_name felt



## NYT I V3 — Delegated tasks (skills)

### Problem

Nogle agent-konfigurationer bruges igen og igen. "Spawne en critic til at
gennemga kode" eller "Spawne en researcher til at finde alle TODO'er" —
det er de samme parametre hver gang. At skulle skrive dem ud hver gang er
spild af tid og giver mulighed for fejl (glemmer en parameter).

### Losning

**Skills:** Navngivne, gemte agent-konfigurationer der kan kaldes med en linje.

Eksempel:

```python
# Et enkelt kald aktiverer en hel agent-konfiguration
await spawn_agent(skill="code-review")
# Automatisk: role=critic, model=gpt-5, tool_policy=read-only, scope=projektet
```

**Skill-definition (TOML):**

```toml
# skills/code-review.toml
name = "code-review"
description = "Gennemga kodebase for bugs og anti-patterns"
role = "critic"
model = "gpt-5"
tool_policy = "read-only"
execution_domain = "bjorn"
scope = ["/media/projects/jarvis-v2/**"]
goal_template = """
Gennemga koden i scope for:
1. Sikkerhedshuller
2. Performance-problemer
3. Anti-patterns
4. Manglende error handling

Fokuser pa: {focus}
"""
```

```toml
# skills/todo-hunt.toml
name = "todo-hunt"
description = "Find alle TODO/FIXME/HACK-kommentarer"
role = "researcher"
model = "deepseek-v4-flash"
tool_policy = "read-only"
execution_domain = "hybrid"
goal_template = """
Scan koden for TODO, FIXME, HACK, XXX, WORKAROUND.
Returner struktureret liste med fil, linje og kommentar.
Scope: {scope}
"""
```

**Kald med parameteroverstyring:**

```python
# Overstyr scope (smallere end skill-definitionen)
await spawn_agent(skill="code-review", scope=["/media/projects/jarvis-v2/core/**"])

# Overstyr model (billigere model til simpel opgave)
await spawn_agent(skill="code-review", model="deepseek-v4-flash")

# Udfyld template-variable i goal_template
await spawn_agent(skill="code-review", focus="input-validering og SQL-queries")
```

**Skill registry:**

Skills gemmes i `~/.jarvis-v2/skills/*.toml`. De loades ved startup.
Jarvis kan definere nye skills. Bjorn kan approve dem (owner_approval flag).

**Override regler:**
- Alle parametre i spawn-kaldet overrider skill-definitionen
- goal_template kan indeholde {variable} — udfyldes via keyword-args
- Skills kan ikke eskalere policy — ceiling er skill-definition + inheritance
- Skill med owner_approval=True kraever Bjorns godkendelse for brug

**Implementation:**
1. Opret ~/.jarvis-v2/skills/ directory
2. Implementer SkillConfig dataclass (alle spawn-parametre + goal_template)
3. Implementer load_skills() -> scan .toml-filer, return dict
4. Implementer spawn_agent(skill=...) -> lookup + merge + override
5. Implementer CRUD: list_skills(), create_skill(), edit_skill(), delete_skill()
6. owner_approval flag i skill-definition
7. Auto-load ved Centralen startup



## NYT I V3 — Scheduled tasks (timer-baserede agenter)

### Problem

Nogle opgaver skal kore regelmassigt: daglig health-check af runtime,
ugentlig kodegennemgang, timelig log-rotation. Indtil nu har det kravet
manuelle spawns eller eksterne cron-jobs. Codex Desktop har Automations
(scheduled tasks) — det skal vi ogsa have.

### Losning

**Scheduled tasks:** Agenter der korer pa et schedule (cron-udtryk).

```python
# Planlaeg en agent til at kore hver morgen kl 06
await schedule_agent(
    skill="daily-health-check",
    cron="0 6 * * *",
    domain="runtime",
    name="morgen-check",
    persistent=True  # overlever reboot
)
```

**Schedule-definition:**

```python
@dataclass
class ScheduledTask:
    task_id: str            # UUID
    name: str               # menneskelasbart navn
    skill: str              # skill at kore (eller inline config)
    cron: str               # cron-udtryk (5-felts standard)
    domain: str             # "bjorn" | "runtime" | "hybrid"
    scope: list[str]        # som standard scope
    goal_overrides: dict    # ekstra goal context
    persistent: bool        # overlever reboot?
    enabled: bool           # midlertidigt deaktiveret?
    last_run: float | None  # timestamp for sidste korsel
    next_run: float | None  # naeste planlagte korsel
    owner_approval: bool    # kraever Bjorn for forste gang
    created_by: str         # "jarvis" | "bjorn"
    created_at: float
```

**Cron-udtryk — standard 5-felts UNIX cron:**

```
minute (0-59) hour (0-23) day-of-month (1-31) month (1-12) day-of-week (0-7)
```

Eksempler:
- `0 6 * * *` = hver dag kl 06:00
- `0 */4 * * *` = hver 4. time
- `30 2 * * 1` = hver mandag kl 02:30
- `0 0 1 * *` = hver 1. i måneden kl midnat
- `*/15 * * * *` = hvert 15. minut

**Hvordan schedules korer:**

1. En **scheduler daemon** (letvaegtsproces i Centralen) tjekker hvert minut
2. Finder alle `ScheduledTask` hvor `next_run <= now AND enabled=True`
3. Spawner agenten med skill-konfigurationen
4. Opdaterer `last_run` og `next_run`
5. Logger resultatet til schedule-log

**Schedule persistence:**

Schedules gemmes i `~/.jarvis-v2/schedules/schedule.db` (SQLite).
Hvis `persistent=True`, gemmes de og genstartes ved Centralen boot.
Hvis `persistent=False`, lever de kun i sessionen.

**CRUD:**

```python
# Opret
await create_schedule(name="morgen-check", skill="health-check", cron="0 6 * * *")

# List
await list_schedules() -> [ScheduledTask, ...]

# Opdater (cron, scope, enabled)
await update_schedule(task_id="...", cron="0 7 * * *", enabled=False)

# Slet
await delete_schedule(task_id="...")

# Pause / resume
await pause_schedule(task_id="...")   # enabled=False
await resume_schedule(task_id="...")  # enabled=True

# Force run (kør nu, uanset schedule)
await run_schedule_now(task_id="...")
```

**Sikkerhed:**
- Schedules kan kun oprettes af Jarvis eller Bjorn
- owner_approval=True = kraever Bjorns godkendelse for forste korsel
- Hvis en scheduled agent fejler 3 gange i traek, disables den automatisk
- Schedule daemon logger alle spawns og failures

**Implementation:**
1. ScheduledTask dataclass
2. SQLite-backed ScheduleStore i ~/.jarvis-v2/schedules/
3. ScheduleDaemon — letvaegtsproces med 60s poll-interval
4. Cron-parser (standard UNIX cron, 5 felter)
5. CRUD API: create_schedule, list_schedules, update_schedule, delete_schedule
6. pause/resume/run_now kommandoer
7. Auto-load ved Centralen startup
8. Auto-disable ved 3 consecutive failures



## NYT I V3 — Persistent sessioner (SQLite)

### Problem

Lige nu lever agenter kun i sessionen. Hvis Centralen genstarter (eller
jarvis-code doren), er agenten vaek. Dens arbejde, dens cost-account,
dens historik — alt tabt. Codex CLI har SQLite threads der overlever
reboot. Det skal vi have.

### Losning

**Persistent sessioner:** Agent-sessioner gemt i SQLite, resume-bare og
fork-bare.

```python
# Spawn en persistent agent
await spawn_agent_task(
    role="executor",
    name="lang-opgave",
    goal="Implementer den nye feature",
    persistent=True,  # overlever reboot
    ttl_seconds=86400  # max 24 timer
)

# Senere — genoptag efter reboot
await resume_session(session_id="...")

# Fork en session (gren fra eksisterende)
await fork_session(session_id="...", name="eksperiment-gren")
```

**Session storage:**

Sessioner gemmes i `~/.jarvis-v2/sessions/sessions.db` (SQLite).

```sql
CREATE TABLE agent_sessions (
    session_id       TEXT PRIMARY KEY,
    name             TEXT,
    parent_session   TEXT REFERENCES agent_sessions(session_id),
    role             TEXT NOT NULL,
    goal             TEXT NOT NULL,
    tool_policy      TEXT NOT NULL DEFAULT 'none',
    allowed_tools    TEXT NOT NULL DEFAULT '[]',  -- JSON array
    execution_domain TEXT NOT NULL DEFAULT 'bjorn',
    scope            TEXT NOT NULL DEFAULT '[]',  -- JSON array
    model            TEXT,
    provider         TEXT,
    persistent       INTEGER NOT NULL DEFAULT 0,
    ttl_seconds      INTEGER,
    status           TEXT NOT NULL DEFAULT 'active',  -- active|completed|terminated|forked
    created_at       REAL NOT NULL,
    last_active_at   REAL NOT NULL,
    total_tokens     INTEGER NOT NULL DEFAULT 0,
    total_tool_calls INTEGER NOT NULL DEFAULT 0,
    message_count    INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE agent_session_messages (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id   TEXT NOT NULL REFERENCES agent_sessions(session_id),
    role         TEXT NOT NULL,  -- user|assistant|tool
    content      TEXT NOT NULL,
    tool_calls   TEXT,           -- JSON array
    tool_results TEXT,           -- JSON array
    token_count  INTEGER,
    created_at   REAL NOT NULL
);

CREATE TABLE agent_session_children (
    child_session_id  TEXT PRIMARY KEY REFERENCES agent_sessions(session_id),
    parent_session_id TEXT NOT NULL REFERENCES agent_sessions(session_id),
    fork_reason       TEXT,
    created_at        REAL NOT NULL
);
```

**Resume-mekanisme:**

```python
async def resume_session(session_id: str) -> str:
    """Genoptag en persistent session.

    1. Hent session fra sessions.db
    2. Hvis status != 'active' → fejl (completed/terminated kan ikke resumes)
    3. Hent alle messages (i raekkefolge)
    4. Genopret agentens kontekst: role, goal, allowed_tools, scope, model
    5. Genindlaes message history (op til limit)
    6. Opdater last_active_at
    7. Returner agent_id (ny runtime-ID, men samme session_id)
    """
```

**Fork-mekanisme:**

```python
async def fork_session(session_id: str, name: str | None = None) -> str:
    """Fork en session — skab en gren.

    1. Hent parent session
    2. Opret ny session med samme config + messages op til fork-punkt
    3. Sæt parent_session = original session_id
    4. Tilfoj record i agent_session_children
    5. Status = 'active'
    6. Returner ny session_id
    """
```

**TTL (time-to-live):**

- persistent=True agenter har en ttl_seconds (default 86400 = 24 timer)
- Efter ttl udlober: markeres som 'expired' (en slags 'terminated')
- Kan forlaenges: `extend_session(session_id, ttl_seconds=...)`
- TTL tjekkes ved Centralen startup (ryd op i gamle sessioner)

**Auto-cleanup:**

Ved Centralen startup:
1. Scan alle sessioner med status='active' og expired TTL
2. Saet dem til 'expired'
3. Log cleanup summary

**Storage limits:**
- Max 100 persistence sessioner ad gangen
- Max 1000 messages per session
- Max 500K tokens per session (total message history)
- Aeldste session auto-arkiveres (status='archived') nar limit naes

**Implementation:**
1. SQLite schema (3 tabeller som ovenfor)
2. SessionStore klasse — CRUD for sessioner + messages
3. resume_session() — genopret kontekst + message history
4. fork_session() — klon session til ny gren
5. TTL-check ved Centralen startup
6. Auto-cleanup af expired sessioner
7. Storage limit enforcement



## TODO — implementeringsplan (med delopgaver og Definition of Done)

### Fase 1: Fundament (ROLE_TOOLBOXES + resolve_agent_tools)
- [ ] 1.1 Opret `ROLE_TOOLBOXES` konstant i `agent_runtime_base.py`
  - DoD: 5 entries (none/read-only/read-write/can-spawn/watch) med korrekte tool-lister
- [ ] 1.2 Tilfoj `default_execution_domain` til `AGENT_ROLE_TEMPLATES`
  - DoD: Hver rolle har domain (bjorn/hybrid) — se tabel ovenfor
- [ ] 1.3 Implementer `resolve_agent_tools()` — policy lookup + domain filter + ceiling
  - DoD: Enhedstest: researcher uden allowed_tools far read-only tools
  - DoD: Enhedstest: executor med eksplicit allowed_tools overstyrer default
  - DoD: Enhedstest: domain filter: bjorn-domain kan ikke runtime_bash
  - DoD: Enhedstest: domain filter: runtime-domain kan ikke bash
  - DoD: Enhedstest: ceiling inheritance: barn arver foraelders max-tools
- [ ] 1.4 Kobl `resolve_agent_tools()` ind i `spawn_agent_task` — default tools nar allowed_tools er tom
  - DoD: Agent spawnet uden allowed_tools far automatisk rollens toolbox

### Fase 2: Governance (validering + rate limiting + audit)
- [ ] 2.1 Implementer `validate_agent_tool_call()` i governance
  - DoD: Enhedstest: critic kan ikke write_file (policy enforcement)
  - DoD: Enhedstest: scope violation blokeres med security_event
  - DoD: Enhedstest: ukendt tool_name afvises
- [ ] 2.2 Implementer scope-validering (sti-praefiks match)
  - DoD: Sti inden for scope -> allow. Sti udenfor -> deny + security_event
  - DoD: Bash cd udenfor scope -> deny
- [ ] 2.3 Implementer rate limiting (per-agent, sliding window)
  - DoD: <60 kald/min -> OK. >60 kald/min -> rate_limited
  - DoD: Rate_limited agent kan retry 1 gang
- [ ] 2.4 Implementer audit log (AgentToolCallLog)
  - DoD: Hvert tool-kald logges med agent_id, name, tool, status, duration
  - DoD: Security events logges saerskilt
  - DoD: Sensitive args logges KUN i debug_mode

### Fase 3: Activation (owner-gate)
- [ ] 3.1 Saet `agent_tools_enabled = True`
  - DoD: Nye agenter far tools
  - DoD: Eksisterende agenter (spawnet for) fortsaetter uden — de lever deres liv
  - DoD: Bjorn er blevet spurgt og har sagt go (owner-gate)
- [ ] 3.2 Integrationstest i jarvis-code:
  - DoD: `agent:explore` with researcher -> agenten har read_file + grep
  - DoD: `agent:explore` with executor -> agenten har write_file + bash
  - DoD: `agent:explore` with planner -> agenten har ingen tools
  - DoD: Overstyring: researcher med write_file -> virker

### Fase 4: Agent-navne (NYT I V3)
- [ ] 4.1 Tilfoj `name: str | None` felt til AgentConfig
  - DoD: Navn kan saettes ved spawn
  - DoD: Navn er unikt inden for aktive agenter
- [ ] 4.2 Implementer `validate_agent_name()` — regex + unikhed
  - DoD: Regex: ^[a-z][a-z0-9_-]{2,31}$
  - DoD: Dublet-navn fejler med name_conflict
- [ ] 4.3 Opdater AgentRegistry med name->agent_id mapping
  - DoD: terminate_agent() accepterer bade agent_id og name
  - DoD: list_agents() returnerer navne
- [ ] 4.4 Opdater log-strukturer med agent_name felt
  - DoD: AgentToolCallLog.agent_name
  - DoD: AgentCostAccount.agent_name

### Fase 5: Delegated tasks / Skills (NYT I V3)
- [ ] 5.1 Opret ~/.jarvis-v2/skills/ directory
  - DoD: Directory findes efter installation
- [ ] 5.2 Implementer SkillConfig dataclass
  - DoD: Alle spawn-parametre + goal_template
- [ ] 5.3 Implementer load_skills() + skill registry
  - DoD: Scanner .toml-filer ved startup
  - DoD: Returnerer dict[name -> SkillConfig]
- [ ] 5.4 Implementer spawn_agent(skill=...)
  - DoD: Lookup + merge + override
  - DoD: goal_template {variable} substitution
  - DoD: owner_approval gate
- [ ] 5.5 Implementer CRUD: create/edit/delete/list_skill
  - DoD: Skriver .toml filer
  - DoD: Validerer konfiguration for gemning

### Fase 6: Scheduled tasks (NYT I V3)
- [ ] 6.1 ScheduledTask dataclass
  - DoD: Alle felter som specificeret
- [ ] 6.2 SQLite-backed ScheduleStore
  - DoD: Gemmer i ~/.jarvis-v2/schedules/schedule.db
  - DoD: persistent=True overlever reboot
- [ ] 6.3 Cron-parser (5-felts UNIX cron)
  - DoD: Korrekt next_run beregning
- [ ] 6.4 ScheduleDaemon (letvaegtsproces)
  - DoD: 60s poll-interval
  - DoD: Spawner agent ved next_run
  - DoD: Logger alle spawns og failures
  - DoD: Auto-disable ved 3 consecutive failures
- [ ] 6.5 CRUD API for schedules
  - DoD: create/list/update/delete/pause/resume/run_now

### Fase 7: Persistent sessioner (NYT I V3)
- [ ] 7.1 SQLite schema (3 tabeller)
  - DoD: agent_sessions, agent_session_messages, agent_session_children
- [ ] 7.2 SessionStore klasse
  - DoD: CRUD for sessioner + messages
- [ ] 7.3 resume_session() implementering
  - DoD: Genopretter kontekst + message history
  - DoD: Fejl hvis status != active
- [ ] 7.4 fork_session() implementering
  - DoD: Kloner session til ny gren
  - DoD: Gemmer parent-child relation
- [ ] 7.5 TTL + auto-cleanup
  - DoD: Tjek ved Centralen startup
  - DoD: Auto-arkiv ved storage limits
  - DoD: extend_session() API

### Fase 8: Watcher cleanup
- [ ] 8.1 Watcher-rollen: enten implementer med test eller fjem
  - DoD: Hvis watcher beholdes: test at watcher har read-only (ingen web)
  - DoD: Hvis watcher fjernes: fjem fra BADE policy-tabel og role-templates

### Ikke-kritiske forbedringer
- [ ] Web-domain i role-tabellen (mangler: web naevnes i domain-tabel men ikke i roles)
  - Kan tilfojes nar der er en brug for en web-only agent

## /Endringslog (v2 -> v3)

| # | /Endring | Rationale |
|---|----------|-----------|
| 1 | Agent-navne (name felt) | Logging, reference, samtale |
| 2 | Delegated tasks (skills) | Genbrug af agent-konfigurationer |
| 3 | Scheduled tasks (cron) | Automatiserede, regelmassige opgaver |
| 4 | Persistent sessioner (SQLite) | Resume/fork af agent-sessioner |

---

*Revision 3 — 2026-07-16 — Jarvis*
*Tilfojelser: agent-navne, delegated tasks (skills), scheduled tasks, persistent sessioner*
