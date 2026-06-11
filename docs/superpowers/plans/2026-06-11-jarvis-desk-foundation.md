# jarvis-desk Foundation (App-shell + Rich-rendering) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Byg det prod-grade fundament for jarvis-desk — contexts/hooks state-lag, density-aware rich-rendering bibliotek, liveness-state-maskine, og app-shell — så Chat-mode virker og Cowork/Code/Memory/Scheduling kan udfyldes senere uden at røre fundamentet.

**Architecture:** React Context + custom hooks (ingen ekstern state-lib). Tre contexts (Settings/Session/Stream) med forskellige livscyklusser. Ren reducer `(state, v2event) → state` som testbar kerne. Density-aware rich-komponenter delt på tværs af modes. Genbruger eksisterende `streamClient.ts`/`api.ts` med målrettede R1-R3-ændringer.

**Tech Stack:** Electron 33 + Vite 5 + React 19 + TypeScript 5. Vitest + @testing-library/react til test. Shiki (code), react-markdown + remark-gfm (markdown/tabeller), mermaid + katex (lazy). Taler `/chat/stream/v2` (Anthropic-style SSE).

**Specs (autoritative):**
- `docs/superpowers/specs/2026-06-11-jarvis-desk-foundation-design.md` — arkitektur, R1-R3, reconcile-state-maskine
- `docs/superpowers/specs/2026-06-11-jarvis-desk-edgecases-tests.md` — kanttilfælde på assertion-niveau
- `docs/superpowers/specs/2026-06-11-jarvis-desk-feature-coverage.md` — scope-autoritet
- `docs/superpowers/specs/2026-06-10-jarvis-desk-chat-mode-design.md` — locked visuelt design + presence-dot

**Arbejdsmappe:** `apps/jarvis-desk/` (alle stier nedenfor er relative hertil medmindre andet er angivet).

**Test-kommando:** `npm test` (Vitest) køres fra `apps/jarvis-desk/`.

**VIGTIGT — transport-realiteter (R1-R3), må ikke brydes:**
- **R1:** Ingen ægte resume. Ved brudt stream: bevar partial lokalt, INGEN blind auto-re-POST (duplikerer user-message). "Genoptag" = ny tur.
- **R2:** Hang-watchdog (90s) → synlig `hung`-status + prompt, IKKE abort→cancelled.
- **R3:** Server-cancel kræver streamClient eksponerer `run_id` + cancel-hook; `abort()` POST'er `/chat/runs/{run_id}/cancel` før lokal abort.

---

## Fase-oversigt

| Fase | Indhold | Shippable increment |
|------|---------|--------------------|
| 0 | Test-infra + deps | `npm test` kører |
| 1 | Pure-logic kerne (sseProtocol, reducer, sanitizers, normalisering) | Testbar kerne, 0 React |
| 2 | streamClient R1-R3 + api.ts content-type | Transport korrekt |
| 3 | Contexts + hooks | State-lag virker |
| 4 | Rich-rendering bibliotek | Komponenter render-testet isoleret |
| 5 | Shell + feedback-komponenter | Visuelt skelet |
| 6 | Views + App-wiring + Electron-lifecycle | Chat-mode virker ende-til-ende |
| 7 | Presence-dot + integration-polish | Klar til hands-on |

Check ind med Bjørn efter **Fase 3** (kerne+transport+state står — det hårde er gjort) og efter **Fase 6** (Chat-mode kører ende-til-ende).

---

## FASE 0 — Test-infra & afhængigheder

### Task 0.1: Installér Vitest + testing-library + rich-libs

**Files:**
- Modify: `package.json`
- Create: `vitest.config.ts`
- Create: `src/test/setup.ts`

- [ ] **Step 1: Installér dev-deps**

```bash
cd apps/jarvis-desk
npm install -D vitest@^2.1.0 @testing-library/react@^16.0.0 @testing-library/jest-dom@^6.5.0 @testing-library/user-event@^14.5.0 jsdom@^25.0.0
```

- [ ] **Step 2: Installér runtime rich-libs**

```bash
npm install shiki@^1.22.0 mermaid@^11.4.0 katex@^0.16.11
npm install -D @types/katex@^0.16.7
```

- [ ] **Step 3: Opret `vitest.config.ts`**

```ts
import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    include: ['src/**/*.test.{ts,tsx}'],
  },
})
```

- [ ] **Step 4: Opret `src/test/setup.ts`**

```ts
import '@testing-library/jest-dom/vitest'
```

- [ ] **Step 5: Tilføj test-script til `package.json`**

I `"scripts"`, tilføj:
```json
"test": "vitest run",
"test:watch": "vitest"
```

- [ ] **Step 6: Sanity-test at infra virker**

Create `src/test/smoke.test.ts`:
```ts
import { describe, it, expect } from 'vitest'

describe('test infra', () => {
  it('runs', () => {
    expect(1 + 1).toBe(2)
  })
})
```

Run: `npm test`
Expected: PASS (1 test)

- [ ] **Step 7: Commit**

```bash
git add package.json package-lock.json vitest.config.ts src/test/
git commit -m "chore(jarvis-desk): vitest + testing-library + rich-libs infra"
```

---

## FASE 1 — Pure-logic kerne (0 React, højeste TDD-værdi)

### Task 1.1: sseProtocol.ts — udtræk v2 event-typer

**Files:**
- Create: `src/lib/sseProtocol.ts`
- Modify: `src/lib/streamClient.ts` (re-eksportér typerne derfra)
- Test: `src/lib/sseProtocol.test.ts`

Formål: typerne der i dag bor i `streamClient.ts` (linje 34-102) skal bruges af både streamClient OG rich-rendering. Udtræk dem til en delt fil for at undgå cirkulær import.

- [ ] **Step 1: Skriv den fejlende test**

```ts
// src/lib/sseProtocol.test.ts
import { describe, it, expect } from 'vitest'
import type { StreamEvent, ContentBlock } from './sseProtocol'
import { isStreamEvent } from './sseProtocol'

describe('sseProtocol', () => {
  it('validates a well-formed message_start event', () => {
    const e = { type: 'message_start', message: { id: 'visible-x', model: 'm', provider: 'p', lane: 'primary', session_id: 's', usage: { input_tokens: 0, output_tokens: 0 } } }
    expect(isStreamEvent(e)).toBe(true)
  })
  it('rejects object without type', () => {
    expect(isStreamEvent({ foo: 1 })).toBe(false)
  })
  it('rejects non-object', () => {
    expect(isStreamEvent('nope')).toBe(false)
    expect(isStreamEvent(null)).toBe(false)
  })
})
```

- [ ] **Step 2: Kør → FAIL** (`npm test src/lib/sseProtocol.test.ts`) — "Cannot find module './sseProtocol'"

- [ ] **Step 3: Implementér `src/lib/sseProtocol.ts`**

Flyt interface-definitionerne `MessageStartEvent`, `ContentBlockStartEvent`, `ContentBlockDeltaEvent`, `ContentBlockStopEvent`, `MessageDeltaEvent`, `MessageStopEvent`, `PingEvent`, `SystemEvent`, og union `StreamEvent` fra `streamClient.ts:34-102` hertil — UÆNDREDE. Tilføj derudover:

```ts
// ContentBlock — den rendrede form (ikke wire-form). Bruges af reducer + rich.
export type ContentBlock =
  | { type: 'text'; text: string }
  | { type: 'thinking'; thinking: string }
  | {
      type: 'tool_use'
      id: string
      name: string
      input: Record<string, unknown>
      partialJson?: string
      status?: 'running' | 'done' | 'error'
      result?: string
    }
  | { type: 'image'; src: string; alt?: string }

export function isStreamEvent(value: unknown): value is StreamEvent {
  if (typeof value !== 'object' || value === null) return false
  const t = (value as { type?: unknown }).type
  return typeof t === 'string'
}
```

- [ ] **Step 4: Re-eksportér fra streamClient for bagudkompat**

I `streamClient.ts`, erstat de inline interface-definitioner (linje 34-102) med:
```ts
export type {
  MessageStartEvent, ContentBlockStartEvent, ContentBlockDeltaEvent,
  ContentBlockStopEvent, MessageDeltaEvent, MessageStopEvent,
  PingEvent, SystemEvent, StreamEvent,
} from './sseProtocol'
```

- [ ] **Step 5: Kør → PASS** (`npm test src/lib/sseProtocol.test.ts`). Verificér også at App.tsx stadig kompilerer: `npx tsc -b --noEmit` (forventet: ingen nye fejl).

- [ ] **Step 6: Commit**

```bash
git add src/lib/sseProtocol.ts src/lib/sseProtocol.test.ts src/lib/streamClient.ts
git commit -m "refactor(jarvis-desk): udtræk v2 event-typer til sseProtocol.ts + ContentBlock"
```

---

### Task 1.2: Stream-reducer — `(state, event) → state` (kernen)

**Files:**
- Create: `src/lib/streamReducer.ts`
- Test: `src/lib/streamReducer.test.ts`

Dette er foundationens hjerte. Ren funktion, ingen netværk. Implementerer datablock-akkumulering + status-overgange jf. spec'ens data-flow + edge-cases sektion 1.

- [ ] **Step 1: Skriv de fejlende tests (hele event-sekvenser + kanttilfælde)**

```ts
// src/lib/streamReducer.test.ts
import { describe, it, expect } from 'vitest'
import { streamReducer, initialStreamState } from './streamReducer'
import type { StreamEvent } from './sseProtocol'

const reduce = (events: StreamEvent[]) =>
  events.reduce(streamReducer, initialStreamState())

describe('streamReducer', () => {
  it('message_start sets working + activeRunId', () => {
    const s = reduce([
      { type: 'message_start', message: { id: 'visible-9', model: 'm', provider: 'p', lane: 'primary', session_id: 's', usage: { input_tokens: 0, output_tokens: 0 } } },
    ])
    expect(s.status).toBe('working')
    expect(s.activeRunId).toBe('visible-9')
  })

  it('accumulates text deltas into one block', () => {
    const s = reduce([
      { type: 'content_block_start', index: 0, content_block: { type: 'text', text: '' } },
      { type: 'content_block_delta', index: 0, delta: { type: 'text_delta', text: 'Hej ' } },
      { type: 'content_block_delta', index: 0, delta: { type: 'text_delta', text: 'Bjørn' } },
    ])
    expect(s.blocks[0]).toEqual({ type: 'text', text: 'Hej Bjørn' })
  })

  it('keeps interleaved blocks separate by index', () => {
    const s = reduce([
      { type: 'content_block_start', index: 0, content_block: { type: 'text', text: '' } },
      { type: 'content_block_delta', index: 0, delta: { type: 'text_delta', text: 'A' } },
      { type: 'content_block_start', index: 1, content_block: { type: 'thinking', thinking: '' } },
      { type: 'content_block_delta', index: 1, delta: { type: 'thinking_delta', thinking: 'hmm' } },
      { type: 'content_block_delta', index: 0, delta: { type: 'text_delta', text: 'B' } },
    ])
    expect(s.blocks[0]).toEqual({ type: 'text', text: 'AB' })
    expect(s.blocks[1]).toEqual({ type: 'thinking', thinking: 'hmm' })
  })

  it('accumulates tool_use input_json into partialJson', () => {
    const s = reduce([
      { type: 'content_block_start', index: 0, content_block: { type: 'tool_use', id: 'tu1', name: 'bash', input: {} } },
      { type: 'content_block_delta', index: 0, delta: { type: 'input_json_delta', partial_json: '{"cmd":"l' } },
      { type: 'content_block_delta', index: 0, delta: { type: 'input_json_delta', partial_json: 's"}' } },
    ])
    const b = s.blocks[0]
    expect(b.type).toBe('tool_use')
    if (b.type === 'tool_use') {
      expect(b.partialJson).toBe('{"cmd":"ls"}')
      expect(b.status).toBe('running')
    }
  })

  it('ignores delta for index without start (no crash)', () => {
    const s = reduce([
      { type: 'content_block_delta', index: 5, delta: { type: 'text_delta', text: 'x' } },
    ])
    expect(s.blocks[5]).toBeUndefined()
    expect(s.status).toBe('idle')
  })

  it('ignores unknown system_event kind', () => {
    const s = reduce([
      { type: 'message_start', message: { id: 'r', model: 'm', provider: 'p', lane: 'primary', session_id: 's', usage: { input_tokens: 0, output_tokens: 0 } } },
      { type: 'system_event', kind: 'totally_unknown', payload: {} },
    ])
    expect(s.status).toBe('working')
  })

  it('message_stop sets done', () => {
    const s = reduce([
      { type: 'message_start', message: { id: 'r', model: 'm', provider: 'p', lane: 'primary', session_id: 's', usage: { input_tokens: 0, output_tokens: 0 } } },
      { type: 'message_stop' },
    ])
    expect(s.status).toBe('done')
  })

  it('empty response (start→stop, no content) → done with no blocks', () => {
    const s = reduce([
      { type: 'message_start', message: { id: 'r', model: 'm', provider: 'p', lane: 'primary', session_id: 's', usage: { input_tokens: 0, output_tokens: 0 } } },
      { type: 'message_stop' },
    ])
    expect(s.blocks).toHaveLength(0)
    expect(s.status).toBe('done')
  })

  it('working_step system_event updates matching tool_use status', () => {
    const s = reduce([
      { type: 'content_block_start', index: 0, content_block: { type: 'tool_use', id: 'tu1', name: 'bash', input: {} } },
      { type: 'system_event', kind: 'working_step', payload: { tool_id: 'tu1', status: 'done', result: 'ok' } },
    ])
    const b = s.blocks[0]
    if (b.type === 'tool_use') {
      expect(b.status).toBe('done')
      expect(b.result).toBe('ok')
    }
  })
})
```

