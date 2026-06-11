# jarvis-desk Preview-panel + Kontekst-ring — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Et trækbart preview/canvas-panel der åbner markdown/kode/interne filer i højre side af den aktive view (cross-mode), plus en backend-gated kontekst-fill ring.

**Architecture:** Mode-agnostisk `PanelContext` (reducer) styrer panel-state; `SplitLayout` giver trækbar split (overlay-fallback < 900px); ren `detectArtifacts` markerer panel-værdige blokke som "Åbn ↗"-affordances i `MessageRow`. Interne filer hentes via et path-jailed `GET /chat/file`. Kontekst-ringen læser et nyt `system_event kind=context` fra v2-streamen.

**Tech Stack:** React 19 + TypeScript, Vitest + @testing-library/react (jsdom), eksisterende rich-bibliotek (`CodeBlock`, `MarkdownRenderer`), FastAPI (backend fil-endpoint), pytest.

**Spec:** `docs/superpowers/specs/2026-06-11-jarvis-desk-preview-panel-design.md`

**Branch:** `feat/jarvis-desk-foundation` (samme branch). **Working dir:** `apps/jarvis-desk/` (backend-task i `apps/api/`).

**Kør tests:** `npm test` (frontend, fra `apps/jarvis-desk/`), `npx tsc -b --noEmit` (typecheck). Backend: `/opt/conda/envs/ai/bin/python -m pytest <fil> -v`.

---

## Filstruktur

| Fil | Ansvar |
|-----|--------|
| `src/lib/artifacts.ts` | `Artifact`/`ArtifactRef` typer + ren `detectArtifacts(blocks)` |
| `src/lib/artifacts.test.ts` | detektions-tests |
| `src/lib/panelReducer.ts` | ren `panelReducer` + actions + width-clamp |
| `src/lib/panelReducer.test.ts` | reducer-tests |
| `src/lib/panelStore.ts` | localStorage persist af `panelWidth` |
| `src/contexts/PanelContext.tsx` | provider der binder reducer + persist |
| `src/hooks/usePanel.ts` | hook til panel-state/actions |
| `src/components/panel/ArtifactPanel.tsx` | panel-shell (header + body-renderer) |
| `src/components/panel/SplitLayout.tsx` | trækbar split + overlay-fallback |
| `src/components/rich/ArtifactAffordance.tsx` | "Åbn ↗"-knap |
| `src/lib/api.ts` | `getFile(config, path)` (modify) |
| `src/components/rich/MessageRow.tsx` | wire affordances (modify) |
| `src/App.tsx` | mount PanelProvider + SplitLayout (modify) |
| `src/styles/app.css` | panel + split + affordance styling (modify) |
| `apps/api/jarvis_api/routes/chat.py` | `GET /chat/file` med path-jail (modify) |

---

## Fase 1 — Ren logik (UI-fri, testbar)

### Task 1: Artifact-typer + detectArtifacts

**Files:**
- Create: `apps/jarvis-desk/src/lib/artifacts.ts`
- Test: `apps/jarvis-desk/src/lib/artifacts.test.ts`

- [ ] **Step 1: Write the failing test**

```ts
// src/lib/artifacts.test.ts
import { describe, it, expect } from 'vitest'
import { detectArtifacts } from './artifacts'
import type { ContentBlock } from './sseProtocol'

const code = (lines: number) => Array.from({ length: lines }, (_, i) => `line ${i}`).join('\n')

describe('detectArtifacts', () => {
  it('markerer kodeblok >= 15 linjer som code-artifact', () => {
    const blocks: ContentBlock[] = [{ type: 'tool_use', id: 't', name: 'write', input: {}, result: code(20) }]
    // kode kommer typisk som tekst-fenced i text-blok; test begge veje
    const text: ContentBlock[] = [{ type: 'text', text: '```python\n' + code(20) + '\n```' }]
    expect(detectArtifacts(text)[0]).toMatchObject({ kind: 'code', language: 'python' })
  })

  it('ignorerer kort kodeblok (< 15 linjer)', () => {
    const blocks: ContentBlock[] = [{ type: 'text', text: '```js\n' + code(5) + '\n```' }]
    expect(detectArtifacts(blocks)).toEqual([])
  })

  it('markerer langt markdown-dok (>=40 linjer, >=2 headers)', () => {
    const md = '# Titel\n' + code(40) + '\n## Sektion\nmere'
    expect(detectArtifacts([{ type: 'text', text: md }])[0]).toMatchObject({ kind: 'markdown' })
  })

  it('ignorerer langt prosa uden headers', () => {
    expect(detectArtifacts([{ type: 'text', text: code(50) }])).toEqual([])
  })

  it('markerer intern fil-reference som file-artifact', () => {
    const refs = detectArtifacts([{ type: 'text', text: 'Se docs/superpowers/specs/x.md for detaljer' }])
    expect(refs.find((r) => r.kind === 'file')).toMatchObject({ kind: 'file', filePath: 'docs/superpowers/specs/x.md' })
  })

  it('ignorerer eksterne URLs (ikke fil)', () => {
    expect(detectArtifacts([{ type: 'text', text: 'https://example.com/a.md' }]).filter((r) => r.kind === 'file')).toEqual([])
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test -- artifacts` → Expected: FAIL ("detectArtifacts is not a function").

