---
status: færdig
audited: 2026-07-08
ground_truth: superpowers artifact shipped (refs/symbols present in tree)
---
# App-Self-Control Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Lade Jarvis *foreslå* (aldrig selv udføre) et chat→code mode-skift eller et ask→trust permission-skift inde i jarvis-desk; ved brugerens godkendelse skifter appen tilstand og gen-sender den oprindelige besked, så Jarvis fortsætter sømløst.

**Architecture:** Backend-tool `request_app_action(action, reason)` returnerer en `app_action`-markør i sit resultat. `visible_runs` opdager markøren og emitterer et inline `app_action_request` SSE system-event (med `original_message`). jarvis-desk renderer et godkendelseskort; godkendelse → `setSurface('code')` og/eller `setPermission('trust')` + auto-continue (gen-send den oprindelige besked med code-mode-opts). Jarvis kan ALDRIG skifte selv — kun brugerens klik muterer state; backendens permission_engine håndhæver stadig hvad brugeren faktisk må.

**Tech Stack:** Python 3.11 (conda env `ai`, kør `/opt/conda/envs/ai/bin/python`), pytest. Frontend: React + TypeScript (Electron), vitest + @testing-library/react. Backend-tests: `/opt/conda/envs/ai/bin/python -m pytest -p no:cacheprovider`. Frontend i `apps/jarvis-desk`: `npx vitest run` + `npx tsc -b`.

**Spec:** `docs/superpowers/specs/2026-06-15-app-self-control-design.md`

---

## File Structure

**Backend (working dir `/media/projects/jarvis-v2`):**
- Create `core/tools/app_control_tool.py` — tool-def + handler + ren helper `build_app_action_event`. Eneansvar: definér `request_app_action` og oversæt en tool-resultat-markør til en event-payload.
- Modify `core/tools/simple_tools.py` — registrér tool (import + `TOOL_DEFINITIONS` + `_TOOL_HANDLERS`).
- Modify `core/services/visible_runs.py` — emit `app_action_request` SSE efter en tool-eksekvering der bærer markøren.
- Modify `core/services/visible_runs_sse_v2.py` — tilføj `"app_action_request"` til `_KNOWN_SYSTEM_EVENT_KINDS`.
- Create `tests/test_app_control_tool.py`.

**Frontend (working dir `/media/projects/jarvis-v2/apps/jarvis-desk`):**
- Create `src/lib/composerPrefs.ts` — delte localStorage-nøgler + `readModelPrefs()`. Eneansvar: én kilde til composer-præferencer (afløser duplikerede consts).
- Create `src/contexts/PermissionContext.tsx` + `src/hooks/usePermission.ts` — løft permission-state ud af Composer så den kan sættes udefra.
- Create `src/components/rich/AppActionCard.tsx` — godkendelseskortet (model på `ApprovalCard`).
- Create `src/lib/appAction.ts` — ren `resolveAppAction()` (testbar approve-logik).
- Modify `src/contexts/StreamContext.tsx` — `pendingAppAction` + `autoContinue`-stash + onEvent-håndtering.
- Modify `src/components/shell/Composer.tsx` — brug `usePermission()` + `composerPrefs`-nøgler.
- Modify `src/App.tsx` — `PermissionProvider`-wrap + `AppActionHost` i Shell.
- Modify `src/views/CodeView.tsx` — auto-continue-effekt.
- Create tests: `src/lib/composerPrefs.test.ts`, `src/contexts/PermissionContext.test.tsx`, `src/components/rich/AppActionCard.test.tsx`, `src/lib/appAction.test.ts`, plus tilføjelser i `src/contexts/StreamContext.test.tsx`.

---

## Task 1: Backend tool `request_app_action` + event-helper

**Files:**
- Create: `core/tools/app_control_tool.py`
- Test: `tests/test_app_control_tool.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_app_control_tool.py`:

```python
"""Tests for app_control_tool (spec 2026-06-15)."""
from __future__ import annotations

from core.tools.app_control_tool import (
    APP_CONTROL_TOOL_DEFINITIONS,
    VALID_APP_ACTIONS,
    _exec_request_app_action,
    build_app_action_event,
)


def test_valid_action_returns_marker() -> None:
    r = _exec_request_app_action({"action": "switch_to_code_mode", "reason": "kræver filer"})
    assert r["status"] == "ok"
    assert r["app_action"] == {"action": "switch_to_code_mode", "reason": "kræver filer"}
    assert r["text"]  # menneskelig note som modellen ser


def test_request_full_access_valid() -> None:
    r = _exec_request_app_action({"action": "request_full_access"})
    assert r["status"] == "ok"
    assert r["app_action"]["action"] == "request_full_access"


def test_unknown_action_errors() -> None:
    r = _exec_request_app_action({"action": "delete_everything"})
    assert r["status"] == "error"
    assert "ukendt action" in r["error"]


def test_build_event_from_marker() -> None:
    result = {"status": "ok", "app_action": {"action": "switch_to_code_mode", "reason": "x"}}
    ev = build_app_action_event(result, user_message="ret bug", session_id="s1")
    assert ev == {
        "type": "app_action_request",
        "action": "switch_to_code_mode",
        "reason": "x",
        "original_message": "ret bug",
        "session_id": "s1",
    }


def test_build_event_none_without_marker() -> None:
    assert build_app_action_event({"status": "ok"}, user_message="x", session_id="s") is None
    assert build_app_action_event(None, user_message="x", session_id="s") is None


def test_build_event_rejects_bad_action() -> None:
    result = {"app_action": {"action": "nope"}}
    assert build_app_action_event(result, user_message="x", session_id="s") is None


def test_tool_definition_shape() -> None:
    d = APP_CONTROL_TOOL_DEFINITIONS[0]
    assert d["function"]["name"] == "request_app_action"
    assert set(d["function"]["parameters"]["properties"]) == {"action", "reason"}
    assert d["function"]["parameters"]["properties"]["action"]["enum"] == list(VALID_APP_ACTIONS)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_app_control_tool.py -q -p no:cacheprovider`
