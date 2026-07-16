---
status: udkast
author: Jarvis
dato: 2026-07-16
revision: 2
supercedes: docs/specs/2026-07-16-agent-tool-delegation.md
forudsaetning: agent_tools_enabled flag + spawn_agent_task.allowed_tools eksisterer men er inaktive
---

# Spec v2 — Agent Tool-delegation: Policy → Faktiske Hænder

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
    │   logger: agent_id, tool, args, result/error, timestamp
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

**Vigtig ændring fra v1:** Domain-filteret er per tool-type, ikke per domain.
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

---

## Roles — policies + domæner (opdateret)

BEMÆRK: Critic har fået opgraderet fra `none` til `read-only` (bevidst ændring).
I v1 havde critic "none (men siges at verificere!)" — det var en bug. En critic
der ikke kan læse kode kan ikke verificere noget. Denne spec retter det.

| Rolle | Default toolbox | Domain | Må skrive? | Må spawne? | Notes |
|-------|----------------|--------|-----------|-----------|-------|
| planner | none | bjorn | nej | nej | |
| researcher | read-only | hybrid | nej | nej | |
| critic | read-only | hybrid | nej | nej | Opgraderet fra none — se note |
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
Den er IKKE dokumenteret i v1 spec men er implementeret. Denne spec
dokumenterer den formelt.

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

3. **Ceiling-inheritance (verificeret, se ovenfor).** Børn arver forælders
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

### Hvordan Jarvis bruger det

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


## TODO — implementeringsplan (med delopgaver og Definition of Done)

### Fase 1: Fundament (ROLE_TOOLBOXES + resolve_agent_tools)
- [ ] 1.1 Opret `ROLE_TOOLBOXES` konstant i `agent_runtime_base.py`
  - DoD: 5 entries (none/read-only/read-write/can-spawn/watch) med korrekte tool-lister
- [ ] 1.2 Tilføj `default_execution_domain` til `AGENT_ROLE_TEMPLATES`
  - DoD: Hver rolle har domain (bjorn/hybrid) — se tabel ovenfor
- [ ] 1.3 Implementér `resolve_agent_tools()` — policy lookup + domain filter + ceiling
  - DoD: Enhedstest: researcher uden allowed_tools får read-only tools
  - DoD: Enhedstest: executor med eksplicit allowed_tools overstyrer default
  - DoD: Enhedstest: domain filter: bjorn-domain kan ikke runtime_bash
  - DoD: Enhedstest: domain filter: runtime-domain kan ikke bash
  - DoD: Enhedstest: ceiling inheritance: barn arver forælders max-tools
- [ ] 1.4 Kobl `resolve_agent_tools()` ind i `spawn_agent_task` — default tools når allowed_tools er tom
  - DoD: Agent spawnet uden allowed_tools får automatisk rollens toolbox

### Fase 2: Governance (validering + rate limiting + audit)
- [ ] 2.1 Implementér `validate_agent_tool_call()` i governance
  - DoD: Enhedstest: critic kan ikke write_file (policy enforcement)
  - DoD: Enhedstest: scope violation blokeres med security_event
  - DoD: Enhedstest: ukendt tool_name afvises
- [ ] 2.2 Implementér scope-validering (sti-præfiks match)
  - DoD: Sti inden for scope → allow. Sti udenfor → deny + security_event
  - DoD: Bash cd udenfor scope → deny
- [ ] 2.3 Implementér rate limiting (per-agent, sliding window)
  - DoD: <60 kald/min → OK. >60 kald/min → rate_limited
  - DoD: Rate_limited agent kan retry 1 gang
- [ ] 2.4 Implementér audit log (AgentToolCallLog)
  - DoD: Hvert tool-kald logges med agent_id, tool, status, duration
  - DoD: Security events logges særskilt
  - DoD: Sensitive args logges KUN i debug_mode

### Fase 3: Activation (owner-gate)
- [ ] 3.1 Sæt `agent_tools_enabled = True`
  - DoD: Nye agenter får tools
  - DoD: Eksisterende agenter (spawnet før) fortsætter uden — de lever deres liv
  - DoD: Bjørn er blevet spurgt og har sagt go (owner-gate)
- [ ] 3.2 Integrationstest i jarvis-code:
  - DoD: `agent:explore` with researcher → agenten har read_file + grep
  - DoD: `agent:explore` with executor → agenten har write_file + bash
  - DoD: `agent:explore` with planner → agenten har ingen tools
  - DoD: Overstyring: researcher med write_file → virker

### Fase 4: Watcher cleanup
- [ ] 4.1 Watcher-rollen: enten implementér med test eller fjern
  - DoD: Hvis watcher beholder: test at watcher har read-only (ingen web)
  - DoD: Hvis watcher fjernes: fjern fra BÅDE policy-tabel og role-templates

### Ikke-kritiske forbedringer
- [ ] Web-domain i role-tabellen (mangler: web nævnes i domain-tabel men ikke i roles)
  - Kan tilføjes når der er en brug for en web-only agent

---

## Ændringslog (v1 → v2)

| # | Ændring | Rationale |
|---|---------|-----------|
| 1 | Scope-begrænsning specificeret (sti-præfiks) | V1 var ukomplet |
| 2 | Domain-filter per tool-type (ikke per domain-blob) | V1 var for rigid |
| 3 | Security principle #1 omformuleret | V1 var misvisende (kaldte det "hard begrænsning") |
| 4 | Rate limiting tilføjet | Manglede helt i v1 |
| 5 | Validation failure handling specificeret | Manglede helt i v1 |
| 6 | Migreringsstrategi for agent_tools_enabled | V1 var uklar |
| 7 | Ceiling-inheritance verificeret og dokumenteret | V1 sagde "eksisterende" men uden bevis |
| 8 | Watcher-rolle: TODO tilføjet (implementér eller fjern) | V1 orphaned |
| 9 | Cost tracking tilføjet | Manglede helt i v1 |
| 10 | Partial failure håndtering specificeret | Manglede helt i v1 |
| 11 | Domain-tabel: inkonsistens noteret (web-domain) | V1 havde web i domain men ikke i roles |
| 12 | Audit logging tilføjet | Manglede helt i v1 |
| 13 | Executor→can-spawn mekanisme specificeret | V1 var uklar |
| 14 | Critic opgradering markeret som bevidst ændring | V1 ændrede uden kommentar |
| 15 | TODO udvidet med delopgaver + DoD | V1 var for simpel |
| 16 | Owner-gate specificeret (config + approve) | V1 var uklar |

---
*Revision 2 — 2026-07-16 — Jarvis*
*Self-review baseret på 16 punkter fra gennemgang*