- [ ] **Step 3: Write minimal implementation**

```ts
// src/lib/artifacts.ts
import type { ContentBlock } from './sseProtocol'

export type ArtifactKind = 'markdown' | 'code' | 'file' // v2: 'mermaid' | 'html'

export interface Artifact {
  kind: ArtifactKind
  title: string
  language?: string
  content?: string   // inline (markdown/code)
  filePath?: string  // for 'file'
}

/** En detekteret reference, klar til at blive til et Artifact ved klik. */
export type ArtifactRef = Artifact

const CODE_MIN_LINES = 15
const MD_MIN_LINES = 40

// Interne sti-rødder vi tør linke (matcher backend path-jail).
const FILE_ROOTS = ['docs', 'workspace', 'core', 'apps', 'scripts']
const FILE_RE = new RegExp(
  `(?<![\\w/])((?:${FILE_ROOTS.join('|')})/[\\w./-]+\\.[a-z]{1,5})`,
  'g',
)

const fencedBlocks = (text: string): Array<{ lang: string; body: string }> => {
  const out: Array<{ lang: string; body: string }> = []
  const re = /```([\w-]*)\n([\s\S]*?)```/g
  let m
  while ((m = re.exec(text)) !== null) out.push({ lang: m[1] || '', body: m[2] ?? '' })
  return out
}

const headerCount = (text: string): number =>
  (text.match(/^#{1,6}\s/gm) ?? []).length

export function detectArtifacts(blocks: ContentBlock[]): ArtifactRef[] {
  const refs: ArtifactRef[] = []
  for (const b of blocks) {
    if (b.type !== 'text') continue
    // 1) fenced kodeblokke
    for (const { lang, body } of fencedBlocks(b.text)) {
      if (body.split('\n').length >= CODE_MIN_LINES) {
        refs.push({ kind: 'code', title: lang ? `${lang}-kode` : 'Kode', language: lang || 'text', content: body })
      }
    }
    // 2) langt markdown-dok (linjer + headers) — kun hvis ikke domineret af kode
    const lines = b.text.split('\n').length
    if (lines >= MD_MIN_LINES && headerCount(b.text) >= 2) {
      const title = (b.text.match(/^#\s+(.+)$/m)?.[1] ?? 'Dokument').trim()
      refs.push({ kind: 'markdown', title, content: b.text })
    }
    // 3) interne fil-referencer
    for (const m of b.text.matchAll(FILE_RE)) {
      const filePath = m[1]
      if (!refs.some((r) => r.kind === 'file' && r.filePath === filePath)) {
        refs.push({ kind: 'file', title: filePath.split('/').pop() ?? filePath, filePath })
      }
    }
  }
  return refs
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test -- artifacts` → Expected: PASS (6/6). Kør også `npx tsc -b --noEmit` → 0 fejl.

- [ ] **Step 5: Commit**

```bash
git add src/lib/artifacts.ts src/lib/artifacts.test.ts
git commit -m "feat(jarvis-desk): detectArtifacts — ren artifact-detektion (kode/markdown/fil)"
```

---

### Task 2: panelReducer

**Files:**
- Create: `apps/jarvis-desk/src/lib/panelReducer.ts`
- Test: `apps/jarvis-desk/src/lib/panelReducer.test.ts`

- [ ] **Step 1: Write the failing test**

```ts
// src/lib/panelReducer.test.ts
import { describe, it, expect } from 'vitest'
import { panelReducer, initialPanelState, MIN_WIDTH } from './panelReducer'
import type { Artifact } from './artifacts'

const art: Artifact = { kind: 'markdown', title: 'T', content: '# x' }

describe('panelReducer', () => {
  it('open sætter open=true + artifact', () => {
    const s = panelReducer(initialPanelState(420), { type: 'open', artifact: art })
    expect(s.open).toBe(true)
    expect(s.artifact).toBe(art)
  })
  it('close nulstiller open men beholder width', () => {
    const opened = panelReducer(initialPanelState(420), { type: 'open', artifact: art })
    const s = panelReducer(opened, { type: 'close' })
    expect(s.open).toBe(false)
    expect(s.width).toBe(420)
  })
  it('replace skifter artifact uden at lukke', () => {
    const opened = panelReducer(initialPanelState(420), { type: 'open', artifact: art })
    const art2: Artifact = { kind: 'code', title: 'C', language: 'js', content: 'a' }
    const s = panelReducer(opened, { type: 'replace', artifact: art2 })
    expect(s.open).toBe(true)
    expect(s.artifact).toBe(art2)
  })
  it('resize clamper til MIN_WIDTH nedadtil', () => {
    const s = panelReducer(initialPanelState(420), { type: 'resize', width: 100 })
    expect(s.width).toBe(MIN_WIDTH)
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test -- panelReducer` → FAIL ("panelReducer is not a function").

- [ ] **Step 3: Write minimal implementation**

