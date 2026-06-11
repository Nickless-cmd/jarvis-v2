import { describe, it, expect } from 'vitest'
import { isStreamEvent } from './sseProtocol'

describe('sseProtocol', () => {
  it('validates a well-formed message_start event', () => {
    const e = { type: 'message_start', message: { id: 'visible-x', model: 'm', provider: 'p', lane: 'primary', session_id: 's', usage: { input_tokens: 0, output_tokens: 0 } } }
    expect(isStreamEvent(e)).toBe(true)
  })
  it('rejects object without type', () => {
    expect(isStreamEvent({ foo: 1 })).toBe(false)
  })
  it('rejects non-object', () => {
    expect(isStreamEvent('nope')).toBe(false)
    expect(isStreamEvent(null)).toBe(false)
  })
})
