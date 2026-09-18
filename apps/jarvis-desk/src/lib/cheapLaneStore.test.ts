/**
 * Datalaget bag kontrolcentret: ét øjebliksbillede, opdateret af Centrals
 * strøm — og med en vej tilbage når strømmen svigter.
 *
 * ## Hvorfor strømmen, og hvorfor en faldback
 *
 * Panelet før dette hentede sine fire kilder hver for sig med hver sin timer.
 * Det er både flere forbindelser end nødvendigt på et API med én worker (se
 * `centralStream.ts`) og en garanti for at fladerne viser hver sit tidspunkt.
 * Her hentes ét sammensat snapshot, og Centrals egen strøm siger hvornår det
 * er forældet.
 *
 * Men en strøm der dør, må ikke efterlade skærmen med tal fra i går uden at
 * sige det. Derfor: fejler den, skifter tilstanden til `polling`, og der
 * hentes igen hvert 15. sekund indtil der kommer begivenheder igen.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { renderHook, act } from '@testing-library/react'

const getDashboard = vi.fn()
const subscribe = vi.fn()

vi.mock('./cheapLaneApi', async () => {
  const ægte = await vi.importActual<Record<string, unknown>>('./cheapLaneApi')
  return { ...ægte, getDashboard: (...a: unknown[]) => getDashboard(...a) }
})
vi.mock('./centralStream', () => ({
  subscribeCentralStream: (...a: unknown[]) => subscribe(...a),
}))

import { useCheapLaneStore, POLL_MS, DEBOUNCE_MS } from './cheapLaneStore'

const config = { apiBaseUrl: 'http://x', authToken: 't' }

/** Fake timers gør `waitFor` ubrugelig — den poller på de ure vi selv styrer.
 *  I stedet drives løfterne frem eksplicit. */
async function flush(ms = 0) {
  await act(async () => { await vi.advanceTimersByTimeAsync(ms) })
}

function snapshot(nu = '2026-09-18T09:00:00Z') {
  return {
    schema_version: 1, generated_at: nu, window_hours: 24, status: 'complete',
    kpis: { requests: 500, tokens: 128159, errors: 255, cost_usd: 0, eligible_slots: 35, active_findings: 9 },
    sections: {
      capacity: { source: 'quota', observed_at: nu, freshness: 'live', data: { windows: [] }, error: null },
    },
  }
}

/** Den sidst tilmeldte lytter — sådan efterlignes en nerve-fyring. */
let sidsteItem: ((i: unknown) => void) | null = null
let sidsteFejl: (() => void) | null = null

beforeEach(() => {
  vi.useFakeTimers()
  getDashboard.mockReset().mockResolvedValue(snapshot())
  subscribe.mockReset().mockImplementation((_c: unknown, onItem: (i: unknown) => void, onErr: () => void) => {
    sidsteItem = onItem
    sidsteFejl = onErr
    return () => { sidsteItem = null; sidsteFejl = null }
  })
})

afterEach(() => {
  vi.useRealTimers()
  vi.restoreAllMocks()
})