```ts
// src/lib/panelReducer.ts
import type { Artifact } from './artifacts'

export const MIN_WIDTH = 320
export const MAX_WIDTH_FRACTION = 0.7 // af vinduesbredden — clamps i context, ikke her

export interface PanelState {
  open: boolean
  width: number
  artifact: Artifact | null
}

export type PanelAction =
  | { type: 'open'; artifact: Artifact }
  | { type: 'replace'; artifact: Artifact }
  | { type: 'close' }
  | { type: 'resize'; width: number }

export function initialPanelState(width: number): PanelState {
  return { open: false, width: Math.max(MIN_WIDTH, width), artifact: null }
}

export function panelReducer(state: PanelState, action: PanelAction): PanelState {
  switch (action.type) {
    case 'open':
    case 'replace':
      return { ...state, open: true, artifact: action.artifact }
    case 'close':
      return { ...state, open: false }
    case 'resize':
      return { ...state, width: Math.max(MIN_WIDTH, action.width) }
    default:
      return state
  }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test -- panelReducer` → PASS (4/4).

- [ ] **Step 5: Commit**

```bash
git add src/lib/panelReducer.ts src/lib/panelReducer.test.ts
git commit -m "feat(jarvis-desk): panelReducer — open/close/replace/resize + width-clamp"
```

---

## Fase 2 — Persist + Context + hook

### Task 3: panelStore (localStorage persist)

**Files:**
- Create: `apps/jarvis-desk/src/lib/panelStore.ts`
- Test: `apps/jarvis-desk/src/lib/panelStore.test.ts`

- [ ] **Step 1: Write the failing test**

```ts
// src/lib/panelStore.test.ts
import { describe, it, expect, beforeEach } from 'vitest'
import { loadPanelWidth, savePanelWidth } from './panelStore'

beforeEach(() => localStorage.clear())

describe('panelStore', () => {
  it('returnerer default når intet er gemt', () => {
    expect(loadPanelWidth(500)).toBe(500)
  })
  it('gemmer og henter width', () => {
    savePanelWidth(640)
    expect(loadPanelWidth(500)).toBe(640)
  })
  it('ignorerer korrupt værdi', () => {
    localStorage.setItem('jarvis-desk:panelWidth', 'abc')
    expect(loadPanelWidth(500)).toBe(500)
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test -- panelStore` → FAIL.

- [ ] **Step 3: Write minimal implementation**

```ts
// src/lib/panelStore.ts
const KEY = 'jarvis-desk:panelWidth'

export function loadPanelWidth(fallback: number): number {
  try {
    const raw = localStorage.getItem(KEY)
    if (raw === null) return fallback
    const n = Number(raw)
    return Number.isFinite(n) && n > 0 ? n : fallback
  } catch {
    return fallback
  }
}

export function savePanelWidth(width: number): void {
  try {
    localStorage.setItem(KEY, String(Math.round(width)))
  } catch {
    /* ignoreres — UI-præference, ikke kritisk */
  }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test -- panelStore` → PASS (3/3).

- [ ] **Step 5: Commit**

```bash
git add src/lib/panelStore.ts src/lib/panelStore.test.ts
git commit -m "feat(jarvis-desk): panelStore — localStorage persist af panel-bredde"
```

---

### Task 4: PanelContext + usePanel

**Files:**
- Create: `apps/jarvis-desk/src/contexts/PanelContext.tsx`
- Create: `apps/jarvis-desk/src/hooks/usePanel.ts`
- Test: `apps/jarvis-desk/src/contexts/PanelContext.test.tsx`

- [ ] **Step 1: Write the failing test**

```tsx
// src/contexts/PanelContext.test.tsx
import { describe, it, expect } from 'vitest'
import { render, screen, act } from '@testing-library/react'
import { PanelProvider } from './PanelContext'
import { usePanel } from '../hooks/usePanel'

function Probe() {
  const p = usePanel()
  return (
    <div>
      <span data-testid="open">{String(p.open)}</span>
      <span data-testid="title">{p.artifact?.title ?? '-'}</span>
      <button onClick={() => p.open_({ kind: 'markdown', title: 'Spec', content: '# x' })}>open</button>
      <button onClick={() => p.close()}>close</button>
    </div>
  )
}

describe('PanelContext', () => {
  it('open_ åbner med artifact, close lukker', () => {
    render(<PanelProvider defaultWidth={480}><Probe /></PanelProvider>)
    expect(screen.getByTestId('open').textContent).toBe('false')
    act(() => { screen.getByText('open').click() })
    expect(screen.getByTestId('open').textContent).toBe('true')
    expect(screen.getByTestId('title').textContent).toBe('Spec')
    act(() => { screen.getByText('close').click() })
    expect(screen.getByTestId('open').textContent).toBe('false')
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test -- PanelContext` → FAIL.

- [ ] **Step 3: Write minimal implementation**

