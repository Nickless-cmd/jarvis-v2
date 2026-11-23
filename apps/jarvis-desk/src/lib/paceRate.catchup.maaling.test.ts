// @vitest-environment node
/**
 * MÅLING (23/11-2026). Bjørn: «Catchup ødelægger det fordi den først falder til
 * ro i enden af slut beskeden.»
 *
 * ## Den matematiske årsag
 *
 * Den ægte `naesteRate` sætter `rate = max(kilde, pending / T)`. Det giver
 *
 *     d(pending)/dt = kilde − pending/T
 *
 * hvis ligevægt er `pending = kilde·T`. Mens kilden leverer, PARKERER efterslæbet
 * altså på `kilde·T` (400 tegn/s · 3 s = 1200 tegn) og bliver aldrig indhentet.
 * Raten står fast på indhentningstempo gennem hele beskeden og falder først når
 * kilden stopper — præcis «falder til ro i enden».
 *
 * ## Formen der måles som alternativ
 *
 * `rate = kilde + pending/T` (tillæg i stedet for erstatning) giver
 *
 *     d(pending)/dt = −pending/T
 *
 * så efterslæbet halveres hver `T·ln2` sekund og forsvinder. Raten decelererer
 * gradvist fra `kilde + pending/T` ned mod `kilde`.
 *
 * Målet er raten ved 25/50/75/90 % af udrulningen: en kurve der FALDER er roen
 * der kommer undervejs; en kurve der står stille er roen der først kommer til
 * sidst.
 */
import { describe, expect, it } from 'vitest'
import {
  naesteRate,
  startPace,
  PACE_GULV,
  PACE_LOFT,
  PACE_KILDE_EMA,
  PACE_KILDE_GLEMSEL_S,
  PACE_GLIDNING,
  PACE_DECAY_HALFLIFE_S,
  type RateTilstand,
} from './paceRate'

const TICK_MS = 33
const MIN_CHARS = 5
const MAX_CHARS = 28

interface Kurve {
  ved: number[]
  andelOverKilde: number
  varighedS: number
  maksTegnPrFrame: number
  ujaevnhed: number
  /** Efterslæb da kilden stoppede — 0 = indhentet. */
  slutPending: number
}

interface RateInput {
  pending: number
  forrigeRate: number
  ankomst: number | null
  dt: number
  tilstand: RateTilstand
  spring?: boolean
}

type RateFn = (i: RateInput) => { rate: number; tilstand: RateTilstand }

/** Tillægs-formen: rate = kilde + pending/T. Prototype, ikke den ægte funktion. */
function lagTillæg(T: number): RateFn {
  return ({ pending, forrigeRate, ankomst, dt, tilstand, spring = false }) => {
    if (pending <= 0) return { rate: PACE_GULV, tilstand: startPace() }
    let { kilde } = tilstand
    const maalt = ankomst !== null && Number.isFinite(ankomst) && ankomst > 0
    if (maalt) {
      const a = ankomst as number
      kilde = kilde <= 0 ? a : PACE_KILDE_EMA * a + (1 - PACE_KILDE_EMA) * kilde
    } else {
      const sek = Math.max(0, Math.min(0.5, dt ?? 1 / 60))
      kilde = PACE_GULV + (kilde - PACE_GULV) * Math.pow(0.5, sek / PACE_KILDE_GLEMSEL_S)
    }
    const indh = pending / T
    const maalRate = Math.min(PACE_LOFT, Math.max(PACE_GULV, kilde + indh))
    let rate = forrigeRate
    if (spring) {
      rate = maalRate
    } else if (maalt) {
      rate = Math.max(rate, Math.min(ankomst as number, PACE_LOFT))
    } else if (rate > maalRate) {
      const sek = Math.max(0, Math.min(0.5, dt ?? 1 / 60))
      rate = maalRate + (rate - maalRate) * Math.pow(0.5, sek / PACE_DECAY_HALFLIFE_S)
    }
    rate += (maalRate - rate) * PACE_GLIDNING
    return { rate: Math.min(PACE_LOFT, Math.max(PACE_GULV, rate)), tilstand: { kilde, indh } }
  }
}

const aegte: RateFn = (i) => naesteRate(i)

/**
 * Bjørns scenarie: jævn strøm (syntese), så et FOLD, så en jævn slutbesked på
 * `slutRate` tegn/s der leverer `slutTegn` tegn i alt og derefter stopper.
 */
