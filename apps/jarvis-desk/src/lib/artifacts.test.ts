import { describe, it, expect } from 'vitest'
import { detectArtifacts } from './artifacts'
import type { ContentBlock } from './sseProtocol'

const code = (lines: number) => Array.from({ length: lines }, (_, i) => `line ${i}`).join('\n')

describe('detectArtifacts', () => {
  it('markerer kodeblok >= 15 linjer som code-artifact', () => {
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