```tsx
// src/contexts/PanelContext.tsx
import { createContext, useCallback, useMemo, useReducer, type ReactNode } from 'react'
import { panelReducer, initialPanelState } from '../lib/panelReducer'
import { loadPanelWidth, savePanelWidth } from '../lib/panelStore'
import type { Artifact } from '../lib/artifacts'

export interface PanelContextValue {
  open: boolean
  width: number
  artifact: Artifact | null
  open_: (artifact: Artifact) => void
  close: () => void
  resize: (width: number) => void
}

export const PanelContext = createContext<PanelContextValue | null>(null)

export function PanelProvider({ defaultWidth, children }: { defaultWidth: number; children: ReactNode }) {
  const [state, dispatch] = useReducer(panelReducer, loadPanelWidth(defaultWidth), initialPanelState)

  const open_ = useCallback((artifact: Artifact) => {
    dispatch({ type: state.open ? 'replace' : 'open', artifact })
  }, [state.open])
  const close = useCallback(() => dispatch({ type: 'close' }), [])
  const resize = useCallback((width: number) => {
    dispatch({ type: 'resize', width })
    savePanelWidth(width)
  }, [])

  const value = useMemo<PanelContextValue>(
    () => ({ open: state.open, width: state.width, artifact: state.artifact, open_, close, resize }),
    [state.open, state.width, state.artifact, open_, close, resize],
  )
  return <PanelContext.Provider value={value}>{children}</PanelContext.Provider>
}
```

> **Note (TDD-fix forventet):** `useCallback`/`useReducer` skal importeres fra `'react'` med korrekt casing (`useCallback`, ikke `useCallback`→`useCallback`). Hvis tsc klager over `useReducer(panelReducer, loadPanelWidth(...), initialPanelState)`-overload, brug 3-arg lazy-init formen: `useReducer(panelReducer, loadPanelWidth(defaultWidth), (w) => initialPanelState(w))`.

```ts
// src/hooks/usePanel.ts
import { useContext } from 'react'
import { PanelContext, type PanelContextValue } from '../contexts/PanelContext'

export function usePanel(): PanelContextValue {
  const ctx = useContext(PanelContext)
  if (!ctx) throw new Error('usePanel skal bruges inde i <PanelProvider>')
  return ctx
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test -- PanelContext` → PASS. `npx tsc -b --noEmit` → 0 fejl (ret import-casing til `useCallback` hvis nødvendigt).

- [ ] **Step 5: Commit**

```bash
git add src/contexts/PanelContext.tsx src/hooks/usePanel.ts src/contexts/PanelContext.test.tsx
git commit -m "feat(jarvis-desk): PanelContext + usePanel (mode-agnostisk panel-state)"
```

---

## Fase 3 — Panel-UI

### Task 5: ArtifactPanel (markdown + kode)

**Files:**
- Create: `apps/jarvis-desk/src/components/panel/ArtifactPanel.tsx`
- Test: `apps/jarvis-desk/src/components/panel/ArtifactPanel.test.tsx`

- [ ] **Step 1: Write the failing test**

```tsx
// src/components/panel/ArtifactPanel.test.tsx
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ArtifactPanel } from './ArtifactPanel'

describe('ArtifactPanel', () => {
  it('viser titel + markdown-indhold', () => {
    render(<ArtifactPanel artifact={{ kind: 'markdown', title: 'Min Spec', content: '# Overskrift' }} onClose={() => {}} />)
    expect(screen.getByText('Min Spec')).toBeTruthy()
    expect(screen.getByRole('heading', { name: 'Overskrift' })).toBeTruthy()
  })
  it('kalder onClose når luk klikkes', () => {
    const onClose = vi.fn()
    render(<ArtifactPanel artifact={{ kind: 'code', title: 'a.js', language: 'js', content: 'const x=1' }} onClose={onClose} />)
    screen.getByLabelText('Luk panel').click()
    expect(onClose).toHaveBeenCalled()
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test -- ArtifactPanel` → FAIL.

- [ ] **Step 3: Write minimal implementation**

```tsx
// src/components/panel/ArtifactPanel.tsx
import { X, FileText, Code2, File } from 'lucide-react'
import type { Artifact } from '../../lib/artifacts'
import { MarkdownRenderer } from '../rich/MarkdownRenderer'
import { CodeBlock } from '../rich/CodeBlock'

const ICON = { markdown: FileText, code: Code2, file: File } as const

/** Panel-shell: header (ikon + titel + luk) + body renderet efter artifact.kind.
 *  'file' håndteres i Task 10 (henter indhold async). */
export function ArtifactPanel({ artifact, onClose }: { artifact: Artifact; onClose: () => void }) {
  const Icon = ICON[artifact.kind] ?? File
  return (
    <div className="artifact-panel">
      <div className="artifact-head">
        <Icon size={14} /> <span className="artifact-title">{artifact.title}</span>
        <button type="button" className="artifact-close" aria-label="Luk panel" onClick={onClose}>
          <X size={15} />
        </button>
      </div>
      <div className="artifact-body">
        {artifact.kind === 'markdown' && <MarkdownRenderer text={artifact.content ?? ''} streaming={false} />}
        {artifact.kind === 'code' && <CodeBlock code={artifact.content ?? ''} lang={artifact.language ?? 'text'} />}
      </div>
    </div>
  )
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test -- ArtifactPanel` → PASS.

- [ ] **Step 5: Commit**

