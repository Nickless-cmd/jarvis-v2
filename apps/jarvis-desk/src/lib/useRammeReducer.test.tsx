import { describe, it, expect, vi, afterEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { FALDBAGSKALD_MS, useRammeReducer } from './useRammeReducer'

const reducer = (s: string[], e: string) => [...s, e]

describe('useRammeReducer — én opdatering pr. frame', () => {
  afterEach(() => { vi.useRealTimers(); vi.unstubAllGlobals() })

  it('mange events i samme frame = ÉN render, i den rækkefølge de kom', async () => {
    let renders = 0
    const { result } = renderHook(() => { renders++; return useRammeReducer(reducer, () => [] as string[]) })
    const foer = renders
    act(() => { for (const e of ['a', 'b', 'c', 'd', 'e']) result.current[1](e) })
    expect(result.current[0]).toEqual([]) // endnu ikke — venter på framen
    await act(() => new Promise<void>((r) => requestAnimationFrame(() => r())))
    expect(result.current[0]).toEqual(['a', 'b', 'c', 'd', 'e'])
    expect(renders - foer).toBe(1)
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

  it('events efter en tømning planlægger en ny frame', async () => {
    const { result } = renderHook(() => useRammeReducer(reducer, () => [] as string[]))
    act(() => result.current[1]('1'))
    await act(() => new Promise<void>((r) => requestAnimationFrame(() => r())))
    act(() => result.current[1]('2'))
    await act(() => new Promise<void>((r) => requestAnimationFrame(() => r())))
    expect(result.current[0]).toEqual(['1', '2'])
  })
})
