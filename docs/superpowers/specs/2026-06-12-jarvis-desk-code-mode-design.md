---
status: færdig
audited: 2026-07-08
ground_truth: superpowers artifact shipped (refs/symbols present in tree)
---
# jarvis-desk Code mode — Design (v1)

**Status:** spec
**Author:** Claude (med Bjørn)
**Created:** 2026-06-12
**Forudsætning:** Chat mode er færdig og deployet (v2-stream, tool_scoping, preview-panel,
context-ring, systray). Code er pt. en tom stub-view (`CodeView`).

## Formål

Code mode er jarvis-desks IDE-agtige flade efter **Claude Desktop**-mønstret: du og Jarvis
arbejder i en kodebase sammen. Jarvis læser/skriver filer, kører kommandoer, og du ser
ændringer som diffs — alt drevet af Jarvis' egen agentic-loop (samme `/chat/stream/v2` som
chat). Forskellen fra chat er: andre **tools** (tool_scope="code") og en **kode-flade** i
højre panel.

## Arkitektur

Code mode genbruger HELE chat-infrastrukturen (v2-stream, sessioner, composer, tool_use-
blokke, liveness). Det nye er en `tool_scope="code"` + workspace-binding + kode-UI.

### Rolle- + filsystem-matrix

| Rolle | Filsystem | Tools |
|-------|-----------|-------|
| **Owner (Bjørn)** | container **+** workstation | read_file/write_file/edit_file, bash, search/find_files, operator_* (read/write/bash/glob/grep/list_dir), `dispatch_to_claude_code` (hand-off-knap) |
| **Member/guest** | kun egen workstation | operator_read_file/write_file/bash/glob/grep/list_dir (sandboxet til deres maskine). INGEN container-adgang, ingen dispatch. |

Håndhæves i `core/tools/tool_scoping.py` via samme mønster som chat-låsen: `tool_scope="code"`
→ allowlist, modificeret af rolle. Owner-only-tools (dispatch m.fl.) strippes for member/guest
som i dag.

### Sessioner

En session er bare en samtale i DB'en (chat_sessions) — **server-gemt, ikke lokal** — som alle
andre. Mode (chat/cowork/code) bestemmer kun tools + UI, ikke lagring. En code-session får
ekstra metadata:

```
workspace = { kind: "container" | "workstation", root: "<absolut sti>" }
```

gemt server-side (ny nullable kolonne på chat_sessions, fx `workspace_kind` + `workspace_root`).
Plumbes ind i requesten (som `mode`/`tool_scope` i dag) så Jarvis' fil-tools ved hvilken rod de
arbejder i. Sessioner deles på tværs af modes — du kan have chat- og code-sessioner side om side.

## Layout (genbrug shell'en)

De tre eksisterende zoner får kode-indhold når mode = code:

- **Venstre panel → sessioner** (UÆNDRET, alle modes — Claude Desktop-mønster). Code-sessioner
  får et lille mode-ikon i rækken så de kan skelnes fra chat.
- **Midten → agentic-stream** (præcis som chat: bobler + tool-kort + liveness). Permissions-
  dropdown'en i composeren **vises** her (skjult i chat) — værktøjs-godkendelse er relevant.
- **Højre preview-panel → kode-fladen:** workspace-vælger øverst + **fil-træ** + **fil-visning +
  diffs**. Genbruger preview-panelet vi byggede, udvidet med fil-træ og diff-rendering.

Klik en fil i træet → åbnes i panelet. Jarvis' read/write/edit-tool_use-blokke (Phase 2)
highlighter automatisk den berørte fil; en write/edit viser en diff i panelet.

**Hand-off-knap** (kun owner): en lille knap der dispatcher den aktuelle opgave til
`dispatch_to_claude_code` (claude -p i isoleret worktree) for store/isolerede opgaver.

## Backend

- **`tool_scope="code"`** i `tool_scoping.py` — rolle-matrix ovenfor. Plumbes via `mode="code"`
  i ChatStreamRequest → start_visible_run(tool_scope) (eksisterende vej).
- **Workspace-binding:** chat_sessions får `workspace_kind` + `workspace_root` (nullable). Sættes
  ved session-oprettelse i code mode / via en "skift workspace"-handling. Sendes i requesten så
  fil-tools' rod-jail matcher.
- **Fil-træ-endpoint:** `GET /chat/tree?kind=…&root=…&path=…` → mappe-listing (mapper/filer).
  - **Container:** path-jailed til whitelistede rødder (genbruger `/chat/file`-jail'en:
    docs/workspace/core/apps/scripts under repo-roden).
  - **Workstation:** via operator-bridgen (`operator_list_dir`) — samme vej som JarvisX' operator-
    tools, scopet til brugerens tilladte rødder.
- **Fil-visning + diffs:** container via `/chat/file`; workstation via `operator_read_file`. Diffs
  renderes klient-side ud fra write/edit-tool_use-blokkenes input (gammelt→nyt) eller ved at
  re-fetche filen efter ændring.

## Out of scope (v1) → v2 deferred

Bevidst UDE af v1; gemt i memory (`project_jarvis_desk_code_mode_v2`) så vi vender tilbage:

- **Separat terminal-rude** (v1: bash-output som tool-kort inline i streamen)
- **Multi-fil-diff-review** (v1: enkelt-fil diff i panelet)
- **Cowork mode** (det andet store mode — egen spec→plan→byg-cyklus)
- **Git-graf / branch-UI**
- **Inline-editor** (v1: du redigerer IKKE selv — Jarvis koder, du ser/godkender via diffs)

## Test

TDD:
- `tool_scoping`: code-scope rolle-matrix (owner får container+workstation+dispatch; member kun
  workstation-operator; ingen action-leak til chat-niveau).
- Workspace-binding: persist/load på chat_sessions; request-plumbing → korrekt tool-rod.
- `/chat/tree`: container path-jail (afvis udenfor rødder) + workstation bridge-rute.
- Frontend: fil-træ-render + ekspander/kollaps, workspace-vælger, diff-visning fra tool_use-blok,
  permissions vist i code-composer (skjult i chat), mode-ikon på code-sessioner i sidebaren.

## Rollback
Per-del git revert. tool_scope="code" er additiv; workspace-kolonner er nullable; /chat/tree er nyt
endpoint; Code-view erstatter kun stub'en.
