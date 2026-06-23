import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'

vi.mock('../../lib/api', () => ({
  getCentralRealtime: vi.fn().mockResolvedValue({
    status: 'green', coverage: { nerves: 116, clusters: 21 },
    clusters: [{ cluster: 'truth', status: 'green', security: false }, { cluster: 'auth', status: 'green', security: true }],
    incidents: [], anomalies: { counts: { total: 0 } }, open_breakers: [], processes: [{ process: 'api' }, { process: 'runtime' }],
  }),
  getCentralProviders: vi.fn().mockResolvedValue({ providers: [{ provider: 'ollama', ok: true, degraded: false, latency_ms: 41, model_count: 3 }], dry_cheap: [], summary: '1/1' }),
  runCentralCommand: vi.fn().mockResolvedValue({ ok: true, command: 'status', lines: ['status: GREEN nerver=116'] }),
  getCentralDiagnostics: vi.fn().mockResolvedValue({
    incidents: [{ severity: 'error', kind: 'x', cluster: 'system', nerve: 'config_drift', message: 'port-drift', ts: '2026-06-23T10:00:00' }],
    anomalies: [], instrument: [], root_causes: [], degrading: [],
  }),
}))
vi.mock('../../lib/centralStream', () => ({ subscribeCentralStream: vi.fn(() => () => {}) }))

import { CentralHud } from './CentralHud'
import { runCentralCommand } from '../../lib/api'
import { subscribeCentralStream } from '../../lib/centralStream'

const CFG = { apiBaseUrl: 'http://x', authToken: 't' }

describe('CentralHud', () => {
  beforeEach(() => { vi.clearAllMocks() })

  it('renderer reaktorkernen med nerve-tal + cluster-konstellation', async () => {
    render(<CentralHud config={CFG} />)
    await waitFor(() => expect(screen.getByText('116')).toBeTruthy())
    expect(screen.getByText('C E N T R A L')).toBeTruthy()
    expect(screen.getByText('truth')).toBeTruthy()
    expect(screen.getByTitle('auth 🔒')).toBeTruthy()  // sikkerheds-cluster markeret
  })

  it('åbner den delte Central-stream for pulsen', () => {
    render(<CentralHud config={CFG} />)
    expect(subscribeCentralStream).toHaveBeenCalled()
  })

  it('terminalen kører en kommando og viser output', async () => {
    const { default: userEvent } = await import('@testing-library/user-event')
    render(<CentralHud config={CFG} />)
    const input = screen.getByPlaceholderText(/status .* help/)
    await userEvent.type(input, 'status{enter}')
    await waitFor(() => expect(runCentralCommand).toHaveBeenCalledWith(CFG, 'status'))
    await waitFor(() => expect(screen.getByText(/nerver=116/)).toBeTruthy())
  })

  it('betjenings-knap kører sin kommando', async () => {
    const { default: userEvent } = await import('@testing-library/user-event')
    render(<CentralHud config={CFG} />)
    await userEvent.click(screen.getByRole('button', { name: /kør scan/ }))
    await waitFor(() => expect(runCentralCommand).toHaveBeenCalledWith(CFG, 'scan'))
  })

  it('skifter til diagnostik-mode og viser flag-detaljer', async () => {
    const { default: userEvent } = await import('@testing-library/user-event')
    render(<CentralHud config={CFG} />)
    await userEvent.click(screen.getByRole('button', { name: /diagnostik/ }))
    await waitFor(() => expect(screen.getByText(/port-drift/)).toBeTruthy())
    expect(screen.getByText(/ULØSTE FLAG/)).toBeTruthy()
  })
})
