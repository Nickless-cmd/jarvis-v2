import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'

vi.mock('../../lib/api', () => ({
  getMindIndex: vi.fn().mockResolvedValue({
    index: [
      { section: 'overview', label: 'Oversigt', ready: true },
      { section: 'mind', label: 'Sind', ready: true },
      { section: 'decisions', label: 'Beslutninger', ready: true },
      { section: 'observability', label: 'Observabilitet', ready: true },
      { section: 'council', label: 'Council', ready: false },
    ],
  }),
  getMindSection: vi.fn().mockImplementation((_c, section: string) => {
    if (section === 'mind') {
      return Promise.resolve({ summary: '2/3 systemer aktive', systems: [
        { system: 'inner_voice', active: true, summary: 'taler' },
        { system: 'dreams', active: false },
      ] })
    }
    if (section === 'decisions') {
      // Formen er taget fra det levende endpoint 2026-09-05, ikke gættet.
      return Promise.resolve({
        queue: { pending: 1, expired_unanswered: 31, answered: 0 },
        items: [
          { kind: 'initiative', id: 'init-1', text: 'Slå det seneste bash-run op',
            why: 'Jeg vil vide om det holdt.', actions: ['approve', 'reject'] },
          { kind: 'life_project', id: 'life-1', text: 'Build a steadier inner architecture',
            why: 'I want a longer thread of coherence.', actions: ['abandon'] },
        ],
      })
    }
    if (section === 'observability') {
      return Promise.resolve({
        feed: [], incidents: [],
        hollow_promises: {
          available: true, window_hours: 24, hollow_total: 31,
          guard_detected: 12, escaped: 19,
          models: [
            { model: 'deepseek-v4-flash-vision-exp', turns: 42, hollow: 24, hollow_pct: 57.1 },
            { model: 'deepseek-v4-flash', turns: 97, hollow: 7, hollow_pct: 7.2 },
          ],
        },
      })
    }
    return Promise.resolve({ status: 'green', coverage: { nerves: 116, clusters: 20 } })
  }),
  actOnDecision: vi.fn().mockResolvedValue({ ok: true }),
  pingServer: vi.fn().mockResolvedValue(20),  // ConnectionPill › useConnection
}))
vi.mock('../../lib/centralStream', () => ({
  subscribeCentralStream: vi.fn(() => () => {}),
}))

import { JarvisMind } from './JarvisMind'
import { actOnDecision, getMindIndex, getMindSection } from '../../lib/api'
import { subscribeCentralStream } from '../../lib/centralStream'

const CFG = { apiBaseUrl: 'http://x', authToken: 't' }

describe('JarvisMind', () => {
  beforeEach(() => { vi.clearAllMocks() })

  it('bygger sub-navbar fra hub-index (ét ground truth)', async () => {
    render(<JarvisMind config={CFG} />)
    await waitFor(() => expect(getMindIndex).toHaveBeenCalled())
    await waitFor(() => expect(screen.getByRole('tab', { name: 'Sind' })).toBeTruthy())
    expect(screen.getByRole('tab', { name: 'Council' })).toBeTruthy()
  })

  it('åbner den DELTE Central-stream for den levende puls', () => {
    render(<JarvisMind config={CFG} />)
    expect(subscribeCentralStream).toHaveBeenCalled()
  })

  it('default-fanen Sind henter sektion fra hub og viser surfaces', async () => {
    render(<JarvisMind config={CFG} />)
    await waitFor(() => expect(getMindSection).toHaveBeenCalledWith(CFG, 'mind'))
    await waitFor(() => expect(screen.getByText(/inner voice/i)).toBeTruthy())
  })

  // Beslutnings-fanen er den ENESTE der ikke bare informerer. Uden knapper var
  // den bare endnu en visning — og 31 initiativer udløb netop ubesvarede fordi
  // ruterne fandtes uden at nogen kunne trykke.
  it('beslutnings-fanen giver ægte knapper, ikke bare en visning', async () => {
    const { default: userEvent } = await import('@testing-library/user-event')
    render(<JarvisMind config={CFG} />)
    await waitFor(() => expect(screen.getByRole('tab', { name: 'Beslutninger' })).toBeTruthy())
    await userEvent.click(screen.getByRole('tab', { name: 'Beslutninger' }))
    await waitFor(() => expect(screen.getByText(/Slå det seneste bash-run op/)).toBeTruthy())
    expect(screen.getByRole('button', { name: 'Godkend' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Afvis' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Læg den fra dig' })).toBeTruthy()
  })

  it('godkend rammer initiativ-ruten med slags og id', async () => {
    const { default: userEvent } = await import('@testing-library/user-event')
    render(<JarvisMind config={CFG} />)
    await waitFor(() => expect(screen.getByRole('tab', { name: 'Beslutninger' })).toBeTruthy())
    await userEvent.click(screen.getByRole('tab', { name: 'Beslutninger' }))
    await waitFor(() => expect(screen.getByRole('button', { name: 'Godkend' })).toBeTruthy())
    await userEvent.click(screen.getByRole('button', { name: 'Godkend' }))
    await waitFor(() =>
      expect(actOnDecision).toHaveBeenCalledWith(CFG, 'initiative', 'init-1', 'approve'))
  })

  it('viser tallet der gør ondt: de ubesvarede', async () => {
    const { default: userEvent } = await import('@testing-library/user-event')
    render(<JarvisMind config={CFG} />)
    await waitFor(() => expect(screen.getByRole('tab', { name: 'Beslutninger' })).toBeTruthy())
    await userEvent.click(screen.getByRole('tab', { name: 'Beslutninger' }))
    await waitFor(() => expect(screen.getByText(/31 tidligere forslag udløb uden svar/)).toBeTruthy())
  })

  // Backenden talte de tomme løfter fra dag ét, men fanen renderede kun feed +
  // flag-antal — så tallet var usynligt uden at folde rå-laget ud.
  it('observabilitet VISER de tomme løfter, ikke kun i rå-laget', async () => {
    const { default: userEvent } = await import('@testing-library/user-event')
    render(<JarvisMind config={CFG} />)
    await waitFor(() => expect(screen.getByRole('tab', { name: 'Observabilitet' })).toBeTruthy())
    await userEvent.click(screen.getByRole('tab', { name: 'Observabilitet' }))
    await waitFor(() => expect(screen.getByText('slap forbi værnet')).toBeTruthy())
    expect(screen.getByText('19')).toBeTruthy()
    expect(screen.getByText('57.1%')).toBeTruthy()
  })

  it('placeholder for pending-faner', async () => {
    const { default: userEvent } = await import('@testing-library/user-event')
    render(<JarvisMind config={CFG} />)
    await waitFor(() => expect(screen.getByRole('tab', { name: 'Council' })).toBeTruthy())
    await userEvent.click(screen.getByRole('tab', { name: 'Council' }))
    expect(screen.getByText(/ikke endnu flyttet|endnu ikke flyttet/i)).toBeTruthy()
  })
})
