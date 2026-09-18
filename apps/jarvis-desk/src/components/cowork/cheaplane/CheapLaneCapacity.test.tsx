/**
 * Kapacitet: forskellen på «0 tilbage» og «vi ved det ikke».
 *
 * Det er hele grunden til at fanen findes. Bjørn skal kunne se om han kan køre
 * videre, og et panel der viser 0 % fordi ingen har fortalt det hvad grænsen
 * er, siger noget FORKERT — ikke noget ufuldstændigt. Derfor er ukendt
 * kapacitet aldrig et tal, aldrig en tom bjælke og aldrig nul procent.
 *
 * Og enheder blandes ikke: tokens, kald og dollars lægges aldrig sammen til
 * ét tal, fordi summen ikke betyder noget.
 */
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { CheapLaneCapacity } from './CheapLaneCapacity'
import type { KvoteVindue } from '../../../lib/cheapLaneApi'

const ukendt: KvoteVindue = {
  period: 'month', unit: 'tokens', provider: 'groq', auth_profile: 'primary',
  limit: null, used: 120, remaining: null, source: 'unknown', confidence: null, reset_at: null,
}
const kendt: KvoteVindue = {
  period: 'day', unit: 'requests', provider: 'kilo', auth_profile: 'primary',
  limit: 1000, used: 250, remaining: 750, source: 'provider', confidence: 0.9,
  reset_at: '2026-09-19T00:00:00Z',
}

describe('CheapLaneCapacity', () => {
  it('viser ukendt kapacitet som ukendt — ikke som nul', () => {
    render(<CheapLaneCapacity vinduer={[ukendt]} />)
    expect(screen.getByText('Ukendt kapacitet')).toBeTruthy()
    expect(screen.queryByText('0 %')).toBeNull()
    expect(screen.queryByText('0 tilbage')).toBeNull()
  })

  it('viser det brugte tal selv når grænsen er ukendt', () => {
    // Forbruget ER målt. At skjule det, fordi grænsen mangler, ville kaste
    // rigtige data væk sammen med de manglende.
    render(<CheapLaneCapacity vinduer={[ukendt]} />)
    expect(screen.getByText(/120/)).toBeTruthy()
  })

  it('viser brugt, grænse, rest og kilde når tallene findes', () => {
    render(<CheapLaneCapacity vinduer={[kendt]} />)
    expect(screen.getByText(/250/)).toBeTruthy()
    expect(screen.getByText(/1\.000/)).toBeTruthy()
    expect(screen.getByText(/750 tilbage/)).toBeTruthy()
    expect(screen.getByText('provider')).toBeTruthy()
  })

  it('blander aldrig enheder i samme gruppe', () => {
    render(<CheapLaneCapacity vinduer={[ukendt, kendt]} />)
    // To vinduer, to enheder, to rækker — ingen samlet total.
    expect(screen.getByText(/tokens/)).toBeTruthy()
    expect(screen.getByText(/kald/)).toBeTruthy()
    expect(screen.queryByText(/samlet/i)).toBeNull()
  })

  it('siger det ligeud når der slet ikke er kvoter at vise', () => {
    render(<CheapLaneCapacity vinduer={[]} />)
    expect(screen.getByText(/ingen kvoter/i)).toBeTruthy()
  })

  it('procent regnes kun når der ER en grænse', () => {
    render(<CheapLaneCapacity vinduer={[kendt]} />)
    expect(screen.getByText('25 %')).toBeTruthy()
  })
})