- [ ] **Step 2: Kør → FAIL** (`npm test src/lib/streamReducer.test.ts`)

- [ ] **Step 3: Implementér `src/lib/streamReducer.ts`**

```ts
import type { StreamEvent, ContentBlock } from './sseProtocol'

export type StreamStatus =
  | 'idle' | 'working' | 'interrupted' | 'hung' | 'error' | 'done'

export interface StreamState {
  status: StreamStatus
  activeRunId: string | null
  blocks: ContentBlock[]
  usage: { input: number; output: number; cacheHit: number; cacheMiss: number }
}

export function initialStreamState(): StreamState {
  return { status: 'idle', activeRunId: null, blocks: [], usage: { input: 0, output: 0, cacheHit: 0, cacheMiss: 0 } }
}

export function streamReducer(state: StreamState, event: StreamEvent): StreamState {
  switch (event.type) {
    case 'message_start':
      return { ...state, status: 'working', activeRunId: event.message.id, blocks: [], usage: { ...state.usage, input: event.message.usage.input_tokens } }

    case 'content_block_start': {
      const blocks = state.blocks.slice()
      const cb = event.content_block
      if (cb.type === 'text') blocks[event.index] = { type: 'text', text: cb.text ?? '' }
      else if (cb.type === 'thinking') blocks[event.index] = { type: 'thinking', thinking: cb.thinking ?? '' }
      else if (cb.type === 'tool_use') blocks[event.index] = { type: 'tool_use', id: cb.id, name: cb.name, input: cb.input ?? {}, partialJson: '', status: 'running' }
      return { ...state, blocks }
    }

    case 'content_block_delta': {
      const existing = state.blocks[event.index]
      if (!existing) return state // delta uden start → ignorér (edge-case)
      const blocks = state.blocks.slice()
      const d = event.delta
      if (d.type === 'text_delta' && existing.type === 'text') blocks[event.index] = { ...existing, text: existing.text + d.text }
      else if (d.type === 'thinking_delta' && existing.type === 'thinking') blocks[event.index] = { ...existing, thinking: existing.thinking + d.thinking }
      else if (d.type === 'input_json_delta' && existing.type === 'tool_use') blocks[event.index] = { ...existing, partialJson: (existing.partialJson ?? '') + d.partial_json }
      return { ...state, blocks }
    }

    case 'content_block_stop':
      return state

    case 'system_event': {
      if (event.kind !== 'working_step') return state // ukendt kind → ignorér
      const p = event.payload as { tool_id?: string; status?: string; result?: string }
      if (!p.tool_id) return state
      const idx = state.blocks.findIndex((b) => b.type === 'tool_use' && b.id === p.tool_id)
      if (idx < 0) return state
      const blocks = state.blocks.slice()
      const b = blocks[idx]
      if (b.type === 'tool_use') blocks[idx] = { ...b, status: (p.status as 'running' | 'done' | 'error') ?? b.status, result: p.result ?? b.result }
      return { ...state, blocks }
    }

    case 'message_delta':
      return { ...state, usage: { ...state.usage, output: event.usage.output_tokens, cacheHit: event.usage.cache_hit_tokens ?? state.usage.cacheHit, cacheMiss: event.usage.cache_miss_tokens ?? state.usage.cacheMiss } }

    case 'message_stop':
      return { ...state, status: 'done' }

    case 'ping':
      return state

    default:
      return state
  }
}
```

- [ ] **Step 4: Kør → PASS** (`npm test src/lib/streamReducer.test.ts`, alle 9 grønne)

- [ ] **Step 5: Commit**

```bash
git add src/lib/streamReducer.ts src/lib/streamReducer.test.ts
git commit -m "feat(jarvis-desk): stream-reducer — testbar (state,event)→state kerne"
```

---

### Task 1.3: Sikkerheds-sanitizers — URL + billede-policy (prod-gate)

**Files:**
- Create: `src/lib/sanitize.ts`
- Test: `src/lib/sanitize.test.ts`

Jf. edge-cases sektion 2 (skarp URL/billede-policy). Rene funktioner, sikkerheds-kritiske.

- [ ] **Step 1: Skriv de fejlende tests**

```ts
// src/lib/sanitize.test.ts
import { describe, it, expect } from 'vitest'
import { safeLinkHref, safeImageSrc } from './sanitize'

describe('safeLinkHref', () => {
  it('allows http/https/mailto', () => {
    expect(safeLinkHref('https://example.com')).toBe('https://example.com')
    expect(safeLinkHref('http://x.dk')).toBe('http://x.dk')
    expect(safeLinkHref('mailto:a@b.dk')).toBe('mailto:a@b.dk')
  })
  it('blocks dangerous schemes', () => {
    expect(safeLinkHref('javascript:alert(1)')).toBeNull()
    expect(safeLinkHref('file:///etc/passwd')).toBeNull()
    expect(safeLinkHref('data:text/html,<script>')).toBeNull()
    expect(safeLinkHref('blob:abc')).toBeNull()
    expect(safeLinkHref('vbscript:x')).toBeNull()
  })
  it('blocks malformed URLs', () => {
    expect(safeLinkHref('not a url ::: http')).toBeNull()
    expect(safeLinkHref('')).toBeNull()
  })
  it('is case-insensitive on scheme', () => {
    expect(safeLinkHref('JavaScript:alert(1)')).toBeNull()
  })
})

describe('safeImageSrc', () => {
  it('allows https', () => {
    expect(safeImageSrc('https://cdn.x/img.png')).toBe('https://cdn.x/img.png')
  })
  it('allows backend attachment relative paths', () => {
    expect(safeImageSrc('/attachments/abc.png')).toBe('/attachments/abc.png')
  })
  it('blocks file: and data: by default', () => {
    expect(safeImageSrc('file:///x.png')).toBeNull()
    expect(safeImageSrc('data:image/png;base64,AAAA')).toBeNull()
  })
  it('blocks data:image/svg+xml (script vector)', () => {
    expect(safeImageSrc('data:image/svg+xml,<svg onload=alert(1)>')).toBeNull()
  })
})
```

- [ ] **Step 2: Kør → FAIL** (`npm test src/lib/sanitize.test.ts`)

- [ ] **Step 3: Implementér `src/lib/sanitize.ts`**

```ts
const ALLOWED_LINK_SCHEMES = new Set(['http:', 'https:', 'mailto:'])

/** Returnér href hvis sikker at åbne via shell.openExternal, ellers null. */
export function safeLinkHref(raw: string): string | null {
  if (!raw) return null
  // mailto har ikke // — håndtér separat for robust parsing
  let url: URL
  try {
    url = new URL(raw)
  } catch {
    return null
  }
  if (!ALLOWED_LINK_SCHEMES.has(url.protocol.toLowerCase())) return null
  return raw
}

/** Returnér img-src hvis tilladt kilde, ellers null.
 *  Tilladt: relative backend-stier (/...), https:. Blokeret default: file:, data:, blob:. */
export function safeImageSrc(raw: string): string | null {
  if (!raw) return null
  if (raw.startsWith('/')) return raw // backend-attachment relativ sti
  let url: URL
  try {
    url = new URL(raw)
  } catch {
    return null
  }
  if (url.protocol.toLowerCase() === 'https:') return raw
  return null // file:, data:, blob:, http (mixed) blokeres default
}
```

- [ ] **Step 4: Kør → PASS** (`npm test src/lib/sanitize.test.ts`)

- [ ] **Step 5: Commit**

```bash
git add src/lib/sanitize.ts src/lib/sanitize.test.ts
git commit -m "feat(jarvis-desk): URL + billede sikkerheds-sanitizers (prod-gate)"
```

---

### Task 1.4: stringToBlocks — normalisér server-besked til ContentBlock[]

**Files:**
- Create: `src/lib/normalizeMessage.ts`
- Test: `src/lib/normalizeMessage.test.ts`

Jf. spec'ens "To kilder, samme model — normalisering". Loadede beskeder (server-string) → ét tekst-block.

- [ ] **Step 1: Skriv den fejlende test**

```ts
// src/lib/normalizeMessage.test.ts
import { describe, it, expect } from 'vitest'
import { stringToBlocks } from './normalizeMessage'

describe('stringToBlocks', () => {
  it('wraps a markdown string in one text block', () => {
    expect(stringToBlocks('**hej**')).toEqual([{ type: 'text', text: '**hej**' }])
  })
  it('empty string → empty array', () => {
    expect(stringToBlocks('')).toEqual([])
  })
})
```

- [ ] **Step 2: Kør → FAIL**

- [ ] **Step 3: Implementér `src/lib/normalizeMessage.ts`**

```ts
import type { ContentBlock } from './sseProtocol'

export function stringToBlocks(content: string): ContentBlock[] {
  if (!content) return []
  return [{ type: 'text', text: content }]
}
```

- [ ] **Step 4: Kør → PASS**

- [ ] **Step 5: Commit**

```bash
git add src/lib/normalizeMessage.ts src/lib/normalizeMessage.test.ts
git commit -m "feat(jarvis-desk): stringToBlocks server-besked normalisering"
```

---

## FASE 2 — Transport (streamClient R1-R3 + api.ts)

### Task 2.1: api.ts — ChatMessage.content → ContentBlock[] + cancelRun + whoami

**Files:**
- Modify: `src/lib/api.ts`
- Test: `src/lib/api.test.ts`

- [ ] **Step 1: Skriv fejlende test for cancelRun + whoami + normaliseret getSession**

```ts
// src/lib/api.test.ts
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { cancelRun, whoami, getSession } from './api'

const cfg = { apiBaseUrl: 'http://test', authToken: 't' }

beforeEach(() => {
  vi.restoreAllMocks()
})

describe('cancelRun', () => {
  it('POSTs to /chat/runs/{id}/cancel and is idempotent on 404', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ status: 'cancelled' }), { status: 200, headers: { 'content-type': 'application/json' } }))
    vi.stubGlobal('fetch', fetchMock)
    await expect(cancelRun(cfg, 'visible-9')).resolves.toBeUndefined()
    expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining('/chat/runs/visible-9/cancel'), expect.objectContaining({ method: 'POST' }))
  })
  it('treats 404 (unknown run) as already-cancelled (no throw)', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('', { status: 404 })))
    await expect(cancelRun(cfg, 'gone')).resolves.toBeUndefined()
  })
})

describe('getSession normalizes string content to blocks', () => {
  it('wraps assistant string content in a text block', async () => {
    const payload = { session: { id: 's', title: 't', updated_at: 'x', messages: [{ id: 'm1', role: 'assistant', content: '**hi**', created_at: 'x' }] } }
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify(payload), { status: 200, headers: { 'content-type': 'application/json' } })))
    const { messages } = await getSession(cfg, 's')
    expect(messages[0].content).toEqual([{ type: 'text', text: '**hi**' }])
  })
})
```

- [ ] **Step 2: Kør → FAIL**

- [ ] **Step 3: Ændringer i `src/lib/api.ts`**

