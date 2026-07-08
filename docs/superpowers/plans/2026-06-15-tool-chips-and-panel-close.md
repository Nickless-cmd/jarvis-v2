---
status: færdig
audited: 2026-07-08
ground_truth: superpowers artifact shipped (refs/symbols present in tree)
---
# Tool-chips berigelse + pæne navne + luk-panel — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tool-kald i jarvis-desk viser pæn label + opsummering + resultat (uden klik) + `+N −M` diff-stat for filændringer, og Jarvis kan lukke paneler igen.

**Architecture:** Backend beriges til at sende `arguments` + `result_text` i tool-kald-event'et (ren data). Et frontend `toolRegistry` ejer label/ikon/opsummering (fallback til Title-Case garanterer komplet dækning). `ToolCard` viser sammenfoldet label+opsummering+diff-stat. `open_ui_panel` får `action: 'open'|'close'`.

**Tech Stack:** Python 3.11 (`/opt/conda/envs/ai/bin/python`), pytest. React+TS (Electron), vitest. Backend-test: `/opt/conda/envs/ai/bin/python -m pytest -p no:cacheprovider`. Frontend i `apps/jarvis-desk`: `npx vitest run` + `npx tsc -b`.

**Spec:** `docs/superpowers/specs/2026-06-15-tool-chips-and-panel-close-design.md`

---

## File Structure

**Backend (`/media/projects/jarvis-v2`):**
- Create `core/services/tool_chip_payload.py` — ren helper `build_tool_capability_payload` (berig+trunkér). Eneansvar: byg data-payloaden for et tool-kald.
- Modify `core/services/visible_runs.py` — brug helper'en på de executed-tool emit-sites (args+result).
- Modify `core/services/visible_runs_sse_v2.py` — `_emit_tool_use` læser `arguments` + sender `result` i `tool_result`.
- Modify `core/tools/ui_panel_tools.py` + `core/services/ui_panel_store.py` — `action: open|close`.
- Create `tests/test_tool_chip_payload.py`. Modify `tests/test_ui_panel_tools.py`, `tests/test_ui_panel_store.py`.

**Frontend (`apps/jarvis-desk`):**
- Create `src/lib/diffStat.ts` — `+N −M`-udregning. Eneansvar: ren diff-statistik.
- Create `src/lib/toolRegistry.ts` — navn → {label, Icon, summarize}; `lookupTool` med Title-Case fallback.
- Create `scripts/gen_tool_registry.cjs` *(dev-hjælper)* — lister tools uden kurateret entry. (Ikke testet; ren rapport.)
- Modify `src/lib/streamReducer.ts` — `tool_result` sætter `result` på blokken.
- Modify `src/components/rich/ToolCard.tsx` — brug registry + diff-stat i hovedet.
- Modify `src/lib/coworkApi.ts` (`UiPanelRequest.action`) + `src/components/UiPanelWatcher.tsx` (close → `panel.close()`).
- Modify `src/styles/app.css` — diff-stat-styling i chip-hovedet.
- Create tests: `src/lib/diffStat.test.ts`, `src/lib/toolRegistry.test.ts`, `src/components/rich/ToolCard.test.tsx`. Modify `src/lib/streamReducer.test.ts` (hvis findes; ellers ny case).

---

## Task 1: Backend — `build_tool_capability_payload` helper

**Files:**
- Create: `core/services/tool_chip_payload.py`
- Test: `tests/test_tool_chip_payload.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_tool_chip_payload.py`:

```python
"""Tests for tool_chip_payload (spec 2026-06-15)."""
from __future__ import annotations

from core.services.tool_chip_payload import build_tool_capability_payload


def test_includes_args_and_result() -> None:
    p = build_tool_capability_payload(
        tool="web_search", status="ok",
        arguments={"query": "vejr"}, result_text="3 resultater",
    )
    assert p["type"] == "tool_result"
    assert p["tool"] == "web_search"
    assert p["status"] == "ok"
    assert p["arguments"] == {"query": "vejr"}
    assert p["result_text"] == "3 resultater"


def test_strips_internal_keys() -> None:
    p = build_tool_capability_payload(
        tool="x", status="ok",
        arguments={"query": "a", "_runtime_user_id": "u1", "session_id": "s", "_runtime_trust_all": True},
        result_text="",
    )
    assert p["arguments"] == {"query": "a"}


def test_truncates_long_arg_value() -> None:
    p = build_tool_capability_payload(
        tool="x", status="ok",
        arguments={"text": "a" * 1000}, result_text="", arg_value_cap=600,
    )
    assert len(p["arguments"]["text"]) == 601  # 600 + ellipsis
    assert p["arguments"]["text"].endswith("…")


def test_truncates_long_result() -> None:
    p = build_tool_capability_payload(
        tool="x", status="ok", arguments={}, result_text="b" * 5000, result_cap=4000,
    )
    assert p["result_text"].startswith("b" * 4000)
    assert "trunkeret" in p["result_text"]


def test_handles_non_dict_args() -> None:
    p = build_tool_capability_payload(tool="x", status="ok", arguments=None, result_text="r")
    assert p["arguments"] == {}
    assert p["result_text"] == "r"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_tool_chip_payload.py -q -p no:cacheprovider`
Expected: FAIL — `ModuleNotFoundError: No module named 'core.services.tool_chip_payload'`

- [ ] **Step 3: Write the implementation**

Create `core/services/tool_chip_payload.py`:

