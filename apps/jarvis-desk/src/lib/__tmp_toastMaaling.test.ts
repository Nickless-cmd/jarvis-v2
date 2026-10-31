/** MIDLERTIDIG MÅLING — slettes efter brug.
 *
 * Spørgsmålet (Bjørn 31/10-2026): approval-kortet får scroll-pilen til at
 * dukke op selv om man står i bunden. Kortet vokser `.composer-area`, så
 * transcripten bliver lavere. Her måles hvad koordinatoren gør ved det.
 */
import { describe, it, expect, vi, afterEach, beforeEach } from 'vitest'
import { act, renderHook } from '@testing-library/react'
import { useChatScroll, SCROLL_SAMPLE_INTERVAL_MS } from './useChatScroll'

interface Maal {
  el: HTMLElement
  top: () => number
  max: () => number
  saetHoejde: (h: number) => void
}

function rude(indholdshoejde: number, hoejde = 500): Maal {
  let top = indholdshoejde - hoejde
  const scrollHeight = indholdshoejde
  let clientHeight = hoejde
  const max = () => Math.max(0, scrollHeight - clientHeight)
  const el = document.createElement('div')
  Object.defineProperty(el, 'scrollTop', {
    get: () => top,
    set: (v: number) => { top = Math.min(v, max()) },
    configurable: true,
  })
  Object.defineProperty(el, 'scrollHeight', { get: () => scrollHeight, configurable: true })
  Object.defineProperty(el, 'clientHeight', { get: () => clientHeight, configurable: true })
  return { el, top: () => top, max, saetHoejde: (h) => { clientHeight = h } }
}

class MockRO {
  static alle: MockRO[] = []
  private cb: () => void
  constructor(cb: () => void) { this.cb = cb; MockRO.alle.push(this) }
  observe() { /* noop */ }
  unobserve() { /* noop */ }
  disconnect() { MockRO.alle = MockRO.alle.filter((r) => r !== this) }
  fyr() { this.cb() }
}

beforeEach(() => { MockRO.alle = []; globalThis.ResizeObserver = MockRO as unknown as typeof ResizeObserver })
afterEach(() => { vi.useRealTimers() })

function opsæt(maal: Maal) {
  const ref = { current: null as HTMLElement | null }
  const hook = renderHook(() => useChatScroll(ref, { arbejder: false, aktiv: false }))
  act(() => { hook.result.current.containerRef(maal.el) })
  return { hook, ref }
}

describe('MÅLING — approval-kortet vokser composeren', () => {
  it('A: browseren justerer rullen efter væksten → flipper atBottom?', () => {
    vi.useFakeTimers()
    const maal = rude(1000, 500) // top=500, max=500 → i bund
    const { hook } = opsæt(maal)
    expect(hook.result.current.atBottom).toBe(true)

    // Approval-kortet kommer: transcripten bliver 100 px lavere (max 500 → 600)
    maal.saetHoejde(400)
    act(() => { MockRO.alle[0]!.fyr() })
    // ResizeObserver-grenen skriver til bund
    console.log('[A] efter resize: top =', maal.top(), 'max =', maal.max())

    // Scroll anchoring: browseren flytter rullen 40 px op og fyrer et scroll-event
    act(() => { maal.el.scrollTop = 560; hook.result.current.onScroll() })
    act(() => { vi.advanceTimersByTime(SCROLL_SAMPLE_INTERVAL_MS + 20) })
    console.log('[A] atBottom efter anchoring+afregning =', hook.result.current.atBottom)
  })

  it('B: læser scrollet op, composeren vokser → ryddes atBottom?', () => {
    vi.useFakeTimers()
    const maal = rude(2000, 500) // top=1500, max=1500
    const { hook } = opsæt(maal)

    // Læseren scroller op
    act(() => { maal.el.scrollTop = 1200; hook.result.current.onScroll() })
    act(() => { vi.advanceTimersByTime(SCROLL_SAMPLE_INTERVAL_MS + 20) })
    expect(hook.result.current.atBottom).toBe(false)

    // Approval-kortet kommer: transcripten krymper, og resize-grenen skriver til bund
    maal.saetHoejde(400)
    act(() => { MockRO.alle[0]!.fyr() })
    console.log('[B] efter resize: top =', maal.top(), 'max =', maal.max(),
      '→ står i bunden?', maal.top() === maal.max())
    console.log('[B] atBottom =', hook.result.current.atBottom, '(pil synlig?', !hook.result.current.atBottom, ')')
  })
})
