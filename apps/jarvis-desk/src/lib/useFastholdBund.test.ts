import { describe, it, expect, vi, afterEach } from 'vitest'
import { renderHook } from '@testing-library/react'
import { useFastholdBund, PIN_INTERVAL_MS } from './useFastholdBund'

afterEach(() => { vi.useRealTimers() })

/** jsdom har ingen layout: vi styrer selv målene, som browseren ville gøre. */
function rude(indholdshoejde: number, hoejde = 500) {
  return { current: { scrollTop: indholdshoejde - hoejde, scrollHeight: indholdshoejde, clientHeight: hoejde } as unknown as HTMLElement & { scrollHeight: number } }
}

describe('useFastholdBund', () => {
  it('pinner til bund når indholdet vokser UDEN en React-opdatering', () => {
    vi.useFakeTimers()
    const ref = rude(1000)
    renderHook(() => useFastholdBund(ref, true, true))
    // Svaret lander ad en anden vej: indholdet vokser, intet re-render sker.
    Object.assign(ref.current!, { scrollHeight: 1800 })
    vi.advanceTimersByTime(PIN_INTERVAL_MS)
    expect(ref.current!.scrollTop).toBe(1800)
  })

  it('rører IKKE ruden når brugeren har scrollet op', () => {
    vi.useFakeTimers()
    const ref = rude(1000)
    ref.current!.scrollTop = 120
    renderHook(() => useFastholdBund(ref, true, false))
    Object.assign(ref.current!, { scrollHeight: 1800 })
    vi.advanceTimersByTime(PIN_INTERVAL_MS * 4)
    expect(ref.current!.scrollTop).toBe(120)
  })

  it('kører ikke når der ikke arbejdes', () => {
    vi.useFakeTimers()
    const ref = rude(1000)
    renderHook(() => useFastholdBund(ref, false, true))
    Object.assign(ref.current!, { scrollHeight: 1800 })
    vi.advanceTimersByTime(PIN_INTERVAL_MS * 4)
    expect(ref.current!.scrollTop).toBe(500)
  })

  it('stopper intervallet når arbejdet slutter', () => {
    vi.useFakeTimers()
    const ref = rude(1000)
    const { unmount } = renderHook(() => useFastholdBund(ref, true, true))
    unmount()
    Object.assign(ref.current!, { scrollHeight: 2400 })
    vi.advanceTimersByTime(PIN_INTERVAL_MS * 4)
    expect(ref.current!.scrollTop).toBe(500)   // urørt: ruden stod i bund da den blev afmonteret
  })
})