Expected: FAIL — `ModuleNotFoundError: No module named 'core.tools.app_control_tool'`

- [ ] **Step 3: Write the implementation**

Create `core/tools/app_control_tool.py`:

```python
"""request_app_action tool (spec 2026-06-15) — Jarvis foreslår mode/permission-skift.

Jarvis kan IKKE skifte appens tilstand selv. Dette tool *anmoder* kun: handleren
returnerer en `app_action`-markør i sit resultat, og visible_runs emitterer et
inline `app_action_request` system-event som jarvis-desk renderer som et
godkendelseskort. Kun brugerens klik skifter mode/permission. Backendens
permission_engine håndhæver stadig hvad brugeren faktisk må efter skiftet.
"""
from __future__ import annotations

from typing import Any

# De eneste gyldige app-actions (spec: "De to konkrete handlinger").
VALID_APP_ACTIONS: tuple[str, ...] = ("switch_to_code_mode", "request_full_access")

_ACTION_NOTE: dict[str, str] = {
    "switch_to_code_mode": (
        "Jeg har bedt appen om at skifte til code mode. Godkend kortet i appen, "
        "så fortsætter jeg opgaven dér."
    ),
    "request_full_access": (
        "Jeg har bedt om fuld adgang (trust) til denne opgave. Godkend kortet i "
        "appen, så fortsætter jeg."
    ),
}


def _exec_request_app_action(args: dict[str, Any]) -> dict[str, Any]:
    action = str(args.get("action") or "").strip()
    if action not in VALID_APP_ACTIONS:
        return {
            "status": "error",
            "error": f"ukendt action '{action}' (gyldige: {', '.join(VALID_APP_ACTIONS)})",
        }
    reason = str(args.get("reason") or "").strip()
    return {
        "status": "ok",
        "text": _ACTION_NOTE[action],
        "app_action": {"action": action, "reason": reason},
        "note": "Afventer brugerens godkendelse i appen.",
    }


def build_app_action_event(
    result: dict[str, Any] | None,
    *,
    user_message: str,
    session_id: str,
) -> dict[str, Any] | None:
    """Ren helper: hvis et tool-resultat bærer en app_action-markør, byg payloaden
    til et `app_action_request` system-event. Returnér None hvis ingen gyldig markør.

    visible_runs kalder denne efter en tool-eksekvering og yield'er et SSE-event
    med returværdien. Holdes ren (ingen sideeffekt) så den er unit-testbar.
    """
    if not isinstance(result, dict):
        return None
    marker = result.get("app_action")
    if not isinstance(marker, dict):
        return None
    action = str(marker.get("action") or "")
    if action not in VALID_APP_ACTIONS:
        return None
    return {
        "type": "app_action_request",
        "action": action,
        "reason": str(marker.get("reason") or ""),
        "original_message": str(user_message or ""),
        "session_id": str(session_id or ""),
    }


APP_CONTROL_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "request_app_action",
            "description": (
                "Bed jarvis-desk-appen om at skifte tilstand når den nuværende mode "
                "eller permission ikke rækker til opgaven. To handlinger: "
                "'switch_to_code_mode' (fra chat til code mode — giver terminal + "
                "fil-adgang) og 'request_full_access' (fra 'spørg' til 'fuld adgang' "
                "i code mode). Du skifter ALDRIG selv: tool'et viser brugeren et "
                "godkendelseskort, og kun deres klik skifter. Når de godkender, "
                "gen-sendes beskeden automatisk så du fortsætter. Virker kun i "
                "desk-appen (ikke web/Discord). Kald det når du selv mærker at "
                "opgaven kræver mere — og afslut din tur med en kort note om at du "
                "afventer godkendelse."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": list(VALID_APP_ACTIONS),
                        "description": "Hvilket skift du anmoder om",
                    },
                    "reason": {
                        "type": "string",
                        "description": "Kort forklaring vist på kortet (fx 'kræver terminal og filer')",
                    },
                },
                "required": ["action"],
            },
        },
    },
]

APP_CONTROL_TOOL_HANDLERS: dict[str, Any] = {
    "request_app_action": _exec_request_app_action,
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_app_control_tool.py -q -p no:cacheprovider`
Expected: PASS (7 passed)

- [ ] **Step 5: Commit**

```bash
git add core/tools/app_control_tool.py tests/test_app_control_tool.py
git commit -m "feat(app-control): request_app_action tool + event-helper (spec 2026-06-15)"
```

---

## Task 2: Registrér tool + wire SSE-emission i visible_runs

**Files:**
- Modify: `core/tools/simple_tools.py` (import ~line 186-189; `TOOL_DEFINITIONS` ~line 3400; `_TOOL_HANDLERS` ~line 8448)
- Modify: `core/services/visible_runs.py` (efter line 1452)
- Modify: `core/services/visible_runs_sse_v2.py` (`_KNOWN_SYSTEM_EVENT_KINDS`, line 49-55)
- Test: `tests/test_app_control_tool.py` (tilføj registrerings-test)

- [ ] **Step 1: Write the failing test**

Tilføj nederst i `tests/test_app_control_tool.py`:

