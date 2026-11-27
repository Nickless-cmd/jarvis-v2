import { describe, expect, it } from 'vitest'
import { initialStreamState, streamReducer, type StreamState } from './streamReducer'
import { codeAnswerStarted, codeHasLateWork } from './codeTurnPresentation'
import { opdel } from './raekkeModel'
import type { ContentBlock } from './sseProtocol'

describe('explicit code protocol supersedes legacy length classification', () => {
  it('keeps even a long legacy-final synthesis in work until the declared answer', () => {
    const work: ContentBlock[] = [
      { type: 'tool_use', id: 'a', name: 'bash', input: {} },
      { type: 'text', text: 'Long synthesis '.repeat(100), phase: 'final_answer', code_answer_protocol: 1 },
    ]
    expect(codeAnswerStarted(work)).toBe(false)
    expect(opdel(work, true, true).svar).toEqual([])
    // Server stop can precede the reader reaching the declared boundary.
    expect(opdel(work, false, false).svar).toEqual([])
    const all: ContentBlock[] = [...work,
      { type: 'text', text: '\nOK', phase: 'commentary', code_answer_protocol: 1, code_answer_start: true },
      { type: 'tool_use', id: 'late', name: 'bash', input: {} },
      { type: 'text', text: 'Saved', phase: 'commentary', code_answer_protocol: 1 },
    ]
    expect(codeAnswerStarted(all)).toBe(true)
    expect(codeHasLateWork(all)).toBe(true)
    expect(opdel(all, false).svar.filter(b => b.type === 'text').map(b => b.text)).toEqual(['\nOK', 'Saved'])
  })
  it('preserves a wire declaration, and rejects another runs boundary', () => {
    let state: StreamState = { ...initialStreamState(), activeRunId: 'r' }
    state = streamReducer(state, { type: 'content_block_start', index: 0, content_block: {
      type: 'text', text: 'Early', phase: 'final_answer', code_answer_protocol: 1,
    } })
    expect(codeAnswerStarted(state.blocks)).toBe(false)
    state = streamReducer(state, { type: 'content_block_start', index: 1, content_block: {
      type: 'text', text: 'OK', code_answer_protocol: 1, code_answer_start: true,
    } })
    expect(state.blocks[1]).toMatchObject({ code_answer_start: true, code_answer_protocol: 1 })
    expect(codeAnswerStarted(state.blocks)).toBe(true)
    const fallback = streamReducer(state, { type: 'system_event', kind: 'code_answer_boundary', payload: { run_id: 'other', index: 0 } })
    expect(fallback).toBe(state)
  })
})
