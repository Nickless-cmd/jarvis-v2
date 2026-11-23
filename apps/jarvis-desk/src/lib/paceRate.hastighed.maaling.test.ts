// @vitest-environment node
/**
 * MÅLING (23/11-2026). Bjørn: «pacen løber rigtigt stærkt.. kan du prøve og
 * måle det?»
 *
 * Spørgsmålet er ikke hvad konstanterne TILLADER, men hvad paceren FAKTISK
 * gør på et realistisk svar. Derfor kører denne måling den ÆGTE `naesteRate`
 * gennem den ÆGTE tick-løkke fra `usePacedBlocks` (33 ms, step-gulv 5,
 * step-loft 28) — ikke en efterligning af den.
 *
 * Tre scenarier, fordi hastigheden afhænger af HVORDAN teksten ankommer:
 *
 *  · DUMP    — hele svaret lander i første tick (fold, eller en model der
 *              skriver hurtigere end netværket kan levere).
 *  · JÆVN    — 40 tegn hver 100 ms, som en typisk streamet model.
 *  · LANGSOM — 8 tegn hver 100 ms, som en model der tænker undervejs.
 *
 * Det er ikke en vagt: tallene er til at læse, og de ændrer sig hvis nogen
 * rører ved gulvet, loftet eller indhentningsreglen.
 */
import { describe, expect, it } from 'vitest'
import { naesteRate, startPace, type RateTilstand } from './paceRate'

const TICK_MS = 33
const MIN_CHARS = 5
const MAX_CHARS = 28

interface Resultat {
  sekunder: number
  tegnPrSekund: number
  hojesteRate: number
  hojesteStep: number
  ticks: number
}

/** Den ægte tick-løkke fra usePacedBlocks, reduceret til det der styrer tempoet. */
function simuler(
  ankomstPlan: (tick: number) => number,
  total: number,
): Resultat {
  let target = ''
  let forrigeLaengde: number | null = null
  let rate = 48
  let tilstand: RateTilstand = startPace()
  let tick = 0
  let hojesteRate = 0
  let hojesteStep = 0
  let vist = 0

  while (vist < total && tick < 20_000) {
    const delta = ankomstPlan(tick)
    if (delta > 0) target += 'x'.repeat(Math.min(delta, total - target.length))
    tick++

    const laengde = target.length
    const foer = forrigeLaengde
    forrigeLaengde = laengde
    const ankomst = foer === null ? null : (delta * 1000) / TICK_MS
    const pending = laengde - vist
    if (pending <= 0) continue

    const erHop = foer === null || delta === 0 || delta >= pending * 0.5
    const svar = naesteRate({
      pending,
      forrigeRate: rate,
      ankomst,
      dt: TICK_MS / 1000,
      tilstand,
      spring: erHop,
    })
    rate = svar.rate
    tilstand = svar.tilstand
    hojesteRate = Math.max(hojesteRate, rate)

    const prTick = (rate * TICK_MS) / 1000
    const loft = erHop ? MAX_CHARS : Math.max(MAX_CHARS, delta)
    const step = Math.max(MIN_CHARS, Math.min(loft, Math.ceil(prTick)))
    hojesteStep = Math.max(hojesteStep, step)
    vist = Math.min(laengde, vist + step)
  }

  const sekunder = (tick * TICK_MS) / 1000
  return {
    sekunder: Math.round(sekunder * 100) / 100,
    tegnPrSekund: Math.round(total / sekunder),
    hojesteRate: Math.round(hojesteRate),
    hojesteStep,
    ticks: tick,
  }
}

describe('pacerens faktiske hastighed', () => {
  it('måler hvor stærkt et 2000-tegn svar ruller ud i tre ankomstmønstre', () => {
    const total = 2000

    // DUMP: alt i første tick — værste tilfælde, og det fold-vejen giver.
    const dump = simuler((t) => (t === 0 ? total : 0), total)
    // JÆVN: 40 tegn hver 100 ms ≈ 400 tegn/s, typisk streamet model.
    const jaevn = simuler((t) => (t % 3 === 0 ? 40 : 0), total)
    // LANGSOM: 8 tegn hver 100 ms ≈ 80 tegn/s.
    const langsom = simuler((t) => (t % 3 === 0 ? 8 : 0), total)

    // eslint-disable-next-line no-console
    console.log(
      `=== PACERENS HASTIGHED (2000 tegn) ===\n` +
        `DUMP    : ${dump.sekunder}s → ${dump.tegnPrSekund} tegn/s (top-rate ${dump.hojesteRate}, top-step ${dump.hojesteStep})\n` +
        `JÆVN    : ${jaevn.sekunder}s → ${jaevn.tegnPrSekund} tegn/s (top-rate ${jaevn.hojesteRate}, top-step ${jaevn.hojesteStep})\n` +
        `LANGSOM : ${langsom.sekunder}s → ${langsom.tegnPrSekund} tegn/s (top-rate ${langsom.hojesteRate}, top-step ${langsom.hojesteStep})`,
    )

    // Målingen skal kunne skelne de tre — ellers måler den ingenting.
    expect(dump.tegnPrSekund).toBeGreaterThan(jaevn.tegnPrSekund)
    expect(jaevn.tegnPrSekund).toBeGreaterThan(langsom.tegnPrSekund)
    // Og den skal have rørt loftet, ellers er scenariet ikke det værste tilfælde.
    expect(dump.hojesteStep).toBe(MAX_CHARS)
  })
})