describe('useCheapLaneStore', () => {
  it('henter ÉT snapshot og opdaterer efter en cheap-lane-begivenhed', async () => {
    const { result } = renderHook(() => useCheapLaneStore(config, 24))
    await flush()
    expect(result.current.snapshot?.schema_version).toBe(1)
    expect(getDashboard).toHaveBeenCalledTimes(1)

    await act(async () => {
      sidsteItem?.({ cluster: 'runtime', nerve: 'cheap_lane', kind: 'runtime.cheap_lane_provider_completed' })
      await vi.advanceTimersByTimeAsync(DEBOUNCE_MS + 10)
    })
    expect(getDashboard).toHaveBeenCalledTimes(2)
  })

  it('samler en byge af begivenheder til ÉN hentning', async () => {
    // Cheap lane fyrer 100-500 kald i timen. Uden sammenlægning ville hver
    // enkelt blive en hentning, og panelet ville slå API'et ihjel for at vise
    // at API'et har travlt.
    const { result } = renderHook(() => useCheapLaneStore(config, 24))
    await flush()
    expect(result.current.snapshot).toBeTruthy()
    await act(async () => {
      for (let i = 0; i < 20; i++) {
        sidsteItem?.({ cluster: 'runtime', nerve: 'x', kind: 'runtime.cheap_lane_provider_completed' })
      }
      await vi.advanceTimersByTimeAsync(DEBOUNCE_MS + 10)
    })
    expect(getDashboard).toHaveBeenCalledTimes(2)
  })

  it('rører sig ikke på begivenheder der ikke er cheap lane', async () => {
    const { result } = renderHook(() => useCheapLaneStore(config, 24))
    await flush()
    expect(result.current.snapshot).toBeTruthy()
    await act(async () => {
      sidsteItem?.({ cluster: 'memory', nerve: 'recall', kind: 'memory.recall_done' })
      await vi.advanceTimersByTimeAsync(DEBOUNCE_MS + 50)
    })
    expect(getDashboard).toHaveBeenCalledTimes(1)
  })

  it('markerer data som forældet og poller når strømmen svigter', async () => {
    const { result } = renderHook(() => useCheapLaneStore(config, 24))
    await flush()
    expect(result.current.snapshot).toBeTruthy()
    expect(result.current.liveState).toBe('live')

    await act(async () => { sidsteFejl?.() })
    expect(result.current.liveState).toBe('polling')

    await act(async () => { await vi.advanceTimersByTimeAsync(POLL_MS + 10) })
    expect(getDashboard).toHaveBeenCalledTimes(2)
  })

  it('stopper med at polle når begivenhederne kommer igen', async () => {
    const { result } = renderHook(() => useCheapLaneStore(config, 24))
    await flush()
    expect(result.current.snapshot).toBeTruthy()
    await act(async () => { sidsteFejl?.() })
    await act(async () => {
      sidsteItem?.({ cluster: 'runtime', nerve: 'x', kind: 'runtime.cheap_lane_provider_completed' })
      await vi.advanceTimersByTimeAsync(DEBOUNCE_MS + 10)
    })
    expect(result.current.liveState).toBe('live')
    const efterGenoptagelse = getDashboard.mock.calls.length
    await act(async () => { await vi.advanceTimersByTimeAsync(POLL_MS * 2) })
    expect(getDashboard).toHaveBeenCalledTimes(efterGenoptagelse)
  })

  it('henter forfra når tidsvinduet skifter', async () => {
    const { result, rerender } = renderHook(
      ({ t }: { t: number }) => useCheapLaneStore(config, t), { initialProps: { t: 24 } })
    await flush()
    expect(result.current.snapshot).toBeTruthy()
    rerender({ t: 168 })
    await flush()
    expect(getDashboard).toHaveBeenCalledTimes(2)
    expect(getDashboard.mock.calls[1]?.[1]).toBe(168)
  })

  it('en fejlet hentning efterlader et svar — ikke en tom skærm', async () => {
    getDashboard.mockRejectedValueOnce(new Error('503'))
    const { result } = renderHook(() => useCheapLaneStore(config, 24))
    await flush()
    expect(result.current.error).toBeTruthy()
    expect(result.current.snapshot).toBeNull()
    expect(result.current.liveState).not.toBe('live')
  })

  it('et svar der lander EFTER unmount sætter ingen tilstand', async () => {
    // Den klassiske React-advarsel, og værre her: et snapshot fra et vindue
    // brugeren har forladt ville skrive sig ind i det næste panel.
    let løs: (v: unknown) => void = () => {}
    getDashboard.mockReturnValueOnce(new Promise((r) => { løs = r }))
    const { unmount } = renderHook(() => useCheapLaneStore(config, 24))
    unmount()
    await act(async () => { løs(snapshot()); await vi.advanceTimersByTimeAsync(10) })
    // Ingen advarsel og ingen kast = bestået; vi tjekker at strømmen blev lukket.
    expect(sidsteItem).toBeNull()
  })

  it('holder KUN ét abonnement på Centrals strøm', async () => {
    const { result } = renderHook(() => useCheapLaneStore(config, 24))
    await flush()
    expect(result.current.snapshot).toBeTruthy()
    await act(async () => {
      sidsteItem?.({ cluster: 'runtime', nerve: 'x', kind: 'runtime.cheap_lane_provider_completed' })
      await vi.advanceTimersByTimeAsync(DEBOUNCE_MS + 10)
    })
    expect(subscribe).toHaveBeenCalledTimes(1)
  })
})

// ── speccens to krav til hvad der sker når noget svigter (18/9-2026) ───────

describe('bevarSidsteKendte', () => {
  it('en sektion der svigtede beholder sine sidste tal — mærket forældede', async () => {
    const { bevarSidsteKendte } = await import('./cheapLaneStore')
    const gammelt = snapshot() as never as Parameters<typeof bevarSidsteKendte>[1]
    const nyt = {
      ...snapshot('2026-09-18T10:00:00Z'),
      sections: { capacity: { source: 'quota', observed_at: null, freshness: 'unknown',
                              data: null, error: { message: 'kilden svarede ikke' } } },
    } as never as Parameters<typeof bevarSidsteKendte>[0]
    const ud = bevarSidsteKendte(nyt, gammelt)
    // Fem minutter gamle tal er stadig svaret paa de fleste spoergsmaal.
    expect(ud.sections.capacity?.data).toBeTruthy()
    expect(ud.sections.capacity?.freshness).toBe('stale')
    // Og fejlen staar stadig, saa ingen tror de er friske.
    expect(ud.sections.capacity?.error).toBeTruthy()
  })

  it('en sund sektion overskrives med de NYE tal', async () => {
    const { bevarSidsteKendte } = await import('./cheapLaneStore')
    const gammelt = snapshot() as never as Parameters<typeof bevarSidsteKendte>[1]
    const nyt = snapshot('2026-09-18T10:00:00Z') as never as Parameters<typeof bevarSidsteKendte>[0]
    const ud = bevarSidsteKendte(nyt, gammelt)
    expect(ud.sections.capacity?.freshness).toBe('live')
  })
})

describe('erGyldigt', () => {
  it('afviser et svar der ikke er et snapshot', async () => {
    const { erGyldigt } = await import('./cheapLaneStore')
    expect(erGyldigt(snapshot())).toBe(true)
    expect(erGyldigt(null)).toBe(false)
    expect(erGyldigt({})).toBe(false)
    expect(erGyldigt({ ...snapshot(), schema_version: 2 })).toBe(false)
    expect(erGyldigt({ ...snapshot(), generated_at: 'ikke en dato' })).toBe(false)
  })

  it('et ugyldigt svar skubber IKKE de rigtige tal af skærmen', async () => {
    const { result } = renderHook(() => useCheapLaneStore(config, 24))
    await flush()
    expect(result.current.snapshot).toBeTruthy()
    getDashboard.mockResolvedValueOnce({ noget: 'helt andet' })
    await act(async () => { result.current.refresh(); await vi.advanceTimersByTimeAsync(10) })
    expect(result.current.snapshot?.schema_version).toBe(1)
    expect(result.current.error).toMatch(/ikke er et snapshot/)
  })
})