```python
"""Bygger data-payloaden for et tool-kald til jarvis-desk-chip'en (spec 2026-06-15).

Ren funktion: beriger et tool-resultat med (trunkerede) arguments + result_text, så
desk-appen kan vise hvad tool'et gjorde. Ingen præsentation (labels/ikoner bor i
frontendens toolRegistry). Interne args-nøgler (session_id, _runtime_*) fjernes.
"""
from __future__ import annotations

from typing import Any

_INTERNAL_ARG_KEYS = {"session_id"}


def build_tool_capability_payload(
    *,
    tool: str,
    status: str,
    arguments: Any = None,
    result_text: str = "",
    arg_value_cap: int = 600,
    result_cap: int = 4000,
) -> dict[str, Any]:
    args_out: dict[str, Any] = {}
    if isinstance(arguments, dict):
        for k, v in arguments.items():
            ks = str(k)
            if ks.startswith("_") or ks in _INTERNAL_ARG_KEYS:
                continue
            if isinstance(v, str) and len(v) > arg_value_cap:
                args_out[ks] = v[:arg_value_cap] + "…"
            else:
                args_out[ks] = v
    rt = str(result_text or "")
    if len(rt) > result_cap:
        rt = rt[:result_cap] + "\n…(trunkeret)"
    return {
        "type": "tool_result",
        "tool": str(tool),
        "status": str(status),
        "arguments": args_out,
        "result_text": rt,
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_tool_chip_payload.py -q -p no:cacheprovider`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add core/services/tool_chip_payload.py tests/test_tool_chip_payload.py
git commit -m "feat(desk): tool_chip_payload helper — berig+trunkér tool-kald-data"
```

---

## Task 2: Backend — wire args+result ind i tool-kald-eventet

**Files:**
- Modify: `core/services/visible_runs.py` (capability tool_result emits, line ~1441 og ~2438)
- Modify: `core/services/visible_runs_sse_v2.py` (`_emit_tool_use`, ~line 300-322)

- [ ] **Step 1: Berig executed-tool emit (round 1) i visible_runs.py**

Find blokken ved line ~1440-1445:

```python
                    _resolved_result_texts[_idx] = sr["result_text"]
                    yield _sse("capability", {
                        "type": "tool_result",
                        "tool": sr["tool_name"],
                        "status": sr["status"],
                    })
```

Erstat `yield _sse("capability", {...})` med:

```python
                    _resolved_result_texts[_idx] = sr["result_text"]
                    from core.services.tool_chip_payload import build_tool_capability_payload
                    yield _sse("capability", build_tool_capability_payload(
                        tool=sr["tool_name"],
                        status=sr["status"],
                        arguments=sr.get("arguments"),
                        result_text=sr.get("result_text", ""),
                    ))
```

- [ ] **Step 2: Berig executed-tool emit (round 2) i visible_runs.py**

Find blokken ved line ~2437-2442:

```python
                        _a_resolved[_a_idx] = _a_sr["result_text"]
                        yield _sse("capability", {
                            "type": "tool_result",
                            "tool": _a_sr["tool_name"],
                            "status": _a_sr["status"],
                        })
```

Erstat `yield _sse("capability", {...})` med:

```python
                        _a_resolved[_a_idx] = _a_sr["result_text"]
                        from core.services.tool_chip_payload import build_tool_capability_payload
                        yield _sse("capability", build_tool_capability_payload(
                            tool=_a_sr["tool_name"],
                            status=_a_sr["status"],
                            arguments=_a_sr.get("arguments"),
                            result_text=_a_sr.get("result_text", ""),
                        ))
```

- [ ] **Step 3: `_emit_tool_use` læser arguments + sender result**

I `core/services/visible_runs_sse_v2.py`, find i `_emit_tool_use` (~line 300):

```python
        tool_input: dict = {}
        for k in ("target_path", "command_text", "write_content", "arguments"):
            v = payload.get(k)
            if v:
                tool_input[k] = v
```

Erstat med (brug `arguments`-dict'en direkte som input, behold legacy-nøgler):

```python
        tool_input: dict = {}
        _args = payload.get("arguments")
        if isinstance(_args, dict):
            tool_input.update(_args)
        for k in ("target_path", "command_text", "write_content"):
            v = payload.get(k)
            if v:
                tool_input[k] = v
```

Find så `tool_result`-SystemEvent'et (~line 318):

```python
        await queue.put(SystemEvent(
            kind="tool_result",
            payload={"tool_use_id": tool_id, "tool": name, "status": status, "type": ptype},
        ).to_sse_line())
```

Erstat med (tilføj `result`):

```python
        await queue.put(SystemEvent(
            kind="tool_result",
            payload={"tool_use_id": tool_id, "tool": name, "status": status, "type": ptype,
                     "result": str(payload.get("result_text") or "")},
        ).to_sse_line())
```

- [ ] **Step 4: Verify compile + existing backend tests**

Run: `/opt/conda/envs/ai/bin/python -m compileall core/services/visible_runs.py core/services/visible_runs_sse_v2.py -q`
Expected: ingen output (kompilerer rent)

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_visible_runs_sse_v2.py -q -p no:cacheprovider`
Expected: PASS (eksisterende tests grønne — ingen regression)

- [ ] **Step 5: Commit**

```bash
git add core/services/visible_runs.py core/services/visible_runs_sse_v2.py
git commit -m "feat(desk): send args+result i tool-kald-event (root cause for tomme chips)"
```

---

## Task 3: Backend — `open_ui_panel` action open/close

**Files:**
- Modify: `core/services/ui_panel_store.py`
- Modify: `core/tools/ui_panel_tools.py`
- Test: `tests/test_ui_panel_store.py`, `tests/test_ui_panel_tools.py`

