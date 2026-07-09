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

  it('message_start captures the run model/provider/lane (footer-bug fix)', () => {
    const s = reduce([
      { type: 'message_start', message: { id: 'r1', model: 'glm-5.1', provider: 'ollama', lane: 'primary', session_id: 's', usage: { input_tokens: 0, output_tokens: 0 } } },
    ])
    expect(s.model).toBe('glm-5.1')
    expect(s.provider).toBe('ollama')
    expect(s.lane).toBe('primary')
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

describe('streamReducer — usage.input fra message_delta (context-ring #9)', () => {
  it('fanger input_tokens fra message_delta', () => {
    const s = reduce([
      { type: 'message_start', message: { id: 'r', model: 'm', provider: 'p', lane: 'l', session_id: 's', usage: { input_tokens: 0, output_tokens: 0 } } },
      { type: 'message_delta', delta: { stop_reason: 'end_turn' }, usage: { input_tokens: 120000, output_tokens: 50, cache_hit_tokens: 8000, cache_miss_tokens: 0 } },
    ] as StreamEvent[])
    expect(s.usage.input).toBe(120000)
    expect(s.usage.cacheHit).toBe(8000)
  })

  it('system_event tool_result sets result + status on the tool_use block', () => {
    const s = reduce([
      { type: 'content_block_start', index: 0, content_block: { type: 'tool_use', id: 't1', name: 'web_search', input: { query: 'vejr' } } },
      { type: 'system_event', kind: 'tool_result', payload: { tool_use_id: 't1', status: 'ok', result: '3 resultater' } },
    ] as StreamEvent[])
    const b = s.blocks[0]
    expect(b?.type).toBe('tool_use')
    if (b?.type === 'tool_use') {
      expect(b.status).toBe('done')
      expect(b.result).toBe('3 resultater')
    }
  })
})

  it('preserves blocks on a second message_start for the SAME run (reconnect/replay)', () => {
    // Byg en tur med en tool-blok + tekst, som brugeren allerede har set.
    let s = streamReducer(initialStreamState(), { type: 'message_start', message: { id: 'visible-same', model: 'm', provider: 'p', lane: 'primary', session_id: 's', usage: { input_tokens: 0, output_tokens: 0 } } } as any)
    s = streamReducer(s, { type: 'content_block_start', index: 0, content_block: { type: 'tool_use', id: 't1', name: 'db_query', input: {} } } as any)
    s = streamReducer(s, { type: 'content_block_start', index: 1, content_block: { type: 'text', text: 'Første linje' } } as any)
    expect(s.blocks.length).toBe(2)
    // Reconnect/relay-replay sender message_start igen med SAMME run-id.
    const s2 = streamReducer(s, { type: 'message_start', message: { id: 'visible-same', model: 'm', provider: 'p', lane: 'primary', session_id: 's', usage: { input_tokens: 0, output_tokens: 0 } } } as any)
    // Tool-blok + tekst må IKKE forsvinde.
    expect(s2.blocks.length).toBe(2)
    expect(s2.blocks[0]).toMatchObject({ type: 'tool_use', id: 't1' })
  })

  it('resets blocks on a message_start for a DIFFERENT run', () => {
    let s = streamReducer(initialStreamState(), { type: 'message_start', message: { id: 'run-a', model: 'm', provider: 'p', lane: 'primary', session_id: 's', usage: { input_tokens: 0, output_tokens: 0 } } } as any)
    s = streamReducer(s, { type: 'content_block_start', index: 0, content_block: { type: 'text', text: 'gammelt' } } as any)
    const s2 = streamReducer(s, { type: 'message_start', message: { id: 'run-b', model: 'm', provider: 'p', lane: 'primary', session_id: 's', usage: { input_tokens: 0, output_tokens: 0 } } } as any)
    expect(s2.blocks.length).toBe(0)
  })

describe('streamReducer tool_result content-blok', () => {
  it('folder tool_result-content-blok ind på matchende tool_use', () => {
    let s = initialStreamState()
    s = streamReducer(s, { type: 'content_block_start', index: 0, content_block: { type: 'tool_use', id: 'toolu_1', name: 'bash', input: {} } } as any)
    s = streamReducer(s, { type: 'content_block_start', index: 1, content_block: { type: 'tool_result', tool_use_id: 'toolu_1', status: 'done', content: 'ok' } } as any)
    const tu = s.blocks.find((b) => b && b.type === 'tool_use') as any
    expect(tu.status).toBe('done')
    expect(tu.result).toBe('ok')
    expect(s.blocks.filter(Boolean).some((b: any) => b.type === 'tool_result')).toBe(false)
  })
  it('bevarer den gamle system_event tool_result-sti (dual-read)', () => {
    let s = initialStreamState()
    s = streamReducer(s, { type: 'content_block_start', index: 0, content_block: { type: 'tool_use', id: 'toolu_9', name: 'bash', input: {} } } as any)
    s = streamReducer(s, { type: 'system_event', kind: 'tool_result', payload: { tool_use_id: 'toolu_9', status: 'ok', result: 'via-legacy' } } as any)
    const tu = s.blocks.find((b) => b && b.type === 'tool_use') as any
    expect(tu.result).toBe('via-legacy')
  })
})
