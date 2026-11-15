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

const RUTINE: LiveRun = {
  id: 'r:run-1', navn: 'Morgenbrief', status: 'running', kind: 'rutine', routineId: 'routine-1',
}
const RUTINE_2: LiveRun = {
  id: 'r:run-2', navn: 'Natrutine', status: 'running', kind: 'rutine', routineId: 'routine-2',
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

  it('viser de rutiner der er i gang, med deres navn', async () => {
    mockHent.mockResolvedValue([RUTINE, RUTINE_2])
    render(<KoererNu config={CONFIG} />)
    expect(await screen.findByText('Morgenbrief')).toBeInTheDocument()
    expect(screen.getByText('Natrutine')).toBeInTheDocument()
    expect(screen.getByText('Kører nu')).toBeInTheDocument()
    expect(screen.getByText('2')).toBeInTheDocument()
  })

  it('et klik på en rutine åbner rutinen — ikke en session den ikke har', async () => {
    mockHent.mockResolvedValue([RUTINE])
    const onOpenRoutine = vi.fn()
    render(<KoererNu config={CONFIG} onOpenRoutine={onOpenRoutine} />)
    fireEvent.click(await screen.findByText('Morgenbrief'))
    // Rutiner kører uden session (målt 15/11-2026) — så klikket må ikke pege
    // på et chatview der ikke findes.
    expect(onOpenRoutine).toHaveBeenCalledWith('routine-1')
  })

  it('folden kan lukke listen, så blokken kun er én linje', async () => {
    mockHent.mockResolvedValue([RUTINE])
    render(<KoererNu config={CONFIG} />)
    await screen.findByText('Morgenbrief')
    fireEvent.click(screen.getByText('Kører nu'))
    expect(screen.queryByText('Morgenbrief')).toBeNull()
  })
})
