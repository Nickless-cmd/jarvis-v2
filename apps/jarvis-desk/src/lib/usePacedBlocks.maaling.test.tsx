/**
 * VAGT — Code Mode-pacerens kurve, målt med den RIGTIGE hook.
 *
 * Bjørn 29/10-2026: «det køre stadig mærkeligt». Chat mode fik den adaptive
 * pacer (`paceRate.ts`); Code Mode blev aldrig koblet på. Den kørte
 * `step = min(28, max(5, ceil(pending/12)))` pr. 33 ms-tick.
 *
 * MÅLT FØR ændringen (deterministisk ur, ingen mock):
 *
 *   2000 tegn → 3,00 s
 *   5000 tegn → 6,53 s   ← lineært, altså ramte den sit 848 tegn/s-loft
 *   100 tegn  → 0,59 s
 *
 * MÅLT EFTER (adaptiv rate, MAX_CHARS=28 stadig en hård kontrakt):
 *
 *   2000 tegn → 3,00 s
 *   5000 tegn → 5,91 s
 *   100 tegn  → 0,66 s
 *
 * Kurven er nu flad for store svar: indhentningskravet (`pending / 3 s`) er
 * den bindende grænse, ikke et fast tegn-loft. Forskellen er beskeden fordi
 * 28 tegn/33 ms = 848 tegn/s allerede lå over indhentningskravet — men den
 * er der, og den vokser med svarets længde.
 *
 * Kontrakten der IKKE må brydes (20/10-2026): højst 28 nye tegn pr. tick.
 * Et pacing-lag må accelerere, aldrig springe. Den vogtes i
 * `usePacedBlocks.test.tsx`; her vogtes KURVEN.
 */
import { act, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { usePacedBlocks } from './usePacedBlocks'
import type { ContentBlock } from './sseProtocol'

const TICK_MS = 33

function tekst(text: string): ContentBlock[] {
  return [{ type: 'text', text }]
}

/** Kør uret frem og returnér antal sekunder til hele target er vist. */
function sekunderTilFuldt(
  hook: { result: { current: ContentBlock[] } },
  target: string,
  maxTicks = 4000,
): number {
  for (let i = 1; i <= maxTicks; i++) {
    act(() => {
      vi.advanceTimersByTime(TICK_MS)
    })
    const vist = hook.result.current
      .filter((b): b is Extract<ContentBlock, { type: 'text' }> => b.type === 'text')
      .map((b) => b.text)
      .join('')
    if (vist === target) return i * (TICK_MS / 1000)
  }
  throw new Error(`nåede ikke hele svaret inden for ${maxTicks} ticks`)
}

describe('Code Mode-pacerens kurve', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })
  afterEach(() => {
    vi.useRealTimers()
  })

  it('et stort svar indhentes — ikke lineært med længden', () => {
    const target = 'a'.repeat(5000)
    const hook = renderHook(({ blocks, live }) => usePacedBlocks(blocks, live), {
      initialProps: { blocks: tekst(target), live: true },
    })
    const sekunder = sekunderTilFuldt(hook, target)
    // Målt 5,91 s. Grænsen ligger over målingen, ikke på den, så en
    // maskinvarie ikke fælder vagten — men et lineært tilbagefald (6,5 s+)
    // gør.
    expect(sekunder).toBeLessThan(6.2)
    expect(sekunder).toBeGreaterThan(2.5)
  })

  it('2000 tegn rammer indhentningsgulvet på 3 s', () => {
    const target = 'b'.repeat(2000)
    const hook = renderHook(({ blocks, live }) => usePacedBlocks(blocks, live), {
      initialProps: { blocks: tekst(target), live: true },
    })
    const sekunder = sekunderTilFuldt(hook, target)
    expect(sekunder).toBeLessThan(3.3)
    expect(sekunder).toBeGreaterThan(2.5)
  })

  it('et kort svar ruller stadig roligt — grundtempoet er urørt', () => {
    const target = 'c'.repeat(100)
    const hook = renderHook(({ blocks, live }) => usePacedBlocks(blocks, live), {
      initialProps: { blocks: tekst(target), live: true },
    })
    const sekunder = sekunderTilFuldt(hook, target)
    // Målt 0,66 s. Et kort svar må ikke blive et dump.
    expect(sekunder).toBeGreaterThan(0.4)
    expect(sekunder).toBeLessThan(1.2)
  })
})
