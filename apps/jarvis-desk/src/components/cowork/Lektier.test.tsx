import { describe, expect, it, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'

const getLektier = vi.fn()
const saetLektionStatus = vi.fn()
vi.mock('../../lib/coworkApi', () => ({
  getLektier: (...a: unknown[]) => getLektier(...a),
  saetLektionStatus: (...a: unknown[]) => saetLektionStatus(...a),
}))

import { Lektier } from './Lektier'

const cfg = { apiBaseUrl: 'http://x', authToken: 't' }
const l = (o: Record<string, unknown> = {}) => ({
  id: 1, signature: 's', lesson: 'Tjek altid brif mod bridge-ports.',
  source: 'tool_error', status: 'proposed', evidence_count: 3,
  repeated_count: 2, first_at: '', last_at: '', ...o,
})

describe('Lektier', () => {
  beforeEach(() => {
    getLektier.mockReset().mockResolvedValue({ proposed: [l()], active: [l({ id: 9 })] })
    saetLektionStatus.mockReset().mockResolvedValue({ status: 'ok' })
  })

  it('viser bevis-tallene — forskellen på en anelse og et mønster', async () => {
    render(<Lektier config={cfg} />)
    expect(await screen.findByText(/set 3× · gentaget 2×/)).toBeTruthy()
    expect(screen.getByText('tool_error')).toBeTruthy()
    expect(screen.getByText('1 i brug')).toBeTruthy()
  })

  it('gemmer som regel — og henter listen igen bagefter', async () => {
    render(<Lektier config={cfg} />)
    fireEvent.click(await screen.findByRole('button', { name: /Gem som regel/ }))
    await waitFor(() => expect(saetLektionStatus).toHaveBeenCalledWith(cfg, 1, 'active'))
    await waitFor(() => expect(getLektier).toHaveBeenCalledTimes(2))
  })

  it('afviser med samme knapsæt', async () => {
    render(<Lektier config={cfg} />)
    fireEvent.click(await screen.findByRole('button', { name: /Afvis/ }))
    await waitFor(() => expect(saetLektionStatus).toHaveBeenCalledWith(cfg, 1, 'rejected'))
  })

  it('siger til når dommen ikke kunne gemmes', async () => {
    saetLektionStatus.mockResolvedValue({ status: 'error', error: 'ukendt status' })
    render(<Lektier config={cfg} />)
    fireEvent.click(await screen.findByRole('button', { name: /Gem som regel/ }))
    expect(await screen.findByText('ukendt status')).toBeTruthy()
  })

  it('viser intet når der hverken er forslag eller aktive', async () => {
    getLektier.mockResolvedValue({ proposed: [], active: [] })
    const { container } = render(<Lektier config={cfg} />)
    await new Promise((r) => setTimeout(r, 15))
    expect(container.firstChild).toBeNull()
  })

  it('siger «ingen nye forslag» når kun de aktive er tilbage', async () => {
    getLektier.mockResolvedValue({ proposed: [], active: [l({ id: 9 })] })
    render(<Lektier config={cfg} />)
    expect(await screen.findByText('Ingen nye forslag.')).toBeTruthy()
  })
})
