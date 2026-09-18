/**
 * Kontrolcentret som helhed — og hvad der sker når noget svigter.
 *
 * Fladen har ÉT snapshot som kilde (18/9-2026). Det gør fejl-matrixen til den
 * vigtigste test her: seks kilder pakkes i én konvolut, og en af dem kan være
 * væk uden at de andre er det. Kravet er at panelet i alle de tilfælde stadig
 * kan bruges — fanerne skal virke, og det der ER hentet, skal stå der.
 *
 * Og de to skel der kan koste noget, hvis de sløres:
 *
 *   slot.pause        balancerens egen tilstand — væk ved næste opbygning
 *   model.deactivate  registret — overlever en genstart
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { CheapLanePanel } from './CheapLanePanel'
import * as api from '../../../lib/cheapLaneApi'
import type { Snapshot } from '../../../lib/cheapLaneApi'

const config = { apiBaseUrl: 'http://x', authToken: 't' }

function snapshot(over: Partial<Snapshot> = {}): Snapshot {
  return {
    schema_version: 1, generated_at: '2026-09-18T09:00:00Z', window_hours: 24,
    status: 'complete',
    kpis: { requests: 15, tokens: 4200, errors: 8, cost_usd: 0.0012,
            eligible_slots: 1, active_findings: 0 },
    sections: {
      capacity: { source: 'quota', observed_at: '2026-09-18T09:00:00Z', freshness: 'live',
                  data: { windows: [] }, error: null },
      balancer: { source: 'balancer', observed_at: '2026-09-18T09:00:00Z', freshness: 'live',
                  data: { pool_size: 2, eligible_now: 1, slots: [{
                    slot_id: 'zai::glm-4::default', provider: 'zai', model: 'glm-4',
                    status: 'cooldown', weight: 0, success_rate: 0.2,
                  }] }, error: null },
      providers: { source: 'provider-registry', observed_at: '2026-09-18T09:00:00Z',
                   freshness: 'live', data: {
                     udbydere: [{ provider: 'zai', enabled: true }],
                     modeller: [{ provider: 'zai', model: 'glm-4', lane: 'cheap', enabled: true }],
                   }, error: null },
      diagnostics: { source: 'diagnostics', observed_at: '2026-09-18T09:00:00Z',
                     freshness: 'live', data: { status: 'ok', findings: [] }, error: null },
    },
    ...over,
  }
}

beforeEach(() => {
  vi.restoreAllMocks()
  vi.spyOn(api, 'getDashboard').mockResolvedValue(snapshot())
  vi.spyOn(api, 'getTidsserie').mockResolvedValue({
    spand: [{ tid: '2026-09-18T08:00', kald: 10, fejl: 8, latens_ms: 900 }],
  })
  vi.spyOn(api, 'getRevisioner').mockResolvedValue({ items: [] })
  vi.spyOn(api, 'getLogs').mockResolvedValue({ items: [], next_cursor: null })
})

/** KPI-tallet læses sammen med SIN etiket: både «8» og «Kald» står flere
 *  steder på fladen (grafens tabel bruger de samme ord). */
const kpi = (etiket: string) => [...document.querySelectorAll('.cl-kpi')]
  .find((k) => k.querySelector('.cl-kpi-label')?.textContent === etiket)
  ?.querySelector('.cl-kpi-tal')?.textContent

