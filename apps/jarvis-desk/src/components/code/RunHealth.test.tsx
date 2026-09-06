import { describe, expect, it, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'

const getKrop = vi.fn()
vi.mock('../../lib/coworkApi', () => ({ getKrop: (...a: unknown[]) => getKrop(...a) }))

import { RunHealth } from './RunHealth'

const cfg = { apiBaseUrl: 'http://x', authToken: 't' }
const KROP = {
  cpu_pct: 12.4, ram_pct: 68.9, ram_used_gb: 11.8, ram_total_gb: 17.2,
  disk_free_gb: 141.2, cpu_temp_c: 45, pressure: 'low',
  gpus: [{ index: 0, util_pct: 3, vram_pct: 67.5, temp_c: 35 }],
}

describe('RunHealth', () => {
  beforeEach(() => { getKrop.mockReset().mockResolvedValue({ krop: KROP, ts: '' }) })

  it('viser maskinen læsbart uden at man skal åbne en log', async () => {
    render(<RunHealth config={cfg} />)
    await waitFor(() => expect(screen.getByText(/12% cpu · 69% ram/)).toBeTruthy())
    expect(screen.getByText(/141 GB fri/)).toBeTruthy()
    expect(screen.getByText(/3% · 68% vram/)).toBeTruthy()
  })

  it('markerer kontekst-tryk når det nærmer sig komprimering', async () => {
    render(<RunHealth config={cfg} tokens={72_000} komprimerVed={80_000} />)
    const v = await screen.findByText(/90% af 80k/)
    expect(v.className).toContain('rh-hoej')
  })

  it('viser intet når kroppen ikke kan hentes — ingen tom ramme', async () => {
    getKrop.mockRejectedValue(new Error('nede'))
    const { container } = render(<RunHealth config={cfg} />)
    await new Promise((r) => setTimeout(r, 10))
    expect(container.querySelector('.rh-rows')).toBeNull()
  })

  it('poller ikke når fanen er skjult', async () => {
    Object.defineProperty(document, 'hidden', { value: true, configurable: true })
    render(<RunHealth config={cfg} />)
    await new Promise((r) => setTimeout(r, 10))
    expect(getKrop).not.toHaveBeenCalled()
    Object.defineProperty(document, 'hidden', { value: false, configurable: true })
  })
})
