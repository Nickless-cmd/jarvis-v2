// @vitest-environment node
import { readFile } from 'node:fs/promises'
import { chromium } from 'playwright'
import { describe, expect, it } from 'vitest'

/**
 * MÅLING (21/11-2026). Bjørn: «så skal foldet bar matche ord animationen..
 * lige nu sker foldet i et blink».
 *
 * jsdom kan se at `data-aaben` skifter, men den kan ikke se en transition — så
 * den kan ikke svare på om folden GLIDER eller HOPPER. Det er hele spørgsmålet,
 * og derfor skal det måles i rigtig Chromium med den ægte CSS.
 *
 * Kravet er todelt, og begge dele er nødvendige:
 *
 *   1. Højden skal passere gennem mange mellemværdier. Gør den ikke det, er
 *      der ingen overgang — og så er folden stadig et blink, uanset hvad
 *      attributterne hedder.
 *   2. Den skal bruge cirka `--dur-fold` (379 ms). En fold der glider på 60 ms
 *      opfylder punkt 1 og føles alligevel som et hop; en der tager 2 s føles
 *      som en defekt. Det er ord-animationens landing der sætter tallet.
 *
 * Målingen er en maaling, ikke en vagt: den rapporterer kurven, så et afvigende
 * tal kan læses i stedet for blot at fejle.
 */
describe.skipIf(process.env.RUN_BROWSER_LAYOUT_MEASUREMENT !== '1')(
  'folden glider i Chromium — den blinker ikke',
  () => {
    it('falder jaevt til nul gennem overgangen i stedet for at springe', async () => {
      const css = (await readFile(new URL('../../styles/tokens.css', import.meta.url), 'utf8'))
        + (await readFile(new URL('../../styles/raekkevisning.css', import.meta.url), 'utf8'))
      // Samme executable-valg som de øvrige målinger: headless-shell mangler
      // nogle API'er, som den fulde Chromium har.
      const executablePath = chromium.executablePath().replace(
        /chromium_headless_shell-([^/]+)\/chrome-headless-shell-linux64\/chrome-headless-shell$/,
        'chromium-$1/chrome-linux64/chrome',
      )
      const browser = await chromium.launch({ headless: true, executablePath })
      try {
        const page = await browser.newPage({ viewport: { width: 640, height: 480 } })
        await page.setContent(`
          <style>${css}</style>
          <div class="raekkevisning" style="width:560px">
            <div id="ydre" class="rv-gruppe-ydre" data-aaben="true">
              <div class="rv-gruppe">
                <div style="height:40px">runde 1</div>
                <div style="height:40px">runde 2</div>
                <div style="height:40px">runde 3</div>
              </div>
            </div>
            <div class="rv-svar" style="height:40px">svaret</div>
          </div>
        `)

        const maal = await page.evaluate(async () => {
          const ydre = document.getElementById('ydre') as HTMLElement
          const svar = document.querySelector('.rv-svar') as HTMLElement
          const hoejde = () => ydre.getBoundingClientRect().height
          const svarTop = () => svar.getBoundingClientRect().top

          const start = { hoejde: hoejde(), svarTop: svarTop() }
          const proever: { t: number; hoejde: number; svarTop: number }[] = []

          // Folden lukkes på præcis den måde komponenten gør det: attributten
          // skifter, elementet bliver i layoutet, CSS'en glider rækken.
          const t0 = performance.now()
          ydre.setAttribute('data-aaben', 'false')

          await new Promise<void>((faerdig) => {
            const tick = () => {
              const t = performance.now() - t0
              proever.push({ t, hoejde: hoejde(), svarTop: svarTop() })
              if (t < 700) requestAnimationFrame(tick)
              else faerdig()
            }
            requestAnimationFrame(tick)
          })

          return { start, proever }
        })

        const slut = maal.proever[maal.proever.length - 1]!
        const hoejder = maal.proever.map((p) => p.hoejde)
        const startHoejde = maal.start.hoejde
        // Mellemværdier: klart under udgangspunktet og klart over nul. Er der
        // ingen af dem, sprang folden fra fuld højde til nul i én frame.
        const mellem = hoejder.filter((h) => h > startHoejde * 0.05 && h < startHoejde * 0.95)
        const naerNul = maal.proever.find((p) => p.hoejde < 2)

        const kurve = maal.proever
          .filter((_, i) => i % 6 === 0)
          .map((p) => `${Math.round(p.t)}ms:${Math.round(p.hoejde)}px`)
          .join(' ')
        // eslint-disable-next-line no-console
        console.log(
          `=== FOLDENS KURVE ===\n`
          + `udgangshoejde ${Math.round(startHoejde)}px, ${maal.proever.length} proever\n`
          + `${kurve}\n`
          + `mellemvaerdier ${mellem.length}, naar nul efter ${naerNul ? Math.round(naerNul.t) : 'aldrig'}ms`,
        )

        // 1. Indholdet skal faktisk fylde noget, ellers måler vi ingenting.
        expect(startHoejde).toBeGreaterThan(100)
        // 2. Den skal glide — ikke springe.
        expect(mellem.length).toBeGreaterThan(5)
        // 3. Den skal lande på nul, så den lukkede fold ikke koster plads.
        expect(slut.hoejde).toBeLessThan(2)
        // 4. Og den skal bruge omkring ord-animationens 379 ms.
        expect(naerNul?.t ?? Infinity).toBeGreaterThan(250)
        expect(naerNul?.t ?? Infinity).toBeLessThan(500)

        // Svaret under folden skal følge med op i ÉN bevægelse, ikke rykke
        // først og glide bagefter: det var præcis det «hop» Bjørn så.
        const svarFlyt = maal.start.svarTop - slut.svarTop
        expect(svarFlyt).toBeGreaterThan(80)
      } finally {
        await browser.close()
      }
    })
  },
)