```bash
git add src/components/panel/ArtifactPanel.tsx src/components/panel/ArtifactPanel.test.tsx
git commit -m "feat(jarvis-desk): ArtifactPanel — markdown/kode-renderer + header"
```

---

### Task 6: SplitLayout (trækbar split + overlay-fallback) + CSS

**Files:**
- Create: `apps/jarvis-desk/src/components/panel/SplitLayout.tsx`
- Test: `apps/jarvis-desk/src/components/panel/SplitLayout.test.tsx`
- Modify: `apps/jarvis-desk/src/styles/app.css`

- [ ] **Step 1: Write the failing test**

```tsx
// src/components/panel/SplitLayout.test.tsx
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { SplitLayout } from './SplitLayout'

describe('SplitLayout', () => {
  it('viser kun main når panel er lukket', () => {
    render(<SplitLayout open={false} width={400} onResize={() => {}} panel={<div>PANEL</div>}><div>MAIN</div></SplitLayout>)
    expect(screen.getByText('MAIN')).toBeTruthy()
    expect(screen.queryByText('PANEL')).toBeNull()
  })
  it('viser både main, håndtag og panel når åbent', () => {
    render(<SplitLayout open width={400} onResize={() => {}} panel={<div>PANEL</div>}><div>MAIN</div></SplitLayout>)
    expect(screen.getByText('MAIN')).toBeTruthy()
    expect(screen.getByText('PANEL')).toBeTruthy()
    expect(screen.getByRole('separator')).toBeTruthy()
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test -- SplitLayout` → FAIL.

- [ ] **Step 3: Write minimal implementation**

```tsx
// src/components/panel/SplitLayout.tsx
import { useEffect, useRef, useState, type ReactNode } from 'react'
import { MAX_WIDTH_FRACTION, MIN_WIDTH } from '../../lib/panelReducer'

const OVERLAY_BELOW_PX = 900

/** Horisontal split: children (main) til venstre, panel til højre, med trækbart
 *  håndtag. Under OVERLAY_BELOW_PX falder panelet tilbage til drawer-overlay. */
export function SplitLayout({
  open, width, onResize, panel, children,
}: {
  open: boolean
  width: number
  onResize: (w: number) => void
  panel: ReactNode
  children: ReactNode
}) {
  const rootRef = useRef<HTMLDivElement>(null)
  const [dragging, setDragging] = useState(false)
  const [overlay, setOverlay] = useState(false)

  useEffect(() => {
    const check = () => setOverlay((rootRef.current?.clientWidth ?? window.innerWidth) < OVERLAY_BELOW_PX)
    check()
    window.addEventListener('resize', check)
    return () => window.removeEventListener('resize', check)
  }, [])

  useEffect(() => {
    if (!dragging) return
    const onMove = (e: MouseEvent) => {
      const root = rootRef.current
      if (!root) return
      const rootW = root.clientWidth
      const fromRight = root.getBoundingClientRect().right - e.clientX
      const clamped = Math.max(MIN_WIDTH, Math.min(fromRight, rootW * MAX_WIDTH_FRACTION))
      onResize(clamped)
    }
    const onUp = () => setDragging(false)
    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup', onUp)
    return () => { window.removeEventListener('mousemove', onMove); window.removeEventListener('mouseup', onUp) }
  }, [dragging, onResize])

  const panelWidth = overlay ? undefined : width
  return (
    <div className={`split-root ${open ? 'split-open' : ''} ${overlay ? 'split-overlay' : ''}`} ref={rootRef}>
      <div className="split-main">{children}</div>
      {open && !overlay && (
        <div
          role="separator"
          aria-orientation="vertical"
          className={`split-handle ${dragging ? 'dragging' : ''}`}
          onMouseDown={() => setDragging(true)}
        />
      )}
      {open && (
        <div className="split-panel" style={panelWidth ? { width: panelWidth } : undefined}>
          {panel}
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 4: Add CSS**

Tilføj i `src/styles/app.css` (efter `.chatview`-blokken):

```css
/* ── Preview-panel / split ── */
.split-root { display: flex; flex: 1; min-width: 0; min-height: 0; position: relative; }
.split-main { flex: 1; min-width: 0; display: flex; flex-direction: column; }
.split-handle {
  width: 5px; cursor: col-resize; flex: 0 0 auto; background: transparent;
  border-left: 1px solid var(--line); transition: background 0.12s;
}
.split-handle:hover, .split-handle.dragging { background: var(--accent); border-left-color: var(--accent); }
.split-panel {
  flex: 0 0 auto; min-width: 0; display: flex; flex-direction: column;
  background: var(--bg-1); border-left: 1px solid var(--line);
}
/* overlay-fallback under 900px */
.split-overlay .split-panel {
  position: absolute; right: 0; top: 0; bottom: 0; width: min(80%, 560px);
  box-shadow: -8px 0 24px rgba(0,0,0,0.4); z-index: 40;
}
.artifact-panel { display: flex; flex-direction: column; height: 100%; min-height: 0; }
.artifact-head {
  display: flex; align-items: center; gap: 8px; flex: 0 0 auto;
  padding: 10px 12px; border-bottom: 1px solid var(--line); font-size: 13px; color: var(--fg-2);
}
.artifact-title { color: var(--fg-1); font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; flex: 1; }
.artifact-close { background: none; border: none; color: var(--fg-3); cursor: pointer; display: grid; place-items: center; width: 26px; height: 26px; border-radius: 5px; }
.artifact-close:hover { background: var(--bg-3); color: var(--fg-1); }
.artifact-body { flex: 1; min-height: 0; overflow-y: auto; overflow-x: hidden; padding: 16px 18px; scrollbar-width: none; }
.artifact-body::-webkit-scrollbar { width: 0; }
```

- [ ] **Step 5: Run test + typecheck + commit**

Run: `npm test -- SplitLayout` → PASS. `npx tsc -b --noEmit` → 0.

```bash
git add src/components/panel/SplitLayout.tsx src/components/panel/SplitLayout.test.tsx src/styles/app.css
git commit -m "feat(jarvis-desk): SplitLayout — trækbar split + overlay-fallback + panel-CSS"
```

---

## Fase 4 — Wire ind i shell + affordances → CHECK-IN

### Task 7: ArtifactAffordance + wire i MessageRow

**Files:**
- Create: `apps/jarvis-desk/src/components/rich/ArtifactAffordance.tsx`
- Modify: `apps/jarvis-desk/src/components/rich/MessageRow.tsx`
- Modify: `apps/jarvis-desk/src/components/shell/shell.test.tsx` (hvis MessageRow-render asserts brydes)

- [ ] **Step 1: Write the failing test**

```tsx
// tilføj i src/components/rich/MessageRow.test.tsx
import { vi } from 'vitest'
it('viser "Åbn"-affordance for langt markdown-svar', () => {
  const long = '# Titel\n' + Array.from({ length: 45 }, (_, i) => `linje ${i}`).join('\n') + '\n## Sektion\nx'
  render(
    <PanelProbe>
      <MessageRow role="assistant" blocks={[{ type: 'text', text: long }]} density="compact" streaming={false} />
    </PanelProbe>,
  )
  expect(screen.getByRole('button', { name: /åbn/i })).toBeTruthy()
})
```

(Tilføj en lille `PanelProbe`-wrapper i test-filen der rendrer `<PanelProvider defaultWidth={400}>{children}</PanelProvider>`.)

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test -- MessageRow` → FAIL (ingen knap).