- [ ] **Step 1: Write failing tests**

Tilføj i `tests/test_ui_panel_store.py`:

```python
def test_request_panel_carries_action_close() -> None:
    from core.services.ui_panel_store import request_panel, list_pending
    rec = request_panel(request_id="p-close-1", panel="preview", session_id="s",
                        detail="", created_at="t", action="close")
    assert rec["action"] == "close"
    assert any(r["id"] == "p-close-1" and r.get("action") == "close" for r in list_pending())


def test_request_panel_defaults_action_open() -> None:
    from core.services.ui_panel_store import request_panel
    rec = request_panel(request_id="p-open-1", panel="preview", session_id="s",
                        detail="", created_at="t")
    assert rec["action"] == "open"
```

Tilføj i `tests/test_ui_panel_tools.py`:

```python
def test_close_action_valid() -> None:
    from core.tools.ui_panel_tools import _exec_open_ui_panel
    r = _exec_open_ui_panel({"action": "close"})
    assert r["status"] == "ok"
    assert r["action"] == "close"


def test_open_is_default_action() -> None:
    from core.tools.ui_panel_tools import _exec_open_ui_panel
    r = _exec_open_ui_panel({"panel": "preview"})
    assert r["status"] == "ok"
    assert r.get("action", "open") == "open"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_ui_panel_store.py tests/test_ui_panel_tools.py -q -p no:cacheprovider`
Expected: FAIL — `request_panel() got unexpected keyword 'action'` / `KeyError: 'action'`

- [ ] **Step 3a: Add action to the store**

In `core/services/ui_panel_store.py`, replace `request_panel`:

```python
def request_panel(*, request_id: str, panel: str, session_id: str, detail: str,
                  created_at: str, action: str = "open") -> dict:
    """Registrér en panel-forespørgsel (open/close). panel clamps til kendte værdier."""
    p = panel if panel in _VALID_PANELS else "preview"
    a = action if action in ("open", "close") else "open"
    rec = {
        "id": str(request_id),
        "panel": p,
        "action": a,
        "session_id": str(session_id or ""),
        "detail": str(detail or "")[:200],
        "status": "pending",
        "created_at": str(created_at or ""),
    }
    items = [r for r in _load() if r.get("id") != rec["id"]]
    items.append(rec)
    _save(items)
    return rec
```

- [ ] **Step 3b: Add action to the tool**

In `core/tools/ui_panel_tools.py`, replace `_exec_open_ui_panel`:

```python
def _exec_open_ui_panel(args: dict[str, Any]) -> dict[str, Any]:
    action = str(args.get("action") or "open").strip().lower()
    if action not in ("open", "close"):
        return {"status": "error", "error": f"ukendt action '{action}' (open/close)"}
    panel = str(args.get("panel") or "preview").strip().lower()
    if action == "open" and panel not in _PANELS:
        return {"status": "error", "error": f"ukendt panel '{panel}' (gyldige: {', '.join(_PANELS)})"}
    detail = str(args.get("detail") or "")
    session_id = str(args.get("session_id") or "")
    rec = request_panel(
        request_id=f"panel-{uuid4().hex[:12]}",
        panel=panel,
        session_id=session_id,
        detail=detail,
        created_at=datetime.now(UTC).isoformat(),
        action=action,
    )
    verb = "lukker" if action == "close" else "åbner"
    return {"status": "ok", "panel": panel, "action": action, "request_id": rec["id"],
            "note": f"Desk-appen {verb} panelet. (Kun synligt i jarvis-desk.)"}
```

And update the tool definition's `parameters` block to add `action` and make `panel` optional:

```python
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["open", "close"],
                        "description": "'open' (default) åbner panelet; 'close' lukker det igen",
                    },
                    "panel": {
                        "type": "string",
                        "enum": list(_PANELS),
                        "description": "Hvilket panel der skal åbnes (ved action='open')",
                    },
                    "detail": {
                        "type": "string",
                        "description": "Valgfri kort note om hvad panelet skal vise",
                    },
                },
                "required": [],
            },
```

Also update the tool `description` string — append: `" Brug action='close' for at lukke panelet igen."`

