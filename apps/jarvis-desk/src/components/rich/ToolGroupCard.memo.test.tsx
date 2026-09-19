import { describe, it, expect, vi } from 'vitest'
import { render } from '@testing-library/react'

const kald = vi.hoisted(() => ({ n: 0 }))
vi.mock('../../lib/toolRound', async (orig) => {
  const ægte = await orig<typeof import('../../lib/toolRound')>()
  return { ...ægte, summarizeRound: (...a: Parameters<typeof ægte.summarizeRound>) => { kald.n++; return ægte.summarizeRound(...a) } }
})

import { ToolGroupCard } from './ToolGroupCard'

const tool = (id: string, extra: Record<string, unknown> = {}) =>
  ({ type: 'tool_use', id, name: 'bash', input: { command: `ls ${id}`, description: `Lister ${id}` }, status: 'done', result: 'ok', ...extra }) as never

describe('ToolGroupCard memo (profileret 19/9-2026)', () => {
  it('en ny runde-OBJEKT med de SAMME værktøjer genberegner intet', () => {
    const a = tool('a'); const b = tool('b')
    const { rerender } = render(<ToolGroupCard block={{ type: 'tool_group', kind: 'round', count: 2, tools: [a, b] } as never} density="compact" />)
    const efterFoerste = kald.n
    // Som under streaming: groupToolRounds bygger et nyt objekt ved hver delta.
    for (let i = 0; i < 20; i++) rerender(<ToolGroupCard block={{ type: 'tool_group', kind: 'round', count: 2, tools: [a, b] } as never} density="compact" />)
    expect(kald.n).toBe(efterFoerste)
  })

  it('men et værktøj der ændrer sig (resultat foldet på) genberegner', () => {
    const a = tool('a'); const b = tool('b', { status: 'running', result: undefined })
    const { rerender } = render(<ToolGroupCard block={{ type: 'tool_group', kind: 'round', count: 2, tools: [a, b] } as never} density="compact" />)
    const foer = kald.n
    rerender(<ToolGroupCard block={{ type: 'tool_group', kind: 'round', count: 2, tools: [a, { ...(b as object), status: 'done', result: 'ok' } as never] } as never} density="compact" />)
    expect(kald.n).toBe(foer + 1)
  })
})

describe('lange samtaler: beskeder uden for skærmen springes over', () => {
  it('CSS-reglen findes (den levende besked er ikke en .msg-block)', async () => {
    const fs = await import('node:fs'); const path = await import('node:path')
    const css = fs.readFileSync(path.resolve(__dirname, '../../styles/transcript-ydelse.css'), 'utf8')
    expect(css).toMatch(/\.transcript > \.msg-block \{\s*content-visibility: auto;\s*contain-intrinsic-size: auto 240px;/)
  })

  it('scroll-ankeret er det ENESTE der må forankres til', async () => {
    const fs = await import('node:fs'); const path = await import('node:path')
    const css = fs.readFileSync(path.resolve(__dirname, '../../styles/transcript-ydelse.css'), 'utf8')
    expect(css).toMatch(/\.transcript \* \{ overflow-anchor: none; \}/)
    expect(css).toMatch(/\.transcript > \.bund-anker \{ overflow-anchor: auto;/)
  })

  it.each(['ChatView', 'CodeView'])('%s har ankeret som SIDSTE barn af transcriptet', async (vis) => {
    const fs = await import('node:fs'); const path = await import('node:path'); const ts = await import('typescript')
    const kilde = fs.readFileSync(path.resolve(__dirname, `../../views/${vis}.tsx`), 'utf8')
    const sf = ts.createSourceFile(`${vis}.tsx`, kilde, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX)
    let sidste = ''
    const besoeg = (n: import('typescript').Node) => {
      if (ts.isJsxElement(n) && n.openingElement.attributes.properties.some((a) => ts.isJsxAttribute(a) && a.name.getText(sf) === 'ref' && a.initializer?.getText(sf) === '{transcriptRef}')) {
        const boern = n.children.filter((c) => ts.isJsxElement(c) || ts.isJsxSelfClosingElement(c))
        sidste = boern.at(-1)?.getText(sf) ?? ''
      }
      ts.forEachChild(n, besoeg)
    }
    besoeg(sf)
    expect(sidste).toContain('bund-anker')
  })

  it.each(['ChatView', 'CodeView'])('%s importerer den', async (vis) => {
    const fs = await import('node:fs'); const path = await import('node:path'); const ts = await import('typescript')
    const kilde = fs.readFileSync(path.resolve(__dirname, `../../views/${vis}.tsx`), 'utf8')
    const sf = ts.createSourceFile(`${vis}.tsx`, kilde, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX)
    const imports = sf.statements.filter(ts.isImportDeclaration).map((d) => (d.moduleSpecifier as import('typescript').StringLiteral).text)
    expect(imports).toContain('../styles/transcript-ydelse.css')
  })
})