Ændr `ChatMessage`:
```ts
import type { ContentBlock } from './sseProtocol'
import { stringToBlocks } from './normalizeMessage'

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant' | 'tool' | 'system' | 'approval_request'
  content: ContentBlock[]        // ændret fra string
  created_at: string
  parent_id?: string | null      // branch-søm
}
```

I `getSession()`, normalisér hver besked (server returnerer `content: string`):
```ts
export async function getSession(config: ApiConfig, sessionId: string): Promise<{ session: ChatSession; messages: ChatMessage[] }> {
  const raw = await apiFetch<{ session: ChatSession & { messages?: Array<{ id: string; role: ChatMessage['role']; content: string; created_at: string; parent_id?: string | null }> } }>(config, `/chat/sessions/${encodeURIComponent(sessionId)}`)
  const session = raw.session
  const messages: ChatMessage[] = (session?.messages ?? []).map((m) => ({
    id: m.id, role: m.role, created_at: m.created_at, parent_id: m.parent_id ?? null,
    content: stringToBlocks(m.content),
  }))
  return { session, messages }
}
```

Tilføj `cancelRun` (idempotent — 404/200 begge = stoppet):
```ts
export async function cancelRun(config: ApiConfig, runId: string): Promise<void> {
  const url = new URL(`/chat/runs/${encodeURIComponent(runId)}/cancel`, config.apiBaseUrl).toString()
  const headers: Record<string, string> = {}
  if (config.authToken) headers.Authorization = `Bearer ${config.authToken}`
  try {
    const res = await fetch(url, { method: 'POST', headers })
    if (res.status === 404 || res.ok) return // begge = run er stoppet
    return // best-effort: andre statusser ignoreres (vi aborter lokalt alligevel)
  } catch {
    return // netværksfejl: aborter lokalt alligevel
  }
}
```

Tilføj `whoami` (cache-first håndteres i SettingsContext; her bare kaldet):
```ts
export interface WhoAmI { user_id: string; display_name: string; role: 'owner' | 'member' | 'guest' }

export async function whoami(config: ApiConfig): Promise<WhoAmI> {
  return apiFetch<WhoAmI>(config, '/api/whoami')
}
```

- [ ] **Step 4: Kør → PASS**. Bemærk: App.tsx bruger stadig `content: string` — det rettes i Fase 6 (MessageRow). For nu kan TS klage; kør `npm test` (ikke tsc) for grøn test. Noter i commit at App.tsx wiring følger i Fase 6.

- [ ] **Step 5: Commit**

```bash
git add src/lib/api.ts src/lib/api.test.ts
git commit -m "feat(jarvis-desk): api.ts content→ContentBlock[] + cancelRun + whoami"
```

---

### Task 2.2: streamClient R1-R3 — run_id, watchdog→hung, cancel-hook, ingen blind re-POST

**Files:**
- Modify: `src/lib/streamClient.ts`
- Test: `src/lib/streamClient.test.ts`

Dette er den ene reelle refactor Jarvis flaggede. **Beslutnings-step først:** læs hele `streamClient.ts` og afgør om de tre ændringer kan laves kirurgisk (forventet: ja). Hvis koden viser sig mere sammenfiltret end ventet, eskalér til Bjørn før du fortsætter.

R1-R3 konkret:
- Tilføj `onRunId(runId)` callback til handlers (kaldes ved message_start).
- Watchdog: i stedet for `abortController.abort()` → kald ny `onHung()` handler (status hung), og lad streamen leve (brugeren beslutter via retry/abort).
- Cancel: ny returneret kontrol `{ abort, getRunId }`; `abort()` er ren netværks-luk (server-cancel laves i useStream via api.cancelRun, ikke her — holder streamClient fri for api-afhængighed).
- Deaktivér blind reconnect for chat: tilføj `autoReconnect: boolean` option (default false). Når false: ved retryable break → kald `onInterrupted()` og stop loopet (ingen re-POST).

- [ ] **Step 1: Skriv fejlende tests**

```ts
// src/lib/streamClient.test.ts
import { describe, it, expect, vi } from 'vitest'
import { startStream } from './streamClient'

function sseResponse(chunks: string[]): Response {
  const body = new ReadableStream({
    start(controller) {
      const enc = new TextEncoder()
      for (const c of chunks) controller.enqueue(enc.encode(c))
      controller.close()
    },
  })
  return new Response(body, { status: 200, headers: { 'content-type': 'text/event-stream' } })
}

describe('startStream R1-R3', () => {
  it('calls onRunId with message_start id', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(sseResponse([
      'event: message_start\ndata: {"type":"message_start","message":{"id":"visible-42","model":"m","provider":"p","lane":"l","session_id":"s","usage":{"input_tokens":0,"output_tokens":0}}}\n\n',
      'event: message_stop\ndata: {"type":"message_stop"}\n\n',
    ])))
    const runIds: string[] = []
    await new Promise<void>((resolve) => {
      startStream(
        { apiBaseUrl: 'http://t', authToken: null, sessionId: 's', message: 'hi' },
        { onEvent: () => {}, onRunId: (id) => runIds.push(id), onComplete: () => resolve() },
      )
    })
    expect(runIds).toEqual(['visible-42'])
  })

  it('does NOT auto-reconnect (re-POST) on broken stream when autoReconnect=false', async () => {
    const fetchMock = vi.fn().mockResolvedValue(sseResponse([
      'event: message_start\ndata: {"type":"message_start","message":{"id":"r","model":"m","provider":"p","lane":"l","session_id":"s","usage":{"input_tokens":0,"output_tokens":0}}}\n\n',
      // stream lukker uden message_stop → interrupted
    ]))
    vi.stubGlobal('fetch', fetchMock)
    let interrupted = false
    await new Promise<void>((resolve) => {
      startStream(
        { apiBaseUrl: 'http://t', authToken: null, sessionId: 's', message: 'hi' },
        { onEvent: () => {}, onInterrupted: () => { interrupted = true; resolve() }, onError: () => resolve() },
      )
    })
    expect(interrupted).toBe(true)
    expect(fetchMock).toHaveBeenCalledTimes(1) // ingen re-POST
  })
})
```

- [ ] **Step 2: Kør → FAIL**

- [ ] **Step 3: Ændringer i `streamClient.ts`**

Udvid `StreamHandlers`:
```ts
export interface StreamHandlers {
  onEvent: (event: StreamEvent) => void
  onRunId?: (runId: string) => void          // R3: ved message_start
  onHung?: () => void                          // R2: watchdog 90s
  onInterrupted?: () => void                   // R1: brudt stream, ingen re-POST
  onError?: (error: StreamError) => void
  onComplete?: () => void
}

export interface StreamRequest {
  // ... eksisterende felter ...
  autoReconnect?: boolean   // default false (chat-lane) — R1
}
```

I `dispatchEvent`, ved message_start, kald `onRunId`:
```ts
// efter validering, før handlers.onEvent:
if (payload.type === 'message_start') {
  const id = (parsed as { message?: { id?: string } }).message?.id
  if (id) handlers.onRunId?.(id)
}
```

Ændr watchdog (linje ~214) — i stedet for `abortController.abort()`:
```ts
pingWatchdogTimer = setTimeout(() => {
  log('ping watchdog: no event in 90s — signalling hung')
  handlers.onHung?.()          // R2: synlig prompt, IKKE abort
}, PING_TIMEOUT_MS)
```
Sæt `PING_TIMEOUT_MS = 90_000`.

I `runReconnectLoop`, når `autoReconnect !== true` (chat default): på retryable fejl ELLER "stream sluttede uden message_stop" → kald `onInterrupted()` og returnér (ingen re-POST):
```ts
if (!request.autoReconnect && (err.retryable || err.message.includes('uden message_stop'))) {
  handlers.onInterrupted?.()
  return
}
```

Returnér run_id-getter sammen med abort:
```ts
let activeRunId: string | null = null
// i onRunId-pathen: activeRunId = id; (sæt også når vi kalder handlers.onRunId)
return { abort: () => { userAborted = true; stopPingWatchdog(); abortController.abort() }, getRunId: () => activeRunId }
```
Opdatér returtype til `{ abort: () => void; getRunId: () => string | null }`. (useStream bruger getRunId + api.cancelRun til server-cancel — R3.)

- [ ] **Step 4: Kør → PASS** (begge nye tests grønne)

- [ ] **Step 5: Commit**

```bash
git add src/lib/streamClient.ts src/lib/streamClient.test.ts
git commit -m "feat(jarvis-desk): streamClient R1-R3 — run_id, watchdog→hung, ingen blind re-POST"
```

---

## FASE 3 — Contexts + hooks

> Hver context er en provider + en hook. Tests bruger `@testing-library/react`'s `renderHook` med en wrapper-provider. Mock `api.ts`/`streamClient.ts` via `vi.mock`.

### Task 3.1: SettingsContext + useSettings (med auth.role, cache-first whoami)

**Files:**
- Create: `src/contexts/SettingsContext.tsx`
- Create: `src/hooks/useSettings.ts`
- Test: `src/contexts/SettingsContext.test.tsx`

- [ ] **Step 1: Skriv fejlende test**

```tsx
// src/contexts/SettingsContext.test.tsx
import { describe, it, expect, vi } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { SettingsProvider } from './SettingsContext'
import { useSettings } from '../hooks/useSettings'

vi.mock('../lib/api', () => ({
  whoami: vi.fn().mockResolvedValue({ user_id: 'u1', display_name: 'Bjørn', role: 'owner' }),
}))

describe('SettingsContext', () => {
  it('isConfigured=false when no apiBaseUrl/token', async () => {
    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <SettingsProvider initialConfig={{ apiBaseUrl: '', authToken: null }}>{children}</SettingsProvider>
    )
    const { result } = renderHook(() => useSettings(), { wrapper })
    expect(result.current.isConfigured).toBe(false)
  })

  it('loads auth.role via whoami when configured', async () => {
    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <SettingsProvider initialConfig={{ apiBaseUrl: 'http://t', authToken: 'tok' }}>{children}</SettingsProvider>
    )
    const { result } = renderHook(() => useSettings(), { wrapper })
    expect(result.current.isConfigured).toBe(true)
    await waitFor(() => expect(result.current.auth?.role).toBe('owner'))
  })
})
```

- [ ] **Step 2: Kør → FAIL**

- [ ] **Step 3: Implementér** `SettingsContext.tsx` + `useSettings.ts`

`SettingsContext.tsx`:
```tsx
import { createContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { whoami, type WhoAmI } from '../lib/api'

export interface AppSettings {
  apiBaseUrl: string
  authToken: string | null
  theme: 'dark'
  defaultModel: string
  defaultThinking: 'think' | 'fast'
  trustDefault: 'ask' | 'trust'
}

export interface SettingsContextValue {
  settings: AppSettings | null
  auth: WhoAmI | null
  isConfigured: boolean
  update: (partial: Partial<AppSettings>) => Promise<void>
}

const DEFAULTS: Omit<AppSettings, 'apiBaseUrl' | 'authToken'> = {
  theme: 'dark', defaultModel: 'deepseek-v4-flash', defaultThinking: 'think', trustDefault: 'ask',
}

export const SettingsContext = createContext<SettingsContextValue | null>(null)

export function SettingsProvider({ children, initialConfig }: { children: ReactNode; initialConfig?: { apiBaseUrl: string; authToken: string | null } }) {
  const [settings, setSettings] = useState<AppSettings | null>(
    initialConfig ? { ...DEFAULTS, ...initialConfig } : null,
  )
  const [auth, setAuth] = useState<WhoAmI | null>(null)

  // Load fra Electron-config hvis ingen initialConfig (rigtig opstart)
  useEffect(() => {
    if (initialConfig) return
    const w = (window as unknown as { jarvisDesk?: { config: { get: () => Promise<{ apiBaseUrl: string; authToken: string | null }> } } }).jarvisDesk
    if (!w) { setSettings({ ...DEFAULTS, apiBaseUrl: '', authToken: null }); return }
    w.config.get().then((cfg) => setSettings({ ...DEFAULTS, ...cfg })).catch(() => setSettings({ ...DEFAULTS, apiBaseUrl: '', authToken: null }))
  }, [initialConfig])

  const isConfigured = !!(settings?.apiBaseUrl && settings?.authToken)

  // Cache-first whoami: behold sidste-kendte rolle ved offline-boot
  useEffect(() => {
    if (!isConfigured || !settings) return
    whoami({ apiBaseUrl: settings.apiBaseUrl, authToken: settings.authToken })
      .then(setAuth)
      .catch(() => { /* behold evt. cached auth; ingen overskrivning */ })
  }, [isConfigured, settings?.apiBaseUrl, settings?.authToken])

  const update = async (partial: Partial<AppSettings>) => {
    setSettings((s) => (s ? { ...s, ...partial } : s))
    const w = (window as unknown as { jarvisDesk?: { config: { set: (c: unknown) => Promise<boolean> } } }).jarvisDesk
    if (w && settings) await w.config.set({ apiBaseUrl: partial.apiBaseUrl ?? settings.apiBaseUrl, authToken: partial.authToken ?? settings.authToken })
  }

  const value = useMemo<SettingsContextValue>(() => ({ settings, auth, isConfigured, update }), [settings, auth, isConfigured])
  return <SettingsContext.Provider value={value}>{children}</SettingsContext.Provider>
}
```

