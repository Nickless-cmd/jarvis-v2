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

  // Phase 2: fil-artifacts bindes til FAKTISKE tool_use-kald (target_path),
  // ikke til stier nævnt i prosa — ellers hober panelet tilfældige filer op.
  it('IGNORERER fil-sti nævnt i prosa-tekst (ingen panel-ophobning)', () => {
    const refs = detectArtifacts([{ type: 'text', text: 'Se docs/superpowers/specs/x.md for detaljer' }])
    expect(refs.filter((r) => r.kind === 'file')).toEqual([])
  })

  it('markerer tool_use target_path som file-artifact', () => {
    const refs = detectArtifacts([
      { type: 'tool_use', id: 't1', name: 'read_file', input: { target_path: 'docs/superpowers/specs/x.md' } },
    ])
    expect(refs.find((r) => r.kind === 'file')).toMatchObject({ kind: 'file', filePath: 'docs/superpowers/specs/x.md' })
  })

  it('læser fil-sti fra tool_use partialJson når input er tom', () => {
    const refs = detectArtifacts([
      { type: 'tool_use', id: 't2', name: 'read_file', input: {}, partialJson: '{"target_path": "core/services/x.py"}' },
    ])
    expect(refs.find((r) => r.kind === 'file')).toMatchObject({ filePath: 'core/services/x.py' })
  })

  it('ignorerer tool_use sti udenfor path-jail-rødder', () => {
    const refs = detectArtifacts([
      { type: 'tool_use', id: 't3', name: 'read_file', input: { target_path: '/etc/passwd' } },
    ])
    expect(refs.filter((r) => r.kind === 'file')).toEqual([])
  })

  it('dedup: samme fil to gange → ét artifact', () => {
    const refs = detectArtifacts([
      { type: 'tool_use', id: 't4', name: 'read_file', input: { target_path: 'apps/x.ts' } },
      { type: 'tool_use', id: 't5', name: 'read_file', input: { target_path: 'apps/x.ts' } },
    ])
    expect(refs.filter((r) => r.kind === 'file')).toHaveLength(1)
  })
})
