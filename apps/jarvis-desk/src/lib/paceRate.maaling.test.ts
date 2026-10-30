/**
 * MÅLING, ikke en vagt: hvor stærkt løber pacen — og hvad driver hastigheden?
 *
 * Bjørn 30/10-2026: «Pacen løber for stærkt». Det er den MODSATTE klage af
 * 29/10 («svaret streames færdigt inde i hoved før det paces»), hvor
 * `Math.min(180, pending/3)` blev fjernet fordi pacen aldrig indhentede.
 *
 * Spørgsmålet er om fjernelsen tog for meget med. Der er to kræfter i
 * `naesteRate`:
 *
 *   1. `pending / 3` — indhentningskravet. Bindende når efterslæbet er stort.
 *   2. EMA(0.1) over den målte ANKOMST.
 *
 * Kraft 2 var den skyldige. MÅLT FØR RETTELSEN: ankomsten blev målt pr.
 * frame, så en SSE-chunk på 100 tegn i én 16,7 ms-frame blev 6000 tegn/s.
 * EMA'en løftede raten til 643 tegn/s — 13,4x grundtempoet — og den faldt
 * ALDRIG tilbage (frame 1, 2 og 5 gav alle 643). Burst-mønster og jævnt
 * mønster med samme gennemsnit gav 4000 mod 600.
 *
 * Rettelsen har to dele, og denne fil måler begge:
 *   A. ankomsten måles over `PACE_ANKOMST_VINDUE_S` i stedet for pr. frame
 *   B. raten glider tilbage mod grundtempoet når intet nyt ankommer
 */
import { describe, expect, it } from 'vitest'
import {
  naesteRate,
  PACE_GULV,
  PACE_CATCH_UP_SECONDS,
  PACE_LOFT,
  PACE_ANKOMST_VINDUE_S,
} from './paceRate'

const FPS = 60
const FRAME_S = 1 / FPS
/** Samme loft pr. frame som hooket bruger. */
const MAX_FRAME_DELTA_S = 0.1

interface Resultat {
  sekunder: number
  maksRate: number
  /** Raten ved udrulningens sidste frame — er den faldet tilbage? */
  slutRate: number
  frames: number
}

/**
 * Simulér hookets tick-løkke med den ægte `naesteRate` — inklusive
 * ankomst-vinduet og `dt`, så målingen følger produktionskoden.
 *
 * `ankomstVed(frame)` returnerer hvor mange kodepunkter der ankom i netop
 * den frame — eller null hvis intet nyt landede.
 */
function simulér(total: number, ankomstVed: (frame: number) => number | null): Resultat {
  let shown = 0
  let rate = PACE_GULV
  let maal = 0
  // Vinduets start — hooket holder `a.maal`/`a.tid` på samme måde, så
  // `vokset` er ALT der er ankommet siden vinduet startede, ikke kun denne
  // frame. Det er hele pointen med rettelsen.
  let vindueStartMaal = 0
  let vindueStartTid = 0
  let maksRate = 0
  let frame = 0
  let kredit = 0

  while (shown < total && frame < 100_000) {
    frame += 1
    const nu = frame * FRAME_S
    const vokset = ankomstVed(frame)
    if (vokset !== null) maal += vokset
    const pending = Math.max(0, maal - shown)
    if (pending <= 0 && maal < total) continue

    const voksetIVindue = maal - vindueStartMaal
    const dtAnkomst = vindueStartTid > 0 ? nu - vindueStartTid : 0
    const vindueUde = dtAnkomst >= PACE_ANKOMST_VINDUE_S
    const ankomst = voksetIVindue > 0 && vindueUde ? voksetIVindue / dtAnkomst : null
    if (vindueUde || vindueStartTid === 0) {
      vindueStartMaal = maal
      vindueStartTid = nu
    }

    rate = naesteRate({ pending, forrigeRate: rate, ankomst, dt: FRAME_S })
    maksRate = Math.max(maksRate, rate)

    const maksPrFrame = Math.max(6, Math.ceil(rate * MAX_FRAME_DELTA_S))
    kredit = Math.min(maksPrFrame, kredit + rate * FRAME_S)
    const step = Math.min(maksPrFrame, Math.floor(kredit))
    if (step > 0) {
      kredit -= step
      shown = Math.min(maal, shown + step)
    }
    if (shown >= total) break
  }

  return {
    sekunder: frame / FPS,
    maksRate: Math.round(maksRate),
    slutRate: Math.round(rate),
    frames: frame,
  }
}

/** Jævn ankomst: `n` tegn hver frame. Modellerer en server der drypper. */
const jaevn = (n: number) => () => n

/** Burst: `stor` tegn hver `hver` frame, intet ind imellem.
 *  Det er hvad en SSE-relæ typisk gør — den samler op og sender i bidder. */
const burst = (stor: number, hver: number) => (frame: number) =>
  frame % hver === 0 ? stor : null

/** Alt på én gang — svaret var allerede færdigt da komponenten mounted. */
const altPaaEnGang = (total: number) => (frame: number) => (frame === 1 ? total : null)