- [ ] **Step 4: Run tests to verify they pass**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_ui_panel_store.py tests/test_ui_panel_tools.py -q -p no:cacheprovider`
Expected: PASS (alle, inkl. de nye)

- [ ] **Step 5: Commit**

```bash
git add core/services/ui_panel_store.py core/tools/ui_panel_tools.py tests/test_ui_panel_store.py tests/test_ui_panel_tools.py
git commit -m "feat(desk): open_ui_panel action open/close — Jarvis kan lukke paneler"
```

---

## Task 4: Frontend — streamReducer sætter `result` på tool_use-blokken

**Files:**
- Modify: `apps/jarvis-desk/src/lib/streamReducer.ts` (`tool_result`-handler, ~line 88-103)
- Test: `apps/jarvis-desk/src/lib/streamReducer.test.ts`

Working dir for frontend-steps: `/media/projects/jarvis-v2/apps/jarvis-desk`

- [ ] **Step 1: Write the failing test**

Append to `src/lib/streamReducer.test.ts` (inside the existing top-level `describe`, or add one). Use the reducer + initial state import already present in the file:

```ts
it('system_event tool_result sets result + status on the tool_use block', () => {
  let s = initialStreamState()
  s = streamReducer(s, { type: 'content_block_start', index: 0, content_block: { type: 'tool_use', id: 't1', name: 'web_search', input: { query: 'vejr' } } } as never)
  s = streamReducer(s, { type: 'system_event', kind: 'tool_result', payload: { tool_use_id: 't1', status: 'ok', result: '3 resultater' } } as never)
  const b = s.blocks[0]
  expect(b.type).toBe('tool_use')
  if (b.type === 'tool_use') {
    expect(b.status).toBe('done')
    expect(b.result).toBe('3 resultater')
  }
})
```

(If `initialStreamState`/`streamReducer` are imported under other names in the test file, match the existing imports.)

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run src/lib/streamReducer.test.ts`
Expected: FAIL — `b.result` is undefined (reducer doesn't set result).

- [ ] **Step 3: Set result in the tool_result handler**

In `src/lib/streamReducer.ts`, find the `tool_result` handler:

```ts
      if (event.kind === 'tool_result') {
        const tr = event.payload as { tool_use_id?: string; status?: string }
        if (!tr.tool_use_id) return state
        const idx = state.blocks.findIndex((b) => b.type === 'tool_use' && b.id === tr.tool_use_id)
        if (idx < 0) return state
        const mapped =
          tr.status === 'ok' || tr.status === 'executed' || tr.status === 'completed'
            ? 'done'
            : tr.status === 'error' || tr.status === 'failed'
              ? 'error'
              : undefined
        const blocks = state.blocks.slice()
        const b = blocks[idx]
        if (b && b.type === 'tool_use') blocks[idx] = { ...b, status: mapped ?? b.status }
        return { ...state, blocks }
      }
```

Change the payload type to include `result`, and set it on the block:

```ts
      if (event.kind === 'tool_result') {
        const tr = event.payload as { tool_use_id?: string; status?: string; result?: string }
        if (!tr.tool_use_id) return state
        const idx = state.blocks.findIndex((b) => b.type === 'tool_use' && b.id === tr.tool_use_id)
        if (idx < 0) return state
        const mapped =
          tr.status === 'ok' || tr.status === 'executed' || tr.status === 'completed'
            ? 'done'
            : tr.status === 'error' || tr.status === 'failed'
              ? 'error'
              : undefined
        const blocks = state.blocks.slice()
        const b = blocks[idx]
        if (b && b.type === 'tool_use') blocks[idx] = { ...b, status: mapped ?? b.status, result: tr.result ?? b.result }
        return { ...state, blocks }
      }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npx vitest run src/lib/streamReducer.test.ts`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd /media/projects/jarvis-v2 && git add apps/jarvis-desk/src/lib/streamReducer.ts apps/jarvis-desk/src/lib/streamReducer.test.ts
git commit -m "feat(desk): streamReducer sætter tool-resultat på tool_use-blokken"
```

---

## Task 5: Frontend — `diffStat` helper (`+N −M`)

**Files:**
- Create: `apps/jarvis-desk/src/lib/diffStat.ts`
- Test: `apps/jarvis-desk/src/lib/diffStat.test.ts`

- [ ] **Step 1: Write the failing test**

Create `src/lib/diffStat.test.ts`:

```ts
import { describe, it, expect } from 'vitest'
import { diffStat } from './diffStat'

describe('diffStat', () => {
  it('edit_file → add/del from line diff', () => {
    const r = diffStat('edit_file', { old_string: 'a\nb\nc', new_string: 'a\nX\nc\nd' })
    expect(r).not.toBeNull()
    expect(r!.add).toBeGreaterThan(0)
    expect(r!.del).toBeGreaterThan(0)
  })

  it('operator_edit_file is recognised', () => {
    const r = diffStat('operator_edit_file', { old: 'x', new: 'y' })
    expect(r).not.toBeNull()
  })

  it('write_file → all lines are additions', () => {
    const r = diffStat('write_file', { content: 'l1\nl2\nl3' })
    expect(r).toEqual({ add: 3, del: 0 })
  })

  it('returns null for non-edit tools', () => {
    expect(diffStat('web_search', { query: 'x' })).toBeNull()
  })

  it('returns null when edit args are empty', () => {
    expect(diffStat('edit_file', {})).toBeNull()
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run src/lib/diffStat.test.ts`
Expected: FAIL — cannot find module `./diffStat`

- [ ] **Step 3: Write the implementation**

Create `src/lib/diffStat.ts`:

```ts
import { lineDiff } from './diff'

/** Insertions/deletions for et fil-ændrende tool-kald — vises som +N −M i chip'en.
 *  Returnerer null for tools der ikke ændrer en fil (eller mangler args). */
export function diffStat(name: string, args: Record<string, unknown>): { add: number; del: number } | null {
  const n = name.toLowerCase()
  if (n.includes('edit_file')) {
    const oldS = String(args.old_string ?? args.old ?? '')
    const newS = String(args.new_string ?? args.new ?? '')
    if (!oldS && !newS) return null
    const d = lineDiff(oldS, newS)
    return {
      add: d.filter((x) => x.type === 'add').length,
      del: d.filter((x) => x.type === 'del').length,
    }
  }
  if (n.includes('write_file')) {
    const content = String(args.content ?? '')
    if (!content) return null
    return { add: content.split('\n').length, del: 0 }
  }
  return null
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npx vitest run src/lib/diffStat.test.ts`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
cd /media/projects/jarvis-v2 && git add apps/jarvis-desk/src/lib/diffStat.ts apps/jarvis-desk/src/lib/diffStat.test.ts
git commit -m "feat(desk): diffStat helper — +N −M for filændringer"
```

---

## Task 6: Frontend — `toolRegistry` (pæne navne, komplet dækning)

**Files:**
- Create: `apps/jarvis-desk/src/lib/toolRegistry.ts`
- Create: `scripts/gen_tool_registry.cjs` (dev-hjælper)
- Test: `apps/jarvis-desk/src/lib/toolRegistry.test.ts`

Komplet dækning garanteres af `lookupTool`-fallback: ethvert ukendt tool får en
Title-Case-label (aldrig rå snake_case). Registret holder kuraterede labels/ikoner/
opsummeringer for de tools brugeren ser oftest. Generatoren rapporterer hvilke tools
der mangler kurateret entry, så dækningen kan udvides over tid.

- [ ] **Step 1: Write the failing test**

Create `src/lib/toolRegistry.test.ts`:

```ts
import { describe, it, expect } from 'vitest'
import { lookupTool } from './toolRegistry'

describe('toolRegistry', () => {
  it('known tool → curated label + summary', () => {
    const m = lookupTool('web_search')
    expect(m.label).toBe('Websøgning')
    expect(m.summarize({ query: 'vejr københavn' })).toBe('vejr københavn')
  })

  it('open_ui_panel summarises open vs close', () => {
    const m = lookupTool('open_ui_panel')
    expect(m.summarize({ panel: 'preview' })).toContain('preview')
    expect(m.summarize({ action: 'close' })).toBe('luk')
  })

  it('unknown tool → Title-Case fallback (never raw snake_case)', () => {
    const m = lookupTool('some_new_internal_tool')
    expect(m.label).toBe('Some New Internal Tool')
    expect(typeof m.summarize).toBe('function')
  })

  it('operator_ prefix is humanised', () => {
    const m = lookupTool('operator_read_file')
    expect(m.label).toBe('Læs fil')
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run src/lib/toolRegistry.test.ts`
Expected: FAIL — cannot find module `./toolRegistry`

- [ ] **Step 3: Write the implementation**

Create `src/lib/toolRegistry.ts`:

```ts
import {
  Wrench, Terminal, FileText, FilePen, FilePlus, FolderTree, Search, Globe,
  Database, MessageSquare, Cpu, PanelRight, Image, Brain, Bell, Calendar,
  type LucideIcon,
} from 'lucide-react'

export interface ToolMeta {
  label: string
  Icon: LucideIcon
  summarize: (args: Record<string, unknown>, result?: string) => string
}

function firstStr(args: Record<string, unknown>, keys: string[]): string {
  for (const k of keys) {
    const v = args[k]
    if (typeof v === 'string' && v.trim()) return v
  }
  return ''
}

function pathOf(args: Record<string, unknown>): string {
  return String(args.path || args.target_path || args.file_path || args.dir || '')
}

/** Kuraterede entries for de mest sete tools. Alle andre dækkes af lookupTool-fallback. */
export const TOOL_REGISTRY: Record<string, ToolMeta> = {
  // Kerne fil/shell (også operator_*-varianter via fallback-humanisering nedenfor)
  bash: { label: 'Terminal', Icon: Terminal, summarize: (a) => String(a.command ?? '') },
  operator_bash: { label: 'Terminal', Icon: Terminal, summarize: (a) => String(a.command ?? '') },
  read_file: { label: 'Læs fil', Icon: FileText, summarize: pathOf },
  operator_read_file: { label: 'Læs fil', Icon: FileText, summarize: pathOf },
  write_file: { label: 'Skriv fil', Icon: FilePlus, summarize: pathOf },
  operator_write_file: { label: 'Skriv fil', Icon: FilePlus, summarize: pathOf },
  edit_file: { label: 'Rediger fil', Icon: FilePen, summarize: pathOf },
  operator_edit_file: { label: 'Rediger fil', Icon: FilePen, summarize: pathOf },
  glob: { label: 'Find filer', Icon: Search, summarize: (a) => firstStr(a, ['pattern', 'glob']) },
  operator_glob: { label: 'Find filer', Icon: Search, summarize: (a) => firstStr(a, ['pattern', 'glob']) },
  grep: { label: 'Søg i kode', Icon: Search, summarize: (a) => firstStr(a, ['pattern', 'query']) },
  operator_grep: { label: 'Søg i kode', Icon: Search, summarize: (a) => firstStr(a, ['pattern', 'query']) },
  list_dir: { label: 'List mappe', Icon: FolderTree, summarize: pathOf },
  operator_list_dir: { label: 'List mappe', Icon: FolderTree, summarize: pathOf },
  // Web + internt
  web_search: { label: 'Websøgning', Icon: Globe, summarize: (a) => firstStr(a, ['query', 'q']) },
  operator_webfetch: { label: 'Hent webside', Icon: Globe, summarize: (a) => firstStr(a, ['url']) },
  internal_api: { label: 'Internt API-kald', Icon: Cpu, summarize: (a) => firstStr(a, ['endpoint', 'path', 'method', 'name']) },
  // UI
  open_ui_panel: { label: 'Panel', Icon: PanelRight, summarize: (a) => (String(a.action) === 'close' ? 'luk' : String(a.panel ?? 'preview')) },
  request_app_action: { label: 'App-handling', Icon: PanelRight, summarize: (a) => String(a.action ?? '') },
  // Hukommelse / brain
  search_memory: { label: 'Søg i hukommelse', Icon: Brain, summarize: (a) => firstStr(a, ['query', 'q', 'text']) },
  search_jarvis_brain: { label: 'Søg i brain', Icon: Brain, summarize: (a) => firstStr(a, ['query', 'q']) },
  remember_this: { label: 'Husk', Icon: Brain, summarize: (a) => firstStr(a, ['text', 'content', 'note']) },
  read_brain_entry: { label: 'Læs brain-entry', Icon: Brain, summarize: (a) => firstStr(a, ['id', 'key']) },
  // Kanaler / besked
  discord_channel: { label: 'Discord', Icon: MessageSquare, summarize: (a) => firstStr(a, ['action', 'query', 'channel']) },
  // Billede / medie
  generate_image: { label: 'Generér billede', Icon: Image, summarize: (a) => firstStr(a, ['prompt']) },
  // Tid / planlægning
  list_scheduled_tasks: { label: 'Planlagte opgaver', Icon: Calendar, summarize: () => '' },
  // Notifikation
  notify: { label: 'Notifikation', Icon: Bell, summarize: (a) => firstStr(a, ['message', 'text']) },
  // Dispatch
  dispatch_to_claude_code: { label: 'Kode-dispatch', Icon: Cpu, summarize: (a) => firstStr(a, ['task', 'prompt', 'goal']) },
  dispatch_code_mode_task: { label: 'Kode-opgave', Icon: Cpu, summarize: (a) => firstStr(a, ['task', 'prompt', 'goal']) },
  read_model_config: { label: 'Model-konfig', Icon: Database, summarize: () => '' },
}

const GENERIC_KEYS = ['query', 'q', 'command', 'path', 'file_path', 'pattern', 'text', 'url', 'name', 'topic', 'prompt', 'action']

/** snake_case → Title Case. operator_-præfiks humaniseres væk. */
function titleCase(name: string): string {
  const base = name.replace(/^operator_/, '')
  return base
    .split('_')
    .filter(Boolean)
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ')
}

/** Slår et tool op. Ukendte tools får en Title-Case-label + generisk opsummering,
 *  så intet tool nogensinde står som rå funktionsnavn. */
export function lookupTool(name: string): ToolMeta {
  const hit = TOOL_REGISTRY[name]
  if (hit) return hit
  return {
    label: titleCase(name),
    Icon: Wrench,
    summarize: (a) => firstStr(a, GENERIC_KEYS),
  }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npx vitest run src/lib/toolRegistry.test.ts`
Expected: PASS (4 passed)

- [ ] **Step 5: Write the dev-helper generator**

Create `scripts/gen_tool_registry.cjs`:

```js
#!/usr/bin/env node
/* Dev-hjælper: rapportér hvilke backend-tools der mangler en kurateret entry i
 * toolRegistry.ts. Læser tool-navne fra et JSON-dump genereret af backend
 * (scripts/dump_tool_names.py > /tmp/tool_names.json) eller stdin. Ikke i test-
 * stien — ren rapport, så dækningen kan udvides over tid. */
const fs = require('fs')
const path = require('path')

const reg = fs.readFileSync(path.join(__dirname, '..', 'apps', 'jarvis-desk', 'src', 'lib', 'toolRegistry.ts'), 'utf8')
const curated = new Set([...reg.matchAll(/^\s{2}([a-z_]+):\s*\{/gm)].map((m) => m[1]))

let names = []
try {
  names = JSON.parse(fs.readFileSync(process.argv[2] || '/tmp/tool_names.json', 'utf8'))
} catch {
  console.error('Forventer en JSON-liste af tool-navne som argument (eller /tmp/tool_names.json).')
  process.exit(1)
}

const missing = names.filter((n) => !curated.has(n))
console.log(`${curated.size} kuraterede, ${missing.length} mangler kurateret entry (dækkes af Title-Case fallback):`)
missing.forEach((n) => console.log('  ' + n))
```

(Ingen test — ren rapport. Backend-navne kan dumpes med:
`/opt/conda/envs/ai/bin/python -c "import json; from core.tools.simple_tools import TOOL_DEFINITIONS; print(json.dumps([d['function']['name'] for d in TOOL_DEFINITIONS]))" > /tmp/tool_names.json`)

- [ ] **Step 6: Commit**

```bash
cd /media/projects/jarvis-v2 && git add apps/jarvis-desk/src/lib/toolRegistry.ts apps/jarvis-desk/src/lib/toolRegistry.test.ts scripts/gen_tool_registry.cjs
git commit -m "feat(desk): toolRegistry — pæne tool-navne + opsummering (Title-Case fallback = komplet dækning)"
```

---

## Task 7: Frontend — `ToolCard` bruger registry + diff-stat i hovedet

**Files:**
- Modify: `apps/jarvis-desk/src/components/rich/ToolCard.tsx`
- Modify: `apps/jarvis-desk/src/styles/app.css`
- Test: `apps/jarvis-desk/src/components/rich/ToolCard.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `src/components/rich/ToolCard.test.tsx`:

```tsx
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ToolCard } from './ToolCard'
import type { ContentBlock } from '../../lib/sseProtocol'

function block(over: Partial<Extract<ContentBlock, { type: 'tool_use' }>>): Extract<ContentBlock, { type: 'tool_use' }> {
  return { type: 'tool_use', id: 't1', name: 'web_search', input: {}, status: 'done', ...over }
}

describe('ToolCard', () => {
  it('shows pretty label + summary collapsed, not raw tool name', () => {
    render(<ToolCard block={block({ name: 'web_search', input: { query: 'vejr københavn' } })} density="compact" />)
    expect(screen.getByText('Websøgning')).toBeInTheDocument()
    expect(screen.getByText('vejr københavn')).toBeInTheDocument()
    expect(screen.queryByText('web_search')).toBeNull()
  })

  it('shows +N −M diff-stat for an edit collapsed', () => {
    render(<ToolCard block={block({ name: 'edit_file', input: { path: 'a.ts', old_string: 'a\nb', new_string: 'a\nc\nd' } })} density="compact" />)
    expect(screen.getByText(/\+\d+/)).toBeInTheDocument()
    expect(screen.getByText(/−\d+/)).toBeInTheDocument()
  })

  it('unknown tool gets Title-Case label', () => {
    render(<ToolCard block={block({ name: 'some_weird_tool', input: {} })} density="compact" />)
    expect(screen.getByText('Some Weird Tool')).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run src/components/rich/ToolCard.test.tsx`
Expected: FAIL — current ToolCard renders raw `block.name` ("web_search"), no diff-stat in head.

- [ ] **Step 3: Update ToolCard head to use registry + diff-stat**

In `src/components/rich/ToolCard.tsx`:

Replace the imports block at top:

```tsx
import { useState } from 'react'
import { Terminal, FilePen, FilePlus, FileText, Search, FolderTree, Check, X, Loader } from 'lucide-react'
import type { ContentBlock } from '../../lib/sseProtocol'
import { lineDiff } from '../../lib/diff'
import { lookupTool } from '../../lib/toolRegistry'
import { diffStat } from '../../lib/diffStat'
```

Replace the component body (lines 10-44, the `export function ToolCard` ... up to and including the closing `}`) with:

```tsx
export function ToolCard({
  block,
  density,
}: {
  block: Extract<ContentBlock, { type: 'tool_use' }>
  density: 'compact' | 'full'
}) {
  const [open, setOpen] = useState(density === 'full')
  const expanded = density === 'full' || open

  const args = parseArgs(block)
  const fam = toolFamily(block.name)
  const meta = lookupTool(block.name)
  const summary = meta.summarize(args, block.result)
  const ds = diffStat(block.name, args)
  const status = block.status ?? 'running'
  const Icon = meta.Icon

  return (
    <div className={`toolcard fam-${fam} status-${status}`}>
      <button
        type="button"
        className="toolcard-head"
        onClick={() => density === 'compact' && setOpen((o) => !o)}
      >
        <Icon size={13} className="toolcard-icon" />
        <span className="toolcard-name">{meta.label}</span>
        {summary && <span className="toolcard-summary">{summary}</span>}
        {ds && (
          <span className="toolcard-diffstat">
            <span className="git-add">+{ds.add}</span> <span className="git-del">−{ds.del}</span>
          </span>
        )}
        <StatusBadge status={status} />
      </button>
      {expanded && (
        <div className="toolcard-body">
          {renderBody(fam, args, block.result)}
        </div>
      )}
    </div>
  )
}
```

Then DELETE the now-unused `describeTool` function (lines ~69-80) and the `genericSummary` function (lines ~82-90) — they are replaced by the registry. Keep `toolFamily`, `parseArgs`, `pathOf`, `StatusBadge`, and `renderBody` (still used for the body). Remove `Wrench` from the lucide import (now unused; verify with tsc).

- [ ] **Step 4: Add diff-stat styling**

In `apps/jarvis-desk/src/styles/app.css`, add after the existing `.toolcard-status` rules:

```css
.toolcard-diffstat { margin-left: auto; font-family: ui-monospace, monospace; font-size: 11px; flex: 0 0 auto; }
.toolcard-diffstat .git-add { color: #6ee7a8; }
.toolcard-diffstat .git-del { color: #e2777a; }
/* når diff-stat er til stede, skub status-badge ud til kanten uden margin-auto-konflikt */
.toolcard-diffstat + .toolcard-status { margin-left: 8px; }
```

- [ ] **Step 5: Run test + tsc to verify it passes**

Run: `npx vitest run src/components/rich/ToolCard.test.tsx`
Expected: PASS (3 passed)

Run: `npx tsc -b`
Expected: ingen fejl. (Hvis "Wrench is declared but never read" → fjern det fra importen.)

- [ ] **Step 6: Commit**

```bash
cd /media/projects/jarvis-v2 && git add apps/jarvis-desk/src/components/rich/ToolCard.tsx apps/jarvis-desk/src/styles/app.css apps/jarvis-desk/src/components/rich/ToolCard.test.tsx
git commit -m "feat(desk): ToolCard viser pæn label + opsummering + diff-stat (uden klik)"
```

---

## Task 8: Frontend — `UiPanelWatcher` håndterer close

**Files:**
- Modify: `apps/jarvis-desk/src/lib/coworkApi.ts` (`UiPanelRequest.action`)
- Modify: `apps/jarvis-desk/src/components/UiPanelWatcher.tsx`
- Test: `apps/jarvis-desk/src/components/UiPanelWatcher.test.tsx`

- [ ] **Step 1: Add `action` to the client type**

In `src/lib/coworkApi.ts`, in the `UiPanelRequest` interface (line ~56), add the field:

```ts
export interface UiPanelRequest {
  id: string
  panel: 'preview' | 'right' | 'files'
  action?: 'open' | 'close'
  session_id: string
  detail: string
  status: string
  created_at: string
}
```

- [ ] **Step 2: Write the failing test**

Create `src/components/UiPanelWatcher.test.tsx`:

```tsx
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { PanelProvider } from '../contexts/PanelContext'
import { usePanel } from '../hooks/usePanel'
import { UiPanelWatcher } from './UiPanelWatcher'

const pending: unknown[] = []
vi.mock('../lib/coworkApi', () => ({
  getUiPanelPending: () => Promise.resolve(pending.splice(0, pending.length)),
  ackUiPanel: () => Promise.resolve(),
}))

let panelRef: ReturnType<typeof usePanel> | null = null
function Probe() { panelRef = usePanel(); return null }
const wrap = (ui: ReactNode) => render(<PanelProvider defaultWidth={400}><Probe />{ui}</PanelProvider>)
const cfg = { apiBaseUrl: 'http://t', authToken: 't' }

describe('UiPanelWatcher', () => {
  beforeEach(() => { panelRef = null; pending.length = 0 })

  it('close-request calls panel.close()', async () => {
    // åbn først
    pending.push({ id: 'p1', panel: 'preview', action: 'open', session_id: '', detail: 'x', status: 'pending', created_at: '' })
    wrap(<UiPanelWatcher config={cfg} />)
    await waitFor(() => expect(panelRef?.open).toBe(true))
    // så luk
    pending.push({ id: 'p2', panel: 'preview', action: 'close', session_id: '', detail: '', status: 'pending', created_at: '' })
    await waitFor(() => expect(panelRef?.open).toBe(false))
  })
})
```

- [ ] **Step 3: Run test to verify it fails**

Run: `npx vitest run src/components/UiPanelWatcher.test.tsx`
Expected: FAIL — watcher always opens; close never closes the panel.

- [ ] **Step 4: Handle close in the watcher**

In `src/components/UiPanelWatcher.tsx`, the watcher captures `panel.open_` via a ref. Add a ref for `panel.close` and branch on `req.action`. Replace the component body's refs + the loop:

Add a close-ref next to the open-ref:

```tsx
  const panel = usePanel()
  const openRef = useRef(panel.open_)
  openRef.current = panel.open_
  const closeRef = useRef(panel.close)
  closeRef.current = panel.close
  const busy = useRef(false)
```

Replace the `for (const req of pending) { ... }` body with:

```tsx
        for (const req of pending) {
          if (req.action === 'close') {
            closeRef.current()
          } else {
            openRef.current({
              kind: 'markdown',
              title: 'Jarvis åbnede et panel',
              content: req.detail || 'Jarvis bad om at åbne dette panel.',
            })
          }
          await ackUiPanel(config, req.id)
        }
```

- [ ] **Step 5: Run test + tsc to verify it passes**

Run: `npx vitest run src/components/UiPanelWatcher.test.tsx`
Expected: PASS

Run: `npx tsc -b`
Expected: ingen fejl.

- [ ] **Step 6: Commit**

```bash
cd /media/projects/jarvis-v2 && git add apps/jarvis-desk/src/lib/coworkApi.ts apps/jarvis-desk/src/components/UiPanelWatcher.tsx apps/jarvis-desk/src/components/UiPanelWatcher.test.tsx
git commit -m "feat(desk): UiPanelWatcher lukker panel ved action=close"
```

---

## Task 9: Fuld suite + deploy (sammen med app-self-control)

- [ ] **Step 1: Fuld backend-test**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_tool_chip_payload.py tests/test_ui_panel_store.py tests/test_ui_panel_tools.py tests/test_visible_runs_sse_v2.py -q -p no:cacheprovider`
Expected: alle PASS

- [ ] **Step 2: Fuld frontend-suite + tsc**

Working dir `apps/jarvis-desk`:
Run: `npx vitest run`
Expected: alle suiter grønne.
Run: `npx tsc -b`
Expected: ingen fejl.

- [ ] **Step 3: Deploy backend (kræver Bjørns ok — ikke autonomt)**

```bash
git push origin main && git push target main
```
Genstart `jarvis-api` (efter idle-bekræftelse) — så berigede tool-events + panel-close går live.

- [ ] **Step 4: Build + installér desk-app (i baggrund)**

Working dir `apps/jarvis-desk`:
```bash
npm run build && npx electron-builder --linux deb && sudo dpkg -i dist/*.deb
```

(Denne build bundter også app-self-control-arbejdet, som allerede er committed men ikke deployet.)

- [ ] **Step 5: Manuel end-to-end verifikation**

1. Kald et tool (fx stil et spørgsmål der trigger `web_search` eller `internal_api`).
2. Forvent: chip viser **pæn label** ("Websøgning") + **opsummering** + status **uden klik**.
3. Klik chip'en → folder ud med args + resultat.
4. Bed Jarvis redigere en fil → chip viser **`+N −M`** i enden.
5. Bed Jarvis åbne preview-panelet, så lukke det igen (`open_ui_panel action=close`) → panelet lukker.

---

## Notes for the implementer

- **conda:** alle Python-kald via `/opt/conda/envs/ai/bin/python`.
- **Coverage-gate:** nye/ændrede `core/`-moduler har matchende `tests/test_<modul>.py` (tool_chip_payload, ui_panel_store, ui_panel_tools). `visible_runs.py`/`visible_runs_sse_v2.py` har eksisterende test-filer.
- **Komplet dækning** = `lookupTool`-fallback giver enhver tool en Title-Case-label; registret enricher de hyppigste. Generatoren (`gen_tool_registry.cjs`) viser hvilke der mangler kuratering, så dækningen kan vokse uden kodeændringer i ToolCard.
- **--workers 1 frys-fælde:** ingen nye blokerende kald i async-ruter (helper'en er ren in-memory).
- **cwd-drift:** git-commits bruger `cd /media/projects/jarvis-v2` → husk at `cd apps/jarvis-desk` igen før næste `npx`-kommando.
