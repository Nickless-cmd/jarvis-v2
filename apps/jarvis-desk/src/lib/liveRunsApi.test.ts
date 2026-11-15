import { describe, it, expect, vi, beforeEach } from 'vitest'

// Vagt for Bjørns rettelse 15/11-2026: «kører nu under artefakter viser den
// kørende samtale og ikk rutiner når de køre.. den ska kun vise rutinerne når
// de køre». Første udgave flettede sessions-kilden ind; den er fjernet, og
// denne test beviser at den ikke kommer tilbage ved et tilfælde.
const { apiFetch, getActiveRunSessions } = vi.hoisted(() => ({
  apiFetch: vi.fn(),
  getActiveRunSessions: vi.fn(),
}))

vi.mock('./api', () => ({ apiFetch, getActiveRunSessions }))

import { hentLiveRuns } from './liveRunsApi'

const CONFIG = { apiBaseUrl: 'http://x', authToken: 't' } as never

beforeEach(() => {
  apiFetch.mockReset()
  getActiveRunSessions.mockReset()
})

describe('hentLiveRuns', () => {
  it('spørger KUN rutine-endpointet — den kørende samtale hører ikke her', async () => {
    apiFetch.mockResolvedValue([])
    await hentLiveRuns(CONFIG)
    expect(apiFetch).toHaveBeenCalledWith(CONFIG, '/api/routines/active-runs')
    expect(getActiveRunSessions).not.toHaveBeenCalled()
  })

  it('giver rutinens navn, id og status videre', async () => {
    apiFetch.mockResolvedValue([
      { run_id: 'run-1', routine_id: 'routine-1', name: 'Morgenbrief', status: 'running' },
    ])
    const ud = await hentLiveRuns(CONFIG)
    expect(ud).toHaveLength(1)
    expect(ud[0]).toMatchObject({
      id: 'r:run-1', navn: 'Morgenbrief', status: 'running', routineId: 'routine-1',
    })
  })

  it('en kørsel uden navn faar en læsbar standard i stedet for tom tekst', async () => {
    apiFetch.mockResolvedValue([{ run_id: 'run-2', routine_id: 'routine-2' }])
    const ud = await hentLiveRuns(CONFIG)
    expect(ud[0]?.navn).toBe('Rutine')
  })

  it('et fejlet opslag giver en tom liste — ikke en kastet fejl i sidebaren', async () => {
    apiFetch.mockRejectedValue(new Error('nede'))
    await expect(hentLiveRuns(CONFIG)).resolves.toEqual([])
  })
})
