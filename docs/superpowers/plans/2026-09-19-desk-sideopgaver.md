# Desk Flaggede Sideopgaver Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Vis og afslut Jarvis' vedvarende flaggede sideopgaver over alle Desk-chats.

**Architecture:** Udvid den eksisterende `side_tasks`-service med terminal status `completed` og et åbent feed. Eksponér feed og statusændring via owner-beskyttede cowork-ruter. En selvstændig Desk-komponent henter og viser feedet under ChatView-headeren.

**Tech Stack:** Python 3.11, FastAPI, React 19, TypeScript, Vitest, pytest, CSS.

**Spec:** `docs/superpowers/specs/2026-09-19-desk-sideopgaver-design.md`

## Global Constraints

- `core.services.side_tasks` forbliver eneste sandhedskilde.
- `pending` og `activated` vises; `completed` og `dismissed` skjules.
- Kun owner må læse og ændre det globale feed via API'et.
- `app.css` ændres ikke, fordi den er over 2000 linjer.
- Ændr ikke `simple_tools.py` eller `simple_tools_definitions.py`, da begge er over 2000 linjer og Boy Scout-reglen gælder.

---

### Task 1: Statusforløb og Jarvis-værktøj

**Files:** `core/services/side_tasks.py`, `tests/test_side_tasks.py`

**Interfaces:** `list_open() -> list[dict]` viser `pending|activated`; `resolve(side_task_id, decision='completed'|'dismissed'|'activated')` styrer status. `_exec_dismiss_side_task` tager valgfri `decision`, med `dismissed` som standard.

- [x] Skriv tests for `list_open()` med `pending`, `activated`, `completed`, `dismissed`; terminal genåbning; og `_exec_dismiss_side_task` med både gammel standard og `completed`.
- [x] Kør `pytest tests/test_side_tasks.py -q` og se forventet fejl i manglende adfærd.
- [x] Indfør `completed`, `list_open()` og opdater værktøjsbeskrivelsen i `side_tasks.py`.
- [x] Kør samme test og den eksisterende `tests/test_turn_side_text_gc_surfaces.py` grønt.

### Task 2: Owner-beskyttet API

**Files:** `apps/api/jarvis_api/routes/cowork.py`, `tests/test_cowork_side_task_routes.py`

**Interfaces:** `GET /cowork/side-tasks` returnerer `{side_tasks, count}`; `POST /cowork/side-tasks/{id}/status` accepterer `{status: completed|dismissed}`.

- [x] Skriv route-tests for owner-liste, owner-status, member-403 og ugyldig status.
- [x] Kør `pytest tests/test_cowork_side_task_routes.py -q` og se forventet fejl.
- [x] Tilføj ruter med `_role_owner()` og `asyncio.to_thread`.
- [x] Kør route-tests grønt.

### Task 3: Desk API og chatliste

**Files:** `apps/jarvis-desk/src/lib/sideTasksApi.ts`, `apps/jarvis-desk/src/lib/sideTasksApi.test.ts`, `apps/jarvis-desk/src/components/chat/SideTasksBar.tsx`, `apps/jarvis-desk/src/components/chat/SideTasksBar.test.tsx`, `apps/jarvis-desk/src/styles/side-tasks.css`, `apps/jarvis-desk/src/views/ChatView.tsx`, `apps/jarvis-desk/src/views/ChatView.test.tsx`

**Interfaces:** `getSideTasks(config)` returnerer `SideTask[]`; `setSideTaskStatus(config,id,status)` accepterer `completed|dismissed`; `<SideTasksBar config={config} />` viser feedet og håndterer mutationer.

- [x] Skriv failing API-tests for GET og status-POST samt komponenttests for titel, beskrivelse, detaljer, Færdig, Fjern og fejl.
- [x] Kør målrettet Vitest og se forventet fejl. *(Afvigelse 19/9, Claude: desk-testene blev skrevet lige EFTER komponenten, så den røde fase blev ikke set. De dækker samme adfærd som planen kræver.)*
- [x] Implementér API, polling-komponent og scoped CSS; placér komponenten efter ChatView-headeren i både tom og aktiv chat.
- [x] Kør målrettet Vitest grønt; byg renderer.

### Task 4: Samlet kontrol

**Files:** Ovenstående.

- [x] Kør `pytest tests/test_side_tasks.py tests/test_cowork_side_task_routes.py tests/test_turn_side_text_gc_surfaces.py -q`.
- [x] Kør `npm test` og `npm run build:renderer` i `apps/jarvis-desk`.
- [x] Inspicér chatlisten visuelt ved tom og aktiv chat samt smalt vindue; kontrollér `git diff --check`. *(19/9, Claude: set i en demo-side med lokale testdata under en chatview-header, foldet ud og ved 420 px — ingen overløb, knapperne inden for, lange titler afkortet med tooltip. Placeringen under headeren i tom OG aktiv chat er holdt af ChatView-testene, ikke set i det kørende vindue.)*
- [x] Commit kun disse filer med `scripts/commit_with_attribution.py`.
