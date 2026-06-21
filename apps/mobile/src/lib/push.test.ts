jest.mock('@react-native-firebase/messaging', () => ({
  __esModule: true,
  default: () => ({
    requestPermission: jest.fn(),
    getToken: jest.fn(),
    onTokenRefresh: jest.fn(),
    onMessage: jest.fn(),
  }),
}))
jest.mock('@notifee/react-native', () => ({
  __esModule: true,
  default: { createChannel: jest.fn(), displayNotification: jest.fn() },
  AndroidImportance: { HIGH: 4 },
}))

import { buildNotification } from './push'

describe('buildNotification', () => {
  it('answer_ready -> titel + body fra hentet besked', () => {
    const n = buildNotification({ kind: 'answer_ready', session_id: 's1' }, 'Hej Bjørn, her er svaret')
    expect(n.title).toMatch(/Jarvis/)
    expect(n.body).toContain('her er svaret')
    expect(n.data.session_id).toBe('s1')
  })

  it('answer_ready uden hentet body -> fallback', () => {
    const n = buildNotification({ kind: 'answer_ready' }, null)
    expect(n.body).toBe('Nyt svar')
  })

  it('reminder -> bruger preview', () => {
    const n = buildNotification({ kind: 'reminder', preview: 'Ring til lægen' }, null)
    expect(n.title).toMatch(/Påmindelse/)
    expect(n.body).toContain('Ring til lægen')
  })

  it('team_invite -> bruger title+preview, IKKE "Jarvis svarede"', () => {
    const n = buildNotification(
      { kind: 'team_invite', title: 'Invitation til Familie', preview: 'Bjørn inviterede dig til Familie' },
      null,
    )
    expect(n.title).toBe('Invitation til Familie')
    expect(n.body).toContain('inviterede dig')
    expect(n.title).not.toMatch(/svarede/)
  })

  it('team_invite uden title -> fallback', () => {
    const n = buildNotification({ kind: 'team_invite' }, null)
    expect(n.title).toBe('Invitation til team')
  })
})
