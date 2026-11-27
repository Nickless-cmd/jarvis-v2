import { describe, expect, it } from 'vitest'
import { codeVisibleBlocks, codeAnswerStarted } from './codeTurnPresentation'
import type { ContentBlock } from './sseProtocol'

describe('code presentation with server ahead of reader', () => {
  const answer: ContentBlock = { type: 'text', text: 'An answer still arriving', phase: 'final_answer' }
  const tool: ContentBlock = { type: 'tool_use', id: 'late', name: 'bash', input: {} }
  const synthesis: ContentBlock = { type: 'text', text: 'Synthesis', phase: 'commentary' }
  const source = [answer, tool, synthesis]
  it('holds later work behind unfinished paced text without changing the text cursor', () => {
    const shown = { ...answer, text: 'An answer' }
    expect(codeVisibleBlocks(source, [shown, tool, { ...synthesis, text: '' }])).toEqual([shown])
    expect(codeVisibleBlocks(source, source)).toBe(source)
  })
  it('does not start the fold before the first displayed answer character', () => {
    expect(codeAnswerStarted([{ ...answer, text: '' }])).toBe(false)
    expect(codeAnswerStarted([{ ...answer, text: 'A' }])).toBe(true)
  })
})
