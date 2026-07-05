import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'

const getCentralRealtime = vi.fn()
vi.mock('../../lib/api', () => ({
  getCentralRealtime: (...a: unknown[]) => getCentralRealtime(...a),
}))

import { CentralBadge } from './CentralBadge'

const CFG = { apiBaseUrl: 'http://x', authToken: 't' }

const GREEN = {
  status: 'green', coverage: { nerves: 116, clusters: 21 },
  incidents: [], open_breakers: [],
}
const RED = {
  status: 'red', coverage: { nerves: 116, clusters: 21 },
  incidents: [
    { cluster: 'truth', nerve: 'fact_gate', kind: 'x', severity: 'error', message: 'boom', ts: '2026-07-05T10:00:00' },
    { cluster: 'auth', nerve: 'token', kind: 'y', severity: 'warn', message: 'meh', ts: '2026-07-05T10:01:00' },
  ],
  open_breakers: ['provider:deepseek'],
}

function stubBridge() {
  const openCli = vi.fn().mockResolvedValue({ ok: true })
  ;(window as unknown as { jarvisDesk: { central: { openCli: typeof openCli } } }).jarvisDesk = { central: { openCli } }
  return openCli
}

describe('CentralBadge', () => {
  beforeEach(() => {
    getCentralRealtime.mockReset()
    getCentralRealtime.mockResolvedValue(GREEN)
    delete (window as unknown as { jarvisDesk?: unknown }).jarvisDesk
  })

  it('renderer Central-label + status-prik for grønt snapshot (owner)', async () => {
    render(<CentralBadge config={CFG} isOwner />)
    await waitFor(() => expect(screen.getByText('Central')).toBeTruthy())
    const badge = screen.getByTestId('central-badge')
    expect(badge.className).toContain('tone-green')
    expect(badge.querySelector('.cb-dot')).toBeTruthy()
  })

  it('viser incident-tæller når der er incidents', async () => {
    getCentralRealtime.mockResolvedValue(RED)
    render(<CentralBadge config={CFG} isOwner />)
    await waitFor(() => expect(screen.getByText('2')).toBeTruthy())
    expect(screen.getByTestId('central-badge').className).toContain('tone-red')
  })

  it('owner-hover afslører detaljerede metrics', async () => {
    getCentralRealtime.mockResolvedValue(RED)
    render(<CentralBadge config={CFG} isOwner />)
    await waitFor(() => expect(screen.getByText('Central')).toBeTruthy())
    fireEvent.mouseEnter(screen.getByTestId('central-badge'))
    await waitFor(() => expect(screen.getByRole('tooltip').textContent).toMatch(/nerver 116/))
    expect(screen.getByRole('tooltip').textContent).toMatch(/incidents 2/)
    expect(screen.getByRole('tooltip').textContent).toMatch(/truth\/fact_gate/)
  })

  it('member-hover viser IKKE detaljerede metrics — kun statusord', async () => {
    getCentralRealtime.mockResolvedValue(RED)
    render(<CentralBadge config={CFG} isOwner={false} />)
    await waitFor(() => expect(screen.getByText('Central')).toBeTruthy())
    fireEvent.mouseEnter(screen.getByTestId('central-badge'))
    await waitFor(() => expect(screen.getByRole('tooltip')).toBeTruthy())
    const tip = screen.getByRole('tooltip').textContent || ''
    expect(tip).toMatch(/Central:/)
    expect(tip).not.toMatch(/nerver/)
    expect(tip).not.toMatch(/breakers/)
  })

  it('owner-klik kalder window.jarvisDesk.central.openCli', async () => {
    const openCli = stubBridge()
    render(<CentralBadge config={CFG} isOwner />)
    await waitFor(() => expect(screen.getByText('Central')).toBeTruthy())
    fireEvent.click(screen.getByTestId('central-badge'))
    await waitFor(() => expect(openCli).toHaveBeenCalledTimes(1))
  })

  it('member-klik gør intet (ingen openCli)', async () => {
    const openCli = stubBridge()
    render(<CentralBadge config={CFG} isOwner={false} />)
    await waitFor(() => expect(screen.getByText('Central')).toBeTruthy())
    fireEvent.click(screen.getByTestId('central-badge'))
    expect(openCli).not.toHaveBeenCalled()
  })

  it('tåler at getCentralRealtime rejecter (offline / 403) uden at crashe', async () => {
    getCentralRealtime.mockRejectedValue(new Error('403 Forbidden'))
    render(<CentralBadge config={CFG} isOwner={false} />)
    await waitFor(() => expect(screen.getByText('Central')).toBeTruthy())
    expect(screen.getByTestId('central-badge').className).toContain('tone-unknown')
  })
})
