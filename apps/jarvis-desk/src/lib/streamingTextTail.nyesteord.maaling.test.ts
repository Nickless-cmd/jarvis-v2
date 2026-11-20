// @vitest-environment node
/**
 * Det NYESTE ord skal farves i det øjeblik det lander — målt i Chromium.
 *
 * Bjørn 20/11-2026: «Det sidste ord bliver aldrig blåt, kun de tre sidste får
 * farve». De to halvdele er forskellige: «kun de tre sidste» er
 * `STREAMING_TAIL_WORD_LIMIT` og er tilsigtet. Men det ord der LIGE er landet
 * bærer aldrig halen, og det er fejlen.
 *
 * Årsagen er `afsluttetGraense`: den regner et ord for uafsluttet indtil der
 * kommer whitespace efter det. Under rigtig SSE-streaming kommer mellemrummet
 * ofte sammen med NÆSTE token, så det nyeste ord på skærmen er systematisk
 * «uafsluttet» — og `completedParts.slice(0, -1)` smider det ud af halen.
 * Resultatet er at hvert ord først farves når det næste ankommer.
 *
 * Målingen streamer uden efterfølgende mellemrum, præcis som token-strømmen
 * gør. Den tæller BÅDE ordene i teksten og de pakkede spans: er de to tal
 * forskellige, ligger det nyeste ord uden for halen — og det er fejlen.
 *
 * `jarvis-stream-word` er et hast-tag; `StreamingWord` renderer et `<span>`,
 * så tag-navnet findes aldrig i DOM'en. Derfor måles der på klasserne.
 */
import { describe, expect, it } from 'vitest'
import { aabnBaenk } from './streamingTextTail.baenk'

const SPRING = 70

interface Maaling {
  tekst: string
  ordIAlt: number
  antalSpans: number
  haleOrd: string[]
  sidsteOrd: string
  sidsteHarHale: boolean
}

describe('det nyeste ord under streaming', () => {
  it('farves i det øjeblik det lander, ikke først når det næste kommer', async () => {
    const baenk = await aabnBaenk({ theme: 'dark' })
    try {
      // Teksten vokser ord for ord UDEN mellemrum efter det nyeste — som SSE.
      const skridt = Array.from({ length: 6 }, (_, i) =>
        Array.from({ length: i + 1 }, (_, k) => `ord${k + 1}`).join(' '),
      )

      const maalt: Maaling[] = []
      for (const tekst of skridt) {
        await baenk.page.evaluate(
          (t) => (window as unknown as { __saetTekst: (s: string) => void }).__saetTekst(t),
          tekst,
        )
        await baenk.page.waitForTimeout(SPRING)
        const fund = await baenk.page.evaluate(() => {
          const spans = Array.from(
            document.querySelectorAll('#krop span.streaming-word-tail, #krop span.streaming-word-settled'),
          ) as HTMLElement[]
          return {
            antalSpans: spans.length,
            haleOrd: spans
              .filter((s) => s.className.includes('streaming-word-tail'))
              .map((s) => (s.textContent ?? '').trim()),
            sidsteOrd: (spans[spans.length - 1]?.textContent ?? '').trim(),
            sidsteHarHale: (spans[spans.length - 1]?.className ?? '').includes('streaming-word-tail'),
          }
        })
        maalt.push({
          tekst,
          ordIAlt: tekst.split(' ').filter(Boolean).length,
          ...fund,
        })
      }

      console.log('[NYESTE-ORD]', JSON.stringify(maalt))

      expect(baenk.fejl).toEqual([])
      // Hvert ord i teksten skal være pakket — ellers er det nyeste ord rå tekst
      // uden animation, og det er præcis det Bjørn ser som «bliver aldrig blåt».
      const upakkede = maalt.filter((m) => m.antalSpans !== m.ordIAlt)
      expect(upakkede.map((m) => ({ tekst: m.tekst, ord: m.ordIAlt, spans: m.antalSpans }))).toEqual([])
      // Og det sidste ord skal bære halen, ikke stå tilbage som `settled`.
      const udenHale = maalt.filter((m) => !m.sidsteHarHale)
      expect(udenHale.map((m) => m.tekst)).toEqual([])
    } finally {
      await baenk.luk()
    }
  }, 60_000)
})
