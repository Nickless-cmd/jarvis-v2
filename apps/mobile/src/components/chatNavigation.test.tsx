import { render } from '@testing-library/react-native'
import { MessageList, medNyeLinje, stickyIndex } from './MessageList'
import type { ChatMessage } from '../lib/types'

const m = (id: string, role: 'user' | 'assistant', content: string) =>
  ({ id, role, content, created_at: '2026-09-19T00:00:00Z' }) as ChatMessage

describe('«Nye beskeder» (Claude Desktop §10)', () => {
  it('står lige over den første række der hører til den nye besked', () => {
    const rows = [{ key: 'u1' }, { key: 'a1' }, { key: 'group-a2-t1' }, { key: 'a2-b3' }]
    expect(medNyeLinje(rows, 'a2').map((r) => r.key)).toEqual(['u1', 'a1', 'nye-a2', 'group-a2-t1', 'a2-b3'])
  })
  it('ikke over ALT — står den nye øverst, er intet ældre at skille fra', () => {
    expect(medNyeLinje([{ key: 'a1' }], 'a1').map((r) => r.key)).toEqual(['a1'])
  })
  it('tegnes i listen', async () => {
    const s = await render(<MessageList messages={[m('u1', 'user', 'Hej'), m('a1', 'assistant', 'Gammelt'), m('a2', 'assistant', 'Nyt')]} blocks={[]} nyeFra="a2" />)
    expect(s.getByTestId('nye-beskeder')).toBeTruthy()
  })
  it('uden noget nyt: ingen linje', async () => {
    const s = await render(<MessageList messages={[m('u1', 'user', 'Hej')]} blocks={[]} nyeFra={null} />)
    expect(s.queryByTestId('nye-beskeder')).toBeNull()
  })
})

describe('sticky prompt (Claude Desktop §10)', () => {
  // Inverteret: [a2, u2, a1, u1] → brugerflag [nej, ja, nej, ja].
  const flag = [false, true, false, true]
  it('er din besked ude af syne, står den nærmeste ovenover fast', () => {
    expect(stickyIndex(flag, [0, 0])).toBe(1)
  })
  it('er en af dine beskeder i syne, står intet fast', () => {
    expect(stickyIndex(flag, [0, 1])).toBeNull()
  })
  it('læser man det ældre svar, er det DET spørgsmål', () => {
    expect(stickyIndex(flag, [2, 2])).toBe(3)
  })
  it('intet målt endnu → intet', () => {
    expect(stickyIndex(flag, null)).toBeNull()
  })
})