`useSettings.ts`:
```ts
import { useContext } from 'react'
import { SettingsContext, type SettingsContextValue } from '../contexts/SettingsContext'

export function useSettings(): SettingsContextValue {
  const ctx = useContext(SettingsContext)
  if (!ctx) throw new Error('useSettings must be used within SettingsProvider')
  return ctx
}
```

- [ ] **Step 4: Kør → PASS**

- [ ] **Step 5: Commit**

```bash
git add src/contexts/SettingsContext.tsx src/hooks/useSettings.ts src/contexts/SettingsContext.test.tsx
git commit -m "feat(jarvis-desk): SettingsContext + useSettings med auth.role"
```

---

### Task 3.2: SessionContext + useSessions (med reconcile-state-maskine)

**Files:**
- Create: `src/contexts/SessionContext.tsx`
- Create: `src/hooks/useSessions.ts`
- Test: `src/contexts/SessionContext.test.tsx`

Implementér reconcile-state-maskinen fra spec'en: `optimistic_user`, `streaming_assistant`, `server_confirmed`, `server_missing_keep_stream`, `server_conflict`. Test fokus: **blank-load ALDRIG** (dagens bug).

- [ ] **Step 1: Skriv fejlende tests** (mindst: appendOptimistic viser straks; reconcile beholder stream-blocks når server-load mangler beskeden)

```tsx
// src/contexts/SessionContext.test.tsx
import { describe, it, expect, vi } from 'vitest'
import { renderHook, act, waitFor } from '@testing-library/react'
import { SessionProvider } from './SessionContext'
import { useSessions } from '../hooks/useSessions'

vi.mock('../lib/api', () => ({
  listSessions: vi.fn().mockResolvedValue([{ id: 's1', title: 'T', updated_at: 'x' }]),
  getSession: vi.fn().mockResolvedValue({ session: { id: 's1', title: 'T', updated_at: 'x' }, messages: [] }),
  createSession: vi.fn(),
}))

const cfg = { apiBaseUrl: 'http://t', authToken: 't' }
const wrapper = ({ children }: { children: React.ReactNode }) => (
  <SessionProvider config={cfg}>{children}</SessionProvider>
)

describe('SessionContext reconcile', () => {
  it('appendOptimistic shows user message immediately', async () => {
    const { result } = renderHook(() => useSessions(), { wrapper })
    await act(async () => { result.current.select('s1') })
    act(() => { result.current.appendOptimistic({ id: 'u-1', role: 'user', content: [{ type: 'text', text: 'hej' }], created_at: 'now', parent_id: null }) })
    expect(result.current.messages.some((m) => m.id === 'u-1')).toBe(true)
  })

  it('reconcile keeps stream blocks when server load is missing the message (no blank)', async () => {
    const { result } = renderHook(() => useSessions(), { wrapper })
    await act(async () => { result.current.select('s1') })
    const assistantBlocks = [{ type: 'text' as const, text: 'svar' }]
    act(() => { result.current.reconcile({ id: 'a-temp', role: 'assistant', content: assistantBlocks, created_at: 'now', parent_id: null }) })
    // server-load returnerer tom (race) — beskeden må IKKE forsvinde
    await act(async () => { await result.current.refresh() })
    expect(result.current.messages.some((m) => m.role === 'assistant' && m.content[0]?.type === 'text' && (m.content[0] as { text: string }).text === 'svar')).toBe(true)
  })
})
```

- [ ] **Step 2: Kør → FAIL**

- [ ] **Step 3: Implementér** `SessionContext.tsx` + `useSessions.ts`

Nøgle-logik: hold en lokal `messages`-liste med `clientStatus` pr. besked. `refresh()` flettes med serverens liste; beskeder med `clientStatus='server_missing_keep_stream'` der ikke findes server-side beholdes (ikke slettet). Server-`server_conflict` (fx "Generation cancelled.") erstatter stream-indhold ved samme position.

```tsx
import { createContext, useCallback, useMemo, useState, type ReactNode } from 'react'
import { listSessions, getSession, createSession, type ChatSession, type ChatMessage } from '../lib/api'

type ClientStatus = 'optimistic_user' | 'streaming_assistant' | 'server_confirmed' | 'server_missing_keep_stream'
interface LocalMessage extends ChatMessage { clientStatus?: ClientStatus }

export interface SessionContextValue {
  sessions: ChatSession[]
  activeId: string | null
  messages: LocalMessage[]
  loading: boolean
  select: (id: string) => void
  create: (title: string) => Promise<void>
  refresh: () => Promise<void>
  appendOptimistic: (msg: ChatMessage) => void
  reconcile: (assistantMsg: ChatMessage) => void
}

export const SessionContext = createContext<SessionContextValue | null>(null)

export function SessionProvider({ children, config }: { children: ReactNode; config: { apiBaseUrl: string; authToken: string | null } }) {
  const [sessions, setSessions] = useState<ChatSession[]>([])
  const [activeId, setActiveId] = useState<string | null>(null)
  const [messages, setMessages] = useState<LocalMessage[]>([])
  const [loading, setLoading] = useState(false)

  const loadSessions = useCallback(async () => {
    const list = await listSessions(config)
    setSessions(list)
  }, [config])

  const select = useCallback((id: string) => {
    setActiveId(id)
    setLoading(true)
    getSession(config, id).then(({ messages: server }) => {
      setMessages(mergeServer([], server))
    }).finally(() => setLoading(false))
  }, [config])

  const refresh = useCallback(async () => {
    if (!activeId) return
    const { messages: server } = await getSession(config, activeId)
    setMessages((local) => mergeServer(local, server))
  }, [config, activeId])

  const create = useCallback(async (title: string) => {
    const sess = await createSession(config, title)
    setSessions((prev) => [sess, ...prev])
    setActiveId(sess.id)
    setMessages([])
  }, [config])

  const appendOptimistic = useCallback((msg: ChatMessage) => {
    setMessages((prev) => [...prev, { ...msg, clientStatus: 'optimistic_user' }])
  }, [])

  const reconcile = useCallback((assistantMsg: ChatMessage) => {
    setMessages((prev) => [...prev, { ...assistantMsg, clientStatus: 'server_missing_keep_stream' }])
  }, [])

  // init
  useMemo(() => { loadSessions() }, [loadSessions])

  const value = useMemo<SessionContextValue>(() => ({ sessions, activeId, messages, loading, select, create, refresh, appendOptimistic, reconcile }), [sessions, activeId, messages, loading, select, create, refresh, appendOptimistic, reconcile])
  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>
}

/** Flet server-beskeder ind. Behold lokale beskeder serveren endnu ikke har (race-beskyttelse). */
function mergeServer(local: LocalMessage[], server: ChatMessage[]): LocalMessage[] {
  const serverById = new Map(server.map((m) => [m.id, m]))
  const result: LocalMessage[] = server.map((m) => ({ ...m, clientStatus: 'server_confirmed' as ClientStatus }))
  // behold lokale beskeder der IKKE findes server-side endnu (keep_stream / optimistic)
  for (const lm of local) {
    if (!serverById.has(lm.id) && (lm.clientStatus === 'server_missing_keep_stream' || lm.clientStatus === 'optimistic_user')) {
      result.push(lm)
    }
  }
  return result
}
```

`useSessions.ts`:
```ts
import { useContext } from 'react'
import { SessionContext, type SessionContextValue } from '../contexts/SessionContext'
export function useSessions(): SessionContextValue {
  const ctx = useContext(SessionContext)
  if (!ctx) throw new Error('useSessions must be used within SessionProvider')
  return ctx
}
```

- [ ] **Step 4: Kør → PASS**

- [ ] **Step 5: Commit**

```bash
git add src/contexts/SessionContext.tsx src/hooks/useSessions.ts src/contexts/SessionContext.test.tsx
git commit -m "feat(jarvis-desk): SessionContext + reconcile-state-maskine (blank-load aldrig)"
```

---

### Task 3.3: StreamContext + useStream (reducer + streamClient + liveness)

**Files:**
- Create: `src/contexts/StreamContext.tsx`
- Create: `src/hooks/useStream.ts`
- Test: `src/contexts/StreamContext.test.tsx`

Binder reducer (Task 1.2) + streamClient (Task 2.2) + cancelRun (Task 2.1) sammen. Eksponerer `status`, `blocks`, `activeRunId`, `elapsedMs`, `error`, `needsAttention`, `send`, `abort`, `continueFromPartial`.

- [ ] **Step 1: Skriv fejlende test** (send → working; message_stop → done; onHung → hung; abort kalder cancelRun med run_id)

```tsx
// src/contexts/StreamContext.test.tsx
import { describe, it, expect, vi } from 'vitest'
import { renderHook, act, waitFor } from '@testing-library/react'
import { StreamProvider } from './StreamContext'
import { useStream } from '../hooks/useStream'

const handlersRef: { current: any } = { current: null }
vi.mock('../lib/streamClient', () => ({
  startStream: (req: any, handlers: any) => {
    handlersRef.current = handlers
    return { abort: vi.fn(), getRunId: () => 'visible-1' }
  },
  StreamError: class extends Error {},
}))
const cancelRunMock = vi.fn().mockResolvedValue(undefined)
vi.mock('../lib/api', () => ({ cancelRun: (...a: any[]) => cancelRunMock(...a) }))

const cfg = { apiBaseUrl: 'http://t', authToken: 't' }
const wrapper = ({ children }: { children: React.ReactNode }) => (
  <StreamProvider config={cfg}>{children}</StreamProvider>
)

describe('StreamContext', () => {
  it('send → working, message_stop → done', async () => {
    const { result } = renderHook(() => useStream(), { wrapper })
    act(() => { result.current.send('hej', { sessionId: 's' }) })
    act(() => { handlersRef.current.onRunId('visible-1'); handlersRef.current.onEvent({ type: 'message_start', message: { id: 'visible-1', model: 'm', provider: 'p', lane: 'l', session_id: 's', usage: { input_tokens: 0, output_tokens: 0 } } }) })
    expect(result.current.status).toBe('working')
    act(() => { handlersRef.current.onEvent({ type: 'message_stop' }) })
    expect(result.current.status).toBe('done')
  })

  it('onHung → hung status', async () => {
    const { result } = renderHook(() => useStream(), { wrapper })
    act(() => { result.current.send('hej', { sessionId: 's' }) })
    act(() => { handlersRef.current.onHung() })
    expect(result.current.status).toBe('hung')
  })

  it('abort() calls cancelRun with active run_id then aborts', async () => {
    const { result } = renderHook(() => useStream(), { wrapper })
    act(() => { result.current.send('hej', { sessionId: 's' }) })
    act(() => { handlersRef.current.onRunId('visible-1') })
    await act(async () => { await result.current.abort() })
    expect(cancelRunMock).toHaveBeenCalledWith(cfg, 'visible-1')
  })
})
```

- [ ] **Step 2: Kør → FAIL**

- [ ] **Step 3: Implementér** `StreamContext.tsx` + `useStream.ts`

