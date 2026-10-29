/**
 * MÅLING — de to tilfælde den tredje vej skal skelne (29/10-2026).
 *
 * Bjørn: «prøv den tredje». Den tredje var: loftet på 28 tegn/tick gælder
 * HOP, ikke jævn ankomst. Et hop er når hele (eller en stor del af) svaret
 * lander i ÉT tick — det er dét 20/10-kontrakten værner imod. Kommer teksten
 * jævnt, er der intet at skjule, og loftet gør bare at visningen ikke kan
 * følge kilden.
 *
 * MÅLT FØR (loftet bandt altid): kurven var konstant 848 tegn/s — flad,
 * fordi den var KLIPPET, ikke fordi den indhentede.
 *
 * Denne fil måler de to scenarier med den RIGTIGE hook og et deterministisk
 * ur. Den er en vagt, ikke en probe: tallene står som kontrakt.
 */
import { act, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { usePacedBlocks } from './usePacedBlocks'
import type { ContentBlock } from './sseProtocol'

const TICK_MS = 33

function tekst(text: string): ContentBlock[] {
  return [{ type: 'text', text }]
}

function vistTekst(blocks: ContentBlock[]): string {
  return blocks
    .filter((b): b is Extract<ContentBlock, { type: 'text' }> => b.type === 'text')
    .map((b) => b.text)
    .join('')
}

describe('Code Mode — loftet gælder hop, ikke jævn ankomst', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })
  afterEach(() => {
    vi.useRealTimers()
  })

  it('HOP: et helt svar i én frame klippes stadig til 28 tegn pr. tick', () => {
    // 20/10-kontrakten. Denne må IKKE ændre sig.
    //
    // 10.000 tegn, ikke 1.000: `pending / 3 s` kræver 110 tegn/tick ved
    // 10.000, så loftet er den bindende grænse. Ved 1.000 tegn kræver
    // indhentningskravet kun 11, og så er det raten — ikke loftet — der
    // bestemmer. Testen skal måle loftet, ikke tilfældet hvor det ikke binder.
    const target = 'a'.repeat(10_000)
    const hook = renderHook(({ blocks, live }) => usePacedBlocks(blocks, live), {
      initialProps: { blocks: tekst(target), live: true },
    })
    act(() => {
      vi.advanceTimersByTime(TICK_MS)
    })
    expect(vistTekst(hook.result.current).length).toBe(28)

    // …og det holder gennem hele udrulningen: intet tick må springe.
    let forrige = vistTekst(hook.result.current).length
    for (let i = 0; i < 60; i++) {
      act(() => {
        vi.advanceTimersByTime(TICK_MS)
      })
      const nu = vistTekst(hook.result.current).length
      expect(nu - forrige).toBeLessThanOrEqual(28)
      forrige = nu
    }
  })

  it('JÆVN ANKOMST: visningen følger kilden i stedet for at hale', () => {
    // Kilden leverer 100 tegn pr. tick = 3030 tegn/s. Det er hurtigere end
    // det gamle loft på 848 tegn/s, så før ændringen voksede efterslæbet
    // lineært. Nu skal det holde sig fladt.
    let target = 'b'.repeat(100)
    const hook = renderHook(({ blocks, live }) => usePacedBlocks(blocks, live), {
      initialProps: { blocks: tekst(target), live: true },
    })

    const efterslæb: number[] = []
    for (let i = 0; i < 40; i++) {
      // Kilden lægger 100 tegn til FØR uret tikker — så ticket ser dem som
      // jævn ankomst, ikke som et hop.
      target += 'b'.repeat(100)
      act(() => {
        hook.rerender({ blocks: tekst(target), live: true })
      })
      act(() => {
        vi.advanceTimersByTime(TICK_MS)
      })
      efterslæb.push(target.length - vistTekst(hook.result.current).length)
    }

    // Efterslæbet må ikke vokse lineært. Ved 100 tegn/tick ind og et loft på
    // 848 tegn/s voksede det med ~72 tegn pr. tick = ~2.900 efter 40 ticks.
    const sidste = efterslæb[efterslæb.length - 1] ?? 0
    const tidlig = efterslæb[5] ?? 0
    const maks = Math.max(...efterslæb)
    expect(maks).toBeLessThan(1200)
    // …og det skal være STABILT, ikke bare mindre: slut-efterslæbet må ikke
    // være større end det tidlige, ellers haler vi stadig.
    expect(sidste).toBeLessThan(tidlig + 600)
  })

  it('grundtempoet på et kort svar er urørt', () => {
    const target = 'c'.repeat(100)
    const hook = renderHook(({ blocks, live }) => usePacedBlocks(blocks, live), {
      initialProps: { blocks: tekst(target), live: true },
    })
    act(() => {
      vi.advanceTimersByTime(TICK_MS)
    })
    const foerste = vistTekst(hook.result.current).length
    // Et kort svar skal begynde roligt — ikke skvulpe ud.
    expect(foerste).toBeLessThanOrEqual(28)
    expect(foerste).toBeGreaterThan(0)
  })
})
