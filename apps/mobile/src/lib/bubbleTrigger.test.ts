import { shouldFloatOnPush } from './bubbleTrigger'

describe('shouldFloatOnPush', () => {
  it('true for answer_ready', () => {
    expect(shouldFloatOnPush({ kind: 'answer_ready', session_id: 's1' })).toBe(true)
  })
  it('true for reminder', () => {
    expect(shouldFloatOnPush({ kind: 'reminder', session_id: 's1' })).toBe(true)
  })
  it('false for presence', () => {
    expect(shouldFloatOnPush({ kind: 'presence', session_id: 's1' })).toBe(false)
  })
  it('false uden session_id', () => {
    expect(shouldFloatOnPush({ kind: 'answer_ready' })).toBe(false)
  })
  it('false for malformet/tom', () => {
    expect(shouldFloatOnPush({})).toBe(false)
    expect(shouldFloatOnPush(undefined as unknown as Record<string, string>)).toBe(false)
  })
})