- [ ] **Step 3: Write minimal implementation**

```tsx
// src/components/rich/ArtifactAffordance.tsx
import { ArrowUpRight } from 'lucide-react'
import type { Artifact } from '../../lib/artifacts'
import { usePanel } from '../../hooks/usePanel'

export function ArtifactAffordance({ artifact }: { artifact: Artifact }) {
  const panel = usePanel()
  return (
    <button type="button" className="artifact-affordance" onClick={() => panel.open_(artifact)}>
      <ArrowUpRight size={13} /> Åbn {artifact.title}
    </button>
  )
}
```

I `MessageRow.tsx` — efter `BlocksRenderer` i jarvis-grenen, kør detektion på blocks og render affordances (kun for afsluttede beskeder, ikke streaming):

```tsx
// top af filen
import { detectArtifacts } from '../../lib/artifacts'
import { ArtifactAffordance } from './ArtifactAffordance'

// i MessageRowImpl, jarvis-grenen, efter <BlocksRenderer .../>:
{!streaming && detectArtifacts(blocks).map((a, i) => (
  <ArtifactAffordance key={`${a.kind}-${i}`} artifact={a} />
))}
```

Tilføj CSS i `app.css`:

```css
.artifact-affordance {
  display: inline-flex; align-items: center; gap: 5px; margin: 6px 0 0;
  background: var(--bg-2); border: 1px solid var(--line); color: var(--fg-2);
  border-radius: 7px; padding: 4px 9px; font-size: 12px; cursor: pointer;
}
.artifact-affordance:hover { background: var(--bg-3); color: var(--fg-1); border-color: var(--accent); }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test -- MessageRow` → PASS. Kør hele suiten `npm test` → grøn.

- [ ] **Step 5: Commit**

```bash
git add src/components/rich/ArtifactAffordance.tsx src/components/rich/MessageRow.tsx src/components/rich/MessageRow.test.tsx src/styles/app.css
git commit -m "feat(jarvis-desk): artifact-affordances i MessageRow ('Åbn ↗')"
```

---

### Task 8: Mount PanelProvider + SplitLayout i App-shell → CHECK-IN

**Files:**
- Modify: `apps/jarvis-desk/src/App.tsx`

- [ ] **Step 1: Wrap app i PanelProvider + læg SplitLayout om den aktive view**

I `App.tsx`: importer `PanelProvider`, `usePanel`, `SplitLayout`, `ArtifactPanel`. Wrap roden i `<PanelProvider defaultWidth={480}>`. Lav en lille inner-komponent der læser `usePanel()` og lægger `<SplitLayout>` rundt om `<main className="main">`-indholdet:

