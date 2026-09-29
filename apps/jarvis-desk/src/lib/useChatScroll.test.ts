/**
 * Testene for scroll-koordinatoren (spec'ens punkt 1a).
 *
 * Hver test er mutationsprøvet: den adfærd testen påstår at måle er slået fra,
 * og testen er set fejle. Mutationerne står i kommentaren over den enkelte test.
 * En grøn test der ikke kan slås fra måler ingenting (spec'ens test-disciplin 7).
 *
 * Målene er sat som `top() === max()`, ikke som et fast tal: det er dét testen
 * mener — «ruden står i bunden» — og det holder når indholdet vokser undervejs.
 */
import { describe, it, expect, vi, afterEach, beforeEach } from 'vitest'
import { act, renderHook } from '@testing-library/react'
import { useChatScroll, PIN_INTERVAL_MS } from './useChatScroll'

interface Maal {
  el: HTMLElement
  top: () => number
  /** Den største scrollTop browseren ville tillade. */
  max: () => number
  antalSkrivninger: () => number
  voksTil: (h: number) => void
  saetHoejde: (h: number) => void
}

/** jsdom har ingen layout: vi styrer selv målene, som browseren ville gøre. */
function rude(indholdshoejde: number, hoejde = 500): Maal {
  let top = indholdshoejde - hoejde
  let skrivninger = 0
  let scrollHeight = indholdshoejde
  let clientHeight = hoejde
  const max = () => Math.max(0, scrollHeight - clientHeight)
  const el = {} as Record<string, unknown>
  Object.defineProperty(el, 'scrollTop', {
    get: () => top,
    // Browseren CLAMPER: koden skriver `scrollHeight`, men ruden kan ikke komme
    // længere end `scrollHeight - clientHeight`. Uden clamps her ville testen
    // måle hvilket tal der blev skrevet, ikke hvor ruden endte.
    set: (v: number) => { skrivninger++; top = Math.min(v, max()) },
    configurable: true,
  })
  Object.defineProperty(el, 'scrollHeight', { get: () => scrollHeight, configurable: true })
  Object.defineProperty(el, 'clientHeight', { get: () => clientHeight, configurable: true })
  return {
    el: el as unknown as HTMLElement,
    top: () => top,
    max,
    antalSkrivninger: () => skrivninger,
    voksTil: (h) => { scrollHeight = h },
    saetHoejde: (h) => { clientHeight = h },
  }
}

/** jsdom har ingen ResizeObserver — vi fanger instanserne så testen kan fyre dem. */
class MockRO {
  static alle: MockRO[] = []
  private cb: () => void
  constructor(cb: () => void) { this.cb = cb; MockRO.alle.push(this) }
  observe() { /* elementet er underforstået i testen */ }
  unobserve() { /* ingen brug for den */ }
  disconnect() { MockRO.alle = MockRO.alle.filter((r) => r !== this) }
  fyr() { this.cb() }
}

beforeEach(() => {
  MockRO.alle = []
  globalThis.ResizeObserver = MockRO as unknown as typeof ResizeObserver
})
afterEach(() => { vi.useRealTimers() })

function opsæt(maal: Maal, props: { arbejder?: boolean; aktiv?: boolean } = {}) {
  const ref = { current: null as HTMLElement | null }
  const hook = renderHook(
    (p: { arbejder: boolean; aktiv: boolean }) => useChatScroll(ref, p),
    { initialProps: { arbejder: false, aktiv: false, ...props } },
  )
  act(() => { hook.result.current.containerRef(maal.el) })
  return { hook, ref }
}

