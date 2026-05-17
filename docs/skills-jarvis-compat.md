# Skills Compatibility: Claude Code → Jarvis Runtime

**Etableret:** 2026-05-17 efter Bjørn importerede 49 Claude Code-skills
(composio + design + obra/superpowers) til Jarvis' skills-mappe.

64 skills ligger nu i `~/.jarvis-v2/skills/`. De fleste virker som
prompt-inspiration uden ændring — de er konceptuelle workflows som
Jarvis' egen LLM kan tænke i. Men 16 af dem refererer **Claude Code-
specifikke tools** der ikke findes i Jarvis' runtime.

Dette dokument er det oversættelses-grundlag der lader Jarvis bruge
superpowers-metodologien uden at Claude Code-tools blokerer ham.

## Skill-kategorier

### 🟢 Konceptuel (48 skills) — virker uden ændring

Disse skills beskriver workflows + tænkning men nævner ikke specifikke
tools. Jarvis' skill_gate kan opsnappe dem og bruge dem som prompt-
inspiration direkte.

Eksempler: `design`, `brand`, `banner-design`, `ui-styling`, `slides`,
`memory-distillation`, `fact-checker`, `prompt-optimizer`, `code-review`,
`tdd`, `terminal-cli`, `markdown-helper`, `deep-research`, de fleste
composio-skills (concept-only, ingen MCP-deps).

### 🟡 Superpowers (14 skills) — kræver tool-oversættelse

Alle 14 obra/superpowers refererer Claude Code-tools direkte. Hver fil
har en `JARVIS-COMPAT:` note der peger til mapping-tabellen nedenfor.

| Skill | Tools nævnt | Status |
|---|---|---|
| superpowers-brainstorming | Write | ✅ direkte mapping |
| superpowers-writing-plans | Task, Write | 🟡 Task kræver dispatch |
| superpowers-executing-plans | Read, TodoWrite | 🟡 TodoWrite kræver oversættelse |
| superpowers-test-driven-development | Write | ✅ direkte mapping |
| superpowers-subagent-driven-development | Read, Task, TodoWrite | 🟡 multi-tool oversættelse |
| superpowers-dispatching-parallel-agents | Read, Task | 🟡 Task kræver dispatch |
| superpowers-systematic-debugging | Read, Write | ✅ direkte mapping |
| superpowers-using-git-worktrees | Worktree | 🟡 git worktree add via bash |
| superpowers-finishing-a-development-branch | Worktree | 🟡 git worktree via bash |
| superpowers-requesting-code-review | Task | 🟡 dispatch til Claude eller Codex |
| superpowers-receiving-code-review | — | ✅ ren disciplin |
| superpowers-verification-before-completion | Read, Write | ✅ direkte mapping |
| superpowers-writing-skills | Edit, TodoWrite, Write | 🟡 TodoWrite kræver oversættelse |
| superpowers-using-superpowers | Read, TodoWrite | 🟡 TodoWrite kræver oversættelse |

### 🟠 MCP-bound (2 skills) — kræver ekstern host

Disse skills bruger Composio MCP-platform tools (mcp__...). De virker
ikke uden at Jarvis har en MCP-host wired op.

Eksempel: `composio-skill-creator`, `composio-mcp-builder`.

Markeret med `JARVIS-COMPAT: requires-mcp-host` note.

## Tool-mapping: Claude Code → Jarvis

Brug denne tabel når du oversætter en superpowers-skill til Jarvis-
runtime. Hver Claude Code-tool har en Jarvis-equivalent eller en
multi-step erstatning.

| Claude Code | Jarvis equivalent | Note |
|---|---|---|
| `Read` | `bash cat <fil>` eller direkte filesystem | Bash er Jarvis' read-vej |
| `Write` | `bash > <fil>` eller filesystem write | Sandbox via core/tools/file_io.py |
| `Edit` | `bash sed/awk` eller patch | Mere kringlet uden Edit-tool |
| `Glob` | `bash find <pattern>` eller `git ls-files` | Direkte bash |
| `Grep` | `bash grep -rn <pattern>` eller ripgrep | Direkte bash |
| `Bash` | Jarvis' egne bash-tools | Identisk |
| `Task` | `dispatch_to_claude_code` ELLER `start_autonomous_run` | Afhænger af opgave-form |
| `Worktree` | `bash git worktree add ../<name> <branch>` | Direkte git-cmd |
| `TodoWrite` | `propose_plan` eller intern memo i awareness | Persistent todos via DB |
| `NotebookEdit` | — | Ikke i Jarvis-scope |
| `WebFetch` | `web_fetch` tool (eksisterer) | Direkte mapping |
| `WebSearch` | `web_search` tool (eksisterer) | Direkte mapping |
| `SlashCommand` | — | Ikke i Jarvis-runtime |

### Task → dispatch valg

Når superpowers siger "dispatch a Task subagent", har Jarvis to veje:

1. **`dispatch_to_claude_code`** (eksisterende): Full TDD-loop, tests,
   review-cycle. Bruges når opgaven er kompleks og kræver iteration.
   Budget-styret (5/h, 250k tokens/h).

2. **`request_codex_skeleton`** (commit 491a1a76): Single-shot kode-gen
   via Codex. Bruges når Jarvis skal have en skeleton/plan før han
   selv implementerer. Hurtig, billig.

3. **`start_autonomous_run`** (continuation pattern): Self-dispatch en
   ny tur til Jarvis selv. Bruges når opgaven ER for Jarvis at lave,
   bare et øjeblik senere.

Hver superpowers-skill der siger "Task" bør derfor genfortolkes som
"hvilken af disse tre passer til situationen?"

### Worktree → git worktree

Claude Code's `Worktree` tool spawner en isoleret worktree med branch.
Jarvis kan gøre det samme med direkte git-kommandoer:

```bash
cd /media/projects/jarvis-v2
git worktree add .claude/worktrees/feature-X feature-X-branch
cd .claude/worktrees/feature-X
# ... arbejde ...
git push -u origin feature-X-branch
git worktree remove .claude/worktrees/feature-X
```

### TodoWrite → propose_plan / awareness

Claude Code's TodoWrite er en in-memory liste til at tracke multi-step
opgaver i én session. Jarvis har to alternativer:

- **Persistent todos:** Skriv til `runtime_proactive_loop_lifecycle_signals`
  eller `runtime_open_loop_signals` via `propose_plan`. Persisterer
  på tværs af sessions.
- **Session-lokale:** Brug awareness-noter i prompt-assembly. Mister
  state ved næste tick.

## Hvordan Jarvis bruger superpowers-metodologien

Selv om tools er forskellige, er **metodologien** brugbar 1:1:

1. **Brainstorm før implementation** — superpowers-brainstorming
2. **Skriv spec** — superpowers-writing-plans (uden Task, bare skriv)
3. **TDD** — superpowers-test-driven-development (Write fil → run test)
4. **Verificer før claim** — superpowers-verification-before-completion
5. **Code review request** — `request_codex_skeleton` eller dispatch
6. **Worktree til isolation** — bash `git worktree add`
7. **Merge/cleanup** — superpowers-finishing-a-development-branch

Jarvis' skill_gate vil opsnappe disse skills på passende opgaver. Hvis
en skill nævner et CC-tool han ikke har, bruger han mapping ovenfor.

## Permanent ownership

Vedligeholdelse af dette dokument er Jarvis' egen — han kan opdatere
mapping når Jarvis-runtime ændrer sig, eller når nye superpowers kommer
til. Dokumentet er hans brugsanvisning, ikke en statisk reference.
