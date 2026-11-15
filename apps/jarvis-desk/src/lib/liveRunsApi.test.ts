import { describe, it, expect, vi, beforeEach } from 'vitest'

// Vagt for Bjørns to rettelser 15/11-2026, som peger på hver sin halvdel af
// samme regel:
//   «den ska kun vise rutinerne når de køre» — den kørende SAMTALE hører ikke her
//   «køre nu skal osse vises de 3 system/owner sessioner/rutiner»
// — altså: rutiner OG autonome sessioner med, almindelige samtaler IKKE.
const apiFetch = vi.fn()
const getActiveRunSessions = vi.fn()

vi.mock('./api', () => ({
  apiFetch: (...a: unknown[]) => apiFetch(...a),
  getActiveRunSessions: (...a: unknown[]) => getActiveRunSessions(...a),
}))

const CONFIG = { apiBaseUrl: 'http://x', authToken: 't' }

beforeEach(() => {
  apiFetch.mockReset()
  getActiveRunSessions.mockReset()
  getActiveRunSessions.mockResolvedValue([])
})

describe('hentLiveRuns', () => {
  it('spørger rutine-endpointet OG de levende sessioner', async () => {
    apiFetch.mockResolvedValue([])
    const { hentLiveRuns } = await import('./liveRunsApi')
    await hentLiveRuns(CONFIG)
    expect(apiFetch).toHaveBeenCalledWith(CONFIG, '/api/routines/active-runs')
    expect(getActiveRunSessions).toHaveBeenCalledWith(CONFIG)
  })

  it('giver rutinens navn, id og status videre', async () => {
    apiFetch.mockResolvedValue([
      { run_id: 'run-1', routine_id: 'routine-1', name: 'Morgenbrief', status: 'running' },
    ])
    const { hentLiveRuns } = await import('./liveRunsApi')
    const ud = await hentLiveRuns(CONFIG)
    expect(ud).toEqual([
      expect.objectContaining({
        id: 'r:run-1', navn: 'Morgenbrief', status: 'running',
        kind: 'rutine', routineId: 'routine-1',
      }),
    ])
  })

  it('en kørsel uden navn faar en læsbar standard i stedet for tom tekst', async () => {
    apiFetch.mockResolvedValue([{ run_id: 'run-2', routine_id: 'r2' }])
    const { hentLiveRuns } = await import('./liveRunsApi')
    const ud = await hentLiveRuns(CONFIG)
    expect(ud[0].navn).toBe('Rutine')
    expect(ud[0].status).toBe('queued')
  })

  it('et fejlet opslag giver en tom liste — ikke en kastet fejl i sidebaren', async () => {
    apiFetch.mockRejectedValue(new Error('nede'))
    getActiveRunSessions.mockRejectedValue(new Error('nede'))
    const { hentLiveRuns } = await import('./liveRunsApi')
    await expect(hentLiveRuns(CONFIG)).resolves.toEqual([])
  })

  it('viser system-rutinernes autonome session — med et læsbart navn', async () => {
    apiFetch.mockResolvedValue([])
    getActiveRunSessions.mockResolvedValue([
      { session_id: 'auto-heartbeat-20261115', run_id: 'vis-1', status: 'working', kind: 'autonom', label: 'Hjerteslag' },
    ])
    const { hentLiveRuns } = await import('./liveRunsApi')
    const ud = await hentLiveRuns(CONFIG)
    expect(ud).toEqual([
      expect.objectContaining({
        id: 's:auto-heartbeat-20261115', navn: 'Hjerteslag',
        kind: 'autonom', sessionId: 'auto-heartbeat-20261115',
      }),
    ])
  })

  it('viser ALDRIG din egen kørende samtale — kun de autonome', async () => {
    apiFetch.mockResolvedValue([])
    getActiveRunSessions.mockResolvedValue([
      { session_id: 'chat-5f65', run_id: 'vis-2', status: 'working', kind: 'samtale' },
      { session_id: 'auto-dream-20261115', run_id: 'vis-3', status: 'working', kind: 'autonom', label: 'Drømme' },
    ])
    const { hentLiveRuns } = await import('./liveRunsApi')
    const ud = await hentLiveRuns(CONFIG)
    expect(ud).toHaveLength(1)
    expect(ud[0].sessionId).toBe('auto-dream-20261115')
  })
})
