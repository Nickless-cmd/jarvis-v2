/**
 * KONTRAKTEN for koblingen mellem pacerens tempo og ord-animationens længde.
 *
 * Vagt, ikke en måling: den skal afvise at nogen går tilbage til et fast
 * fade-tal, for det er præcis fejlen der blev rettet 23/11-2026. Den ægte
 * Chromium-måling af HVOR MANGE ord der er accent samtidigt ligger i
 * `streamingTextTail.samtidige.maaling.test.ts`.
 */
import { describe, expect, it } from 'vitest'
import {
  FADE_GULV_MS,
  FADE_LOFT_MS,
  DELAY_LOFT_MS,
  delayMsForFade,
  fadeMsForRate,
} from './paceFade'
import { PACE_GULV, PACE_LOFT } from './paceRate'

describe('fadeMsForRate', () => {
  it('giver en KORTERE fade naar paceren korer hurtigere', () => {
    // Kernen i koblingen. Med et fast tal ville alle fire vaere ens.
    const rolig = fadeMsForRate(PACE_GULV)
    const mellem = fadeMsForRate(200)
    const hurtig = fadeMsForRate(600)
    expect(mellem).toBeLessThan(rolig)
    expect(hurtig).toBeLessThanOrEqual(mellem)
  })

  it('rammer loftet ved grundtempoet, saa den rolige kurve er uaendret', () => {
    // 48 tegn/s og 6 tegn pr. ord = 125 ms mellem ord. Det er under loftet,
    // saa den rolige ende faar netop den fade Bjorn godkendte 23/11.
    expect(fadeMsForRate(PACE_GULV)).toBeCloseTo(125, 0)
    expect(fadeMsForRate(PACE_GULV)).toBeLessThanOrEqual(FADE_LOFT_MS)
  })

  it('falder aldrig under gulvet, uanset hvor hurtigt kilden lober', () => {
    // Uden gulvet ville 4000 tegn/s give 1,5 ms = 0 frames = et hop, og et
    // hop er den fejl vi startede med.
    expect(fadeMsForRate(PACE_LOFT)).toBe(FADE_GULV_MS)
    expect(fadeMsForRate(100000)).toBe(FADE_GULV_MS)
  })

  it('giver loftet naar intet er maalt endnu', () => {
    // Foerste frame: rate 0 betyder «intet maalt», ikke «kilden staar stille».
    // Loftet er det sikre valg — en for kort fade ville hakke i starten.
    expect(fadeMsForRate(0)).toBe(FADE_LOFT_MS)
    expect(fadeMsForRate(-5)).toBe(FADE_LOFT_MS)
    expect(fadeMsForRate(Number.NaN)).toBe(FADE_LOFT_MS)
  })

  it('er monoton: hojere rate giver aldrig laengere fade', () => {
    let forrige = Infinity
    for (const rate of [10, 48, 60, 100, 200, 400, 800, 1600, 4000]) {
      const fade = fadeMsForRate(rate)
      expect(fade).toBeLessThanOrEqual(forrige)
      forrige = fade
    }
  })
})

describe('delayMsForFade', () => {
  it('ska lerer med faden, saa glidningen ikke bliver spist', () => {
    // Fast delay 40 ms paa en fade paa 70 ms ville efterlade 30 ms til selve
    // glidningen — og det er et hop, ikke en glidning.
    const kort = delayMsForFade(FADE_GULV_MS)
    const lang = delayMsForFade(FADE_LOFT_MS)
    expect(kort).toBeLessThan(lang)
    expect(kort).toBeGreaterThan(0)
    // Glidningen skal vaere den stoerste del af forloebet.
    expect(FADE_GULV_MS - kort).toBeGreaterThan(kort)
  })

  it('foelger faden gennem HELE kurven, ikke kun i dens to ender', () => {
    // MÅLT 24/11-2026: testen ovenfor er grøn baade med delay-loft 40 og 60,
    // fordi den kun maaler fadens to yderpunkter (70 og 220). Maetningen sker
    // imellem dem, og et loft der maetter giver et PLATEAU — som stadig er
    // ikke-faldende, saa en monotonitets-vagt fanger den ikke.
    //
    // Det der faktisk skal maales er hvor stor en del af kurven der FOELGER
    // faden. Maalt trin for trin (70→220 ms i skridt paa 5):
    //
    //   loft 40 → maetter ved fade 125 → 11 stigende, 19 flade skridt
    //   loft 60 → maetter ved fade 185 → 23 stigende,  7 flade skridt
    //
    // Vagten kraever at delayet foelger faden gennem mindst 2/3 af kurven.
    // Det fanger ethvert loft der maetter inde i det interval faden arbejder i.
    let stigende = 0
    let skridt = 0
    for (let fade = FADE_GULV_MS; fade < FADE_LOFT_MS; fade += 5) {
      const a = delayMsForFade(fade)
      const b = delayMsForFade(fade + 5)
      expect(b).toBeGreaterThanOrEqual(a)
      if (b > a) stigende += 1
      skridt += 1
    }
    expect(stigende / skridt).toBeGreaterThanOrEqual(2 / 3)
  })

  it('gaar aldrig over loftet', () => {
    expect(delayMsForFade(FADE_LOFT_MS)).toBeLessThanOrEqual(DELAY_LOFT_MS)
    expect(delayMsForFade(10000)).toBeLessThanOrEqual(DELAY_LOFT_MS)
  })

  it('falder tilbage til loftet paa en ugyldig fade', () => {
    expect(delayMsForFade(0)).toBe(DELAY_LOFT_MS)
    expect(delayMsForFade(Number.NaN)).toBe(DELAY_LOFT_MS)
  })
})
