import { describe, expect, it, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'

const getKrop = vi.fn()
vi.mock('../../lib/coworkApi', () => ({ getKrop: (...a: unknown[]) => getKrop(...a) }))

import { RunHealth } from './RunHealth'
import { DESK_CHROME } from '../../lib/deskChrome'

const cfg = { apiBaseUrl: 'http://x', authToken: 't' }
const KROP = {
  cpu_pct: 12.4, ram_pct: 68.9, ram_used_gb: 11.8, ram_total_gb: 17.2,
  disk_free_gb: 141.2, cpu_temp_c: 45, pressure: 'low',
  gpus: [{ index: 0, util_pct: 3, vram_pct: 67.5, temp_c: 35 }],
}

describe('RunHealth', () => {
  beforeEach(() => { getKrop.mockReset().mockResolvedValue({ krop: KROP, ts: '' }) })

  it('viser maskinen læsbart — når maskin-rækkerne er slået til', async () => {
    // Bjørn slog dem fra 8/9-2026 (DESK_CHROME.envMachineRows). Testen bliver
    // stående og springer over, så den er klar hvis de tændes igen — frem for
    // at blive slettet og skulle skrives forfra.
    if (!DESK_CHROME.envMachineRows) return
    render(<RunHealth config={cfg} />)
    await waitFor(() => expect(screen.getByText(/12% cpu · 69% ram/)).toBeTruthy())
    expect(screen.getByText(/141 GB fri/)).toBeTruthy()
    expect(screen.getByText(/3% · 68% vram/)).toBeTruthy()
  })

  it('viser IKKE maskine, GPU eller disk når de er slået fra', async () => {
    render(<RunHealth config={cfg} tokens={1_000} komprimerVed={80_000} />)
    await screen.findByText(/1% af 80k/)
    expect(screen.queryByText(/cpu/)).toBeNull()
    expect(screen.queryByText(/vram/)).toBeNull()
    expect(screen.queryByText(/GB fri/)).toBeNull()
  })

  it('kontekst overlever at maskin-tallene er væk', async () => {
    // Den egentlige risiko ved ændringen: komponenten returnerede før `null`
    // når `krop` manglede, og så ville kontekst-tallet forsvinde sammen med
    // maskin-tallene — selv om det ikke har noget med dem at gøre.
    getKrop.mockRejectedValue(new Error('nede'))
    render(<RunHealth config={cfg} tokens={40_000} komprimerVed={80_000} />)
    expect(await screen.findByText(/50% af 80k/)).toBeTruthy()
  })

  it('poller slet ikke når maskin-rækkerne er slået fra', async () => {
    // En usynlig poll hvert 15. sekund efter noget ingen viser er ren omkostning.
    if (DESK_CHROME.envMachineRows) return
    render(<RunHealth config={cfg} tokens={1_000} komprimerVed={80_000} />)
    await new Promise((r) => setTimeout(r, 10))
    expect(getKrop).not.toHaveBeenCalled()
  })

  it('markerer kontekst-tryk når det nærmer sig komprimering', async () => {
    render(<RunHealth config={cfg} tokens={72_000} komprimerVed={80_000} />)
    const v = await screen.findByText(/90% af 80k/)
    expect(v.className).toContain('rh-hoej')
  })

  it('viser intet når der hverken er maskine eller kontekst — ingen tom ramme', async () => {
    getKrop.mockRejectedValue(new Error('nede'))
    const { container } = render(<RunHealth config={cfg} />)
    await new Promise((r) => setTimeout(r, 10))
    expect(container.querySelector('.rh-rows')).toBeNull()
  })

  it('poller ikke når fanen er skjult', async () => {
    if (!DESK_CHROME.envMachineRows) return   // poller slet ikke — daekket ovenfor
    Object.defineProperty(document, 'hidden', { value: true, configurable: true })
    render(<RunHealth config={cfg} />)
    await new Promise((r) => setTimeout(r, 10))
    expect(getKrop).not.toHaveBeenCalled()
    Object.defineProperty(document, 'hidden', { value: false, configurable: true })
  })
})
