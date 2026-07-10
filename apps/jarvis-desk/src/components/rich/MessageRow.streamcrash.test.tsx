import { describe, it, expect } from 'vitest'
import { render } from '@testing-library/react'
import { MessageRow } from './MessageRow'
import { streamReducer, initialStreamState, type StreamState } from '../../lib/streamReducer'
import crashContent from '../../lib/__fixtures__/crashContent.json'

// Repro af LIVE streaming-crashet: byg SSE-event-sekvensen fra den ægte
// content_json (Strategy 2: tool_result som content-blok på nyt index) og fød
// reduceren, render stream.blocks undervejs. 36 tools → ~36 sparsomme huller.
function buildEvents(blocks: Array<Record<string, unknown>>) {
  const ev: unknown[] = [{ type: 'message_start', message: { id: 'r', model: '', provider: '', lane: '', session_id: null, usage: { input_tokens: 0, output_tokens: 0 } } }]
  blocks.forEach((b, i) => {
    if (b.type === 'text') {
      ev.push({ type: 'content_block_start', index: i, content_block: { type: 'text', text: '' } })
      ev.push({ type: 'content_block_delta', index: i, delta: { type: 'text_delta', text: String(b.text ?? '') } })
      ev.push({ type: 'content_block_stop', index: i })
    } else if (b.type === 'tool_use') {
      ev.push({ type: 'content_block_start', index: i, content_block: { type: 'tool_use', id: b.id, name: b.name, input: {} } })
      ev.push({ type: 'content_block_delta', index: i, delta: { type: 'input_json_delta', partial_json: typeof b.input === 'string' ? b.input : JSON.stringify(b.input ?? {}) } })
      ev.push({ type: 'content_block_stop', index: i })
    } else if (b.type === 'tool_result') {
      ev.push({ type: 'content_block_start', index: i, content_block: { type: 'tool_result', tool_use_id: b.tool_use_id, status: b.status, content: b.content, is_error: b.is_error } })
      ev.push({ type: 'content_block_stop', index: i })
    }
  })
  ev.push({ type: 'message_delta', delta: { stop_reason: 'end_turn' }, usage: { input_tokens: 0, output_tokens: 0, cache_hit_tokens: 0, cache_miss_tokens: 0 } })
  ev.push({ type: 'message_stop' })
  return ev
}

describe('LIVE streaming af crash-run kaster ikke', () => {
  it('reducer + render undervejs (hver 10. event) uden throw', () => {
    const events = buildEvents(crashContent as Array<Record<string, unknown>>)
    let s: StreamState = initialStreamState()
    expect(() => {
      events.forEach((e, idx) => {
        s = streamReducer(s, e as never)
        // render løbende (som React ville) hver 10. event + til sidst
        if (idx % 10 === 0 || idx === events.length - 1) {
          render(<MessageRow role="assistant" blocks={s.blocks as never} density="compact" streaming />)
        }
      })
    }).not.toThrow()
  })
})
