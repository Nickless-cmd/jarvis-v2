// @vitest-environment node
/**
 * E2E-MÅLING (23/11-2026): arver `--pace-fade-ms` faktisk ned til ordet?
 *
 * Koblingen mellem pacerens tempo og ord-animationens længde hviler på ÉN
 * antagelse der ikke må gættes: at `var(--pace-fade-ms, …)` — sat som inline
 * style på `<jarvis-stream-word>`, et CUSTOM ELEMENT — arver fra containeren
 * og re-timer den kørende CSS-animation.
 *
 * Derfor måler denne fil den FAKTISKE varighed via `getAnimations()`, ikke
 * den stil-streng vi selv skrev. Skriver vi `var(--pace-fade-ms)` og
 * browseren ikke arver den, ville stil-strengen stadig se rigtig ud mens
 * animationen kørte uændret — samme fælde som en vagt der matcher alt.
 *
 * Gates som de øvrige målinger (RUN_BROWSER_LAYOUT_MEASUREMENT=1).
 */
import { describe, expect, it } from 'vitest'
import { aabnBaenk, ordTekst } from './streamingTextTail.baenk'
import { fadeMsForRate, delayMsForFade } from './paceFade'
import { PACE_GULV } from './paceRate'

interface Maalt {
  farveNavn: string | null
  farveMs: number | null
  delayMs: number | null
  antalAnimationer: number
}

/** Tilføjer et nyt ord med en given fade-variabel sat på roden, og måler det
 *  NYESTE hal-ords faktiske animationstider. */
async function maalVedFade(
  page: import('playwright').Page,
  fadeMs: number | null,
  tekst: string,
): Promise<Maalt | null> {
  const delayMs = fadeMs === null ? null : Math.round(delayMsForFade(fadeMs))
  return page.evaluate(
    async ({ fade, delay, t }) => {
      const root = document.getElementById('root')!
      if (fade === null) {
        root.style.removeProperty('--pace-fade-ms')
        root.style.removeProperty('--pace-delay-ms')
      } else {
        // BEGGE variabler, praecis som `MessageRow`s frame-loekke saetter dem.
        // Saettes kun fade, falder delay'en tilbage til Snappys 40 ms, og saa
        // maaler testen en tilstand produktionen aldrig indtager (maalt:
        // «expected 40 to be 23»).
        root.style.setProperty('--pace-fade-ms', `${fade}ms`)
        root.style.setProperty('--pace-delay-ms', `${delay}ms`)
      }
      ;(window as any).__saetTekst(t)
      // To frames: én til at montere ordet, én til at animationen er sat i gang.
      await new Promise((r) => requestAnimationFrame(r))
      await new Promise((r) => requestAnimationFrame(r))
      const alle = [...document.querySelectorAll('.streaming-word-tail')] as HTMLElement[]
      // Det FOERSTE hal-ord, ikke det sidste: `order` er indeks i halen, og
      // CSS'en laegger `order * part-offset` oveni delay'en. Det sidste ord
      // har order 2 og giver derfor 40 + 2x30 = 100 ms — maalte jeg det,
      // sammenlignede jeg min formel med en anden stoerrelse (maalt: fejlede
      // med «expected 100 to be 40»).
      const ord = alle[0]
      if (!ord) return null
      const anims = ord.getAnimations() as (Animation & { animationName?: string })[]
      const farve = anims.find((a) => a.animationName === 'streaming-word-color')
      const timing = farve?.effect?.getTiming()
      const d = timing?.duration
      const del = timing?.delay
      return {
        farveNavn: farve?.animationName ?? null,
        farveMs: typeof d === 'number' ? Math.round(d) : null,
        delayMs: typeof del === 'number' ? Math.round(del) : null,
        antalAnimationer: anims.length,
      }
    },
    { fade: fadeMs, delay: delayMs, t: tekst },
  )
}

describe.skipIf(process.env.RUN_BROWSER_LAYOUT_MEASUREMENT !== '1')('ord-animationen arver pacerens tempo', () => {
  it('forkorter den FAKTISKE animation naar --pace-fade-ms saettes', async () => {
    const b = await aabnBaenk({ theme: 'dark' })
    try {
      const { page } = b
      // Grundtilstand: ingen variabel → variantens eget tal (fallback).
      const uden = await maalVedFade(page, null, ordTekst(4))
      // Rolig pacer: 48 tegn/s.
      const rolig = await maalVedFade(page, fadeMsForRate(PACE_GULV), ordTekst(6))
      // Hurtig pacer: 600 tegn/s.
      const hurtig = await maalVedFade(page, fadeMsForRate(600), ordTekst(9))

      console.info('[RATEKOBLING]', {
        uden: uden?.farveMs,
        rolig: rolig?.farveMs,
        hurtig: hurtig?.farveMs,
        forventetRolig: fadeMsForRate(PACE_GULV),
        forventetHurtig: fadeMsForRate(600),
      })

      expect(b.fejl).toEqual([])
      // Animationen findes overhovedet — ellers måler vi ingenting.
      expect(uden?.farveNavn).toBe('streaming-word-color')

      // 1. Uden variablen: fallback'en er Snappys 120 ms.
      expect(uden?.farveMs).toBe(120)

      // 2. Med variablen: den FAKTISKE varighed følger den, afrundet til ms.
      //    Dette er beviset for at arven virker gennem custom-elementet.
      expect(rolig?.farveMs).toBe(Math.round(fadeMsForRate(PACE_GULV)))
      expect(hurtig?.farveMs).toBe(Math.round(fadeMsForRate(600)))

      // 3. Retningen: hurtigere pacer → kortere fade. Kernen i koblingen.
      expect(hurtig!.farveMs!).toBeLessThan(rolig!.farveMs!)
    } finally {
      await b.luk()
    }
  }, 120_000)

  it('forkorter ogsaa ankomstforskydningen, saa glidningen ikke spises', async () => {
    const b = await aabnBaenk({ theme: 'dark' })
    try {
      const { page } = b
      const rolig = await maalVedFade(page, fadeMsForRate(PACE_GULV), ordTekst(3))
      const hurtig = await maalVedFade(page, fadeMsForRate(600), ordTekst(6))

      expect(b.fejl).toEqual([])
      // Forskydningen er sat paa det FOERSTE ord (order 0), saa den er ren
      // `--pace-delay-ms` uden part-offset.
      expect(rolig?.delayMs).toBe(Math.round(delayMsForFade(fadeMsForRate(PACE_GULV))))
      expect(hurtig?.delayMs).toBe(Math.round(delayMsForFade(fadeMsForRate(600))))

      // Glidningen skal stadig vaere den stoerste del af forloebet — ellers
      // er vi tilbage ved et hop.
      expect(hurtig!.farveMs! - hurtig!.delayMs!).toBeGreaterThan(hurtig!.delayMs!)
    } finally {
      await b.luk()
    }
  }, 120_000)
})
