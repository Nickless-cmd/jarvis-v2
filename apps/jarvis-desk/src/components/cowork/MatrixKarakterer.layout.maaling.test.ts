// @vitest-environment node
/**
 * Karakter-rækkens layout i rigtig Chromium.
 *
 * ## Hvorfor den findes
 *
 * `KarakterFigur.maaling.test.ts` tegner SVG'en isoleret på et canvas og
 * beviser at figuren har et synligt kropsareal. Den siger INTET om hvor
 * figuren står henne i den faktiske række — og det var netop der fejlen var:
 * målt 18/11-2026 knækkede rækken ved 620 px (højde 32 → 54) og ved 420 px
 * (→ 60), fordi de tre faste kolonner (90+120+170 px) plus navnets 220 px
 * ikke kunne være der. jsdom har ingen layout-motor og kan per definition
 * ikke se det.
 *
 * ## Hvad den værner
 *
 * Figuren er karakterens identitet. Den må aldrig stå alene på sin egen linje
 * — så er der ingen at knytte den til. Vagten kræver derfor, ved hver bredde,
 * at figuren står på samme linje som navnet, og at intet element løber ud
 * over rækkens kant.
 *
 * ## Hvorfor den læser app.css fra disken
 *
 * En genskabelse af reglerne i testen ville måle testen, ikke produktet. Her
 * indlæses den faktiske fil, så en ændring i CSS'en rammer målingen.
 */
import { readFileSync } from 'node:fs'
import { chromium, type Browser } from 'playwright'
import { describe, expect, it } from 'vitest'

const CSS_STI = new URL('../../styles/app.css', import.meta.url)

/** Rækkens markup, 1:1 med MatrixKarakterer.tsx. */
const RAEKKE_HTML = `
<div class="jm-feed mk-liste">
  <div class="jm-feed-row mk-raekke" id="r">
    <svg class="mk-figur" width="22" height="22" viewBox="0 0 48 48">
      <circle cx="24" cy="24" r="18" fill="#6f8fd0" />
    </svg>
    <span class="jm-dot"></span>
    <span class="mk-navn"><b>Déjà Vu</b><span> — ufrivillig erindring af et tidligere run</span></span>
    <span class="mk-sidste">2t 14m</span>
    <span class="mk-cooldown">×3.2</span>
    <span class="mk-udfald">ok</span>
  </div>
</div>`

const BREDDER = [1400, 900, 720, 620, 560, 420, 360] as const

interface Maaling {
  bredde: number
  hoejde: number
  figurStoerrelse: string
  figurVedNavn: boolean
  udfaldIndenfor: boolean
  intetUdenfor: boolean
}

describe.skipIf(process.env.RUN_BROWSER_LAYOUT_MEASUREMENT !== '1')(
  'Karakter-rækken i rigtig Chromium',
  () => {
    it(
      'holder figuren ved navnet og alt inden for rækken ved alle bredder',
      async () => {
        const css = readFileSync(CSS_STI, 'utf8')
        const browser: Browser = await chromium.launch()
        const maalinger: Maaling[] = []
        try {
          const page = await browser.newPage()
          await page.setContent(`<!doctype html><html><head><style>
:root { --radius-sm: 6px; --bg-1: #1a1a1a; --fg-2: #bbb; --fg-3: #888; --error-fg: #f66; }
body { margin: 0; font: 12px system-ui; background: #111; color: #ddd; }
.jm-feed { display: flex; flex-direction: column; gap: 2px; }
.jm-dot { width: 6px; height: 6px; border-radius: 50%; background: #3a3; flex: 0 0 6px; }
${css}
</style></head><body>${RAEKKE_HTML}</body></html>`)

          for (const bredde of BREDDER) {
            await page.setViewportSize({ width: bredde, height: 400 })
            const m = await page.evaluate(() => {
              const raekke = document.getElementById('r')!
              const figur = raekke.querySelector('.mk-figur')!
              const navn = raekke.querySelector('.mk-navn')!
              const udfald = raekke.querySelector('.mk-udfald')!
              const rr = raekke.getBoundingClientRect()
              const fr = figur.getBoundingClientRect()
              const alle = [...raekke.children].map((el) => el.getBoundingClientRect())
              return {
                hoejde: Math.round(rr.height),
                figurStoerrelse: `${Math.round(fr.width)}x${Math.round(fr.height)}`,
                figurVedNavn: Math.abs(navn.getBoundingClientRect().top - fr.top) < 12,
                udfaldIndenfor: Math.round(udfald.getBoundingClientRect().right) <= Math.round(rr.right) + 1,
                intetUdenfor: alle.every(
                  (b) => b.right <= rr.right + 1 && b.left >= rr.left - 1,
                ),
              }
            })
            maalinger.push({ bredde, ...m })
          }
        } finally {
          await browser.close()
        }

        // Figuren er identitet: den skal staa ved navnet, ikke alene paa en linje.
        const udenFigurVedNavn = maalinger.filter((m) => !m.figurVedNavn)
        expect(udenFigurVedNavn.map((m) => m.bredde)).toEqual([])

        // Intet maa loebe ud over raekken — det er det der goer den ulæselig.
        const udenfor = maalinger.filter((m) => !m.udfaldIndenfor || !m.intetUdenfor)
        expect(udenfor.map((m) => m.bredde)).toEqual([])

        // Figuren maa ikke straekkes af flex, uanset bredde.
        expect(maalinger.map((m) => m.figurStoerrelse)).toEqual(
          BREDDER.map(() => '22x22'),
        )

        // Ved bred plads skal raekken vaere én linje (32 px). Knækker den
        // bredere end det, er de faste kolonner kommet tilbage.
        const brede = maalinger.filter((m) => m.bredde >= 560)
        expect(brede.map((m) => m.hoejde)).toEqual(brede.map(() => 32))
      },
      30_000,
    )
  },
)
