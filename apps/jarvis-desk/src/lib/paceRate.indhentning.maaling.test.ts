// @vitest-environment node
/**
 * MÅLING (23/11-2026). Bjørn: «Roligt er klart den mest flydende.. men det
 * teksten der løber stærkt over skærmen.»
 *
 * To klager der lyder som én, men har hver sin knap:
 *
 *   1. «løber stærkt over skærmen» — hvor mange TEGN DER LANDER PR. FRAME.
 *      Et spring på 28 tegn i ét 33 ms-tick er næsten en halv linje, og det
 *      læses som at teksten hopper, uanset hvor rolig raten er i tegn/s.
 *   2. «mest flydende» — hvor jævn raten er over svaret.
 *
 * ## Hvorfor T kan måles uden at ændre koden
 *
 * `pending` bruges præcis ÉT sted i `naesteRate`: `behov = pending / T`.
 * Regnestykket er lineært, så `behov = (pending·f) / T = pending / (T/f)`.
 * At sende `pending · f` ind er derfor matematisk identisk med at køre med
 * indhentningsvinduet `T/f` — ikke en efterligning. Skaleringen rammer kun
 * `behov`; grænsen `pending <= 0` og resten af funktionen er uafhængige af
 * `pending`.
 *
 * RETTELSE (skrevet efter første kørsel): jeg dividerede først med f, hvilket
 * giver `T·f` — altså et KORTERE vindue. Målingen viste det modsatte af
 * forventningen (T=6 blev hurtigere og hakkere), og det afslørede fejlen.
 *
 * Denne fil måler derfor den ægte `naesteRate` gennem den ægte tick-løkke
 * (samme som `paceRate.maaling.test.ts`) ved fire indhentningsvinduer.
 */
import { describe, expect, it } from 'vitest'
import { PACE_CATCH_UP_SECONDS, naesteRate, startPace } from './paceRate'

const TICK_MS = 33
const MIN_CHARS = 5
const MAX_CHARS = 28

/** Kildens ankomst: jævn strøm af `tegnPerTick` hvert tick i `ticks` ticks,
 *  derefter et dump af resten — det er den form et rigtigt svar har
 *  (synteser kommer jævnt, slutbeskeden lander i hug). */
const JAEVN_TEGN_PER_TICK = 4
const JAEVN_TICKS = 60
const DUMP_TEGN = 600

interface Udfald {
  varighedS: number
  tegnPrFrameSnit: number
  tegnPrFrameMaks: number
  framesOver10: number
  framesIAlt: number
  ujaevnhed: number
  snitRate: number
}

/** Kør den ÆGTE naesteRate gennem den ÆGTE step-beregning fra usePacedBlocks. */
function koer(tFaktor: number, dump: number = DUMP_TEGN): Udfald {
  let target = 0
  let vist = 0
  let rate = 48
  let tilstand = startPace()
  const rater: number[] = []
  const steps: number[] = []
  let frames = 0

  // Jævn fase
  for (let i = 0; i < JAEVN_TICKS; i++) {
    target += JAEVN_TEGN_PER_TICK
    const pending = target - vist
    // Skaleringen: pending/tFaktor giver behov = pending/(T*tFaktor).
    const svar = naesteRate({
      pending: pending * tFaktor,
      forrigeRate: rate,
      ankomst: (JAEVN_TEGN_PER_TICK * 1000) / TICK_MS,
      dt: TICK_MS / 1000,
      tilstand,
    })
    rate = svar.rate
    tilstand = svar.tilstand
    const prTick = (rate * TICK_MS) / 1000
    const delta = JAEVN_TEGN_PER_TICK
    const loft = Math.max(MAX_CHARS, delta)
    const step = Math.max(MIN_CHARS, Math.min(loft, Math.ceil(prTick)))
    const faktisk = Math.min(step, pending)
    vist += faktisk
    rater.push(rate)
    steps.push(faktisk)
    frames++
  }

  // Dump-fase: kilden er stoppet, resten lander på én gang.
  target += dump
  let guard = 0
  while (vist < target && guard++ < 3000) {
    const pending = target - vist
    const svar = naesteRate({
      pending: pending * tFaktor,
      forrigeRate: rate,
      ankomst: null,
      dt: TICK_MS / 1000,
      tilstand,
      spring: true,
    })
    rate = svar.rate
    tilstand = svar.tilstand
    const prTick = (rate * TICK_MS) / 1000
    const loft = MAX_CHARS
    const step = Math.max(MIN_CHARS, Math.min(loft, Math.ceil(prTick)))
    const faktisk = Math.min(step, pending)
    vist += faktisk
    rater.push(rate)
    steps.push(faktisk)
    frames++
  }

  const aktive = rater.slice(Math.floor(rater.length * 0.15))
  const minRate = Math.min(...aktive)
  const maksRate = Math.max(...aktive)
  return {
    varighedS: (frames * TICK_MS) / 1000,
    tegnPrFrameSnit: steps.reduce((a, b) => a + b, 0) / steps.length,
    tegnPrFrameMaks: Math.max(...steps),
    framesOver10: steps.filter((s) => s > 10).length,
    framesIAlt: frames,
    ujaevnhed: maksRate / Math.max(1, minRate),
    snitRate: rater.reduce((a, b) => a + b, 0) / rater.length,
  }
}

