import { describe, it, expect } from 'vitest'
import { streamReducer, initialStreamState, type StreamState } from './streamReducer'

// Regression (Bjørn 10. jul, sort skærm — ægte fangede fejl:
// "Cannot read properties of undefined (reading 'type')" i Array.findIndex i
// reduceren). Rod: med flag ON dual-emitter serveren tool_result som BÅDE en
// content-blok (folder → efterlader undefined-HUL på sit index) OG et
// system_event. Reducerens system_event-håndtering gjorde
// `state.blocks.findIndex(b => b.type === 'tool_use' ...)` UDEN `b &&`-guard →
// ramte hullet → crashede HELE reduceren → sort skærm. Fix: `b &&`-guard.
function ev(s: StreamState, e: unknown): StreamState { return streamReducer(s, e as never) }

describe('reducer crasher ikke på sparsomt hul under dual-emit', () => {
  it('2 tools m. content-blok-fold + system_event tool_result kaster ikke', () => {
    let s = initialStreamState()
    s = ev(s, { type: 'message_start', message: { id: 'r', model: '', provider: '', lane: '', session_id: null, usage: { input_tokens: 0, output_tokens: 0 } } })
    s = ev(s, { type: 'content_block_start', index: 0, content_block: { type: 'text', text: '' } })
    s = ev(s, { type: 'content_block_delta', index: 0, delta: { type: 'text_delta', text: 'ok' } })
    // tool 1
    s = ev(s, { type: 'content_block_start', index: 1, content_block: { type: 'tool_use', id: 't1', name: 'bash', input: {} } })
    s = ev(s, { type: 'content_block_stop', index: 1 })
    s = ev(s, { type: 'content_block_start', index: 2, content_block: { type: 'tool_result', tool_use_id: 't1', status: 'done', content: 'a' } }) // folder → hul@2
    s = ev(s, { type: 'content_block_stop', index: 2 })
    // tool 2 → tool_use@3 gør hul@2 synligt
    s = ev(s, { type: 'content_block_start', index: 3, content_block: { type: 'tool_use', id: 't2', name: 'bash', input: {} } })
    s = ev(s, { type: 'content_block_stop', index: 3 })
    // DEN dual-emittede system_event for tool 2 → findIndex over [text, tool_use, <hul>, tool_use]
    expect(() => {
      s = ev(s, { type: 'system_event', kind: 'tool_result', payload: { tool_use_id: 't2', status: 'ok', result: 'b' } })
    }).not.toThrow()
    // og working_step-stien (samme guard)
    expect(() => {
      s = ev(s, { type: 'system_event', kind: 'working_step', payload: { tool_id: 't2', status: 'done', detail: 'kører' } })
    }).not.toThrow()
    // folding virkede stadig: begge tool_use bærer deres resultat
    const t2 = s.blocks.find((b) => b && b.type === 'tool_use' && b.id === 't2') as { result?: string }
    expect(t2.result).toBe('b')
  })
})
