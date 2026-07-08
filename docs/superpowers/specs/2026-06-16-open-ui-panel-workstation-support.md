---
status: færdig
audited: 2026-07-08
ground_truth: superpowers artifact shipped (refs/symbols present in tree)
---
# open_ui_panel: Workstation-support (scope-parameter)

**Dato:** 2026-06-16  
**Status:** Spec (revideret)  
**Forfatter:** Jarvis

## Problem

`open_ui_panel(panel='file_tree', detail='sti/til/fil.py')` tvinger altid
file tree til serverens repo-root (`container`/`repo`). Når brugeren arbejder
med et lokalt workspace (`workstation`/`/sti/paa/egen/maskine`), kan Jarvis
ikke highlighte filer dér.

## Løsning

Tilføj et `scope`-parameter til `open_ui_panel`:

```
open_ui_panel(
  panel='file_tree',
  detail='sti/til/fil.py',
  scope='workstation'  // 'repo' (default) eller 'workstation'
)
```

### scope='repo' (default)

Nuværende adfærd uændret — detail er en repo-relativ sti, FileTree viser
serverens repo-root.

### scope='workstation'

detail er en sti **relativ til det valgte workstation workspace**. Hvis
brugerens workspace er `/home/bs/projects/myapp`, og detail er
`src/main.ts`, vises filen `/home/bs/projects/myapp/src/main.ts`.

## Backend-ændringer

### app_control_tool.py

- Udvid `open_ui_panel` tool-definition med valgfrit `scope`-felt:

  ```python
  "scope": {
    "type": "string",
    "enum": ["repo", "workstation"],
    "default": "repo"
  }
  ```

- `_exec_open_ui_panel` videregiver `scope` til `request_panel()`.
- Hvis `scope` udelades, default `'repo'` (backward compatible).

### ui_panel_store.py

- `request_panel()` accepterer og gemmer `scope`-felt i request-objektet.
- Validér at scope er enten `'repo'` eller `'workstation'`. Default `'repo'`.
- `list_pending()` returnerer `scope` som del af payload (findes allerede i
  `value_json` via `runtime_state_kv`).

## Frontend-ændringer

### fileTreeHighlight.ts (pub/sub)

Opdater typerne:

```typescript
export interface HighlightEvent {
  path: string
  scope: 'repo' | 'workstation'
}

type Listener = (event: HighlightEvent) => void

export function emitHighlight(path: string, scope: 'repo' | 'workstation' = 'repo'): void {
  for (const l of listeners) {
    try { l({ path, scope }) } catch { /* isoler fejl pr. lytter */ }
  }
}
```

`onHighlight` returnerer stadig en unsubscribe-funktion; signaturen ændres
til at modtage `HighlightEvent`.

### UiPanelWatcher.tsx

- Ved `panel='file_tree'`: parse `scope` fra `req.scope`.
- Kald `emitHighlight(req.detail, req.scope || 'repo')`.
- Ingen ændring af `_looksLikeFilePath` — den bruges kun til preview/right,
  ikke file_tree.

### CodeView.tsx

Opdater `onHighlight`-listeneren (linje ~98):

```typescript
useEffect(() => onHighlight((evt) => {
  if (evt.scope === 'workstation') {
    setKind('workstation')
    // Bevar den allerede valgte wsPath — brug den som root.
    // Hvis wsPath er tom: kald pickFolder() via bridge.
    if (!wsPath) {
      pickFolder().then((p) => { if (p) setWsPath(p); setFilesOpen(true) })
    } else {
      setFilesOpen(true)
    }
  } else {
    // scope='repo' (default) — nuværende adfærd
    setKind('container')
    if (isOwner) setRoot('repo')
    setFilesOpen(true)
  }
  setHighlightPath('')
  requestAnimationFrame(() => setHighlightPath(evt.path))
}), [isOwner, wsPath])
```

- Når `scope='workstation'` og `wsPath` er tom: Kald `pickFolder()`-bridge
  (Electron dialog) for at bede brugeren vælge en mappe. Når mappen er valgt,
  sæt `wsPath` og kør highlight.
- Hvis `pickFolder` ikke er tilgængelig (web/non-Electron): vis en
  fejlmeddelelse eller ignorér.

### FileTree.tsx

- **Ingen ændring nødvendig.** `FileTree` understøtter allerede
  `kind='workstation'` + `root` = den valgte sti. Den nuværende
  `highlightPath`-logik (auto-ekspander, scroll-into-view) fungerer identisk
  uanset scope.