```tsx
function ShellWithPanel({ children }: { children: ReactNode }) {
  const panel = usePanel()
  return (
    <SplitLayout
      open={panel.open}
      width={panel.width}
      onResize={panel.resize}
      panel={panel.artifact ? <ArtifactPanel artifact={panel.artifact} onClose={panel.close} /> : null}
    >
      {children}
    </SplitLayout>
  )
}
```

Brug `<ShellWithPanel>` rundt om view-switch'en (ChatView/CoworkView/CodeView) inde i `<main>`. PanelProvider ligger yderst (så den deles på tværs af modes).

- [ ] **Step 2: Verify**

Run: `npm test` → grøn. `npx tsc -b --noEmit` → 0. Manuel: reload appen, send et langt svar fra Jarvis, klik "Åbn ↗" → panel åbner i højre side, træk håndtaget → bredden ændres, luk → chat fuld bredde.

- [ ] **Step 3: Commit**

```bash
git add src/App.tsx
git commit -m "feat(jarvis-desk): mount PanelProvider + SplitLayout i app-shell (cross-mode)"
```

**→ CHECK-IN med Bjørn:** panel-mekanisme + split + affordances + markdown/kode live. Vis det, få feedback før fil-endpoint.

---

## Fase 5 — Interne filer (backend + klient)

### Task 9: Backend GET /chat/file med path-jail

**Files:**
- Modify: `apps/api/jarvis_api/routes/chat.py`
- Test: `apps/api/tests/test_chat_file.py` (create)

- [ ] **Step 1: Write the failing test**

```python
# apps/api/tests/test_chat_file.py
import pytest
from fastapi.testclient import TestClient
from apps.api.jarvis_api.app import app

client = TestClient(app)

def test_reads_whitelisted_doc():
    r = client.get("/chat/file", params={"path": "docs/superpowers/specs/2026-06-11-jarvis-desk-preview-panel-design.md"})
    assert r.status_code == 200
    assert "Preview-panel" in r.json()["content"]

def test_rejects_path_traversal():
    r = client.get("/chat/file", params={"path": "../../etc/passwd"})
    assert r.status_code == 403

def test_rejects_outside_whitelist():
    r = client.get("/chat/file", params={"path": "/etc/hosts"})
    assert r.status_code == 403

def test_404_for_missing_whitelisted():
    r = client.get("/chat/file", params={"path": "docs/does-not-exist-xyz.md"})
    assert r.status_code == 404
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/opt/conda/envs/ai/bin/python -m pytest apps/api/tests/test_chat_file.py -v` → FAIL (404 route mangler).

- [ ] **Step 3: Write minimal implementation**

Tilføj i `apps/api/jarvis_api/routes/chat.py` (genbrug repo-rod-resolver + path-jail mønster fra `operator_read_file`/`dispatch_to_claude_code`):

```python
from pathlib import Path
from fastapi import HTTPException, Query

_FILE_ROOTS = ("docs", "workspace", "core", "apps", "scripts")
_LANG_BY_EXT = {".py": "python", ".ts": "typescript", ".tsx": "tsx", ".js": "javascript",
                ".json": "json", ".md": "markdown", ".css": "css", ".sh": "bash"}

def _repo_root() -> Path:
    # chat.py ligger i apps/api/jarvis_api/routes/ → fire niveauer op til repo-rod
    return Path(__file__).resolve().parents[4]

@router.get("/file")
async def chat_read_file(path: str = Query(...)) -> dict:
    root = _repo_root()
    candidate = (root / path).resolve()
    # path-jail: skal ligge under en whitelisted rod inde i repoet
    try:
        rel = candidate.relative_to(root)
    except ValueError:
        raise HTTPException(status_code=403, detail="uden for jail")
    if rel.parts and rel.parts[0] not in _FILE_ROOTS:
        raise HTTPException(status_code=403, detail="ikke-whitelisted rod")
    if not candidate.is_file():
        raise HTTPException(status_code=404, detail="ikke fundet")
    content = candidate.read_text(encoding="utf-8", errors="replace")
    return {"path": path, "content": content, "language": _LANG_BY_EXT.get(candidate.suffix, "text")}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `/opt/conda/envs/ai/bin/python -m pytest apps/api/tests/test_chat_file.py -v` → PASS (4/4).

- [ ] **Step 5: Commit**

```bash
git add apps/api/jarvis_api/routes/chat.py apps/api/tests/test_chat_file.py
git commit -m "feat(api): GET /chat/file med path-jail (whitelisted rødder) til preview-panel"
```

---

### Task 10: Klient getFile + 'file'-rendering i ArtifactPanel

**Files:**
- Modify: `apps/jarvis-desk/src/lib/api.ts`
- Modify: `apps/jarvis-desk/src/components/panel/ArtifactPanel.tsx`
- Test: `apps/jarvis-desk/src/components/panel/ArtifactPanel.test.tsx` (udvid)

- [ ] **Step 1: Write the failing test**

```tsx
// udvid ArtifactPanel.test.tsx
import { vi } from 'vitest'
it('henter og viser fil-indhold for file-artifact', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(
    JSON.stringify({ path: 'docs/x.md', content: '# Fil-titel', language: 'markdown' }),
    { status: 200, headers: { 'content-type': 'application/json' } },
  )))
  render(<ArtifactPanel artifact={{ kind: 'file', title: 'x.md', filePath: 'docs/x.md' }} onClose={() => {}} config={{ apiBaseUrl: 'http://t', authToken: 't' }} />)
  expect(await screen.findByRole('heading', { name: 'Fil-titel' })).toBeTruthy()
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test -- ArtifactPanel` → FAIL.

- [ ] **Step 3: Write minimal implementation**

I `api.ts`:

```ts
export async function getFile(config: ApiConfig, path: string): Promise<{ path: string; content: string; language: string }> {
  return apiFetch(config, `/chat/file?path=${encodeURIComponent(path)}`)
}
```

I `ArtifactPanel.tsx` — tilføj `config`-prop (valgfri) + async fetch for `kind === 'file'`:

```tsx
import { useEffect, useState } from 'react'
import { getFile, type ApiConfig } from '../../lib/api'