```tsx
import { createContext, useCallback, useMemo, useReducer, useRef, useState, type ReactNode } from 'react'
import { startStream } from '../lib/streamClient'
import { cancelRun } from '../lib/api'
import { streamReducer, initialStreamState, type StreamState } from '../lib/streamReducer'
import type { StreamEvent } from '../lib/sseProtocol'

export interface SendOpts { sessionId: string; approvalMode?: 'ask' | 'trust'; thinkingMode?: 'think' | 'fast' }
export interface StreamContextValue extends Pick<StreamState, 'status' | 'blocks' | 'activeRunId'> {
  elapsedMs: number
  error: Error | null
  needsAttention: boolean
  send: (message: string, opts: SendOpts) => void
  abort: () => Promise<void>
  continueFromPartial: () => void
}

export const StreamContext = createContext<StreamContextValue | null>(null)

export function StreamProvider({ children, config }: { children: ReactNode; config: { apiBaseUrl: string; authToken: string | null } }) {
  const [state, dispatch] = useReducer(streamReducer, undefined, initialStreamState)
  const [error, setError] = useState<Error | null>(null)
  const controlRef = useRef<{ abort: () => void; getRunId: () => string | null } | null>(null)
  const runIdRef = useRef<string | null>(null)
  const startedAtRef = useRef<number>(0)
  const [elapsedMs, setElapsedMs] = useState(0)
  // status-overgange udenfor reducer (hung/interrupted/error kommer fra handlers)
  const [override, setOverride] = useState<null | 'hung' | 'interrupted' | 'error'>(null)

  const send = useCallback((message: string, opts: SendOpts) => {
    setError(null); setOverride(null); runIdRef.current = null
    startedAtRef.current = Date.now()
    controlRef.current = startStream(
      { apiBaseUrl: config.apiBaseUrl, authToken: config.authToken, sessionId: opts.sessionId, message, approvalMode: opts.approvalMode, thinkingMode: opts.thinkingMode, autoReconnect: false },
      {
        onEvent: (e: StreamEvent) => dispatch(e),
        onRunId: (id) => { runIdRef.current = id },
        onHung: () => setOverride('hung'),
        onInterrupted: () => setOverride('interrupted'),
        onError: (err) => { setError(err); setOverride('error') },
        onComplete: () => { /* status=done sættes af message_stop i reducer */ },
      },
    )
  }, [config])

  const abort = useCallback(async () => {
    const runId = controlRef.current?.getRunId() ?? runIdRef.current
    if (runId) await cancelRun(config, runId)   // R3: server-cancel FØR lokal
    controlRef.current?.abort()
  }, [config])

  const continueFromPartial = useCallback(() => { setOverride(null) /* caller (ChatView) starter ny tur via send() */ }, [])

  const status = override ?? state.status
  const needsAttention = (status === 'working' || status === 'hung' || status === 'interrupted') && typeof document !== 'undefined' && document.hidden

  const value = useMemo<StreamContextValue>(() => ({ status, blocks: state.blocks, activeRunId: state.activeRunId, elapsedMs, error, needsAttention, send, abort, continueFromPartial }), [status, state.blocks, state.activeRunId, elapsedMs, error, needsAttention, send, abort, continueFromPartial])
  return <StreamContext.Provider value={value}>{children}</StreamContext.Provider>
}
```

`useStream.ts`:
```ts
import { useContext } from 'react'
import { StreamContext, type StreamContextValue } from '../contexts/StreamContext'
export function useStream(): StreamContextValue {
  const ctx = useContext(StreamContext)
  if (!ctx) throw new Error('useStream must be used within StreamProvider')
  return ctx
}
```

> Note: elapsed-timer (setInterval mens working) tilføjes i Fase 5 sammen med LivenessIndicator for at holde denne task fokuseret. `elapsedMs` er 0 indtil da.

- [ ] **Step 4: Kør → PASS**

- [ ] **Step 5: Commit**

```bash
git add src/contexts/StreamContext.tsx src/hooks/useStream.ts src/contexts/StreamContext.test.tsx
git commit -m "feat(jarvis-desk): StreamContext + useStream (reducer+streamClient+liveness)"
```

**▶ CHECK-IN MED BJØRN efter Fase 3** — kerne + transport + state-lag står. Det hårde er gjort; resten er UI ovenpå en testet kerne.

---

## FASE 4 — Rich-rendering bibliotek

> Hver komponent er en ren funktion af props. Render-tests med `@testing-library/react`. Density-prop hvor relevant.

### Task 4.1: MarkdownRenderer (streaming-buffer + sanitering)

**Files:**
- Create: `src/components/rich/MarkdownRenderer.tsx`
- Create: `src/lib/streamingMarkdown.ts` (buffer-logik, ren funktion)
- Test: `src/lib/streamingMarkdown.test.ts`
- Test: `src/components/rich/MarkdownRenderer.test.tsx`

- [ ] **Step 1: Skriv fejlende test for buffer-logik (ren funktion først)**

```ts
// src/lib/streamingMarkdown.test.ts
import { describe, it, expect } from 'vitest'
import { stabilizeStreamingMarkdown } from './streamingMarkdown'

describe('stabilizeStreamingMarkdown', () => {
  it('holds back an unclosed code fence', () => {
    // ufærdig fence → fence-indhold skjules indtil luk (ingen brækket <pre>)
    const out = stabilizeStreamingMarkdown('tekst\n```js\nconst x')
    expect(out).toBe('tekst') // fence-delen holdes tilbage
  })
  it('renders a closed code fence fully', () => {
    const md = 'tekst\n```js\nconst x = 1\n```'
    expect(stabilizeStreamingMarkdown(md)).toBe(md)
  })
  it('passes through plain text unchanged', () => {
    expect(stabilizeStreamingMarkdown('bare tekst')).toBe('bare tekst')
  })
})
```

- [ ] **Step 2: Kør → FAIL**

- [ ] **Step 3: Implementér `src/lib/streamingMarkdown.ts`**

```ts
/** Hold ufærdige code-fences tilbage under streaming så rendering ikke flasher.
 *  Hvis antallet af ``` er ulige, klip fra sidste åbne fence. */
export function stabilizeStreamingMarkdown(md: string): string {
  const fenceCount = (md.match(/```/g) || []).length
  if (fenceCount % 2 === 0) return md
  const lastFence = md.lastIndexOf('```')
  // klip fra fence og fjern foregående newline
  return md.slice(0, lastFence).replace(/\n+$/, '')
}
```

- [ ] **Step 4: Kør → PASS** (buffer-logik)

- [ ] **Step 5: Skriv fejlende test for MarkdownRenderer (sanitering + ingen rå HTML)**

```tsx
// src/components/rich/MarkdownRenderer.test.tsx
import { describe, it, expect } from 'vitest'
import { render } from '@testing-library/react'
import { MarkdownRenderer } from './MarkdownRenderer'

describe('MarkdownRenderer', () => {
  it('renders bold markdown as <strong>', () => {
    const { container } = render(<MarkdownRenderer text="**fed**" streaming={false} />)
    expect(container.querySelector('strong')?.textContent).toBe('fed')
  })
  it('does NOT render raw HTML (XSS guard)', () => {
    const { container } = render(<MarkdownRenderer text={'<img src=x onerror=alert(1)>'} streaming={false} />)
    expect(container.querySelector('img')).toBeNull()
  })
  it('blocks javascript: links (renders without href)', () => {
    const { container } = render(<MarkdownRenderer text={'[klik](javascript:alert(1))'} streaming={false} />)
    const a = container.querySelector('a')
    expect(a?.getAttribute('href') ?? null).toBeNull()
  })
})
```

- [ ] **Step 6: Kør → FAIL**

- [ ] **Step 7: Implementér `src/components/rich/MarkdownRenderer.tsx`**

```tsx
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { stabilizeStreamingMarkdown } from '../../lib/streamingMarkdown'
import { safeLinkHref } from '../../lib/sanitize'

export function MarkdownRenderer({ text, streaming }: { text: string; streaming: boolean }) {
  const md = streaming ? stabilizeStreamingMarkdown(text) : text
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      // INGEN rehype-raw → rå HTML renderes ikke (XSS-guard)
      components={{
        a: ({ href, children }) => {
          const safe = href ? safeLinkHref(href) : null
          if (!safe) return <span>{children}</span>
          return <a href={safe} rel="noopener noreferrer" onClick={(e) => { e.preventDefault(); openExternal(safe) }}>{children}</a>
        },
      }}
    >{md}</ReactMarkdown>
  )
}

function openExternal(url: string) {
  const w = (window as unknown as { jarvisDesk?: { openExternal?: (u: string) => void } }).jarvisDesk
  if (w?.openExternal) w.openExternal(url)
}
```

> `jarvisDesk.openExternal` bridge tilføjes i Fase 6 (Electron). Indtil da er onClick en no-op (preventDefault), hvilket er sikkert.

- [ ] **Step 8: Kør → PASS** (alle MarkdownRenderer-tests)

- [ ] **Step 9: Commit**

```bash
git add src/lib/streamingMarkdown.ts src/lib/streamingMarkdown.test.ts src/components/rich/MarkdownRenderer.tsx src/components/rich/MarkdownRenderer.test.tsx
git commit -m "feat(jarvis-desk): MarkdownRenderer — streaming-buffer + XSS/link-sanitering"
```

---

### Task 4.2: CodeBlock (Shiki + kopiér rå)

**Files:**
- Create: `src/components/rich/CodeBlock.tsx`
- Test: `src/components/rich/CodeBlock.test.tsx`

- [ ] **Step 1: Skriv fejlende test** (renderer kode-tekst; kopiér-knap kopierer RÅ uden linjenumre)

```tsx
// src/components/rich/CodeBlock.test.tsx
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { CodeBlock } from './CodeBlock'

describe('CodeBlock', () => {
  it('renders the code text', async () => {
    render(<CodeBlock code={'const x = 1'} lang="js" />)
    expect(await screen.findByText(/const x = 1/)).toBeInTheDocument()
  })
  it('copy button copies raw code', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined)
    vi.stubGlobal('navigator', { clipboard: { writeText } })
    render(<CodeBlock code={'line1\nline2'} lang="txt" />)
    await userEvent.click(screen.getByRole('button', { name: /kopiér/i }))
    expect(writeText).toHaveBeenCalledWith('line1\nline2')
  })
})
```

- [ ] **Step 2: Kør → FAIL**

- [ ] **Step 3: Implementér `src/components/rich/CodeBlock.tsx`** — Shiki highlight (async, fallback til plain `<pre>` mens den loader), sprog-label, kopiér-knap:

```tsx
import { useEffect, useState } from 'react'
import { codeToHtml } from 'shiki'

export function CodeBlock({ code, lang }: { code: string; lang: string }) {
  const [html, setHtml] = useState<string | null>(null)
  useEffect(() => {
    let alive = true
    codeToHtml(code, { lang: lang || 'text', theme: 'github-dark' }).then((h) => { if (alive) setHtml(h) }).catch(() => setHtml(null))
    return () => { alive = false }
  }, [code, lang])
  return (
    <div className="codeblock">
      <div className="codeblock-bar"><span className="codeblock-lang">{lang || 'text'}</span>
        <button type="button" aria-label="Kopiér" onClick={() => navigator.clipboard.writeText(code)}>Kopiér</button>
      </div>
      {html ? <div dangerouslySetInnerHTML={{ __html: html }} /> : <pre><code>{code}</code></pre>}
    </div>
  )
}
```

> Bemærk: `dangerouslySetInnerHTML` her er på **Shiki's egen** highlightede output af kode-strengen — ikke på model-leveret HTML. Shiki escaper kode-indhold; dette er ikke en XSS-vektor da input er ren tekst der highlightes.

- [ ] **Step 4: Kør → PASS**

- [ ] **Step 5: Commit**

```bash
git add src/components/rich/CodeBlock.tsx src/components/rich/CodeBlock.test.tsx
git commit -m "feat(jarvis-desk): CodeBlock — Shiki highlight + kopiér rå"
```

---

### Task 4.3: ToolCard (density-aware) + ApprovalCard (inert tekst)

**Files:**
- Create: `src/components/rich/ToolCard.tsx`
- Create: `src/components/rich/ApprovalCard.tsx`
- Test: `src/components/rich/ToolCard.test.tsx`
- Test: `src/components/rich/ApprovalCard.test.tsx`

- [ ] **Step 1: Skriv fejlende ToolCard-test** (compact = navn + status, ingen args; full = args+result synlige)

```tsx
// src/components/rich/ToolCard.test.tsx
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ToolCard } from './ToolCard'

const block = { type: 'tool_use' as const, id: 't1', name: 'bash', input: { command: 'ls' }, status: 'done' as const, result: 'fil.txt' }

