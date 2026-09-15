import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MissionControl } from './MissionControl'

/**
 * En RIGTIG rendering, ikke en kilde-vagt.
 *
 * Omlægningen 15/9-2026 flyttede fire sektioner ind i Mission Control. Kilde-
 * vagterne fanger at koden står der — men ikke at fanen faktisk kan vælges og
 * at panelerne monterer. Det er forskellen på «linjen findes» og «det virker».
 */
vi.mock('../../../hooks/useMissionControl', () => ({
  useMissionControl: () => ({
    runs: [], activeRun: null, failedCount: 0,
    agents: [{ id: 'a1', name: 'explore', status: 'active' }],
    scheduled: [], overview: null, refresh: () => {},
  }),
}))
// Panelerne henter selv; de skal bare kunne monteres.
vi.mock('../AgentWork', () => ({ AgentWork: () => <div data-testid="agentwork" /> }))
vi.mock('../Lektier', () => ({ Lektier: () => <div data-testid="lektier" /> }))
vi.mock('../ReviewPanel', () => ({ ReviewPanel: () => <div data-testid="review" /> }))

const props = {
  config: { apiBaseUrl: 'http://t', authToken: 't' },
  isOwner: true,
  queue: [],
  onResolveQueue: () => {},
  extras: { plans: [], todos: [], channels: [], shareGuard: [],
            refresh: () => {}, onResolveShare: () => {} },
} as unknown as Parameters<typeof MissionControl>[0]

beforeEach(() => { vi.clearAllMocks() })

describe('Mission Control bærer de fire sektioner', () => {
  it('Review-fanen kan vælges', async () => {
    const { default: userEvent } = await import('@testing-library/user-event')
    render(<MissionControl {...props} />)
    await userEvent.click(screen.getByRole('button', { name: /^Review/ }))
    expect(screen.getByTestId('lektier')).toBeTruthy()
    expect(screen.getByTestId('review')).toBeTruthy()
  })

  it('Agenter-fanen viser BÅDE rosteret og arbejdet', async () => {
    const { default: userEvent } = await import('@testing-library/user-event')
    render(<MissionControl {...props} />)
    // «Agenter» staar BAADE som fane og som panel-overskrift, saa en ren
    // tekst-soegning finder to. Fanen er en knap.
    await userEvent.click(screen.getByRole('button', { name: /^Agenter/ }))
    expect(screen.getByTestId('agentwork')).toBeTruthy()
  })

  it('der er ingen «Arbejde»-sektion mere', () => {
    render(<MissionControl {...props} />)
    // Overskriften fra den slettede WorkQueue. Dukker den op igen, er
    // dobbelt-sandheden tilbage.
    expect(screen.queryByRole('heading', { name: 'Arbejde' })).toBeNull()
  })
})
