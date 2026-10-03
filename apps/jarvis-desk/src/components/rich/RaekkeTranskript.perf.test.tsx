import { describe, expect, it, vi } from 'vitest'
import { render } from '@testing-library/react'
import { RaekkeTranskript } from './RaekkeTranskript'
import { MarkdownRenderer } from './MarkdownRenderer'
import { summarizeRound } from '../../lib/toolRound'
import type { ContentBlock } from '../../lib/sseProtocol'

vi.mock('./MarkdownRenderer', () => ({
  MarkdownRenderer: vi.fn(({ text }: { text: string }) => <p>{text}</p>),
}))
vi.mock('../../lib/toolRound', async (importOriginal) => {
  const original = await importOriginal<typeof import('../../lib/toolRound')>()
  return { ...original, summarizeRound: vi.fn(original.summarizeRound) }
})

const tool = (id: string): ContentBlock => ({
  type: 'tool_use', id, name: 'bash', input: { command: 'true' }, status: 'done',
})

describe('live transcript work', () => {
  it('genrenderer ikke en færdig syntese når den seneste tekst får et delta', () => {
    const past = 'Den forrige undersøgelse er afsluttet.'
    const blocks: ContentBlock[] = [tool('one'), { type: 'text', text: past }, tool('two'), { type: 'text', text: 'Nu' }]
    const view = render(<RaekkeTranskript blocks={blocks} streaming />)
    const countPast = () => vi.mocked(MarkdownRenderer).mock.calls.filter(([props]) => props.text === past).length
    expect(countPast()).toBe(1)

    view.rerender(<RaekkeTranskript blocks={[...blocks.slice(0, -1), { type: 'text', text: 'Nu fortsætter jeg' }]} streaming />)
    expect(countPast()).toBe(1)
  })

  it('genberegner ikke afsluttede arbejdsrunder når kun slutteksten ændres', () => {
    vi.mocked(summarizeRound).mockClear()
    const blocks: ContentBlock[] = [tool('one'), { type: 'text', text: 'Første fund.' }, tool('two'), { type: 'text', text: 'Nu' }]
    const view = render(<RaekkeTranskript blocks={blocks} streaming />)
    const initial = vi.mocked(summarizeRound).mock.calls.length
    expect(initial).toBeGreaterThan(0)

    view.rerender(<RaekkeTranskript blocks={[...blocks.slice(0, -1), { type: 'text', text: 'Nu fortsætter jeg' }]} streaming />)
    expect(vi.mocked(summarizeRound).mock.calls.length).toBe(initial)
  })
})