describe('ToolCard', () => {
  it('compact shows name + status, hides args by default', () => {
    render(<ToolCard block={block} density="compact" />)
    expect(screen.getByText(/bash/)).toBeInTheDocument()
    expect(screen.queryByText(/fil\.txt/)).toBeNull() // result skjult i compact
  })
  it('full shows args and result', () => {
    render(<ToolCard block={block} density="full" />)
    expect(screen.getByText(/fil\.txt/)).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Kør → FAIL**

- [ ] **Step 3: Implementér `ToolCard.tsx`** (compact = linje med expand-toggle; full = altid udfoldet; resultater rendres som inert tekst via `<pre>`, ALDRIG via MarkdownRenderer med rå HTML):

```tsx
import { useState } from 'react'
import type { ContentBlock } from '../../lib/sseProtocol'

export function ToolCard({ block, density }: { block: Extract<ContentBlock, { type: 'tool_use' }>; density: 'compact' | 'full' }) {
  const [open, setOpen] = useState(density === 'full')
  const expanded = density === 'full' || open
  return (
    <div className="toolcard">
      <button type="button" className="toolcard-head" onClick={() => density === 'compact' && setOpen((o) => !o)}>
        <span className="toolcard-name">{block.name}</span>
        <span className="toolcard-status">{block.status ?? 'running'}</span>
      </button>
      {expanded && (
        <div className="toolcard-body">
          {block.partialJson && <pre className="toolcard-args">{block.partialJson}</pre>}
          {block.result && <pre className="toolcard-result">{block.result}</pre>}
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 4: Kør → PASS**

- [ ] **Step 5: Skriv fejlende ApprovalCard-test** (approve/deny knapper er ægte UI; tool-tekst er inert)

```tsx
// src/components/rich/ApprovalCard.test.tsx
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ApprovalCard } from './ApprovalCard'

describe('ApprovalCard', () => {
  it('renders action text inert and fires onApprove (owner)', async () => {
    const onApprove = vi.fn()
    render(<ApprovalCard approvalId="a1" tool="operator_bash" action={'<b>rm</b>'} risk="destructive" canApprove onApprove={onApprove} onDeny={() => {}} />)
    // action-tekst vises som tekst, ikke som HTML
    expect(screen.getByText('<b>rm</b>')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: /godkend/i }))
    expect(onApprove).toHaveBeenCalledWith('a1')
  })
  it('member sees read-only (no approve button)', () => {
    render(<ApprovalCard approvalId="a1" tool="x" action="y" risk="normal" canApprove={false} onApprove={() => {}} onDeny={() => {}} />)
    expect(screen.queryByRole('button', { name: /godkend/i })).toBeNull()
  })
})
```

- [ ] **Step 6: Kør → FAIL**

- [ ] **Step 7: Implementér `ApprovalCard.tsx`**

```tsx
export function ApprovalCard({ approvalId, tool, action, risk, canApprove, onApprove, onDeny }: {
  approvalId: string; tool: string; action: string; risk: string
  canApprove: boolean; onApprove: (id: string) => void; onDeny: (id: string) => void
}) {
  return (
    <div className={`approvalcard risk-${risk}`}>
      <div className="approvalcard-head">{tool} · {risk}</div>
      <pre className="approvalcard-action">{action}</pre>
      {canApprove ? (
        <div className="approvalcard-actions">
          <button type="button" onClick={() => onApprove(approvalId)}>Godkend</button>
          <button type="button" onClick={() => onDeny(approvalId)}>Afvis</button>
        </div>
      ) : <div className="approvalcard-readonly">Kun owner kan godkende</div>}
    </div>
  )
}
```

- [ ] **Step 8: Kør → PASS**

- [ ] **Step 9: Commit**

```bash
git add src/components/rich/ToolCard.tsx src/components/rich/ApprovalCard.tsx src/components/rich/ToolCard.test.tsx src/components/rich/ApprovalCard.test.tsx
git commit -m "feat(jarvis-desk): ToolCard (density) + ApprovalCard (inert tekst, rolle-gate)"
```

---

### Task 4.4: ImageBlock + Table + MathBlock + MermaidBlock (lazy)

**Files:**
- Create: `src/components/rich/ImageBlock.tsx`
- Create: `src/components/rich/MathBlock.tsx`
- Create: `src/components/rich/MermaidBlock.tsx`
- Test: `src/components/rich/ImageBlock.test.tsx`
- Test: `src/components/rich/MathBlock.test.tsx`

(Table håndteres af remark-gfm i MarkdownRenderer + CSS; ingen separat komponent nødvendig — YAGNI.)

- [ ] **Step 1: Skriv fejlende ImageBlock-test** (blokeret kilde → placeholder; https → img)

```tsx
// src/components/rich/ImageBlock.test.tsx
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ImageBlock } from './ImageBlock'

