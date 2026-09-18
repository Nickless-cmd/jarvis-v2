/**
 * Oversigten: nøgletallene, grafen og — vigtigst — hvad der IKKE kunne hentes.
 *
 * Snapshotet er sammensat af seks kilder, og en af dem kan svigte uden at de
 * andre gør. Fladen skal derfor kunne sige «balanceren svarede ikke» og stadig
 * vise resten. Et panel der går helt i sort fordi én kilde fejlede, fortæller
 * mindre end det ved.
 *
 * Grafen skal kunne læses uden mus: Recharts' tooltip findes kun under en
 * markør, så tallene står også i en tabel.
 */
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { CheapLaneOverview } from './CheapLaneOverview'
import type { Snapshot } from '../../../lib/cheapLaneApi'

function snapshot(over: Partial<Snapshot> = {}): Snapshot {
  return {
    schema_version: 1,
    generated_at: '2026-09-18T09:00:00Z',
    window_hours: 24,
    status: 'complete',
    kpis: { requests: 500, tokens: 128159, errors: 255, cost_usd: 0, eligible_slots: 35, active_findings: 9 },
    sections: {
      trends: { source: 'invocation-history', observed_at: '2026-09-18T09:00:00Z', freshness: 'live',
        data: { requests: 500, tokens: 128159, errors: 255, cost_usd: 0 }, error: null },
      balancer: { source: 'balancer', observed_at: '2026-09-18T09:00:00Z', freshness: 'live',
        data: { pool_size: 161, eligible_now: 35 }, error: null },
    },
    ...over,
  }
}

describe('CheapLaneOverview', () => {
  it('viser nøgletallene fra snapshotet', () => {
    render(<CheapLaneOverview snapshot={snapshot()} serie={[]} />)
    expect(screen.getByText('500')).toBeTruthy()
    expect(screen.getByText(/128\.159/)).toBeTruthy()
    expect(screen.getByText('35')).toBeTruthy()
  })

  it('en sektion der fejlede skjuler ikke resten af skærmen', () => {
    const s = snapshot()
    s.sections.balancer = {
      source: 'balancer', observed_at: null, freshness: 'unknown', data: null,
      error: { message: 'balancer state unreadable' },
    }
    render(<CheapLaneOverview snapshot={s} serie={[]} />)
    expect(screen.getByText(/balancer state unreadable/)).toBeTruthy()
    expect(screen.getByText('500')).toBeTruthy()   // resten staar endnu
  })

  it('siger hvornår tallene er fra — serverens tid, ikke klientens', () => {
    render(<CheapLaneOverview snapshot={snapshot()} serie={[]} />)
    expect(screen.getByText(/18\.09|18-09|09:00|11:00/)).toBeTruthy()
  })

  it('grafens tal kan læses uden mus', () => {
    render(<CheapLaneOverview snapshot={snapshot()} serie={[
      { start: '2026-09-18T08:00:00Z', kald: 100, fejl: 10, tokens: 2000 },
    ]} />)
    expect(screen.getByRole('table', { name: /tabel/i })).toBeTruthy()
  })

  it('en tom tidsserie giver ingen tom graf-ramme', () => {
    render(<CheapLaneOverview snapshot={snapshot()} serie={[]} />)
    expect(screen.getByText(/ingen målinger/i)).toBeTruthy()
  })
})
