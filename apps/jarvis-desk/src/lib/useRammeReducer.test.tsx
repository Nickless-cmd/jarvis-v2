import { describe, it, expect, vi, afterEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { FALDBAGSKALD_MS, KADENCE_FRAMES, useRammeReducer } from './useRammeReducer'

const reducer = (s: string[], e: string) => [...s, e]

/** Vent hele kadence-vinduet: KADENCE_FRAMES nestede frames. */
const ventKadence = () => act(() => new Promise<void>((r) => {
  const naeste = (tilbage: number) => {
    if (tilbage <= 0) { r(); return }
    requestAnimationFrame(() => naeste(tilbage - 1))
  }
  naeste(KADENCE_FRAMES)
}))

describe('useRammeReducer — ét kadence-vindue, ikke én frame', () => {
  afterEach(() => { vi.useRealTimers(); vi.unstubAllGlobals() })

  it('mange events i samme vindue = ÉN render, i den rækkefølge de kom', async () => {
    let renders = 0
    const { result } = renderHook(() => { renders++; return useRammeReducer(reducer, () => [] as string[]) })
    const foer = renders
    act(() => { for (const e of ['a', 'b', 'c', 'd', 'e']) result.current[1](e) })
    expect(result.current[0]).toEqual([]) // endnu ikke — venter på kadence-vinduet
    await ventKadence()
    expect(result.current[0]).toEqual(['a', 'b', 'c', 'd', 'e'])
    expect(renders - foer).toBe(1)
  })

  it('viser INTET efter ét rAF — vinduet er større end én frame (kadence-loftet)', async () => {
    const { result } = renderHook(() => useRammeReducer(reducer, () => [] as string[]))
    act(() => result.current[1]('1'))
    // Ét rAF = midt i vinduet. Før kadence-ændringen (29/9) ville køen være
    // tømt her; nu er den ikke. Det er præcis loftet der er sat ned.
    await act(() => new Promise<void>((r) => requestAnimationFrame(() => r())))
    expect(result.current[0]).toEqual([])
    await ventKadence()
    expect(result.current[0]).toEqual(['1'])
  })

  it('skjult vindue (rAF fyrer aldrig): timeren tømmer køen alligevel', () => {
    vi.useFakeTimers()
    vi.stubGlobal('requestAnimationFrame', () => 0) // som når vinduet ligger i bakken
    vi.stubGlobal('cancelAnimationFrame', () => {})
    const { result } = renderHook(() => useRammeReducer(reducer, () => [] as string[]))
    act(() => { result.current[1]('x'); result.current[1]('y') })
    expect(result.current[0]).toEqual([])
    act(() => { vi.advanceTimersByTime(FALDBAGSKALD_MS) })
    expect(result.current[0]).toEqual(['x', 'y'])
  })

  it('events efter en tømning planlægger et nyt vindue', async () => {
    const { result } = renderHook(() => useRammeReducer(reducer, () => [] as string[]))
    act(() => result.current[1]('1'))
    await ventKadence()
    act(() => result.current[1]('2'))
    await ventKadence()
    expect(result.current[0]).toEqual(['1', '2'])
  })

  it('KADENCE_FRAMES = 3 — loftet er ~20 opdateringer/s ved 60 Hz', () => {
    expect(KADENCE_FRAMES).toBe(3)
    expect(FALDBAGSKALD_MS).toBeGreaterThan(KADENCE_FRAMES * 16)
  })
})
