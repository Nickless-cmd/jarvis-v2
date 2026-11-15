import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { KoererNu } from './KoererNu'
import { hentLiveRuns, type LiveRun } from '../../lib/liveRunsApi'

vi.mock('../../lib/liveRunsApi', () => ({ hentLiveRuns: vi.fn() }))
// Ro-mekanismen forlænger intervallet når ingen kigger. I test skal den ikke
// kunne undertrykke det første kald — det er ikke det testen måler.
vi.mock('../../lib/ro', () => ({ maaPolle: () => true }))

const mockHent = vi.mocked(hentLiveRuns)
const CONFIG = { apiBaseUrl: 'http://x', authToken: 't' }

const SAMTALE: LiveRun = {
  id: 's:chat-1', kind: 'samtale', navn: 'Samtale', status: 'working', sessionId: 'chat-1',
}
const RUTINE: LiveRun = {
  id: 'r:run-1', kind: 'rutine', navn: 'Morgenbrief', status: 'running', routineId: 'routine-1',
}

beforeEach(() => {
  mockHent.mockReset()
})

describe('KoererNu', () => {
  it('findes IKKE når intet kører — den er en tilstand, ikke et arkiv', async () => {
    mockHent.mockResolvedValue([])
    const { container } = render(<KoererNu config={CONFIG} />)
    await waitFor(() => expect(mockHent).toHaveBeenCalled())
    expect(container.querySelector('.koerer-nu')).toBeNull()
  })

  it('viser de kørsler der er i gang, med et læsbart navn', async () => {
    mockHent.mockResolvedValue([SAMTALE, RUTINE])
    render(<KoererNu config={CONFIG} />)
    expect(await screen.findByText('Samtale')).toBeInTheDocument()
    expect(screen.getByText('Morgenbrief')).toBeInTheDocument()
    expect(screen.getByText('Kører nu')).toBeInTheDocument()
  })

  it('et klik på en session skifter til DEN session', async () => {
    mockHent.mockResolvedValue([SAMTALE])
    const onOpenSession = vi.fn()
    render(<KoererNu config={CONFIG} onOpenSession={onOpenSession} />)
    fireEvent.click(await screen.findByText('Samtale'))
    expect(onOpenSession).toHaveBeenCalledWith('chat-1')
  })

  it('et klik på en rutine åbner rutinen — ikke en session den ikke har', async () => {
    mockHent.mockResolvedValue([RUTINE])
    const onOpenRoutine = vi.fn()
    const onOpenSession = vi.fn()
    render(<KoererNu config={CONFIG} onOpenRoutine={onOpenRoutine} onOpenSession={onOpenSession} />)
    fireEvent.click(await screen.findByText('Morgenbrief'))
    expect(onOpenRoutine).toHaveBeenCalledWith('routine-1')
    // Rutiner kører uden session (målt 15/11-2026) — så der må ikke skiftes
    // til en session der ikke findes.
    expect(onOpenSession).not.toHaveBeenCalled()
  })

  it('folden kan lukke listen, så blokken kun er én linje', async () => {
    mockHent.mockResolvedValue([SAMTALE])
    render(<KoererNu config={CONFIG} />)
    await screen.findByText('Samtale')
    fireEvent.click(screen.getByText('Kører nu'))
    expect(screen.queryByText('Samtale')).toBeNull()
  })
})
