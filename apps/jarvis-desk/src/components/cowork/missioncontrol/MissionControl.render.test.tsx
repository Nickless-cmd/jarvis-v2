import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MissionControl } from './MissionControl'

/**
 * En RIGTIG rendering, ikke en kilde-vagt.
 *
 * Omlægningen 15/9-2026 flyttede fire sektioner ind i Mission Control. Kilde-
 * vagterne fanger at koden står der — men ikke at fanen faktisk kan vælges og
 * at panelerne monterer. Det er forskellen på «linjen findes» og «det virker».
 */
// `udfald` er de kilder der IKKE kunne hentes. Tom = alt kom hjem.
const udfald: string[] = []
vi.mock('../../../hooks/useMissionControl', () => ({
  useMissionControl: () => ({
    runs: [], activeRun: null, failedCount: 0,
    agents: [{ agent_id: 'a1', name: 'explore', status: 'active' }],
    scheduled: [], overview: null, udfald, refresh: () => {},
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
  it('oversigten viser kun de første tre afventende og åbner resten ved behov', async () => {
    const { default: userEvent } = await import('@testing-library/user-event')
    const queue = Array.from({ length: 5 }, (_, i) => ({
      id: `a${i}`, title: `Godkendelse ${i + 1}`, kind: 'proposal' as const, detail: '', source: 'test',
    }))
    render(<MissionControl {...props} queue={queue} />)
    expect(screen.getByText('Godkendelse 1')).toBeInTheDocument()
    expect(screen.queryByText('Godkendelse 4')).not.toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Se alle godkendelser (5)' }))
    expect(screen.getByText('Godkendelse 4')).toBeInTheDocument()
  })

  it('Gennemgang-fanen kan vælges', async () => {
    const { default: userEvent } = await import('@testing-library/user-event')
    render(<MissionControl {...props} />)
    await userEvent.click(screen.getByRole('button', { name: /^Gennemgang/ }))
    expect(screen.getByTestId('lektier')).toBeTruthy()
    expect(screen.getByTestId('review')).toBeTruthy()
  })

  it('viser læsbare danske navne på driftsfanerne', () => {
    render(<MissionControl {...props} />)
    expect(screen.getByRole('button', { name: 'Kørsler' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Forbrug' })).toBeInTheDocument()
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

describe('et udfald maa ikke tegnes som ro', () => {
  // Codex' punkt 2 (21/9-2026). `useMissionControl` brugte `allSettled` og
  // kasserede hver afvisning, saa tilstanden blev staaende paa sin start-[].
  // Forsiden skrev «alt roligt» over fem nuller om noget den intet vidste om
  // — den mest selvsikre maade en fejl kan se ud paa.
  afterEach(() => { udfald.length = 0 })

  it('siger «ingen kontakt» og viser — i stedet for 0 naar kilderne faldt', () => {
    udfald.push('kørslerne', 'agenterne')
    render(<MissionControl {...props} />)
    expect(screen.getByRole('alert')).toHaveTextContent(/ikke kontakt til kørslerne og agenterne/)
    expect(screen.getByText('ingen kontakt')).toBeInTheDocument()
    expect(screen.queryByText('alt roligt')).not.toBeInTheDocument()
    // «kører», «fejlet» og «agenter» er ukendte; «afventer» kommer fra en
    // anden kilde og er stadig et rigtigt tal.
    expect(screen.getAllByText('—')).toHaveLength(3)
    expect(screen.getByText(/Kørslerne kunne ikke hentes/)).toBeInTheDocument()
  })

  it('siger stadig «alt roligt» naar der bare ikke er noget', () => {
    render(<MissionControl {...props} />)
    expect(screen.getByText('alt roligt')).toBeInTheDocument()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    expect(screen.getByText('Ingen kørsler')).toBeInTheDocument()
  })
})
