import { isWorking, computeUnread } from './sessionStatus'
import type { ChatSession } from './types'

const S = (id: string, count: number): ChatSession =>
  ({ id, title: id, message_count: count } as ChatSession)

describe('isWorking', () => {
  it('true når session-id er i active-runs', () => {
    expect(isWorking('s1', ['s1', 's2'])).toBe(true)
    expect(isWorking('s3', ['s1', 's2'])).toBe(false)
  })
})

describe('computeUnread', () => {
  it('ulæst når server-count > gemt og ikke aktiv', () => {
    const sessions = [S('s1', 5), S('s2', 3), S('s3', 0)]
    const lastSeen = { s1: 3, s2: 3 }
    const r = computeUnread(sessions, lastSeen, 'none')
    expect(r).toEqual({ s1: true, s2: false, s3: false })
  })
  it('aktiv session er aldrig ulæst', () => {
    const r = computeUnread([S('s1', 9)], { s1: 0 }, 's1')
    expect(r.s1).toBe(false)
  })
  it('manglende lastSeen → 0-baseline', () => {
    const r = computeUnread([S('s1', 2)], {}, 'none')
    expect(r.s1).toBe(true)
  })
})
