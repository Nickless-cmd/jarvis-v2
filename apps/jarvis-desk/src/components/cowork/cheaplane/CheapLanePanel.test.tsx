import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { CheapLanePanel } from './CheapLanePanel'
import * as api from '../../../lib/cheapLaneApi'

/**
 * Fladen skal svare på Bjørns spørgsmål: «hvordan klarer cheap lane sig».
 *
 * Testene måler de tre ting der kan gå galt uden at nogen ser det:
 *  1. «ingen data» må ikke vises som «0 %»
 *  2. fejl-fanen må ikke vise loftet som om det var antallet
 *  3. knapperne skal ramme det rigtige lag (slot = pause, model = registret)
 */
const config = { apiBaseUrl: 'http://x', authToken: 't' }

const historik = {
  udbydere: [
    {
      provider: 'zai', model: 'glm-4', auth_profile: 'default',
      kald: 10, ok: 2, fejl: 8, succesrate: 0.2,
      latens_p50_ms: 900, latens_p95_ms: 2500, pris_usd: 0,
      fejlkoder: [{ kode: 'request-failed', antal: 8 }],
    },
    {
      provider: 'cloudflare', model: 'llama-4', auth_profile: 'default',
      kald: 5, ok: 5, fejl: 0, succesrate: 1,
      latens_p50_ms: 810, latens_p95_ms: 900, pris_usd: 0,
      fejlkoder: [],
    },
  ],
  opsummering: { kald: 15, ok: 7, fejl: 8, succesrate: 0.4667, pris_usd: 0.0012, udbydere: 2 },
}

beforeEach(() => {
  vi.restoreAllMocks()
  vi.spyOn(api, 'getBalancerState').mockResolvedValue({
    enabled: true, pool_size: 2, eligible_now: 1,
    header: { total_slots: 2, healthy: 1, cooldown: 1, disabled: 0 },
    slots: [{
      slot_id: 'zai::glm-4::default', provider: 'zai', model: 'glm-4',
      status: 'cooldown', weight: 0, rpm_used: 3, rpm_limit: 10,
      success_rate: 0.2, breaker_level: 2, manually_disabled: false,
    }],
  })
  vi.spyOn(api, 'getHistorik').mockResolvedValue(historik)
  vi.spyOn(api, 'getFejl').mockResolvedValue({
    raekker: [{
      provider: 'zai', model: 'glm-4', error_code: 'request-failed',
      error_message: 'The read operation timed out', created_at: '2026-09-16T18:00:00Z',
    }],
    vist: 1, antal_i_vinduet: 253,
  })
  vi.spyOn(api, 'getTidsserie').mockResolvedValue({
    spand: [{ tid: '2026-09-16T17:00', kald: 10, fejl: 8, latens_ms: 900 }],
  })
  vi.spyOn(api, 'getDashboard').mockResolvedValue({
    schema_version: 1, generated_at: '2026-09-18T09:00:00Z', window_hours: 24,
    status: 'complete',
    kpis: { requests: 15, tokens: 4200, errors: 8, cost_usd: 0.0012,
            eligible_slots: 1, active_findings: 0 },
    sections: {
      capacity: { source: 'quota', observed_at: '2026-09-18T09:00:00Z', freshness: 'live',
                  data: { windows: [] }, error: null },
    },
  })
  vi.spyOn(api, 'getRegistret').mockResolvedValue({
    udbydere: [{ provider: 'zai', enabled: true, model_count: 1, enabled_model_count: 1 }],
    modeller: [{ provider: 'zai', model: 'glm-4', lane: 'cheap', enabled: true }],
  })
})

