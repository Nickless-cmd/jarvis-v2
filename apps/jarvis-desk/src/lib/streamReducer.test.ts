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
    expect(b).toBeDefined()
    expect(b?.type).toBe('tool_use')
    if (b && b.type === 'tool_use') {
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
    if (b && b.type === 'tool_use') {
      expect(b.status).toBe('done')
      expect(b.result).toBe('ok')
    }
  })
})

describe('streamReducer — tool_result status (Phase 2)', () => {
  it('tool_result system_event sætter tool_use-blok status til done', () => {
    const s = reduce([
      { type: 'content_block_start', index: 0, content_block: { type: 'tool_use', id: 'cap_1', name: 'read_file', input: {} } },
      { type: 'content_block_stop', index: 0 },
      { type: 'system_event', kind: 'tool_result', payload: { tool_use_id: 'cap_1', tool: 'read_file', status: 'ok' } },
    ] as StreamEvent[])
    const b = s.blocks[0]
    expect(b?.type).toBe('tool_use')
    if (b && b.type === 'tool_use') expect(b.status).toBe('done')
  })

  it('tool_result med status error sætter error', () => {
    const s = reduce([
      { type: 'content_block_start', index: 0, content_block: { type: 'tool_use', id: 'cap_2', name: 'bash', input: {} } },
      { type: 'system_event', kind: 'tool_result', payload: { tool_use_id: 'cap_2', status: 'failed' } },
    ] as StreamEvent[])
    const b = s.blocks[0]
    if (b && b.type === 'tool_use') expect(b.status).toBe('error')
  })

  it('tool_result for ukendt id ignoreres gracefully', () => {
    const s = reduce([
      { type: 'content_block_start', index: 0, content_block: { type: 'text', text: 'hej' } },
      { type: 'system_event', kind: 'tool_result', payload: { tool_use_id: 'mangler', status: 'ok' } },
    ] as StreamEvent[])
    expect(s.blocks[0]).toEqual({ type: 'text', text: 'hej' })
  })
})