function koer(fn: RateFn, foldTegn: number, slutTegn: number, slutRate: number): Kurve {
  const tickS = TICK_MS / 1000
  const tegnPrTick = Math.max(1, Math.round((slutRate * TICK_MS) / 1000))

  let target = 0
  let vist = 0
  let rate = 48
  let tilstand = startPace()
  const rater: number[] = []
  const steps: number[] = []
  let overKilde = 0
  let maaltFrames = 0

  const skridt = (delta: number, pending: number) => {
    const step = Math.max(
      MIN_CHARS,
      Math.min(Math.max(MAX_CHARS, delta), Math.ceil((rate * TICK_MS) / 1000)),
    )
    steps.push(step)
    vist += Math.min(step, pending)
    rater.push(rate)
  }

  // Fase 1: jævn syntese-agtig strøm
  for (let i = 0; i < 40; i++) {
    target += 4
    const pending = target - vist
    const ankomst = (4 * 1000) / TICK_MS
    const svar = fn({ pending, forrigeRate: rate, ankomst, dt: tickS, tilstand })
    rate = svar.rate
    tilstand = svar.tilstand
    maaltFrames++
    if (rate > ankomst) overKilde++
    skridt(4, pending)
  }

  // Fase 2: FOLDET — hele slutbeskeden lander i ét hug
  target += foldTegn

  // Fase 3: kilden leverer slutbeskeden jævnt, `slutTegn` i alt, så stop
  let tick = 0
  let leveret = 0
  let slutPending = 0
  while (tick < 3000) {
    const pending = target - vist
    if (pending <= 0) break
    if (tick > 0 && leveret < slutTegn) {
      const giv = Math.min(tegnPrTick, slutTegn - leveret)
      target += giv
      leveret += giv
    }
    const ankomst = tick === 0 ? null : (tegnPrTick * 1000) / TICK_MS
    const svar = fn({
      pending,
      forrigeRate: rate,
      ankomst,
      dt: tickS,
      tilstand,
      spring: tick === 0,
    })
    rate = svar.rate
    tilstand = svar.tilstand
    if (ankomst !== null) {
      maaltFrames++
      if (rate > ankomst) overKilde++
    }
    skridt(tick === 0 ? foldTegn : tegnPrTick, pending)
    slutPending = Math.max(0, target - vist)
    tick++
  }

  const aktive = rater.filter((r) => r > 0)
  const ved = [0.25, 0.5, 0.75, 0.9].map((a) => aktive[Math.floor(aktive.length * a)] ?? -1)
  const maksRate = Math.max(...aktive)
  const minRate = Math.min(...aktive.slice(Math.floor(aktive.length * 0.15)))
  return {
    ved,
    andelOverKilde: overKilde / Math.max(1, maaltFrames),
    varighedS: (steps.length * TICK_MS) / 1000,
    maksTegnPrFrame: Math.max(...steps),
    ujaevnhed: Number((maksRate / Math.max(1, minRate)).toFixed(2)),
    slutPending,
  }
}

const vis = (navn: string, k: Kurve) =>
  console.log(
    `${navn.padEnd(12)} → 25/50/75/90%: ${k.ved.map((v) => String(Math.round(v)).padStart(4)).join(' / ')}` +
      ` | over kilde ${(k.andelOverKilde * 100).toFixed(0).padStart(3)}%` +
      ` | maks ${String(k.maksTegnPrFrame).padStart(2)} tegn/frame` +
      ` | ${k.varighedS.toFixed(2)}s | uj ${String(k.ujaevnhed).padStart(4)}x` +
      ` | slut-efterslæb ${k.slutPending}`,
  )

describe('catch-up: falder roen først i enden?', () => {
  it('måler ratekurven gennem fold + jævn slutbesked', () => {
    for (const fold of [600, 1200, 2000]) {
      console.log(`=== fold ${fold} tegn, slutbesked 400 tegn/s, 1200 tegn ===`)
      vis('NU (erstat)', koer(aegte, fold, 1200, 400))
      for (const T of [3, 4, 6, 8]) {
        vis(`tillæg T=${T}`, koer(lagTillæg(T), fold, 1200, 400))
      }
    }
    expect(true).toBe(true)
  })
})