describe('CheapLanePanel', () => {
  it('viser vinduets noegletal paa oversigten', async () => {
    // Oversigten kommer fra ÉT snapshot siden 18/9-2026 — ikke fra fire
    // hentninger med hver sit tidspunkt.
    render(<CheapLanePanel config={config} />)
    await waitFor(() => expect(document.querySelector('.cl-kpi')).toBeTruthy())
    // Tallet laeses sammen med SIN etiket inde i KPI-kortet: baade «8» og
    // «Kald» staar flere steder paa fladen (grafens tabel bruger de samme ord),
    // saa en loesere soegning ville bestaa selv hvis tallet forsvandt.
    const kpi = (etiket: string) => [...document.querySelectorAll('.cl-kpi')]
      .find((k) => k.querySelector('.cl-kpi-label')?.textContent === etiket)
      ?.querySelector('.cl-kpi-tal')?.textContent
    expect(kpi('Kald')).toBe('15')
    expect(kpi('Fejl')).toBe('8')
    expect(kpi('Slots klar')).toBe('1')
  })

  it('kapacitet uden kvoter siger det — den viser ikke 0 %', async () => {
    const bruger = userEvent.setup()
    render(<CheapLanePanel config={config} />)
    await waitFor(() => expect(screen.getByRole('button', { name: 'Kapacitet' })).toBeInTheDocument())
    await bruger.click(screen.getByRole('button', { name: 'Kapacitet' }))
    expect(screen.getByText(/ingen kvoter/i)).toBeInTheDocument()
    expect(screen.queryByText('0 %')).not.toBeInTheDocument()
  })

  it('fejl-fanen siger hvor mange der ER, ikke hvor mange der vises', async () => {
    const bruger = userEvent.setup()
    render(<CheapLanePanel config={config} />)
    await waitFor(() => expect(screen.getByRole('button', { name: /Fejl \(253\)/ })).toBeInTheDocument())
    await bruger.click(screen.getByRole('button', { name: /Fejl \(253\)/ }))
    expect(screen.getByText('253 fejl i vinduet. Viser de 1 nyeste.')).toBeInTheDocument()
    expect(screen.getByText('The read operation timed out')).toBeInTheDocument()
  })

  it('pause i puljen rammer SLOTTET, ikke registret', async () => {
    // Samme skel som før, nu gennem kontrol-ruten: `slot.pause` er
    // balancerens egen tilstand og forsvinder ved næste opbygning, mens
    // `model.deactivate` skriver i registret og overlever en genstart.
    const kontrol = vi.spyOn(api, 'udfoerKontrol').mockResolvedValue({ status: 'ok' })
    const bruger = userEvent.setup()
    render(<CheapLanePanel config={config} />)
    await waitFor(() => expect(screen.getByRole('button', { name: 'Puljen nu' })).toBeInTheDocument())
    await bruger.click(screen.getByRole('button', { name: 'Puljen nu' }))
    await bruger.click(screen.getByRole('button', { name: /zai \/ glm-4/ }))
    await bruger.click(screen.getByRole('button', { name: 'Pause slot' }))
    expect(kontrol).toHaveBeenCalledWith(config, expect.objectContaining({
      action: 'slot.pause', target: 'zai::glm-4::default',
    }))
    expect(kontrol).not.toHaveBeenCalledWith(config, expect.objectContaining({
      action: 'model.deactivate',
    }))
  })

  it('«deaktivér» på udbydere rammer REGISTRET, ikke slottet', async () => {
    // Samme skel som før, men gennem den reviderede kontrol-rute (18/9-2026):
    // handlingen skrives i revisionssporet og kræver en grund.
    const slot = vi.spyOn(api, 'slotHandling').mockResolvedValue({ status: 'ok' })
    const kontrol = vi.spyOn(api, 'udfoerKontrol').mockResolvedValue({ status: 'ok' })
    const bruger = userEvent.setup()
    render(<CheapLanePanel config={config} />)
    await waitFor(() => expect(screen.getByRole('button', { name: 'Udbydere' })).toBeInTheDocument())
    await bruger.click(screen.getByRole('button', { name: 'Udbydere' }))
    await bruger.click(screen.getByRole('button', { name: /^Deaktivér glm-4/ }))
    await bruger.type(screen.getByLabelText(/grund/i), 'for dyr')
    await bruger.click(screen.getByRole('button', { name: 'Bekræft' }))
    expect(kontrol).toHaveBeenCalledWith(config, expect.objectContaining({
      action: 'model.deactivate', target: 'zai/glm-4', reason: 'for dyr',
    }))
    expect(slot).not.toHaveBeenCalled()
  })

  it('en kilde der fejler tømmer ikke de andre', async () => {
    vi.spyOn(api, 'getFejl').mockRejectedValue(new Error('nede'))
    render(<CheapLanePanel config={config} />)
    await waitFor(() => expect(screen.getByText('1 af 5 kilder svarede ikke')).toBeInTheDocument())
    expect(screen.getByText('15')).toBeInTheDocument()   // snapshotet staar endnu
  })
})