## Edge cases

| # | Situation | Forventet adfærd |
|---|-----------|------------------|
| 1 | `scope` udeladt | Default `'repo'` — backward compatible |
| 2 | `scope='workstation'` med valgt wsPath | Highlight i eksisterende workspace |
| 3 | `scope='workstation'` uden valgt wsPath | Electron: `pickFolder()` dialog. Web: ignorér eller fejlbesked |
| 4 | `scope='workstation'` men detail starter med `/` | Stien er absolut — brug den som fuld sti (skip wsPath) |
| 5 | Brugeren i chat-mode | `surfaceRef.current?.('code')` skifter til code mode |
| 6 | wsPath ændret mellem highlights | Hvert highlight bruger aktuelle wsPath |
| 7 | `pickFolder` afbrudt (dialog lukket) | Highlight springes over, ingen crash |
| 8 | detail er tom | Ingen highlight — `fileTree` tvinger stadig code mode åben |
| 9 | detail matcher ikke nogen fil | FileTree viser mappen uden highlight — ingen crash |
| 10 | scope='workstation' i non-Electron (web) | `pickFolder` returnerer null → highlight springes over |

## Backward compatibility

- `scope` er **valgfrit** med default `'repo'`.
- Alle eksisterende `open_ui_panel`-kald fortsætter uændret.
- `fileTreeHighlight`'s nye `emitHighlight(path, scope)` har scope default
  `'repo'` — eksisterende kald (uden scope) fungerer stadig.

## Tests

### Backend (Python, pytest)

Tilføj til `tests/test_app_control_tool.py`:

1. `test_open_ui_panel_with_scope_repo()` — kald med `scope='repo'`,
   verificer at `scope` er med i payload.
2. `test_open_ui_panel_with_scope_workstation()` — kald med
   `scope='workstation'`, verificer payload.
3. `test_open_ui_panel_default_scope()` — kald uden `scope`, verificer at
   default er `'repo'`.
4. `test_open_ui_panel_invalid_scope()` — kald med ugyldig scope,
   verificer error-status.

Tilføj til `tests/test_ui_panel_store.py`:

5. `test_request_panel_with_scope()` — verificer at scope gemmes og
   returneres korrekt i `list_pending()`.

### Frontend (Jest + React Testing Library)

Tilføj til `apps/jarvis-desk/src/components/UiPanelWatcher.test.tsx`:

6. `test_file_tree_with_scope_workstation()` — mock pending request med
   `scope='workstation'`, verificer at `emitHighlight` kaldes med korrekt
   scope.
7. `test_file_tree_with_scope_repo()` — mock pending request med
   `scope='repo'`, verificer `emitHighlight` scope.

Tilføj til `apps/jarvis-desk/src/components/panel/FileTree.test.tsx`:

8. `test_highlight_path_workstation()` — sæt `kind='workstation'`,
   `root='/home/user/project'`, `highlightPath='src/main.ts'`, verificer at
   TreeNode med `path='src/main.ts'` har CSS-klassen `highlight`.

### Manuelle tests

9. **scope='repo' (default)**: `open_ui_panel(panel='file_tree',
   detail='core/tools/app_control_tool.py')` → highlight i serverens repo.
10. **scope='workstation' med valgt workspace**: `open_ui_panel(panel='file_tree',
    detail='src/main.rs', scope='workstation')` → highlight i lokale workspace.
11. **scope='workstation' uden valgt workspace**: → `pickFolder()`-dialog vises.
12. **scope='workstation' med absolut sti**: `detail='/etc/hosts'` → vis filen
    direkte (ignorér wsPath).

## Implementeringsrækkefølge

1. Opdater `fileTreeHighlight.ts` (typer + emit/on signatures)
2. Opdater `app_control_tool.py` (tool-definition + scope-parameter)
3. Opdater `ui_panel_store.py` (scope i request_panel + validering)
4. Opdater `UiPanelWatcher.tsx` (læs scope, send med emitHighlight)
5. Opdater `CodeView.tsx` (onHighlight: scope-gren + pickFolder-fallback)
6. Skriv backend-tests (`test_app_control_tool.py`)
7. Skriv frontend-tests (`UiPanelWatcher.test.tsx`, `FileTree.test.tsx`)
8. Udfør manuelle tests