describe('ImageBlock', () => {
  it('renders https image', () => {
    render(<ImageBlock src="https://x/i.png" alt="billede" />)
    expect(screen.getByRole('img')).toHaveAttribute('src', 'https://x/i.png')
  })
  it('blocks data: src → shows alt placeholder, no img', () => {
    render(<ImageBlock src="data:image/svg+xml,<svg>" alt="ondsindet" />)
    expect(screen.queryByRole('img')).toBeNull()
    expect(screen.getByText(/ondsindet/)).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Kør → FAIL**

- [ ] **Step 3: Implementér `ImageBlock.tsx`**

```tsx
import { safeImageSrc } from '../../lib/sanitize'
export function ImageBlock({ src, alt }: { src: string; alt?: string }) {
  const safe = safeImageSrc(src)
  if (!safe) return <span className="image-blocked">{alt || 'billede blokeret'}</span>
  return <img src={safe} alt={alt ?? ''} loading="lazy" />
}
```

- [ ] **Step 4: Kør → PASS**

- [ ] **Step 5: Skriv fejlende MathBlock-test** (KaTeX parse-fejl → fallback til rå)

```tsx
// src/components/rich/MathBlock.test.tsx
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MathBlock } from './MathBlock'

describe('MathBlock', () => {
  it('renders fallback raw text on invalid latex', async () => {
    render(<MathBlock latex={'\\frac{'} />) // ufærdig → KaTeX kaster
    expect(await screen.findByText(/frac/)).toBeInTheDocument()
  })
})
```

- [ ] **Step 6: Kør → FAIL**

- [ ] **Step 7: Implementér `MathBlock.tsx`** (lazy katex) og `MermaidBlock.tsx` (lazy mermaid, fallback til CodeBlock ved parse-fejl):

```tsx
// MathBlock.tsx
import { useEffect, useState } from 'react'
export function MathBlock({ latex }: { latex: string }) {
  const [html, setHtml] = useState<string | null>(null)
  const [failed, setFailed] = useState(false)
  useEffect(() => {
    let alive = true
    import('katex').then(({ default: katex }) => {
      try { const h = katex.renderToString(latex, { throwOnError: true }); if (alive) setHtml(h) }
      catch { if (alive) setFailed(true) }
    })
    return () => { alive = false }
  }, [latex])
  if (failed) return <code>{latex}</code>
  if (html) return <span dangerouslySetInnerHTML={{ __html: html }} />
  return <code>{latex}</code>
}
```

```tsx
// MermaidBlock.tsx
import { useEffect, useState } from 'react'
import { CodeBlock } from './CodeBlock'
export function MermaidBlock({ source }: { source: string }) {
  const [svg, setSvg] = useState<string | null>(null)
  const [failed, setFailed] = useState(false)
  useEffect(() => {
    let alive = true
    import('mermaid').then(async ({ default: mermaid }) => {
      try { mermaid.initialize({ startOnLoad: false, theme: 'dark' }); const { svg } = await mermaid.render('m' + Math.abs(hash(source)), source); if (alive) setSvg(svg) }
      catch { if (alive) setFailed(true) }
    })
    return () => { alive = false }
  }, [source])
  if (failed) return <CodeBlock code={source} lang="mermaid" />
  if (svg) return <div dangerouslySetInnerHTML={{ __html: svg }} />
  return <CodeBlock code={source} lang="mermaid" />
}
function hash(s: string): number { let h = 0; for (let i = 0; i < s.length; i++) h = (h << 5) - h + s.charCodeAt(i) | 0; return h }
```

> KaTeX/Mermaid `dangerouslySetInnerHTML` er på deres egne biblioteks-genererede outputs af tekst-input (latex/mermaid-kilde), ikke model-HTML. Det er bibliotekernes tilsigtede API.

- [ ] **Step 8: Kør → PASS** (ImageBlock + MathBlock)

- [ ] **Step 9: Commit**

```bash
git add src/components/rich/ImageBlock.tsx src/components/rich/MathBlock.tsx src/components/rich/MermaidBlock.tsx src/components/rich/ImageBlock.test.tsx src/components/rich/MathBlock.test.tsx
git commit -m "feat(jarvis-desk): ImageBlock (sikker) + lazy MathBlock + MermaidBlock"
```

---

### Task 4.5: MessageRow + blocks-renderer (binder rich sammen, density)

**Files:**
- Create: `src/components/rich/BlocksRenderer.tsx`
- Create: `src/components/rich/MessageRow.tsx`
- Test: `src/components/rich/MessageRow.test.tsx`

- [ ] **Step 1: Skriv fejlende test** (assistant tekst-block → markdown; thinking foldet sammen default; kopiér hele besked = rå markdown)

```tsx
// src/components/rich/MessageRow.test.tsx
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MessageRow } from './MessageRow'

describe('MessageRow', () => {
  it('renders assistant text block as markdown', () => {
    render(<MessageRow role="assistant" blocks={[{ type: 'text', text: '**hej**' }]} density="compact" streaming={false} />)
    expect(screen.getByText('hej').tagName).toBe('STRONG')
  })
  it('thinking block is collapsed by default', () => {
    render(<MessageRow role="assistant" blocks={[{ type: 'thinking', thinking: 'intern' }]} density="compact" streaming={false} />)
    expect(screen.queryByText('intern')).toBeNull() // foldet
    expect(screen.getByText(/tænkte/i)).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Kør → FAIL**

- [ ] **Step 3: Implementér `BlocksRenderer.tsx`** (dispatch på block-type → rich-komponent) + `MessageRow.tsx` (bobble-layout fra locked design + actions). Komplet kode:

```tsx
// BlocksRenderer.tsx
import type { ContentBlock } from '../../lib/sseProtocol'
import { MarkdownRenderer } from './MarkdownRenderer'
import { ToolCard } from './ToolCard'
import { ImageBlock } from './ImageBlock'
import { useState } from 'react'

export function BlocksRenderer({ blocks, density, streaming }: { blocks: ContentBlock[]; density: 'compact' | 'full'; streaming: boolean }) {
  return <>{blocks.map((b, i) => <BlockView key={i} block={b} density={density} streaming={streaming} />)}</>
}

function BlockView({ block, density, streaming }: { block: ContentBlock; density: 'compact' | 'full'; streaming: boolean }) {
  const [thinkingOpen, setThinkingOpen] = useState(false)
  switch (block.type) {
    case 'text': return <MarkdownRenderer text={block.text} streaming={streaming} />
    case 'tool_use': return <ToolCard block={block} density={density} />
    case 'image': return <ImageBlock src={block.src} alt={block.alt} />
    case 'thinking': return (
      <div className="thinking">
        <button type="button" onClick={() => setThinkingOpen((o) => !o)}>{thinkingOpen ? 'Skjul tanke' : 'tænkte…'}</button>
        {thinkingOpen && <MarkdownRenderer text={block.thinking} streaming={false} />}
      </div>
    )
    default: return null
  }
}
```

```tsx
// MessageRow.tsx
import type { ContentBlock } from '../../lib/sseProtocol'
import { BlocksRenderer } from './BlocksRenderer'

export function MessageRow({ role, blocks, density, streaming }: { role: 'user' | 'assistant'; blocks: ContentBlock[]; density: 'compact' | 'full'; streaming: boolean }) {
  if (role === 'user') {
    const text = blocks.map((b) => (b.type === 'text' ? b.text : '')).join('')
    return <div className="msg-user-wrap"><div className="bubble">{text}</div></div>
  }
  return (
    <div className="msg-jarvis-wrap">
      <article className="msg-jarvis">
        <div className="avatar-jarvis">J</div>
        <div className="jarvis-body"><BlocksRenderer blocks={blocks} density={density} streaming={streaming} /></div>
      </article>
    </div>
  )
}
```

- [ ] **Step 4: Kør → PASS**

- [ ] **Step 5: Commit**

```bash
git add src/components/rich/BlocksRenderer.tsx src/components/rich/MessageRow.tsx src/components/rich/MessageRow.test.tsx
git commit -m "feat(jarvis-desk): BlocksRenderer + MessageRow (density-aware)"
```

---

## FASE 5 — Shell + feedback-komponenter

### Task 5.1: Feedback-komponenter (Liveness/Interrupted/Error/Hang) + elapsed-timer

**Files:**
- Create: `src/components/feedback/LivenessIndicator.tsx`
- Create: `src/components/feedback/InterruptedBanner.tsx`
- Create: `src/components/feedback/ErrorBanner.tsx`
- Create: `src/components/feedback/HangPrompt.tsx`
- Modify: `src/contexts/StreamContext.tsx` (tilføj elapsed-timer)
- Test: `src/components/feedback/feedback.test.tsx`

- [ ] **Step 1: Skriv fejlende test**

```tsx
// src/components/feedback/feedback.test.tsx
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { HangPrompt } from './HangPrompt'
import { LivenessIndicator } from './LivenessIndicator'

describe('feedback', () => {
  it('LivenessIndicator shows elapsed time when working', () => {
    render(<LivenessIndicator status="working" elapsedMs={42000} density="compact" />)
    expect(screen.getByText(/0:42/)).toBeInTheDocument()
  })
  it('HangPrompt fires onResume and onAbort', async () => {
    const onResume = vi.fn(), onAbort = vi.fn()
    render(<HangPrompt onResume={onResume} onAbort={onAbort} />)
    await userEvent.click(screen.getByRole('button', { name: /genoptag/i }))
    expect(onResume).toHaveBeenCalled()
    await userEvent.click(screen.getByRole('button', { name: /afbryd/i }))
    expect(onAbort).toHaveBeenCalled()
  })
})
```

- [ ] **Step 2: Kør → FAIL**

- [ ] **Step 3: Implementér de fire feedback-komponenter** (komplet kode):

```tsx
// LivenessIndicator.tsx
export function LivenessIndicator({ status, elapsedMs, density }: { status: string; elapsedMs: number; density: 'compact' | 'full' }) {
  if (status !== 'working') return null
  const s = Math.floor(elapsedMs / 1000)
  const t = `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`
  return <div className={`liveness liveness-${density}`}><span className="liveness-dot" /> arbejder — {t}</div>
}
```
```tsx
// InterruptedBanner.tsx
export function InterruptedBanner({ onResume }: { onResume: () => void }) {
  return <div className="banner banner-warn">Forbindelse afbrudt. <button type="button" onClick={onResume}>Genoptag</button></div>
}
```
```tsx
// ErrorBanner.tsx
export function ErrorBanner({ message, onDismiss }: { message: string; onDismiss: () => void }) {
  return <div className="banner banner-error"><span>{message}</span><button type="button" aria-label="luk" onClick={onDismiss}>×</button></div>
}
```
```tsx
// HangPrompt.tsx
export function HangPrompt({ onResume, onAbort }: { onResume: () => void; onAbort: () => void }) {
  return <div className="banner banner-warn">Jarvis svarer ikke. <button type="button" onClick={onResume}>Genoptag</button> <button type="button" onClick={onAbort}>Afbryd</button></div>
}
```

- [ ] **Step 4: Tilføj elapsed-timer i StreamContext** — `setInterval` mens `status==='working'`, opdatér `elapsedMs`:

```tsx
// i StreamProvider, tilføj:
useEffect(() => {
  if (status !== 'working') return
  const id = setInterval(() => setElapsedMs(Date.now() - startedAtRef.current), 500)
  return () => clearInterval(id)
}, [status])
```
(Husk `import { useEffect } from 'react'`.)

- [ ] **Step 5: Kør → PASS**

- [ ] **Step 6: Commit**

```bash
git add src/components/feedback/ src/contexts/StreamContext.tsx
git commit -m "feat(jarvis-desk): feedback-komponenter + elapsed-timer"
```

---

### Task 5.2: Shell-komponenter (Sidebar, ModeSlider, SecondaryNav, StatusBar, Composer)

**Files:**
- Create: `src/components/shell/ModeSlider.tsx`
- Create: `src/components/shell/SecondaryNav.tsx`
- Create: `src/components/shell/Sidebar.tsx`
- Create: `src/components/shell/StatusBar.tsx`
- Create: `src/components/shell/Composer.tsx`
- Test: `src/components/shell/shell.test.tsx`

Disse følger locked visuelt design. Tests fokuserer på interaktion (mode-skift, send), ikke pixels.

- [ ] **Step 1: Skriv fejlende test**

```tsx
// src/components/shell/shell.test.tsx
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ModeSlider } from './ModeSlider'
import { Composer } from './Composer'

describe('shell', () => {
  it('ModeSlider switches active mode', async () => {
    const onChange = vi.fn()
    render(<ModeSlider active="chat" onChange={onChange} />)
    await userEvent.click(screen.getByRole('button', { name: /code/i }))
    expect(onChange).toHaveBeenCalledWith('code')
  })
  it('Composer sends on Enter, not Shift+Enter', async () => {
    const onSend = vi.fn()
    render(<Composer disabled={false} onSend={onSend} model="deepseek-flash" thinking="think" />)
    const ta = screen.getByRole('textbox')
    await userEvent.type(ta, 'hej{Enter}')
    expect(onSend).toHaveBeenCalledWith('hej')
  })
})
```

- [ ] **Step 2: Kør → FAIL**

- [ ] **Step 3: Implementér de fem shell-komponenter.** Komplet kode for ModeSlider + Composer (resten følger samme mønster, struktur fra eksisterende App.tsx linje 266-425):

```tsx
// ModeSlider.tsx
const MODES = ['chat', 'cowork', 'code'] as const
export type Mode = typeof MODES[number]
export function ModeSlider({ active, onChange }: { active: Mode; onChange: (m: Mode) => void }) {
  return (
    <div className="mode-slider">
      {MODES.map((m) => (
        <button key={m} type="button" className={`mode-seg ${active === m ? 'active' : ''}`} onClick={() => onChange(m)}>
          {m === 'chat' ? 'Chat' : m === 'cowork' ? 'Cowork' : 'Code'}
        </button>
      ))}
    </div>
  )
}
```

```tsx
// Composer.tsx
import { useRef, useState } from 'react'
import { ArrowUp } from 'lucide-react'
export function Composer({ disabled, onSend, model, thinking }: { disabled: boolean; onSend: (text: string) => void; model: string; thinking: string }) {
  const [text, setText] = useState('')
  const ref = useRef<HTMLTextAreaElement>(null)
  const send = () => { const t = text.trim(); if (!t || disabled) return; onSend(t); setText('') }
  return (
    <div className="composer">
      <textarea ref={ref} className="composer-input" rows={2} disabled={disabled} value={text}
        placeholder={disabled ? 'Jarvis svarer…' : 'Skriv en besked til Jarvis...'}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() } }} />
      <div className="composer-bar">
        <div className="composer-right">
          <button type="button" className="model-pill"><span className="dot" />{model}<span className="caret">▾</span></button>
          <button type="button" className="model-pill">{thinking}<span className="caret">▾</span></button>
          <button type="button" className="composer-send" disabled={!text.trim() || disabled} onClick={send} aria-label="Send"><ArrowUp size={14} strokeWidth={2.5} /></button>
        </div>
      </div>
    </div>
  )
}
```

Sidebar/SecondaryNav/StatusBar: byg fra eksisterende App.tsx-markup (linje 266-319 sidebar, 419-425 statusbar), opdelt i komponenter. SecondaryNav er Memory/Scheduling/Settings ikoner i sidebar-foden.

- [ ] **Step 4: Kør → PASS**

- [ ] **Step 5: Commit**

```bash
git add src/components/shell/
git commit -m "feat(jarvis-desk): shell-komponenter (ModeSlider, Composer, Sidebar, SecondaryNav, StatusBar)"
```

---

## FASE 6 — Views + App-wiring + Electron-lifecycle

### Task 6.1: SetupScreen + placeholder-views

**Files:**
- Create: `src/views/SetupScreen.tsx`
- Create: `src/views/CoworkView.tsx`, `src/views/CodeView.tsx`, `src/views/MemoryView.tsx`, `src/views/SchedulingView.tsx`, `src/views/SettingsView.tsx`
- Test: `src/views/SetupScreen.test.tsx`

- [ ] **Step 1: Skriv fejlende SetupScreen-test** (gem URL+token → kalder update)

```tsx
// src/views/SetupScreen.test.tsx
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { SetupScreen } from './SetupScreen'

describe('SetupScreen', () => {
  it('saves apiBaseUrl + token', async () => {
    const onSave = vi.fn()
    render(<SetupScreen onSave={onSave} />)
    await userEvent.type(screen.getByLabelText(/server/i), 'http://10.0.0.39')
    await userEvent.type(screen.getByLabelText(/token/i), 'jvs-x')
    await userEvent.click(screen.getByRole('button', { name: /forbind/i }))
    expect(onSave).toHaveBeenCalledWith({ apiBaseUrl: 'http://10.0.0.39', authToken: 'jvs-x' })
  })
})
```

- [ ] **Step 2: Kør → FAIL**

- [ ] **Step 3: Implementér SetupScreen + placeholder-views.** Placeholders er enkle:

```tsx
// CoworkView.tsx (+ tilsvarende Code/Memory/Scheduling)
export function CoworkView() {
  return <div className="view-placeholder"><h2>Cowork</h2><p>Kommer i egen spec.</p></div>
}
// MemoryView / SchedulingView tager role-prop:
export function MemoryView({ role }: { role: 'owner' | 'member' | 'guest' }) {
  return <div className="view-placeholder"><h2>Memory</h2><p>{role === 'owner' ? 'Fuld indre memory (kommer)' : 'Din relation med Jarvis (kommer)'}</p></div>
}
```

```tsx
// SetupScreen.tsx
import { useState } from 'react'
export function SetupScreen({ onSave }: { onSave: (cfg: { apiBaseUrl: string; authToken: string }) => void }) {
  const [url, setUrl] = useState(''); const [token, setToken] = useState('')
  return (
    <div className="setup">
      <h1>Forbind til Jarvis</h1>
      <label>Server-URL<input aria-label="server" value={url} onChange={(e) => setUrl(e.target.value)} placeholder="http://10.0.0.39" /></label>
      <label>Token<input aria-label="token" type="password" value={token} onChange={(e) => setToken(e.target.value)} /></label>
      <button type="button" onClick={() => onSave({ apiBaseUrl: url.trim(), authToken: token.trim() })}>Forbind</button>
    </div>
  )
}
```

- [ ] **Step 4: Kør → PASS**

- [ ] **Step 5: Commit**

```bash
git add src/views/
git commit -m "feat(jarvis-desk): SetupScreen + placeholder-views (rolle-skopet)"
```

---

### Task 6.2: ChatView (binder StreamContext + SessionContext + rich)

**Files:**
- Create: `src/views/ChatView.tsx`
- Test: `src/views/ChatView.test.tsx`

ChatView orkestrerer: transcript (SessionContext.messages → MessageRow density=compact), igangværende stream (StreamContext.blocks → MessageRow streaming), composer → send-flow (appendOptimistic + stream.send), reconcile på done, feedback-bannere efter status.

- [ ] **Step 1: Skriv fejlende integration-test** (send → optimistic user vises; stream-delta → assistant tekst vises)

```tsx
// src/views/ChatView.test.tsx — integrationstest med ægte contexts, mocked lib
import { describe, it, expect, vi } from 'vitest'
import { render, screen, act } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ChatView } from './ChatView'
import { SessionProvider } from '../contexts/SessionContext'
import { StreamProvider } from '../contexts/StreamContext'

const handlersRef: { current: any } = { current: null }
vi.mock('../lib/streamClient', () => ({ startStream: (_r: any, h: any) => { handlersRef.current = h; return { abort: vi.fn(), getRunId: () => 'r1' } }, StreamError: class extends Error {} }))
vi.mock('../lib/api', () => ({
  listSessions: vi.fn().mockResolvedValue([{ id: 's1', title: 'T', updated_at: 'x' }]),
  getSession: vi.fn().mockResolvedValue({ session: { id: 's1', title: 'T', updated_at: 'x' }, messages: [] }),
  createSession: vi.fn(), cancelRun: vi.fn(),
}))