describe('useChatScroll — den ene skriver', () => {
  it('pinner til bund når indholdet vokser UDEN en React-opdatering (17/9-nettet)', () => {
    // MUTATION: fjern intervallet i effekten → ruden bliver på 500 mens max er
    // 1300 → fejler. Det er 17/9-tilfældet: et svar lander ad en vej hvor
    // hverken stream-blokke, follow-blokke eller besked-antallet ændrer sig.
    vi.useFakeTimers()
    const maal = rude(1000)
    const { hook } = opsæt(maal, { aktiv: true })
    maal.voksTil(1800)
    act(() => { vi.advanceTimersByTime(PIN_INTERVAL_MS) })
    expect(maal.top()).toBe(maal.max())
    expect(hook.result.current.atBottom).toBe(true)
  })

  it('rører IKKE ruden når brugeren har scrollet op', () => {
    // MUTATION: fjern `if (atBottomRef.current)` i `melder`s indhold/resize-gren
    // → ruden rives ned til 1900 → fejler.
    vi.useFakeTimers()
    const maal = rude(2000)
    const { hook } = opsæt(maal, { aktiv: true })
    act(() => { maal.el.scrollTop = 300; hook.result.current.onScroll() })
    expect(hook.result.current.atBottom).toBe(false)
    const foer = maal.antalSkrivninger()
    maal.voksTil(2400)
    act(() => { vi.advanceTimersByTime(PIN_INTERVAL_MS * 4) })
    expect(maal.top()).toBe(300)
    expect(maal.antalSkrivninger()).toBe(foer)
  })

  it('læser-input i bunden opdaterer follow-ejerskabet med det samme', () => {
    // MUTATION: gør tærsklen eksakt (`scrollTop === max`) i stedet for
    // NEAR_BOTTOM_PX → 480 tæller ikke som bund → fejler.
    const maal = rude(1000) // max = 500
    const { hook } = opsæt(maal)
    act(() => { maal.el.scrollTop = 480; hook.result.current.onScroll() })
    expect(hook.result.current.atBottom).toBe(true)
  })

  it('skriver ikke når ruden allerede står i bund — så vores skrivning ikke nulstiller brugerens scroll', () => {
    // MUTATION: fjern «kun hvis rykket»-guarden i skrivTilBund → der skrives
    // hvert tick → fejler. Dette er beviset for at der er ÉN skriver: en
    // skrivning der ikke ændrer noget må ikke fyre et scroll-event, for det
    // ville nulstille brugerens «jeg har scrollet op» hvert kvarte sekund.
    vi.useFakeTimers()
    const maal = rude(1000)
    opsæt(maal, { aktiv: true })
    const foer = maal.antalSkrivninger()
    act(() => { vi.advanceTimersByTime(PIN_INTERVAL_MS * 4) })
    expect(maal.antalSkrivninger()).toBe(foer)
  })

  it('pinner når containeren krymper — banneret dukker op uden at indholdet ændrer sig', () => {
    // MUTATION: fjern ResizeObserver-effekten → ingen instans → fejler på
    // længden alene. Kant-tilfælde 5 i spec'ens tabel.
    const maal = rude(1000, 500) // står i bund
    opsæt(maal)
    expect(MockRO.alle).toHaveLength(1)
    maal.saetHoejde(400) // containeren bliver lavere; vi står nu 100 px over bunden
    act(() => { MockRO.alle[0]!.fyr() })
    expect(maal.top()).toBe(maal.max())
  })

  it('opretter ResizeObserveren når transcripten dukker op — ikke kun ved mount (kold sti)', () => {
    // MUTATION: gør effekten afhængig af `ref` i stedet for `container` →
    // observeren oprettes ved mount hvor ref.current er null → fejler.
    // Transcripten er betinget monteret (tom-samtale-grenen), så dette er den
    // sti ChatViews gamle `[atBottom]`-afhængighed ikke dækkede.
    const maal = rude(1000)
    const ref = { current: null as HTMLElement | null }
    const hook = renderHook((p: { arbejder: boolean; aktiv: boolean }) => useChatScroll(ref, p),
      { initialProps: { arbejder: false, aktiv: false } })
    expect(MockRO.alle).toHaveLength(0)
    act(() => { hook.result.current.containerRef(maal.el) })
    expect(MockRO.alle).toHaveLength(1)
  })

  it('springer til bund når dit eget svar begynder', () => {
    // MUTATION: fjern `pin-start`-grenen i melder → atBottom bliver falsk og
    // ruden står på 100 → fejler.
    const maal = rude(2000)
    const { hook } = opsæt(maal)
    act(() => { maal.el.scrollTop = 100; hook.result.current.onScroll() })
    expect(hook.result.current.atBottom).toBe(false)
    act(() => { hook.rerender({ arbejder: true, aktiv: true }) })
    expect(maal.top()).toBe(maal.max())
    expect(hook.result.current.atBottom).toBe(true)
  })

  it('ny session lander i bunden, også når man stod scrollet op i den forrige', () => {
    // MUTATION: fjern `ny-session`-grenen → ruden bliver på 100 → fejler.
    const maal = rude(2000)
    const { hook } = opsæt(maal)
    act(() => { maal.el.scrollTop = 100; hook.result.current.onScroll() })
    act(() => { hook.result.current.melder('ny-session') })
    expect(maal.top()).toBe(maal.max())
    expect(hook.result.current.atBottom).toBe(true)
  })

  it('tæller ulæste når man ikke står i bunden, og følger med når man gør', () => {
    // MUTATION: lad `ny-besked` skrive ubetinget → ruden flytter sig fra 100
    // mens man læser → fejler.
    const maal = rude(2000)
    const { hook } = opsæt(maal)
    act(() => { maal.el.scrollTop = 100; hook.result.current.onScroll() })
    act(() => { hook.result.current.melder('ny-besked') })
    expect(hook.result.current.unread).toBe(1)
    expect(maal.top()).toBe(100)

    // Tilbage til bunden, og indholdet vokser: næste besked skal FØLGES.
    act(() => { maal.el.scrollTop = maal.max(); hook.result.current.onScroll() })
    maal.voksTil(2400)
    act(() => { hook.result.current.melder('ny-besked') })
    expect(hook.result.current.unread).toBe(0)
    expect(maal.top()).toBe(maal.max())
  })

  it('til-bund-pilen springer til bund og nulstiller tælleren', () => {
    // MUTATION: fjern `til-bund`-grenen → ruden bliver på 100 → fejler.
    const maal = rude(2000)
    const { hook } = opsæt(maal)
    act(() => { maal.el.scrollTop = 100; hook.result.current.onScroll() })
    act(() => { hook.result.current.melder('ny-besked') })
    expect(hook.result.current.unread).toBe(1)
    act(() => { hook.result.current.melder('til-bund') })
    expect(maal.top()).toBe(maal.max())
    expect(hook.result.current.unread).toBe(0)
    expect(hook.result.current.atBottom).toBe(true)
  })

  it('holder ikke rullen i bund når der ikke arbejdes', () => {
    // MUTATION: fjern `if (!aktiv) return` → intervallet kører → fejler.
    vi.useFakeTimers()
    const maal = rude(1000)
    opsæt(maal, { aktiv: false })
    maal.voksTil(1800)
    act(() => { vi.advanceTimersByTime(PIN_INTERVAL_MS * 4) })
    expect(maal.top()).toBe(500)
  })

  it('stopper intervallet når arbejdet slutter', () => {
    // MUTATION: fjern `if (!aktiv) return` → intervallet fortsætter efter
    // rerender → fejler.
    vi.useFakeTimers()
    const maal = rude(1000)
    const { hook } = opsæt(maal, { aktiv: true })
    act(() => { hook.rerender({ arbejder: false, aktiv: false }) })
    maal.voksTil(1800)
    act(() => { vi.advanceTimersByTime(PIN_INTERVAL_MS * 4) })
    expect(maal.top()).toBe(500)
  })

  it('stopper intervallet når hooken afmonteres', () => {
    // MUTATION: fjern cleanup'en (`clearInterval`) → intervallet lever videre → fejler.
    vi.useFakeTimers()
    const maal = rude(1000)
    const { hook } = opsæt(maal, { aktiv: true })
    hook.unmount()
    maal.voksTil(2400)
    act(() => { vi.advanceTimersByTime(PIN_INTERVAL_MS * 4) })
    expect(maal.top()).toBe(500)
  })

  it('melder ikke resize når man er scrollet op', () => {
    // MUTATION: fjern `if (atBottomRef.current)` i resize-grenen → ruden rives
    // ned når layoutet ændrer sig mens man læser → fejler.
    const maal = rude(2000)
    const { hook } = opsæt(maal)
    act(() => { maal.el.scrollTop = 300; hook.result.current.onScroll() })
    maal.saetHoejde(400)
    act(() => { MockRO.alle[0]!.fyr() })
    expect(maal.top()).toBe(300)
  })
})
