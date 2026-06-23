import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, screen, waitFor, cleanup } from '@testing-library/react'
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
})