```python
def test_tool_registered_in_simple_tools() -> None:
    from core.tools.simple_tools import _TOOL_HANDLERS, TOOL_DEFINITIONS
    assert "request_app_action" in _TOOL_HANDLERS
    assert any(
        d.get("function", {}).get("name") == "request_app_action" for d in TOOL_DEFINITIONS
    )


def test_app_action_request_is_known_system_kind() -> None:
    from core.services.visible_runs_sse_v2 import _KNOWN_SYSTEM_EVENT_KINDS
    assert "app_action_request" in _KNOWN_SYSTEM_EVENT_KINDS
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_app_control_tool.py::test_tool_registered_in_simple_tools tests/test_app_control_tool.py::test_app_action_request_is_known_system_kind -q -p no:cacheprovider`
Expected: FAIL — `request_app_action` ikke i registret; `app_action_request` ikke i known kinds.

- [ ] **Step 3a: Registrér tool i simple_tools.py**

Tilføj import efter `UI_PANEL_TOOL_HANDLERS,`-importen (omkring line 186-189):

```python
from core.tools.app_control_tool import (
    APP_CONTROL_TOOL_DEFINITIONS,
    APP_CONTROL_TOOL_HANDLERS,
)
```

Tilføj i `TOOL_DEFINITIONS`-listen lige efter linjen `*UI_PANEL_TOOL_DEFINITIONS,` (~line 3400):

```python
    *APP_CONTROL_TOOL_DEFINITIONS,
```

Tilføj i `_TOOL_HANDLERS`-dict'en lige efter linjen `**UI_PANEL_TOOL_HANDLERS,` (~line 8448):

```python
    **APP_CONTROL_TOOL_HANDLERS,
```

- [ ] **Step 3b: Tilføj known system-kind i visible_runs_sse_v2.py**

I `core/services/visible_runs_sse_v2.py`, find `_KNOWN_SYSTEM_EVENT_KINDS` (line 49) og tilføj `"app_action_request",` til settet, så det bliver:

```python
_KNOWN_SYSTEM_EVENT_KINDS = {
    "working_step",
    "capability",
    "approval_request",
    "steer_received",
    "turn_changelog",
    "app_action_request",
}
```

- [ ] **Step 3c: Emit i visible_runs.py**

I `core/services/visible_runs.py`, find blokken der emitterer et normalt tool-resultat (linje 1440-1452, slutter med `working_step` `status: "done"`). Indsæt UMIDDELBART efter `working_step`-yield'et på line 1452 (stadig inde i `for _idx, sr in enumerate(simple_results):`-loopet, samme indrykning som de to `yield _sse(...)` ovenfor):

```python
                    # App-self-control (spec 2026-06-15): hvis tool'et bad om et
                    # app-skift (request_app_action), emit et inline system-event
                    # som desk viser som godkendelseskort. run.user_message giver
                    # den besked der skal gen-sendes efter godkendelse.
                    try:
                        from core.tools.app_control_tool import build_app_action_event
                        _app_ev = build_app_action_event(
                            sr.get("result"),
                            user_message=run.user_message,
                            session_id=run.session_id or "",
                        )
                        if _app_ev:
                            yield _sse("app_action_request", _app_ev)
                    except Exception:
                        pass
```

- [ ] **Step 4: Run tests + compile to verify it passes**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_app_control_tool.py -q -p no:cacheprovider`
Expected: PASS (9 passed)

Run: `/opt/conda/envs/ai/bin/python -m compileall core/services/visible_runs.py core/services/visible_runs_sse_v2.py core/tools/simple_tools.py -q`
Expected: ingen output (kompilerer rent)

- [ ] **Step 5: Commit**

```bash
git add core/tools/simple_tools.py core/services/visible_runs.py core/services/visible_runs_sse_v2.py tests/test_app_control_tool.py
git commit -m "feat(app-control): registrér tool + emit app_action_request SSE i visible_runs"
```

---

## Task 3: Delte composer-præferencer (`composerPrefs.ts`)

**Files:**
- Create: `apps/jarvis-desk/src/lib/composerPrefs.ts`
- Test: `apps/jarvis-desk/src/lib/composerPrefs.test.ts`

Working dir for alle frontend-steps: `/media/projects/jarvis-v2/apps/jarvis-desk`

- [ ] **Step 1: Write the failing test**

Create `src/lib/composerPrefs.test.ts`:

```ts
import { describe, it, expect, beforeEach } from 'vitest'
import { PERM_KEY, MODEL_KEY, PROV_KEY, readModelPrefs } from './composerPrefs'