describe('PACE-MÅLING — hvor stærkt løber pacen?', () => {
  it('A: jævn ankomst 10 tegn/frame (600 tegn/s)', () => {
    const r = simulér(2000, jaevn(10))
    console.log('A jævn 10/frame:', r)
    expect(r.maksRate).toBeLessThanOrEqual(PACE_LOFT)
  })

  it('B: burst vs jævn ankomst — SAMME gennemsnit, lille svar', () => {
    // MÅLT VED 300 TEGN, ikke 2000. Ved 2000 er `pending/2` = 1000 så stor at
    // den overdøver alt hvad EMA'en gør, og testen blev grøn med og uden
    // vindue — den målte intet. Ved 300 tegn (pending/2 = 150) er det
    // ANKOMSTMÅLINGEN der bestemmer, og forskellen er synlig.
    const a = simulér(300, jaevn(10))
    const r = simulér(300, burst(100, 10))
    console.log('B jævn 10/frame (600 tegn/s):', a)
    console.log('B burst 100/10. frame (gns. 600 tegn/s):', r)
    console.log('  forskel i maksRate:', r.maksRate - a.maksRate)
    // Kernen i rettelsen: samme gennemsnit skal give nogenlunde samme rate.
    // MÅLT: med vindue er forskellen −20; uden er den +928. Grænsen på ×1,5
    // er sat mellem de to, så den fanger et tilbagefald til per-frame-måling
    // uden at være følsom over for simulerings-støj.
    expect(r.maksRate).toBeLessThan(a.maksRate * 1.5)
  })

  it('C: alt på én gang — 2000 tegn i første frame', () => {
    const r = simulér(2000, altPaaEnGang(2000))
    console.log('C alt-i-én-frame:', r)
    // Her ER efterslæbet reelt 2000, så pending/3 = 667 tegn/s er korrekt —
    // og sikkerhedsloftet må ikke blive den bindende grænse.
    expect(r.maksRate).toBeLessThan(PACE_LOFT)
  })

  it('D: én burst på 100 tegn — falder raten tilbage?', () => {
    const rate1 = naesteRate({ pending: 100, forrigeRate: PACE_GULV, ankomst: 100 / 0.3, dt: FRAME_S })
    let rate = rate1
    for (let i = 0; i < 30; i += 1) {
      rate = naesteRate({ pending: Math.max(1, 90 - i), forrigeRate: rate, ankomst: null, dt: FRAME_S })
    }
    console.log('D én burst på 100 tegn (målt over 300 ms = 333 tegn/s):')
    console.log('  rate efter burst:', Math.round(rate1))
    console.log('  rate efter 30 frames uden nyt (0,5 s):', Math.round(rate))
    console.log('  grundtempo:', PACE_GULV)
    // FØR rettelsen stod den stille på 643 tegn/s i alle efterfølgende frames.
    expect(rate).toBeLessThan(rate1)
    expect(rate).toBeLessThan(PACE_GULV * 2)
  })

  it('E: sikkerhedsloftet holder stadig', () => {
    const absurd = naesteRate({ pending: 100_000, forrigeRate: PACE_GULV, ankomst: 50_000, dt: FRAME_S })
    console.log('E absurd target:', Math.round(absurd), '/ loft', PACE_LOFT)
    expect(absurd).toBeLessThanOrEqual(PACE_LOFT)
  })

  it('F: grundtempoet er urørt — 100 tegn ruller stadig roligt', () => {
    const r = simulér(100, altPaaEnGang(100))
    console.log('F 100 tegn i ét hug:', r)
    // Kontrakten fra 20/10: et kort svar må ikke blinke frem. Målt 2,05 s
    // med T=2 — derfor er 1,9 den nedre grænse, ikke 1,5.
    expect(r.sekunder).toBeGreaterThan(1.9)
  })

  it('G: 29/10-gevinsten holder — 2000 tegn indhentes, ikke 15 s', () => {
    const r = simulér(2000, altPaaEnGang(2000))
    console.log('G 2000 tegn i ét hug:', r, '— catch-up-krav:', Math.round(2000 / PACE_CATCH_UP_SECONDS))
    // Målt 7,22 s med T=2. Klagen 29/10 var 15,07 s — så loftet her er 9 s.
    expect(r.sekunder).toBeLessThan(9)
  })

  it('H: kurven — hvad koster et svar af hver længde?', () => {
    // `pending / T` er ASYMPTOTISK: p(t) = p0·exp(-t/T), så halen bliver
    // hængende. Ved p0=2000 når den først under 10 tegn efter ~3·ln(200).
    // Spørgsmålet er om det er et problem i praksis eller kun i teorien.
    for (const n of [100, 300, 500, 1000, 2000, 4000]) {
      const r = simulér(n, altPaaEnGang(n))
      console.log(
        `H ${String(n).padStart(4)} tegn → ${r.sekunder.toFixed(2)} s` +
        ` (maks ${r.maksRate} tegn/s, ${(n / r.sekunder).toFixed(0)} tegn/s i snit)`,
      )
    }
  })
})
