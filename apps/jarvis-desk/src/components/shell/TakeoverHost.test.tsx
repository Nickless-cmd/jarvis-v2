/**
 * Det flydende takeover-kort må ikke vises (12/11-2026).
 *
 * Bjørn: «dette chat-vindue bliver vist i arbejdsfladen når et run kører, den skal væk — den
 * viser også andres sessioner.» TakeoverHost hentede `/chat/active-runs` (alle sessioner
 * brugeren MÅ se, også andres) og tegnede et live-kort med «Åbn chat» på de øvrige flader.
 * Chat og Code har deres egen liveness; kortet var kun for de andre. Det er fjernet — og med
 * det de to polls (active-runs hvert 1,5 s, transcript hvert 1,2 s), der også åd rate-limit.
 *
 * Komponenten BLIVER, fordi den bærer Jarvis-figurens bro: et klik på dens taleboble åbner
 * samtalen den talte om.
 */
import { render } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const api = vi.hoisted(() => ({
  getActiveRuns: vi.fn(async () => ['chat-anden-brugers-session']),
  followRun: vi.fn(() => ({ abort: vi.fn() })),
  getSession: vi.fn(async () => null),
}))
vi.mock('../../lib/api', () => api)

// Stabile referencer: komponentens effekter afhænger af `settings`, så et nyt objekt pr.
// render ville give en uendelig løkke (testopsætningen, ikke koden).
const mocks = vi.hoisted(() => ({
  select: vi.fn(),
  sessions: [{ id: 'chat-anden-brugers-session', title: 'Eksperimentelle bevidsthedsmålinger' }],
  settings: { apiBaseUrl: 'http://test.local', authToken: 't' },
}))
const select = mocks.select
vi.mock('../../hooks/useSessions', () => ({
  useSessions: () => ({ sessions: mocks.sessions, select: mocks.select }),
}))
vi.mock('../../hooks/useSettings', () => ({
  useSettings: () => ({ settings: mocks.settings }),
}))

import { TakeoverHost } from './TakeoverHost'

beforeEach(() => { vi.useFakeTimers() })
afterEach(() => {
  vi.useRealTimers()
  vi.clearAllMocks()
  delete (window as unknown as { jarvisDesk?: unknown }).jarvisDesk
})

describe('TakeoverHost', () => {
  for (const surface of ['cowork', 'settings', 'central']) {
    it(`tegner intet kort og poller ikke active-runs på «${surface}» — heller ikke når en andens session kører`, async () => {
      const { container } = render(<TakeoverHost surface={surface} setSurface={vi.fn()} />)
      await vi.advanceTimersByTimeAsync(10_000)

      expect(container.querySelector('.takeover-live')).toBeNull()
      expect(container.textContent).toBe('')
      expect(api.getActiveRuns).not.toHaveBeenCalled()
      expect(api.followRun).not.toHaveBeenCalled()
      expect(api.getSession).not.toHaveBeenCalled()
    })
  }

  it('figurens taleboble åbner stadig samtalen: vælg den og gå til chat', () => {
    let aabn: (sid: string) => void = () => {}
    const afmeld = vi.fn()
    ;(window as unknown as { jarvisDesk: unknown }).jarvisDesk = {
      figur: {
        paaAabnSamtale: (cb: (sid: string) => void) => { aabn = cb; return afmeld },
        paaStemme: () => afmeld,
      },
    }
    const setSurface = vi.fn()
    const { unmount } = render(<TakeoverHost surface="cowork" setSurface={setSurface} />)

    aabn('chat-som-figuren-talte-om')

    expect(select).toHaveBeenCalledWith('chat-som-figuren-talte-om')
    expect(setSurface).toHaveBeenCalledWith('chat')
    unmount()
    expect(afmeld).toHaveBeenCalled()      // og afmelder ved unmount
  })

  it('i code-fladen skifter figurens klik ikke flade (som før)', () => {
    let aabn: (sid: string) => void = () => {}
    ;(window as unknown as { jarvisDesk: unknown }).jarvisDesk = {
      figur: { paaAabnSamtale: (cb: (sid: string) => void) => { aabn = cb; return vi.fn() }, paaStemme: () => vi.fn() },
    }
    const setSurface = vi.fn()
    render(<TakeoverHost surface="code" setSurface={setSurface} />)

    aabn('chat-x')

    expect(select).toHaveBeenCalledWith('chat-x')
    expect(setSurface).not.toHaveBeenCalled()
  })
})