// signatur:
export function ArtifactPanel({ artifact, onClose, config }: { artifact: Artifact; onClose: () => void; config?: ApiConfig }) {
  const [fileData, setFileData] = useState<{ content: string; language: string } | null>(null)
  const [error, setError] = useState<string | null>(null)
  useEffect(() => {
    setFileData(null); setError(null)
    if (artifact.kind === 'file' && artifact.filePath && config) {
      getFile(config, artifact.filePath)
        .then((d) => setFileData({ content: d.content, language: d.language }))
        .catch(() => setError('Kunne ikke hente filen'))
    }
  }, [artifact, config])
  // ... i body, for kind === 'file':
  // {error ? <div className="artifact-error">{error}</div>
  //  : !fileData ? <div className="artifact-loading">Henter…</div>
  //  : fileData.language === 'markdown' ? <MarkdownRenderer text={fileData.content} streaming={false} />
  //  : <CodeBlock code={fileData.content} lang={fileData.language} />}
}
```

Send `config` med fra `App.tsx`' `ShellWithPanel` (fra `useSettings()`): `<ArtifactPanel ... config={settings ? { apiBaseUrl: settings.apiBaseUrl, authToken: settings.authToken } : undefined} />`.

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test -- ArtifactPanel` → PASS. `npx tsc -b --noEmit` → 0.

- [ ] **Step 5: Commit**

```bash
git add src/lib/api.ts src/components/panel/ArtifactPanel.tsx src/components/panel/ArtifactPanel.test.tsx src/App.tsx
git commit -m "feat(jarvis-desk): interne fil-artifacts henter via GET /chat/file og renderes i panel"
```

**→ v1-kerne komplet** (A+B+C+D). Reload + manuel verifikation: langt svar → affordance → panel; fil-reference → klik → fil-indhold i panel.

---

## Fase 6 — (Senere) Mermaid/HTML i panel

Bygges når v1-kernen er bekræftet. Skitse (egne TDD-tasks når vi tager den):
- Udvid `ArtifactKind` med `'mermaid' | 'html'`; `detectArtifacts` markerer ` ```mermaid ` og ` ```html ` fenced-blokke.
- `ArtifactPanel` renderer mermaid via eksisterende `MermaidBlock`; HTML i `<iframe sandbox>` med saniteret indhold (genbrug `sanitize.ts`-politik, ingen scripts, ingen ekstern navigation).
- Sikkerheds-tests: ingen `<script>` overlever, `file:`/`javascript:` blokeres.

## Fase 7 — (Backend-gated) Kontekst-ring

Bygges når backend sender `context`-event. Tasks når vi tager den:
1. **Backend:** v2-stream-generator emitterer `event: system_event` med `{"kind":"context","payload":{"used_tokens":N,"limit":M,"compacted":bool}}` ved `message_start` og når `_maybe_compact_agentic_messages` komprimerer. (`estimate_messages_tokens` + `context_run_compact_threshold_tokens`.)
2. **streamReducer:** ny `context: { usedTokens, limit, compacted } | null`-felt + `system_event kind=context`-case (parallelt med `kind=run`/`kind=working_step`). Test: event → felt sat.
3. **ContextRing:** SVG-ring i chat-header (venstre for `ConnectionPill`). Ren `ringColor(pct)`-funktion: `<0.6` blå, `<0.85` gul, ellers rød. Test grænseværdier 0.6/0.85. Compaction-pulse-klasse når `compacted` skifter til true. Tooltip `{used}/{limit}`.

---

## Self-Review (udført)

**Spec-dækning:** A→Task 4-8, B→Task 1+7, C→Task 5+10, D→Task 9-10, E→Fase 7, mermaid/HTML→Fase 6. Alle spec-dele har tasks. ✓
**Type-konsistens:** `Artifact`/`ArtifactKind` defineret i Task 1, brugt konsistent i 4/5/7/10. `panelReducer`-actions matcher `PanelContext`-kald. `getFile`-retur matcher `ArtifactPanel`-forbrug. ✓
**Placeholders:** Ingen TBD/TODO; alle kode-steps har konkret kode. Fase 6/7 er bevidst skitser (deferred scope), ikke v1-tasks. ✓