const cfg = { apiBaseUrl: 'http://t', authToken: 't' }

describe('ChatView integration', () => {
  it('shows optimistic user msg + streamed assistant text', async () => {
    render(<SessionProvider config={cfg}><StreamProvider config={cfg}><ChatView sessionId="s1" /></StreamProvider></SessionProvider>)
    await userEvent.type(screen.getByRole('textbox'), 'hej{Enter}')
    expect(screen.getByText('hej')).toBeInTheDocument() // optimistic
    act(() => {
      handlersRef.current.onRunId('r1')
      handlersRef.current.onEvent({ type: 'message_start', message: { id: 'r1', model: 'm', provider: 'p', lane: 'l', session_id: 's1', usage: { input_tokens: 0, output_tokens: 0 } } })
      handlersRef.current.onEvent({ type: 'content_block_start', index: 0, content_block: { type: 'text', text: '' } })
      handlersRef.current.onEvent({ type: 'content_block_delta', index: 0, delta: { type: 'text_delta', text: 'svar' } })
    })
    expect(screen.getByText('svar')).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Kør → FAIL**

- [ ] **Step 3: Implementér `ChatView.tsx`** (komplet orkestrering):

```tsx
import { useEffect } from 'react'
import { useSessions } from '../hooks/useSessions'
import { useStream } from '../hooks/useStream'
import { MessageRow } from '../components/rich/MessageRow'
import { Composer } from '../components/shell/Composer'
import { LivenessIndicator } from '../components/feedback/LivenessIndicator'
import { InterruptedBanner } from '../components/feedback/InterruptedBanner'
import { HangPrompt } from '../components/feedback/HangPrompt'
import { ErrorBanner } from '../components/feedback/ErrorBanner'

export function ChatView({ sessionId }: { sessionId: string }) {
  const sessions = useSessions()
  const stream = useStream()

  useEffect(() => { sessions.select(sessionId) }, [sessionId])

  // reconcile når stream når done
  useEffect(() => {
    if (stream.status === 'done' && stream.blocks.length > 0) {
      sessions.reconcile({ id: `a-${Date.now()}`, role: 'assistant', content: stream.blocks, created_at: new Date().toISOString(), parent_id: null })
    }
  }, [stream.status])

  const handleSend = (text: string) => {
    sessions.appendOptimistic({ id: `u-${Date.now()}`, role: 'user', content: [{ type: 'text', text }], created_at: new Date().toISOString(), parent_id: null })
    stream.send(text, { sessionId })
  }

  const streaming = stream.status === 'working'
  return (
    <div className="chatview">
      <div className="transcript">
        {sessions.messages.map((m) => <MessageRow key={m.id} role={m.role === 'user' ? 'user' : 'assistant'} blocks={m.content} density="compact" streaming={false} />)}
        {streaming && stream.blocks.length > 0 && <MessageRow role="assistant" blocks={stream.blocks} density="compact" streaming />}
        <LivenessIndicator status={stream.status} elapsedMs={stream.elapsedMs} density="compact" />
        {stream.status === 'interrupted' && <InterruptedBanner onResume={() => stream.continueFromPartial()} />}
        {stream.status === 'hung' && <HangPrompt onResume={() => stream.continueFromPartial()} onAbort={() => stream.abort()} />}
        {stream.status === 'error' && stream.error && <ErrorBanner message={stream.error.message} onDismiss={() => {}} />}
      </div>
      <Composer disabled={streaming} onSend={handleSend} model="deepseek-flash" thinking="think" />
    </div>
  )
}
```

- [ ] **Step 4: Kør → PASS**

- [ ] **Step 5: Commit**

```bash
git add src/views/ChatView.tsx src/views/ChatView.test.tsx
git commit -m "feat(jarvis-desk): ChatView — ende-til-ende orkestrering"
```

---

### Task 6.3: App.tsx wiring + Electron run_id lifecycle

**Files:**
- Rewrite: `src/App.tsx` (~40 linjer wiring)
- Modify: `electron/main.ts` (run_id ejerskab + cancel ved quit)
- Modify: `electron/preload.ts` (openExternal + run-id IPC)
- Test: manuel (E2E ikke i foundation)

- [ ] **Step 1: Genskriv `src/App.tsx`** til ren wiring:

```tsx
import { useState } from 'react'
import { SettingsProvider } from './contexts/SettingsContext'
import { SessionProvider } from './contexts/SessionContext'
import { StreamProvider } from './contexts/StreamContext'
import { useSettings } from './hooks/useSettings'
import { useSessions } from './hooks/useSessions'
import { SetupScreen } from './views/SetupScreen'
import { ChatView } from './views/ChatView'
import { CoworkView } from './views/CoworkView'
import { CodeView } from './views/CodeView'
import { MemoryView } from './views/MemoryView'
import { SchedulingView } from './views/SchedulingView'
import { SettingsView } from './views/SettingsView'
import { Sidebar } from './components/shell/Sidebar'
import { StatusBar } from './components/shell/StatusBar'
import type { Mode } from './components/shell/ModeSlider'
import './styles/tokens.css'
import './styles/app.css'

type Surface = Mode | 'memory' | 'scheduling' | 'settings'

export function App() {
  const { settings, auth, isConfigured, update } = useSettings()
  const [surface, setSurface] = useState<Surface>('chat')
  if (!settings) return null
  if (!isConfigured) return <SetupScreen onSave={(cfg) => update(cfg)} />
  const cfg = { apiBaseUrl: settings.apiBaseUrl, authToken: settings.authToken }
  return (
    <SessionProvider config={cfg}>
      <StreamProvider config={cfg}>
        <Shell surface={surface} setSurface={setSurface} role={auth?.role ?? 'guest'} />
      </StreamProvider>
    </SessionProvider>
  )
}

function Shell({ surface, setSurface, role }: { surface: Surface; setSurface: (s: Surface) => void; role: 'owner' | 'member' | 'guest' }) {
  const { activeId } = useSessions()
  return (
    <div className="window">
      <Sidebar surface={surface} onSurface={setSurface} />
      <main className="main">
        {surface === 'chat' && activeId && <ChatView sessionId={activeId} />}
        {surface === 'cowork' && <CoworkView />}
        {surface === 'code' && <CodeView />}
        {surface === 'memory' && <MemoryView role={role} />}
        {surface === 'scheduling' && <SchedulingView role={role} />}
        {surface === 'settings' && <SettingsView />}
        <StatusBar />
      </main>
    </div>
  )
}
```

Wrap i `main.tsx` med `<SettingsProvider>` (uden initialConfig — rigtig opstart loader fra Electron).

- [ ] **Step 2: Tilføj `openExternal` til preload + main**

`electron/preload.ts` — tilføj til bridge:
```ts
openExternal: (url: string) => ipcRenderer.invoke('shell:openExternal', url),
setActiveRun: (runId: string | null) => ipcRenderer.invoke('run:setActive', runId),
```

`electron/main.ts`:
```ts
import { shell } from 'electron'
let activeRunId: string | null = null
let activeApiBase = '', activeToken: string | null = null
ipcMain.handle('shell:openExternal', (_e, url: string) => { if (/^https?:|^mailto:/i.test(url)) shell.openExternal(url) })
ipcMain.handle('run:setActive', (_e, runId: string | null) => { activeRunId = runId })
ipcMain.handle('run:setAuth', (_e, base: string, token: string | null) => { activeApiBase = base; activeToken = token })
// ved before-quit: best-effort cancel af aktivt run
app.on('before-quit', async () => {
  if (activeRunId && activeApiBase) {
    try { await fetch(new URL(`/chat/runs/${activeRunId}/cancel`, activeApiBase).toString(), { method: 'POST', headers: activeToken ? { Authorization: `Bearer ${activeToken}` } : {} }) } catch { /* best-effort */ }
  }
})
```

StreamContext kalder `window.jarvisDesk.setActiveRun(runId)` i `onRunId` og `setActiveRun(null)` ved done/idle (R3 + Electron-lifecycle edge-case). Tilføj de kald i StreamContext.

- [ ] **Step 3: Verificér build** `npm run build` (forventet: ingen TS-fejl). Kør `npm test` (alle grønne). Start appen `npm run dev:electron` og bekræft: SetupScreen → forbind → ChatView loader sessioner.

- [ ] **Step 4: Commit**

```bash
git add src/App.tsx src/main.tsx electron/main.ts electron/preload.ts src/contexts/StreamContext.tsx
git commit -m "feat(jarvis-desk): App-wiring + Electron run_id lifecycle + openExternal"
```

**▶ CHECK-IN MED BJØRN efter Fase 6** — Chat-mode kører ende-til-ende mod live Jarvis.

---

## FASE 7 — Presence-dot + integration-polish

### Task 7.1: Presence-dot i chat-header (Jarvis' ønske)

**Files:**
- Create: `src/components/shell/PresenceDot.tsx`
- Modify: `src/views/ChatView.tsx` (header med presence-dot)
- Test: `src/components/shell/PresenceDot.test.tsx`

- [ ] **Step 1: Skriv fejlende test** (status → farve; INGEN affektiv data-polling)

```tsx
// src/components/shell/PresenceDot.test.tsx
import { describe, it, expect } from 'vitest'
import { render } from '@testing-library/react'
import { PresenceDot } from './PresenceDot'

describe('PresenceDot', () => {
  it('green when connected/idle', () => {
    const { container } = render(<PresenceDot status="idle" />)
    expect(container.querySelector('.presence-dot.green')).not.toBeNull()
  })
  it('yellow when working', () => {
    const { container } = render(<PresenceDot status="working" />)
    expect(container.querySelector('.presence-dot.yellow')).not.toBeNull()
  })
})
```

- [ ] **Step 2: Kør → FAIL**

- [ ] **Step 3: Implementér `PresenceDot.tsx`** (kun liveness fra StreamContext.status — ingen `/mc/affective-meta-state`):

```tsx
export function PresenceDot({ status }: { status: string }) {
  const color = status === 'working' ? 'yellow' : status === 'error' || status === 'interrupted' ? 'red' : 'green'
  return <span className={`presence-dot ${color}`} title="Jarvis" />
}
```

Tilføj en header i ChatView med `<PresenceDot status={stream.status} />` + Jarvis-navn.

- [ ] **Step 4: Kør → PASS**

- [ ] **Step 5: Commit**

```bash
git add src/components/shell/PresenceDot.tsx src/components/shell/PresenceDot.test.tsx src/views/ChatView.tsx
git commit -m "feat(jarvis-desk): presence-dot (liveness, ingen affektiv polling) — Jarvis' ønske"
```

---

### Task 7.2: Styles + endelig integrations-gennemgang

**Files:**
- Modify: `src/styles/app.css` (nye komponent-klasser: codeblock, toolcard, approvalcard, liveness, banner, presence-dot, view-placeholder)
- Test: fuld suite + manuel

- [ ] **Step 1:** Tilføj CSS for alle nye komponent-klasser, jf. locked palette i `tokens.css`. Hold accent (`--accent`) KUN til dots (presence-dot green, liveness-dot). Tool/approval-kort bruger `--bg-2/--bg-3`.

- [ ] **Step 2:** Kør fuld suite: `npm test` (alle grønne).

- [ ] **Step 3:** Kør `npm run build` (ingen TS-fejl).

- [ ] **Step 4:** Manuel smoke mod live Jarvis (10.0.0.39): send besked, se streaming, tool-cards (compact), afbryd midt-i (verificér server-cancel via runtime-log), luk vindue midt-i stream (verificér cancel ved quit).

- [ ] **Step 5: Commit**

```bash
git add src/styles/app.css
git commit -m "style(jarvis-desk): komponent-styles + integrations-polish"
```

---

## Afslutning

Efter Fase 7: brug **superpowers:finishing-a-development-branch** til at verificere tests og beslutte merge/PR.

**Eksplicit IKKE i denne plan** (egne specs/planer senere): Cowork/Code/Memory/Scheduling indhold, Chat slash-kommandoer/voice/screenshot/søg, virtualisering, E2E-tests, lys-tema, ægte server-resume-endpoint.