describe('pacerens indhentningsvindue — tegn pr. frame, ikke tegn/s', () => {
  it('maa ler fire vinduer og viser hvad der styrer «løber over skærmen»', () => {
    // FASTE vinduer, ikke relative til konstanten — ellers maaler filen
    // T=4,12,16,24 naar konstanten selv er 4, og sammenligningen bliver meningsloes.
    const vinduer: { navn: string; faktor: number }[] = [
      { navn: 'T=2', faktor: PACE_CATCH_UP_SECONDS / 2 },
      { navn: 'T=3', faktor: PACE_CATCH_UP_SECONDS / 3 },
      { navn: 'T=4', faktor: 1 },
      { navn: 'T=6', faktor: PACE_CATCH_UP_SECONDS / 6 },
    ]
    const linjer: string[] = []
    for (const v of vinduer) {
      const u = koer(v.faktor)
      linjer.push(
        `${v.navn.padEnd(14)} varighed ${u.varighedS.toFixed(2)}s  ` +
          `tegn/frame snit ${u.tegnPrFrameSnit.toFixed(1)} maks ${u.tegnPrFrameMaks}  ` +
          `frames>10: ${u.framesOver10}/${u.framesIAlt}  ` +
          `ujaevnhed ${u.ujaevnhed.toFixed(2)}x  snitrate ${Math.round(u.snitRate)}`,
      )
    }
    // eslint-disable-next-line no-console
    console.log('=== INDHENTNING: TEGN PR. FRAME ===\n' + linjer.join('\n'))

    // Kontrakt: målingen skal kunne SE forskel, ellers beviser den intet.
    const nu = koer(PACE_CATCH_UP_SECONDS / 2)
    const langsom = koer(1)
    expect(langsom.tegnPrFrameSnit).toBeLessThan(nu.tegnPrFrameSnit)
    expect(langsom.varighedS).toBeGreaterThan(nu.varighedS)
  })

  it('maa PRISEN paa et langt svar — den reelle risiko ved hoejere T', () => {
    const linjer: string[] = []
    for (const dump of [600, 1500, 3000]) {
      const dele: string[] = []
      for (const v of [
        { navn: 'T=2', faktor: PACE_CATCH_UP_SECONDS / 2 },
        { navn: 'T=3', faktor: PACE_CATCH_UP_SECONDS / 3 },
        { navn: 'T=4', faktor: 1 },
      ]) {
        const u = koer(v.faktor, dump)
        // Dump-fasens tid = samlet tid minus den jaevne fase (60 ticks)
        const dumpTid = u.varighedS - (JAEVN_TICKS * TICK_MS) / 1000
        dele.push(`${v.navn}: ${dumpTid.toFixed(2)}s`)
      }
      linjer.push(`dump ${String(dump).padStart(4)} tegn  ->  ` + dele.join('   '))
    }
    // eslint-disable-next-line no-console
    console.log('=== PRIS VED LAENGERE INDHENTNING ===\n' + linjer.join('\n'))

    // Prisen skal vaere maalt, ikke paastaaet: T=4 maa tage laengere end T=2
    const pris2 = koer(PACE_CATCH_UP_SECONDS / 2, 3000).varighedS
    const pris4 = koer(1, 3000).varighedS
    expect(pris4).toBeGreaterThan(pris2)
  })
})