describe('CheapLanePanel', () => {
  it('viser vinduets nøgletal fra ét snapshot', async () => {
    render(<CheapLanePanel config={config} />)
    await waitFor(() => expect(document.querySelector('.cl-kpi')).toBeTruthy())
    expect(kpi('Kald')).toBe('15')
    expect(kpi('Fejl')).toBe('8')
    expect(kpi('Slots klar')).toBe('1')
  })

  it('kapacitet uden kvoter siger det — den viser ikke 0 %', async () => {
    const bruger = userEvent.setup()
    render(<CheapLanePanel config={config} />)
    await waitFor(() => expect(screen.getByRole('button', { name: 'Kapacitet' })).toBeTruthy())
    await bruger.click(screen.getByRole('button', { name: 'Kapacitet' }))
    expect(screen.getByText(/ingen kvoter/i)).toBeTruthy()
    expect(screen.queryByText('0 %')).toBeNull()
  })

  it('pause i puljen rammer SLOTTET, ikke registret', async () => {
    const kontrol = vi.spyOn(api, 'udfoerKontrol').mockResolvedValue({ status: 'ok' })
    const bruger = userEvent.setup()
    render(<CheapLanePanel config={config} />)
    await waitFor(() => expect(screen.getByRole('button', { name: 'Puljen nu' })).toBeTruthy())
    await bruger.click(screen.getByRole('button', { name: 'Puljen nu' }))
    await bruger.click(await screen.findByRole('button', { name: /zai \/ glm-4/ }))
    await bruger.click(screen.getByRole('button', { name: 'Pause slot' }))
    expect(kontrol).toHaveBeenCalledWith(config, expect.objectContaining({
      action: 'slot.pause', target: 'zai::glm-4::default',
    }))
    expect(kontrol).not.toHaveBeenCalledWith(config, expect.objectContaining({
      action: 'model.deactivate',
    }))
  })

  it('«deaktivér» på udbydere rammer REGISTRET og kræver en grund', async () => {
    const kontrol = vi.spyOn(api, 'udfoerKontrol').mockResolvedValue({ status: 'ok' })
    const bruger = userEvent.setup()
    render(<CheapLanePanel config={config} />)
    await waitFor(() => expect(screen.getByRole('button', { name: 'Udbydere' })).toBeTruthy())
    await bruger.click(screen.getByRole('button', { name: 'Udbydere' }))
    await bruger.click(await screen.findByRole('button', { name: /^Deaktivér glm-4/ }))
    await bruger.type(screen.getByLabelText(/grund/i), 'for dyr')
    await bruger.click(screen.getByRole('button', { name: 'Bekræft' }))
    expect(kontrol).toHaveBeenCalledWith(config, expect.objectContaining({
      action: 'model.deactivate', target: 'zai/glm-4', reason: 'for dyr',
    }))
  })
})

// ── fejl-matrixen ─────────────────────────────────────────────────────────
//
// Seks kilder i én konvolut. Kravet er ikke at alt virker altid — det er at
// fladen bliver ved med at KUNNE BRUGES, og at den siger hvad der mangler.

describe('CheapLanePanel · fejl-matrix', () => {
  const delvis = () => {
    const s = snapshot({ status: 'partial' })
    s.sections.balancer = {
      source: 'balancer', observed_at: null, freshness: 'unknown', data: null,
      error: { message: 'balancer state unreadable' },
    }
    return s
  }
  const kunUkendtKapacitet = () => {
    const s = snapshot()
    s.sections.capacity = {
      source: 'quota', observed_at: '2026-09-18T09:00:00Z', freshness: 'stale',
      data: { windows: [{
        period: 'month', unit: 'tokens', provider: 'groq', limit: null, used: 900,
        remaining: null, source: 'unknown', confidence: null, reset_at: null,
      }] }, error: null,
    }
    return s
  }

  it.each([
    ['en kilde mangler', delvis, 'balancer state unreadable'],
    ['kapaciteten er ukendt', kunUkendtKapacitet, 'Ukendt kapacitet'],
  ])('%s — fladen kan stadig bruges', async (_navn, lav, forventet) => {
    vi.spyOn(api, 'getDashboard').mockResolvedValue(lav())
    const bruger = userEvent.setup()
    render(<CheapLanePanel config={config} />)
    await waitFor(() => expect(document.querySelector('.cl-kpi')).toBeTruthy())

    if (forventet === 'Ukendt kapacitet') {
      await bruger.click(screen.getByRole('button', { name: 'Kapacitet' }))
    }
    expect(await screen.findByText(new RegExp(forventet))).toBeTruthy()
    // Og fanerne virker stadig — det er dét «kan bruges» betyder.
    expect(screen.getByRole('button', { name: 'Udbydere' })).toBeEnabled()
  })

  it('et dashboard der slet ikke svarer efterlader en besked, ikke en tom skærm', async () => {
    vi.spyOn(api, 'getDashboard').mockRejectedValue(new Error('503 utilgængelig'))
    render(<CheapLanePanel config={config} />)
    expect(await screen.findByText(/503 utilgængelig/)).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Udbydere' })).toBeEnabled()
  })

  it('tidsserien kan fejle uden at tage snapshotet med sig', async () => {
    vi.spyOn(api, 'getTidsserie').mockRejectedValue(new Error('nede'))
    render(<CheapLanePanel config={config} />)
    await waitFor(() => expect(document.querySelector('.cl-kpi')).toBeTruthy())
    expect(kpi('Kald')).toBe('15')
    expect(screen.getByText(/tidsserien kunne ikke hentes/)).toBeTruthy()
  })
})
