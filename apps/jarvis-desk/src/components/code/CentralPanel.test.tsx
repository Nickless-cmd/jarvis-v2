import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, screen, waitFor, cleanup, fireEvent } from '@testing-library/react'
import * as api from '../../lib/api'
import { CentralPanel } from './CentralPanel'

const snap = {
  status: 'red' as const,
  coverage: { nerves: 113, clusters: 19, security_clusters: 6, trace_buffer: 4 },
  diagnose: { decide_ok: true, observe_ok: true, degraded: false },
  feed: [{ cluster: 'auth', nerve: 'tool_access', kind: 'decide', decision: 'green', reason: '', run_id: '', security: true }],
  incidents: [{ cluster: 'privacy', nerve: 'cross_user_share', kind: 'fail_open', severity: 'severe', message: 'guard kastede', ts: '' }],
  open_breakers: [],
  config_drift: null,
  learning: { autonomy: 'moden', proposals: 8, degrading: [], root_causes: [] },
}

vi.mock('../../lib/api', () => ({
  getCentralRealtime: vi.fn(() => Promise.resolve(snap)),
  streamCentral: vi.fn(() => ({ abort: vi.fn() })),
  getCentralNerve: vi.fn(() => Promise.resolve({ nerve: 'tool_access', cluster: 'auth', security: true, location: 'x.py', enabled: true, recent: [] })),
  toggleCentralNerve: vi.fn(() => Promise.resolve({})),
}))

const cfg = { apiBaseUrl: 'http://t', authToken: 't' }

afterEach(() => cleanup())

describe('CentralPanel', () => {
  it('returnerer null for ikke-ejere', () => {
    const { container } = render(<CentralPanel config={cfg} isOwner={false} />)
    expect(container.firstChild).toBeNull()
  })

  it('viser puls + feed + flag for owner', async () => {
    render(<CentralPanel config={cfg} isOwner />)
    expect(screen.getByText('Central')).toBeInTheDocument()
    await waitFor(() => expect(screen.getByText(/113 nerver/)).toBeInTheDocument())
    // live feed-nerve
    await waitFor(() => expect(screen.getByText('tool_access')).toBeInTheDocument())
    // incident-flag
    expect(screen.getByText(/cross_user_share/)).toBeInTheDocument()
  })

  // Codex' punkt 2 (21/9-2026): panelet swallowede BEGGE sine klik-fejl med
  // `.catch(() => undefined)`. Klikkede man «Sluk» og kaldet faldt, skete der
  // praecis ingenting paa skaermen — nerven saa stadig taendt ud, og man havde
  // ingen maade at vide om det var lykkedes.
  it('siger det hoejt naar en nerve IKKE blev slukket', async () => {
    vi.mocked(api.toggleCentralNerve).mockRejectedValueOnce(new Error('503'))
    // Detaljen skal vaere en ALMINDELIG nerve: en sikkerheds-nerve kan ikke
    // slaas fra og viser «laast» i stedet for knappen.
    vi.mocked(api.getCentralNerve).mockResolvedValueOnce({
      nerve: 'tool_access', cluster: 'auth', security: false,
      location: 'x.py', enabled: true, recent: [],
    } as never)
    render(<CentralPanel config={cfg} isOwner />)
    fireEvent.click(await screen.findByText('tool_access'))
    const sluk = await screen.findByRole('button', { name: 'Sluk' })
    fireEvent.click(sluk)
    expect(await screen.findByRole('alert')).toHaveTextContent(/blev IKKE slukket/)
  })

  it('siger det naar sporet ikke kunne hentes — i stedet for slet ikke at reagere', async () => {
    vi.mocked(api.getCentralNerve).mockRejectedValueOnce(new Error('offline'))
    render(<CentralPanel config={cfg} isOwner />)
    fireEvent.click(await screen.findByText('tool_access'))
    expect(await screen.findByRole('alert')).toHaveTextContent(/Sporet for tool_access kunne ikke hentes/)
  })

  it('indroemmer at tallene er gamle naar pollet har fejlet tre gange', async () => {
    vi.mocked(api.getCentralRealtime)
      .mockRejectedValueOnce(new Error('x'))
      .mockRejectedValueOnce(new Error('x'))
      .mockRejectedValueOnce(new Error('x'))
    vi.useFakeTimers({ shouldAdvanceTime: true })
    render(<CentralPanel config={cfg} isOwner />)
    await vi.advanceTimersByTimeAsync(11_000)
    vi.useRealTimers()
    expect(await screen.findByRole('status')).toHaveTextContent(/Ingen kontakt til Centralen/)
  })
})