describe('composerPrefs', () => {
  beforeEach(() => localStorage.clear())

  it('exposes stable storage keys', () => {
    expect(PERM_KEY).toBe('jarvis-desk:permission')
    expect(MODEL_KEY).toBe('jarvis-desk:model')
    expect(PROV_KEY).toBe('jarvis-desk:provChoice')
  })

  it('defaults model to empty and provider to deepseek', () => {
    expect(readModelPrefs()).toEqual({ model: '', providerChoice: 'deepseek' })
  })

  it('reads stored values', () => {
    localStorage.setItem(MODEL_KEY, 'pro')
    localStorage.setItem(PROV_KEY, 'glm')
    expect(readModelPrefs()).toEqual({ model: 'pro', providerChoice: 'glm' })
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run src/lib/composerPrefs.test.ts`
Expected: FAIL — cannot find module `./composerPrefs`

- [ ] **Step 3: Write the implementation**

Create `src/lib/composerPrefs.ts`:

```ts
/** Delte localStorage-nøgler + læser for composer-præferencer.
 *  Én kilde, så Composer og auto-continue (CodeView) ikke duplikerer dem. */
export const PERM_KEY = 'jarvis-desk:permission'
export const PROV_KEY = 'jarvis-desk:provChoice'
export const MODEL_KEY = 'jarvis-desk:model'

export function readModelPrefs(): { model: string; providerChoice: string } {
  let model = ''
  let providerChoice = 'deepseek'
  try { model = localStorage.getItem(MODEL_KEY) || '' } catch { /* ignore */ }
  try { providerChoice = localStorage.getItem(PROV_KEY) || 'deepseek' } catch { /* ignore */ }
  return { model, providerChoice }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npx vitest run src/lib/composerPrefs.test.ts`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add src/lib/composerPrefs.ts src/lib/composerPrefs.test.ts
git commit -m "feat(desk): delte composerPrefs (localStorage-nøgler + readModelPrefs)"
```

---

## Task 4: `PermissionContext` + `usePermission`

**Files:**
- Create: `apps/jarvis-desk/src/contexts/PermissionContext.tsx`
- Create: `apps/jarvis-desk/src/hooks/usePermission.ts`
- Test: `apps/jarvis-desk/src/contexts/PermissionContext.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `src/contexts/PermissionContext.test.tsx`:

```tsx
import { describe, it, expect, beforeEach } from 'vitest'
import type { ReactNode } from 'react'
import { renderHook, act } from '@testing-library/react'
import { PermissionProvider } from './PermissionContext'
import { usePermission } from '../hooks/usePermission'

const wrapper = ({ children }: { children: ReactNode }) => (
  <PermissionProvider>{children}</PermissionProvider>
)

describe('PermissionContext', () => {
  beforeEach(() => localStorage.clear())

  it('defaults to ask', () => {
    const { result } = renderHook(() => usePermission(), { wrapper })
    expect(result.current.permission).toBe('ask')
  })

  it('setPermission updates and persists', () => {
    const { result } = renderHook(() => usePermission(), { wrapper })
    act(() => result.current.setPermission('trust'))
    expect(result.current.permission).toBe('trust')
    expect(localStorage.getItem('jarvis-desk:permission')).toBe('trust')
  })

  it('initialises from localStorage', () => {
    localStorage.setItem('jarvis-desk:permission', 'trust')
    const { result } = renderHook(() => usePermission(), { wrapper })
    expect(result.current.permission).toBe('trust')
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run src/contexts/PermissionContext.test.tsx`
Expected: FAIL — cannot find module `./PermissionContext`

- [ ] **Step 3: Write the implementation**

Create `src/contexts/PermissionContext.tsx`:

```tsx
import { createContext, useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import { PERM_KEY } from '../lib/composerPrefs'

export type Permission = 'ask' | 'trust'

export interface PermissionContextValue {
  permission: Permission
  setPermission: (p: Permission) => void
}

export const PermissionContext = createContext<PermissionContextValue | null>(null)

/** Løfter permission ud af Composer så et godkendelseskort kan sætte 'trust'
 *  udefra. localStorage-bagudkompatibel (samme PERM_KEY som før). */
export function PermissionProvider({ children }: { children: ReactNode }) {
  const [permission, setPermissionState] = useState<Permission>(() => {
    try { return localStorage.getItem(PERM_KEY) === 'trust' ? 'trust' : 'ask' } catch { return 'ask' }
  })
  useEffect(() => {
    try { localStorage.setItem(PERM_KEY, permission) } catch { /* ignore */ }
  }, [permission])
  const setPermission = useCallback((p: Permission) => setPermissionState(p), [])
  const value = useMemo(() => ({ permission, setPermission }), [permission, setPermission])
  return <PermissionContext.Provider value={value}>{children}</PermissionContext.Provider>
}
```

Create `src/hooks/usePermission.ts`:

```ts
import { useContext } from 'react'
import { PermissionContext } from '../contexts/PermissionContext'

export function usePermission() {
  const ctx = useContext(PermissionContext)
  if (!ctx) throw new Error('usePermission must be used within PermissionProvider')
  return ctx
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npx vitest run src/contexts/PermissionContext.test.tsx`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add src/contexts/PermissionContext.tsx src/hooks/usePermission.ts src/contexts/PermissionContext.test.tsx
git commit -m "feat(desk): PermissionContext — løft permission ud af Composer"
```

---

## Task 5: Composer bruger `usePermission` + delte nøgler

**Files:**
- Modify: `apps/jarvis-desk/src/components/shell/Composer.tsx`

Dette task ændrer ikke adfærd; det flytter blot permission-state til konteksten og bruger de delte localStorage-nøgler. Composer renderes allerede inde i `PermissionProvider` efter Task 8 — men test'en her wrapper selv.

- [ ] **Step 1: Erstat lokale nøgle-consts med imports**

I `src/components/shell/Composer.tsx`, fjern de lokale linjer (line 37, 40, 41):

```ts
const PERM_KEY = 'jarvis-desk:permission'
```
```ts
const PROV_KEY = 'jarvis-desk:provChoice'
const MODEL_KEY = 'jarvis-desk:model'
```

Tilføj i stedet en import øverst (ved de øvrige imports):

```ts
import { PERM_KEY, MODEL_KEY, PROV_KEY } from '../../lib/composerPrefs'
import { usePermission } from '../../hooks/usePermission'
```

(Behold `PERM_KEY`/`MODEL_KEY`/`PROV_KEY`-brugen i `provChoice`/`selModel`-init og persist-effekter — de peger nu på de importerede konstanter.)

- [ ] **Step 2: Erstat lokal permission-state med konteksten**

Fjern den lokale permission-state (line 106-110):

```ts
const [permission, setPermission] = useState<'ask' | 'trust'>(() => {
  try {
    return localStorage.getItem(PERM_KEY) === 'trust' ? 'trust' : 'ask'
  } catch { return 'ask' }
})
```

Fjern også permission-persist-effekten (line 140-142):

```ts
useEffect(() => {
  try { localStorage.setItem(PERM_KEY, permission) } catch { /* ignore */ }
}, [permission])
```

Tilføj i stedet, sammen med de øvrige hooks øverst i `Composer`-funktionen:

```ts
const { permission, setPermission } = usePermission()
```

Resten af Composer (dropdown `onClick={() => { setPermission(p.key); setPermOpen(false) }}` og `onSend(..., { permission, ... })`) virker uændret. `PERM_KEY` bruges nu kun via konteksten — hvis ingen anden reference til `PERM_KEY` er tilbage i filen, fjern `PERM_KEY` fra importen for at undgå unused-import-fejl (tjek med tsc i Step 3).

- [ ] **Step 3: Verify build (type-check)**

Run: `npx tsc -b`
Expected: ingen fejl. (Hvis "PERM_KEY is declared but never read" → fjern `PERM_KEY` fra importen i Step 1.)

Run: `npx vitest run`
Expected: alle eksisterende tests grønne (ingen adfærdsændring).

- [ ] **Step 4: Commit**

```bash
git add src/components/shell/Composer.tsx
git commit -m "refactor(desk): Composer bruger PermissionContext + delte composerPrefs-nøgler"
```

---

## Task 6: StreamContext — `pendingAppAction` + auto-continue-stash

**Files:**
- Modify: `apps/jarvis-desk/src/contexts/StreamContext.tsx`
- Test: `apps/jarvis-desk/src/contexts/StreamContext.test.tsx` (tilføj cases)

- [ ] **Step 1: Write the failing test**

Tilføj i `src/contexts/StreamContext.test.tsx` et nyt `it`-blok inde i det eksisterende `describe('StreamContext', ...)` (genbrug `wrapper` + `handlersRef` fra filen):

```tsx
  it('app_action_request → pendingAppAction; survives message_stop; armable auto-continue', () => {
    const { result } = renderHook(() => useStream(), { wrapper })
    act(() => { result.current.send('ret bug i db.py', { sessionId: 's' }) })
    act(() => {
      handlersRef.current?.onEvent({
        type: 'system_event',
        kind: 'app_action_request',
        payload: { action: 'switch_to_code_mode', reason: 'kræver filer', original_message: 'ret bug i db.py' },
      })
    })
    expect(result.current.pendingAppAction).toEqual({
      action: 'switch_to_code_mode',
      reason: 'kræver filer',
      originalMessage: 'ret bug i db.py',
    })
    // Kortet skal OVERLEVE message_stop (Jarvis afslutter turen; kortet bliver stående).
    act(() => { handlersRef.current?.onEvent({ type: 'message_stop' }) })
    expect(result.current.pendingAppAction).not.toBeNull()

    // Auto-continue arm/consume.
    act(() => { result.current.armAutoContinue('ret bug i db.py') })
    expect(result.current.autoContinue).toBe('ret bug i db.py')
    let consumed: string | null = null
    act(() => { consumed = result.current.consumeAutoContinue() })
    expect(consumed).toBe('ret bug i db.py')
    expect(result.current.autoContinue).toBeNull()

    // clearAppAction rydder kortet.
    act(() => { result.current.clearAppAction() })
    expect(result.current.pendingAppAction).toBeNull()
  })
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run src/contexts/StreamContext.test.tsx`
Expected: FAIL — `pendingAppAction`/`armAutoContinue`/`consumeAutoContinue`/`clearAppAction` findes ikke på context-værdien.

- [ ] **Step 3: Implementér i StreamContext.tsx**

3a. Tilføj typen efter `PendingApproval`-interfacet (efter line 35):

```tsx
export interface PendingAppAction {
  action: 'switch_to_code_mode' | 'request_full_access'
  reason: string
  originalMessage: string
}
```

3b. Udvid `StreamContextValue` (efter `deny`-feltet, line 55):

```tsx
  /** Afventende app-action-anmodning (mode/permission-skift), ellers null. */
  pendingAppAction: PendingAppAction | null
  /** Ryd app-action-kortet (efter approve/deny). */
  clearAppAction: () => void
  /** Besked der skal gen-sendes efter et godkendt skift, ellers null. */
  autoContinue: string | null
  /** Arm en auto-continue (kaldes af kort-handler ved godkendelse). */
  armAutoContinue: (message: string) => void
  /** Forbrug + ryd auto-continue (kaldes af den view der gen-sender). */
  consumeAutoContinue: () => string | null
```

3c. Tilføj state + ref i `StreamProvider` (efter line 78, `const [pendingApproval, ...]`):

```tsx
  const [pendingAppAction, setPendingAppAction] = useState<PendingAppAction | null>(null)
  const [autoContinue, setAutoContinue] = useState<string | null>(null)
  const autoContinueRef = useRef<string | null>(null)
```

(Importér `useRef` hvis det ikke allerede er importeret øverst — det er det typisk, da `runIdRef` bruger det.)

3d. I `send`-callback'en, lige efter `setPendingApproval(null)` (line 83), ryd også app-action-state ved en ny tur:

```tsx
    setPendingAppAction(null)
    autoContinueRef.current = null
    setAutoContinue(null)
```

3e. I `onEvent`-handleren, udvid if-kæden. Tilføj en gren EFTER `approval_request`-grenen og FØR `message_stop`-grenen (mellem line 116 og 117):

```tsx
          } else if (e.type === 'system_event' && e.kind === 'app_action_request') {
            const p = (e.payload || {}) as { action?: string; reason?: string; original_message?: string }
            if (p.action === 'switch_to_code_mode' || p.action === 'request_full_access') {
              setPendingAppAction({
                action: p.action,
                reason: p.reason || '',
                originalMessage: p.original_message || '',
              })
            }
```

VIGTIGT: rør IKKE `message_stop`-grenen — `pendingAppAction` skal overleve tur-afslutning (modsat `pendingApproval`).

3f. Tilføj callbacks efter `deny` (efter line 160):

```tsx
  const clearAppAction = useCallback(() => setPendingAppAction(null), [])
  const armAutoContinue = useCallback((message: string) => {
    autoContinueRef.current = message
    setAutoContinue(message)
  }, [])
  const consumeAutoContinue = useCallback((): string | null => {
    const msg = autoContinueRef.current
    autoContinueRef.current = null
    setAutoContinue(null)
    return msg
  }, [])
```

3g. Tilføj felterne i `value`-memo'en (objektet ved line 209 + deps-array ved line 213):

I objektet, efter `deny,`:

```tsx
      pendingAppAction,
      clearAppAction,
      autoContinue,
      armAutoContinue,
      consumeAutoContinue,
```

I deps-array'et, tilføj: `pendingAppAction, clearAppAction, autoContinue, armAutoContinue, consumeAutoContinue`.

- [ ] **Step 4: Run test to verify it passes**

Run: `npx vitest run src/contexts/StreamContext.test.tsx`
Expected: PASS (alle, inkl. den nye)

Run: `npx tsc -b`
Expected: ingen fejl.

- [ ] **Step 5: Commit**

```bash
git add src/contexts/StreamContext.tsx src/contexts/StreamContext.test.tsx
git commit -m "feat(desk): StreamContext pendingAppAction + auto-continue-stash"
```

---

## Task 7: `AppActionCard`-komponent

**Files:**
- Create: `apps/jarvis-desk/src/components/rich/AppActionCard.tsx`
- Test: `apps/jarvis-desk/src/components/rich/AppActionCard.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `src/components/rich/AppActionCard.test.tsx`:

```tsx
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { AppActionCard } from './AppActionCard'

describe('AppActionCard', () => {
  it('renders code-mode prompt + reason, fires onApprove', async () => {
    const onApprove = vi.fn()
    render(<AppActionCard action="switch_to_code_mode" reason="kræver terminal og filer" onApprove={onApprove} onReject={() => {}} />)
    expect(screen.getByText(/code mode/i)).toBeInTheDocument()
    expect(screen.getByText(/kræver terminal og filer/i)).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: /ja/i }))
    expect(onApprove).toHaveBeenCalledTimes(1)
  })

  it('renders full-access prompt, fires onReject', async () => {
    const onReject = vi.fn()
    render(<AppActionCard action="request_full_access" reason="" onApprove={() => {}} onReject={onReject} />)
    expect(screen.getByText(/fuld adgang/i)).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: /nej/i }))
    expect(onReject).toHaveBeenCalledTimes(1)
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run src/components/rich/AppActionCard.test.tsx`
Expected: FAIL — cannot find module `./AppActionCard`

- [ ] **Step 3: Write the implementation**

Create `src/components/rich/AppActionCard.tsx`:

```tsx
type AppAction = 'switch_to_code_mode' | 'request_full_access'

const PROMPT: Record<AppAction, string> = {
  switch_to_code_mode: 'Jarvis vil skifte til code mode for at fortsætte. Skift nu?',
  request_full_access: 'Jarvis beder om fuld adgang (trust) til denne opgave. Slå til?',
}

/** Inline godkendelseskort: Jarvis foreslår et mode-/permission-skift.
 *  Kun brugerens klik skifter noget — kortet udfører intet selv. */
export function AppActionCard({
  action,
  reason,
  onApprove,
  onReject,
}: {
  action: AppAction
  reason: string
  onApprove: () => void
  onReject: () => void
}) {
  return (
    <div className="appactioncard">
      <div className="appactioncard-head">{PROMPT[action]}</div>
      {reason ? <div className="appactioncard-reason">{reason}</div> : null}
      <div className="appactioncard-actions">
        <button type="button" onClick={onApprove}>Ja</button>
        <button type="button" onClick={onReject}>Nej</button>
      </div>
    </div>
  )
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npx vitest run src/components/rich/AppActionCard.test.tsx`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add src/components/rich/AppActionCard.tsx src/components/rich/AppActionCard.test.tsx
git commit -m "feat(desk): AppActionCard — inline godkendelseskort for mode/permission-skift"
```

---

## Task 8: `resolveAppAction` + `AppActionHost` + App-wiring

**Files:**
- Create: `apps/jarvis-desk/src/lib/appAction.ts`
- Create: `apps/jarvis-desk/src/lib/appAction.test.ts`
- Modify: `apps/jarvis-desk/src/App.tsx`

- [ ] **Step 1: Write the failing test (ren approve-logik)**

Create `src/lib/appAction.test.ts`:

```ts
import { describe, it, expect, vi } from 'vitest'
import { resolveAppAction } from './appAction'

describe('resolveAppAction', () => {
  it('switch_to_code_mode → setSurface(code) + arm auto-continue', () => {
    const setSurface = vi.fn()
    const setPermission = vi.fn()
    const armAutoContinue = vi.fn()
    resolveAppAction('switch_to_code_mode', { setSurface, setPermission, armAutoContinue }, 'ret bug')
    expect(setSurface).toHaveBeenCalledWith('code')
    expect(setPermission).not.toHaveBeenCalled()
    expect(armAutoContinue).toHaveBeenCalledWith('ret bug')
  })

  it('request_full_access → setPermission(trust) + arm auto-continue', () => {
    const setSurface = vi.fn()
    const setPermission = vi.fn()
    const armAutoContinue = vi.fn()
    resolveAppAction('request_full_access', { setSurface, setPermission, armAutoContinue }, 'kør tests')
    expect(setPermission).toHaveBeenCalledWith('trust')
    expect(setSurface).not.toHaveBeenCalled()
    expect(armAutoContinue).toHaveBeenCalledWith('kør tests')
  })

  it('does not arm auto-continue when message is empty', () => {
    const armAutoContinue = vi.fn()
    resolveAppAction('switch_to_code_mode', { setSurface: vi.fn(), setPermission: vi.fn(), armAutoContinue }, '')
    expect(armAutoContinue).not.toHaveBeenCalled()
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run src/lib/appAction.test.ts`
Expected: FAIL — cannot find module `./appAction`

- [ ] **Step 3a: Write the helper**

Create `src/lib/appAction.ts`:

```ts
export type AppAction = 'switch_to_code_mode' | 'request_full_access'

export interface AppActionDeps {
  setSurface: (s: 'code') => void
  setPermission: (p: 'trust') => void
  armAutoContinue: (message: string) => void
}

/** Ren oversættelse: app-action → konkrete state-mutationer. Holdes ren så
 *  approve-logikken er unit-testbar uden React. */
export function resolveAppAction(
  action: AppAction,
  deps: AppActionDeps,
  originalMessage: string,
): void {
  if (action === 'switch_to_code_mode') deps.setSurface('code')
  if (action === 'request_full_access') deps.setPermission('trust')
  if (originalMessage) deps.armAutoContinue(originalMessage)
}
```

- [ ] **Step 3b: Wire AppActionHost + PermissionProvider i App.tsx**

I `src/App.tsx`:

Tilføj imports øverst:

```tsx
import { PermissionProvider } from './contexts/PermissionContext'
import { usePermission } from './hooks/usePermission'
import { useStream } from './hooks/useStream'
import { AppActionCard } from './components/rich/AppActionCard'
import { resolveAppAction } from './lib/appAction'
```

Wrap Shell-træet i `PermissionProvider`. Erstat blokken (line 36-49):

```tsx
  return (
    <SessionProvider config={cfg}>
      <StreamProvider config={cfg}>
        <PanelProvider defaultWidth={480}>
          <Shell
            surface={surface}
            setSurface={setSurface}
            role={auth?.role ?? 'guest'}
            userName={auth?.display_name ?? 'Bruger'}
            model={settings.defaultModel}
          />
          <UiPanelWatcher config={cfg} />
        </PanelProvider>
      </StreamProvider>
    </SessionProvider>
  )
```

med:

```tsx
  return (
    <SessionProvider config={cfg}>
      <StreamProvider config={cfg}>
        <PermissionProvider>
          <PanelProvider defaultWidth={480}>
            <Shell
              surface={surface}
              setSurface={setSurface}
              role={auth?.role ?? 'guest'}
              userName={auth?.display_name ?? 'Bruger'}
              model={settings.defaultModel}
            />
            <UiPanelWatcher config={cfg} />
          </PanelProvider>
        </PermissionProvider>
      </StreamProvider>
    </SessionProvider>
  )
```

Tilføj `AppActionHost`-komponenten i samme fil (fx efter `Shell`-funktionen). Den læser `pendingAppAction` fra StreamContext og er placeret inde i Shell (som er inde i alle providere):

```tsx
/** Viser AppActionCard når Jarvis har anmodet om et mode/permission-skift.
 *  Renderes inde i Shell (har adgang til Stream + Permission + setSurface). */
function AppActionHost({ setSurface }: { setSurface: (s: Surface) => void }) {
  const stream = useStream()
  const { setPermission } = usePermission()
  const pending = stream.pendingAppAction
  if (!pending) return null
  return (
    <div className="appaction-host">
      <AppActionCard
        action={pending.action}
        reason={pending.reason}
        onApprove={() => {
          resolveAppAction(
            pending.action,
            {
              setSurface: (s) => setSurface(s),
              setPermission,
              armAutoContinue: stream.armAutoContinue,
            },
            pending.originalMessage,
          )
          stream.clearAppAction()
        }}
        onReject={() => stream.clearAppAction()}
      />
    </div>
  )
}
```

Render `AppActionHost` i `Shell` lige inde i `<main className="main">`, før `<ShellWithPanel>` (omkring line 89):

```tsx
      <main className="main">
        <AppActionHost setSurface={setSurface} />
        <ShellWithPanel>
```

- [ ] **Step 4: Run tests + build to verify**

Run: `npx vitest run src/lib/appAction.test.ts`
Expected: PASS (3 passed)

Run: `npx tsc -b`
Expected: ingen fejl.

Run: `npx vitest run`
Expected: alle tests grønne.

- [ ] **Step 5: Commit**

```bash
git add src/lib/appAction.ts src/lib/appAction.test.ts src/App.tsx
git commit -m "feat(desk): AppActionHost + resolveAppAction + PermissionProvider-wiring"
```

---

## Task 9: CodeView auto-continue

**Files:**
- Modify: `apps/jarvis-desk/src/views/CodeView.tsx`

Når surface bliver `'code'` (efter et godkendt `switch_to_code_mode`) ELLER permission lige er sat til `'trust'` (efter `request_full_access`), skal CodeView opdage en armet auto-continue og gen-sende den oprindelige besked med code-mode-opts.

- [ ] **Step 1: Tilføj imports + hooks i CodeView**

I `src/views/CodeView.tsx`, tilføj imports øverst:

```tsx
import { useEffect } from 'react'
import { useStream } from '../hooks/useStream'
import { usePermission } from '../hooks/usePermission'
import { readModelPrefs } from '../lib/composerPrefs'
```

(Hvis `useStream` allerede importeres et andet sted i filen, undgå dublet. `react`-importen kan allerede have `useEffect` — tilføj kun det manglende.)

Tilføj i `CodeView`-funktionen sammen med de øvrige hooks (efter `const isOwner = role === 'owner'`):

```tsx
  const stream = useStream()
  const { permission } = usePermission()
```

- [ ] **Step 2: Tilføj auto-continue-effekten**

Placér efter `doSend`-definitionen (efter line ~160, hvor `doSend` slutter). `ready` og `isOwner` er allerede i scope:

```tsx
  // Auto-continue: efter et godkendt mode/permission-skift gen-sendes den
  // oprindelige besked her, så Jarvis fortsætter sømløst i code mode.
  useEffect(() => {
    if (!stream.autoContinue || !ready) return
    const msg = stream.consumeAutoContinue()
    if (!msg) return
    const prefs = readModelPrefs()
    const sendModel = isOwner ? prefs.model : (prefs.model === 'pro' ? 'pro' : 'standard')
    const sendProvider = isOwner ? prefs.providerChoice : ''
    void doSend(msg, {
      planMode: false,
      permission,
      attachments: [],
      model: sendModel,
      providerChoice: sendProvider,
    })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [stream.autoContinue, ready])
```

Note: `doSend`/`permission`/`isOwner` med vilje udeladt fra deps — effekten skal kun fyre når en auto-continue armes (og workspace er klar), ikke ved hver permission-render. `consumeAutoContinue()` rydder stash'en med det samme, så StrictMonde-dobbeltkald ikke gen-sender to gange.

- [ ] **Step 3: Verify build + tests**

Run: `npx tsc -b`
Expected: ingen fejl.

Run: `npx vitest run`
Expected: alle tests grønne.

- [ ] **Step 4: Manuel røgtest-note (ingen automatisk test for denne effekt)**

Auto-continue-effekten afhænger af CodeView's `doSend`/`ready`/workspace-state, som er svær at isolere i vitest uden at mocke hele view'et. Den dækkes i stedet af den end-to-end manuelle verifikation i Task 10. De rene enheder (`resolveAppAction`, `consumeAutoContinue`, `build_app_action_event`) er allerede unit-dækket.

- [ ] **Step 5: Commit**

```bash
git add src/views/CodeView.tsx
git commit -m "feat(desk): CodeView auto-continue — gen-send besked efter godkendt skift"
```

---

## Task 10: Styling, fuld test, build + deploy

**Files:**
- Modify: `apps/jarvis-desk/src/styles/app.css` (kort-styling)

- [ ] **Step 1: Tilføj minimal styling**

I `apps/jarvis-desk/src/styles/app.css`, tilføj (genbrug eksisterende tokens; matcher approvalcard-stilen):

```css
.appaction-host { padding: 8px 12px 0; }
.appactioncard {
  border: 1px solid var(--border, #333);
  border-radius: 8px;
  padding: 10px 12px;
  background: var(--surface-2, #1b1b1b);
}
.appactioncard-head { font-weight: 600; margin-bottom: 4px; }
.appactioncard-reason { opacity: 0.8; font-size: 0.9em; margin-bottom: 8px; }
.appactioncard-actions { display: flex; gap: 8px; }
.appactioncard-actions button {
  padding: 4px 14px; border-radius: 6px; cursor: pointer;
}
```

(Hvis `app.css` bruger andre token-navne, match dem; tjek hvordan `.approvalcard` er stylet og spejl.)

- [ ] **Step 2: Fuld test-suite (backend + frontend)**

Backend (working dir `/media/projects/jarvis-v2`):
Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_app_control_tool.py -q -p no:cacheprovider`
Expected: PASS (9 passed)

Frontend (working dir `apps/jarvis-desk`):
Run: `npx vitest run`
Expected: alle suiter grønne.
Run: `npx tsc -b`
Expected: ingen fejl.

- [ ] **Step 3: Commit styling**

```bash
git add apps/jarvis-desk/src/styles/app.css
git commit -m "style(desk): AppActionCard-styling"
```

- [ ] **Step 4: Deploy backend (kræver Bjørns ok — ikke autonomt)**

Push + genstart API (idle-tjek FØRST jf. deploy-vane — genstart ikke midt i et aktivt run):

```bash
git push origin main && git push target main
```

Genstart `jarvis-api` (efter idle-bekræftelse) så det nye tool + SSE-emission går live. Brug den etablerede deploy-procedure for `jarvis-api.service`.

- [ ] **Step 5: Build + installér desk-app**

Working dir `apps/jarvis-desk` (kør i baggrund — bygning tager tid):

```bash
npm run build && npx electron-builder --linux deb && sudo dpkg -i dist/*.deb
```

- [ ] **Step 6: Manuel end-to-end verifikation**

1. Åbn jarvis-desk i **chat mode**. Bed Jarvis om noget der kræver filer/terminal (fx "ret en lille bug i en fil i repoet").
2. Forvent: Jarvis kalder `request_app_action("switch_to_code_mode", …)`, afslutter turen med en kort note, og et **AppActionCard** vises ("…skifte til code mode…").
3. Klik **Ja** → appen skifter til code mode og **gen-sender** din oprindelige besked automatisk; Jarvis fortsætter med code-tools.
4. I **code mode** med permission=`ask`: bed om en krævende opgave. Forvent et kort "…fuld adgang (trust)…". Klik **Ja** → permission bliver `trust`, beskeden gen-sendes, opgaven kører uden per-kald-godkendelse.
5. Klik **Nej** på et kort → intet skifter; Jarvis' note står som hans svar.

---

## Notes for the implementer

- **Sikkerhedsgrænse:** tool'et muterer ALDRIG desk-state. Det returnerer kun en markør; desk handler først på brugerens klik. Backendens permission_engine/tool-scoping håndhæver stadig hvad en member faktisk må efter et skift — eskaleringen åbner ingen bagdør.
- **Hvorfor `pendingAppAction` overlever `message_stop`:** `request_app_action` kaldes under et run, hvorefter Jarvis afslutter turen (→ `message_stop` fyrer straks). Modsat `pendingApproval` (der blokerer streamen) skal app-action-kortet blive stående til brugeren klikker.
- **conda:** alle Python-kald via `/opt/conda/envs/ai/bin/python`.
- **--workers 1 frys-fælde:** ingen nye blokerende kald tilføjes i async-ruter her (emissionen er en ren in-memory helper i en allerede-async generator), så ingen `asyncio.to_thread` nødvendig.
