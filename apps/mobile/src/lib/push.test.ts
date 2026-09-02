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
  default: {
    createChannel: jest.fn(),
    displayNotification: jest.fn(),
    getInitialNotification: jest.fn(),
    onForegroundEvent: jest.fn(() => () => {})
  },
  AndroidImportance: { HIGH: 4 },
  AndroidStyle: { BIGTEXT: 'bigtext' },
  EventType: { PRESS: 1 },
}))

import notifee from '@notifee/react-native'
import { buildNotification, isApprovalPush, openedFromApprovalPush } from './push'

describe('buildNotification', () => {
  it('answer_ready -> titel + body fra hentet besked', () => {
    const n = buildNotification({ kind: 'answer_ready', session_id: 's1' }, 'Hej Bjørn, her er svaret')
    expect(n.title).toMatch(/Jarvis/)
    expect(n.body).toContain('her er svaret')
    expect(n.data.session_id).toBe('s1')
  })

  it('answer_ready uden hentet body -> server-preview fallback', () => {
    const n = buildNotification({ kind: 'answer_ready', preview: 'Serverens svar-tekst' }, null)
    expect(n.body).toBe('Serverens svar-tekst')
  })

  it('answer_ready uden hentet body OG uden preview -> generisk fallback', () => {
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

  it('error -> ærlig fejl-titel + serverens besked, IKKE "Jarvis svarede"', () => {
    const n = buildNotification(
      { kind: 'error', message: 'Model-udbyderen svarede ikke', severity: 'error' },
      null,
    )
    expect(n.title).toMatch(/problem/i)
    expect(n.title).not.toMatch(/svarede/)
    expect(n.body).toContain('Model-udbyderen svarede ikke')
  })

  it('error kritisk -> kritisk titel', () => {
    const n = buildNotification({ kind: 'error', severity: 'critical', message: 'Kerne-fejl' }, null)
    expect(n.title).toMatch(/kritisk/i)
    expect(n.body).toContain('Kerne-fejl')
  })
})

describe('approval_requested (fase 1s leverance-kriterie)', () => {
  it('bruger serverens egen titel — ikke «Jarvis svarede»', () => {
    const n = buildNotification(
      {
        kind: 'approval_requested',
        request_id: 'cap-1',
        title: 'Godkendelse kræves',
        preview: 'run non-destructive command'
      },
      null
    )
    expect(n.title).toBe('Godkendelse kræves')
    expect(n.body).toBe('run non-destructive command')
  })

  it('har en titel selv hvis serveren glemmer at sende en', () => {
    const n = buildNotification({ kind: 'approval_requested' }, null)
    expect(n.title).toBe('Godkendelse kræves')
  })

  it('falder tilbage på kapabilitetsnavnet, så beskeden aldrig bliver intetsigende', () => {
    const n = buildNotification(
      { kind: 'approval_requested', capability_name: 'run non-destructive command' },
      null
    )
    expect(n.body).toBe('run non-destructive command')
  })

  it('kendes fra andre kinds', () => {
    expect(isApprovalPush({ kind: 'approval_requested' })).toBe(true)
    expect(isApprovalPush({ kind: 'answer_ready' })).toBe(false)
    expect(isApprovalPush(null)).toBe(false)
  })

  it('opstart fra en godkendelses-notifikation kan aflæses', async () => {
    ;(notifee.getInitialNotification as jest.Mock).mockResolvedValueOnce({
      notification: { data: { kind: 'approval_requested' } }
    })
    await expect(openedFromApprovalPush()).resolves.toBe(true)
  })

  it('en fejlende notifee må ikke vælte opstarten', async () => {
    ;(notifee.getInitialNotification as jest.Mock).mockRejectedValueOnce(new Error('nede'))
    await expect(openedFromApprovalPush()).resolves.toBe(false)
  })

  // Regression, målt på enheden 2026-09-02: infra-vagtens flag kom frem som
  // «Jarvis svarede / Nyt svar» hver halve time, selv om serveren ikke havde
  // sendt ét answer_ready i fire timer. Årsagen var en catch-all der gav
  // ENHVER ukendt kind svar-titlen. En notifikation må ikke påstå noget andet
  // end det, den bærer.
  it('central_flag -> serverens egen ordlyd, IKKE "Jarvis svarede"', () => {
    const n = buildNotification(
      { kind: 'central_flag', title: 'Central-flag: infra/pve_disk', message: "Disk-pres på 'pve': 94% brugt" },
      null
    )
    expect(n.title).toBe('Central-flag: infra/pve_disk')
    expect(n.body).toBe("Disk-pres på 'pve': 94% brugt")
  })

  it('infra_security -> serverens titel + besked', () => {
    const n = buildNotification(
      { kind: 'infra_security', title: '⚠️ Netværks-trussel: port_scan', message: 'port_scan fra 204.76.203.231 — BLOKERET' },
      null
    )
    expect(n.title).toBe('⚠️ Netværks-trussel: port_scan')
    expect(n.body).toContain('BLOKERET')
  })

  it('ukendt kind uden tekst -> neutral titel, aldrig svar-paastand', () => {
    const n = buildNotification({ kind: 'noget_nyt' }, null)
    expect(n.title).toBe('Jarvis')
    expect(n.body).not.toBe('Nyt svar')
  })

  it('answer_ready -> stadig "Jarvis svarede"', () => {
    const n = buildNotification({ kind: 'answer_ready', preview: 'hej' }, null)
    expect(n.title).toBe('Jarvis svarede')
    expect(n.body).toBe('hej')
  })
})
