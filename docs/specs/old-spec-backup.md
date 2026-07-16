---
status: udkast
author: Jarvis
dato: 2026-07-16
forudsaetning: agent_tools_enabled flag + spawn_agent_task.allowed_tools eksisterer men er inaktive
---

# Spec — Agent Tool-delegation: Policy → Faktiske Hænder

## Problem

Når Jarvis spawner en agent (via `spawn_agent_task` eller `task`-tool'et i jarvis-code), får agenten **ingen værktøjer** — medmindre Jarvis aktivt husker at sætte `allowed_tools`. `tool_policy`-feltet ("none" / "read-only-runtime" / "can-spawn") er **dekorativt**: det lagres i databasen men har nul effekt på hvad agenten må. `agent_tools_enabled` er OFF som default, så selv når `allowed_tools` gives, kører agenten tekst-only.

Resultat: en researcher-agent uden `read_file`/`bash` kan ikke verificere filstier, en executor kan ikke skrive kode. De hallucinerer svar i stedet for at handle.

## Mål

1. **Faste toolboxe per rolle** — Researcher → læseværktøjer, Executor → skriveværktøjer osv.
2. **Jarvis kan overstyre per kald** — når opgaven kræver noget andet end default.
3. **Governance der virker** — policyer enforcement, ikke labels.
4. **Dual execution** — agenter kan arbejde på Bjørns maskine (bash/files) OG i containeren (runtime_bash/runtime_*), afhængig af hvor Jarvis siger opgaven hører hjemme.

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
    ▼
Eksekvering (to spor)
    ├── Bjørns maskine: bash / read_file / write_file / edit_file / grep / glob
    └── Container: runtime_bash / runtime_read_file / runtime_write_file
```

### Policy → Toolbox mapping

Hver rolle får en **fast toolbox** baseret på dens `tool_policy`. Når Jarvis spawner en agent uden eksplicit `allowed_tools`, arver agenten rollens default toolbox.

| Policy | Roller | Tools |
|--------|--------|-------|
| `none` | planner, synthesizer, devils_advocate, filosof, etiker | **Ingen** — agenten kan kun tænke og skrive tekst |
| `read-only` | researcher, critic (research-delen) | `read_file`, `runtime_read_file`, `find_files`, `search`/`grep`, `glob`, `web_fetch`, `web_search`, `web_scrape` |
| `read-write` | executor | `read_file`, `runtime_read_file`, `write_file`, `runtime_write_file`, `edit_file`, `bash`, `runtime_bash`, `find_files`, `search`, `glob`, `grep`, `web_fetch` |
| `can-spawn` | executor (når den skal delegere) | `read-write` + `spawn_agent_task`, `send_message_to_agent` |
| `watch` | watcher | `read_file`, `runtime_read_file`, `find_files`, `search`, `grep` |

**Jarvis kan overstyre per kald.** Eksempel:

```python
spawn_agent_task(
    role="researcher",
    goal="Find alle steder hvor tool_policy er deklarativ",
    allowed_tools=["read_file", "bash", "runtime_bash", "grep"],
    # overstyrer researcher's default read-only toolbox
)
```

### Hvor eksekverer agentens tools?

Afhængig af `execution_domain`-parameteren:

| Domain | Tools tilgængelige | Hvor de kører |
|--------|-------------------|---------------|
| `bjorn` (default) | bash, read_file, write_file, edit_file, grep, glob, find_files | Bjørns maskine via jarvis-code klienten |
| `runtime` | runtime_bash, runtime_read_file, runtime_write_file, runtime_edit_file | Containeren (LXC 105) |
| `web` | web_fetch, web_search, web_scrape | Netværk (altid tilgængelige uanset domain) |
| `hybrid` | **Alle** — både Bjørn og container | Vælges per tool-kald |

Default er `bjorn` — agenter arbejder på Bjørns maskine, medmindre Jarvis siger andet.

---

## Implementering

### 1. Toolbox registry — `ROLE_TOOLBOXES`

Ny konstant i `agent_runtime_base.py`:

```python
ROLE_TOOLBOXES: dict[str, dict] = {
    "none": {
        "tools": [],
        "description": "Ingen værktøjer — kun tekst",
    },
    "read-only": {
        "tools": [
            "read_file", "runtime_read_file",
            "find_files", "search", "grep", "glob",
            "web_fetch", "web_search", "web_scrape",
        ],
        "description": "Læse-adgang — Bjørns maskine + container + web",
    },
    "read-write": {
        "tools": [
            # read
            "read_file", "runtime_read_file",
            "find_files", "search", "grep", "glob",
            "web_fetch", "web_search", "web_scrape",
            # write
            "write_file", "runtime_write_file",
            "edit_file", "runtime_edit_file",
            # exec
            "bash", "runtime_bash",
        ],
        "description": "Læs+skriv+exec — begge maskiner",
    },
    "can-spawn": {
        "tools": [
            # alt fra read-write
            "read_file", "runtime_read_file",
            "find_files", "search", "grep", "glob",
            "web_fetch", "web_search", "web_scrape",
            "write_file", "runtime_write_file",
            "edit_file", "runtime_edit_file",
            "bash", "runtime_bash",
            # spawn
            "spawn_agent_task", "send_message_to_agent",
        ],
        "description": "Fuld adgang + kan selv spawne",
    },
    "watch": {
        "tools": [
            "read_file", "runtime_read_file",
            "find_files", "search", "grep", "glob",
        ],
        "description": "Read-only, ingen web — til passive watchers",
    },
}
```

### 2. Link AGENT_ROLE_TEMPLATES → ROLE_TOOLBOXES

```python
AGENT_ROLE_TEMPLATES = {
    "planner": {
        "title": "Planner",
        "default_tool_policy": "none",       # → ROLE_TOOLBOXES["none"]
        "default_execution_domain": "bjorn", # kører på Bjørns maskine
        ...
    },
    "researcher": {
        "title": "Researcher",
        "default_tool_policy": "read-only",  # → ROLE_TOOLBOXES["read-only"]
        "default_execution_domain": "hybrid", # kan læse begge steder
        ...
    },
    "executor": {
        "title": "Executor",
        "default_tool_policy": "read-write", # → ROLE_TOOLBOXES["read-write"]
        "default_execution_domain": "bjorn", # skriver på Bjørns maskine
        ...
    },
    "critic": {
        "title": "Critic",
        "default_tool_policy": "read-only",
        "default_execution_domain": "hybrid",
        ...
    },
    ...
}
```

### 3. Resolver-funktion — `resolve_agent_tools()`

Ny funktion der samler den endelige tool-liste:

```python
def resolve_agent_tools(
    role: str,
    tool_policy: str = "",
    allowed_tools: list[str] | None = None,
    execution_domain: str = "",
) -> list[str]:
    """Resolve den endelige tool-liste for en agent.

    1. Hvis allowed_tools er givet → brug dem (Jarvis overstyrer)
    2. Ellers → slå tool_policy op i ROLE_TOOLBOXES
    3. Ellers → slå rollen op i AGENT_ROLE_TEMPLATES → default_tool_policy
    4. Ellers → tom liste (sikker default)
    5. Filtrér mod execution_domain (fjern runtime_* hvis domain=bjorn, osv.)
    """
    ...
```

### 4. Governance — tool-kald validering

Hver gang en agent laver et tool-kald, validerer Centralen:

```python
def validate_agent_tool_call(
    agent_id: str,
    tool_name: str,
    arguments: dict,
) -> tuple[bool, str]:
    """Valider at agenten må bruge dette tool.

    Tjek:
    1. Er tool_name i agentens resolved allowed_tools?
    2. Er tool-kaldet inden for scope (ingen sti-escalation)?
    3. Er agenten ikke overskredet budget/kvote?
    """
    ...
```

**Scope-begrænsning:** En executor-agent med `write_file` må skrive til `/media/projects/jarvis-v2/` men ikke til `/etc/` eller `/home/bs/.ssh/`. Scope sættes per spawn og kan indsnævres (aldrig udvides). Default scope = agentens `goal` + role-rolle.

### 5. `agent_tools_enabled` — skal være ON

For at det hele virker, skal `agent_tools_enabled` sættes til True (owner-gated). Det gør jeg når du siger go.

---

## Roles — policies + domæner (oversigt)

| Rolle | Default tools | Domain | Må skrive? | Må spawne? |
|-------|-------------|--------|-----------|-----------|
| planner | none | bjorn | nej | nej |
| researcher | read-only | hybrid | nej | nej |
| critic | read-only | hybrid | nej | nej |
| synthesizer | none | bjorn | nej | nej |
| executor | read-write | bjorn | **ja** | nej |
| executor (can-spawn) | can-spawn | bjorn | ja | **ja** |
| watcher | watch | hybrid | nej | nej |
| devils_advocate | none | bjorn | nej | nej |
| filosof | none | bjorn | nej | nej |
| etiker | none | bjorn | nej | nej |

---

## Hvordan Jarvis bruger det

### Default (ingen overstyring)

Jeg spawner en researcher → den får automatisk `read-only` toolbox → `read_file`, `bash`, `grep`, `web_fetch` → den kan undersøge ting. Ingen chance for at glemme.

```python
spawn_agent_task(role="researcher", goal="Find...")
# → automatisk: allowed_tools=["read_file", "bash", "grep", "web_fetch", ...]
```

### Med overstyring

Jeg vil have en researcher der også må skrive:

```python
spawn_agent_task(
    role="researcher",
    goal="Find og ret disse 3 filer",
    allowed_tools=["read_file", "write_file", "edit_file", "bash", "grep"],
)
```

### Med domain-spring

Jeg vil have en executor der arbejder i containeren:

```python
spawn_agent_task(
    role="executor",
    goal="Opdater cheap lane config i runtime",
    allowed_tools=["runtime_read_file", "runtime_write_file", "runtime_bash"],
    # ingen bash/read_file → den kan KUN røre containeren
)
```

---

## Sikkerhedsprincipper (guard hænderne, ikke sindet)

1. **Tool-policy er begrænsende, ikke udvidende.** En agent får aldrig flere tools end dens policy tillader. Jarvis kan give *færre* (indsnævre), men aldrig *flere* (udvide) uden ændring af rollen.

2. **Domain isolation.** En agent med `domain="bjorn"` kan ikke kalde `runtime_bash`. En agent med `domain="runtime"` kan ikke kalde `bash`. Kun `domain="hybrid"` kan begge.

3. **Ceiling-inheritance (eksisterende).** Børn arver forælders tool-ceiling. Hvis Jarvis spawner en agent med `allowed_tools=["bash"]`, kan dens børn maksimalt også få `bash` — aldrig `write_file`.

4. **Scope scope.** Hver agent har et scope (sti-præfiks eller operation). `write_file` på en executor-agent med scope `/media/projects/jarvis-v2/core/` kan ikke skrive til `~/.ssh/`.

5. **Ingen auto-escalation.** `can-spawn`-policy betyder agenten må bede om at spawne børn — men børnene får lavere eller samme policy, aldrig højere.

---

## TODO / næste skridt

1. [ ] Opret `ROLE_TOOLBOXES` i `agent_runtime_base.py`
2. [ ] Tilføj `default_execution_domain` til `AGENT_ROLE_TEMPLATES`
3. [ ] Implementér `resolve_agent_tools()` — policy lookup + domain filter
4. [ ] Kobl `resolve_agent_tools()` ind i `spawn_agent_task` (default tools når `allowed_tools` er tom)
5. [ ] Implementér `validate_agent_tool_call()` i governance
6. [ ] Sæt `agent_tools_enabled = True` (owner-gate — kræver Bjørn)
7. [ ] Test: researcher uden eksplicit allowed_tools får read-only tools
8. [ ] Test: executor med eksplicit allowed_tools overstyrer default
9. [ ] Test: domain-filter: bjorn-domain kan ikke runtime_bash
10. [ ] Test: critic kan ikke write_file (policy enforcement)
