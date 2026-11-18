// @vitest-environment node
/**
 * Karakter-figuren maalt i rigtig Chromium.
 *
 * ## Hvorfor den findes
 *
 * `KarakterFigur.test.tsx` og `karakterFigur.test.ts` kører i jsdom. De kan
 * bevise at modellen er deterministisk, at paletten er brugt, og at det rigtige
 * navn gaar ind i komponenten. De kan IKKE se om figuren tegner noget.
 *
 * En `<path>` findes i DOM'en uanset om dens bezier-kurve er degenereret og
 * giver nul areal. En accessory kan ligge uden for viewBox og blive klippet
 * vaek. To karakterer kan vaere pixel-identiske uden at nogen prop-test ser
 * det. Alt tre er usynligt i jsdom — og det er praecis den slags fejl der ser
 * færdig ud.
 *
 * ## Hvad der maales
 *
 * 1. Alle 10 former tegner et synligt KROPSAREAL (maalt uden øjne).
 * 2. Ingen form er domineret af en anden — arealet ligger i et baand.
 * 3. De 28 registrerede karakterer giver mindst 20 forskellige billeder, maalt
 *    som hash af de malede pixels.
 * 4. Krop, tilbehoer og øjne ligger inden for viewBox (0-48).
 *
 * ## To maalefælder der blev fanget ved at injicere fejl (18/11-2026)
 *
 * Foerste version bestod MED en tom `heart` og MED alt tilbehoer skubbet 40
 * enheder ud af billedet. Aarsagerne var ikke i produktionskoden:
 *
 * - Øjnene tegnes altid og giver ~115 pixels alene. Maalte man hele figuren,
 *   kunne en degenereret krop aldrig komme under en nul-taelling. Derfor maales
 *   kropsarealet for sig: den sidste gruppe (øjnene) fjernes foer tegning.
 * - `getBBox()` returnerer den LOKALE boks og ser ikke gruppens egen
 *   `transform`. En gruppe skubbet ud af billedet havde uændret bbox. Derfor
 *   maales positionen med `getBoundingClientRect` relativt til SVG'en, som
 *   medregner transform, og omregnes til viewBox-enheder.
 *
 * ## Hvorfor den er bag et flag
 *
 * `npm test` skal kunne køre uden Playwright-browsere. Flaget
 * `RUN_BROWSER_LAYOUT_MEASUREMENT` sættes i CI's `desk-browser`-job, hvor
 * Chromium er installeret foerst — samme flag som crossfade- og layout-maaleren.
 */
import { mkdtemp, rm, writeFile } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'
import { build } from 'esbuild'
import { chromium, type Browser, type Page } from 'playwright'
import { describe, expect, it } from 'vitest'

/** App-roden (`apps/jarvis-desk`) — tre niveauer op fra `src/components/cowork/`. */
const APP_DIR = fileURLToPath(new URL('../../..', import.meta.url))

/** ViewBox for alle figurer — `KarakterFigur.tsx` › `VIEWBOX`. */
const VIEWBOX_MAL = 48

/** De 28 karakterer der faktisk er registreret i cadence-registret (maalt 18/11-2026). */
const KARAKTERER = [
  'construct', 'oracle', 'architect', 'echo_breaker', 'continuity_healer',
  'red_dress', 'analyst', 'redpill', 'dissent', 'white_rabbit',
  'belief_gap', 'machines', 'morpheus', 'trinity', 'dejavu',
  'sentinel', 'ghost', 'mourning', 'merovingian', 'dream_action',
  'rca', 'relational', 'glitch', 'trainman', 'seraph',
  'persephone', 'twins', 'exile',
]

/**
 * Baenken monterer den ÆGTE komponent.
 *
 * Formerne rammes med syntetiske navne (`f0`, `f1`, …) fordi figuren er en
 * funktion af navnet: for hver af de 10 former findes det foerste navn der
 * rammer den. Det maaler de ægte tegninger uden at eksportere internals fra
 * produktionskoden for testens skyld.
 */
const BAENK = `
import { createRoot } from 'react-dom/client'
import { KarakterFigur } from './src/components/cowork/KarakterFigur'
import { karakterFigur, KARAKTER_SHAPES } from './src/lib/karakterFigur'

const navnPrForm: Record<string, string> = {}
for (let i = 0; i < 4000; i++) {
  const navn = 'f' + i
  const form = karakterFigur(navn).shape
  if (!navnPrForm[form]) navnPrForm[form] = navn
  if (Object.keys(navnPrForm).length === KARAKTER_SHAPES.length) break
}

const KARAKTERER: string[] = ${JSON.stringify(KARAKTERER)}

function Baenk() {
  return (
    <div>
      <div id="former">
        {KARAKTER_SHAPES.map((form) => (
          <span key={form} data-form={form} style={{ display: 'inline-block' }}>
            <KarakterFigur navn={navnPrForm[form] ?? 'ukendt'} stoerrelse={48} />
          </span>
        ))}
      </div>
      <div id="karakterer">
        {KARAKTERER.map((navn) => (
          <span key={navn} data-navn={navn} style={{ display: 'inline-block' }}>
            <KarakterFigur navn={navn} stoerrelse={48} />
          </span>
        ))}
      </div>
    </div>
  )
}

;(window as any).__former = navnPrForm
createRoot(document.getElementById('root')!).render(<Baenk />)
`

interface Side {
  browser: Browser
  page: Page
  rydOp: () => Promise<void>
}

/** Bundler baenken, skriver den til en temp-mappe og starter Chromium paa den. */
async function startSide(): Promise<Side> {
  const resultat = await build({
    stdin: { contents: BAENK, resolveDir: APP_DIR, loader: 'tsx', sourcefile: 'karakter-baenk.tsx' },
    bundle: true,
    write: false,
    outdir: 'out',
    format: 'iife',
    // React 19's automatiske runtime — uden den kalder esbuild
    // `React.createElement`, som ikke findes uden en default-import.
    jsx: 'automatic',
    define: { 'process.env.NODE_ENV': '"production"' },
    logLevel: 'silent',
  })

  const js = resultat.outputFiles.find((f) => f.path.endsWith('.js'))
  if (!js) throw new Error('esbuild gav ingen JS — baenken kunne ikke bundles')

  const mappe = await mkdtemp(join(tmpdir(), 'karakter-maal-'))
  await writeFile(join(mappe, 'bundle.js'), js.contents)
  await writeFile(
    join(mappe, 'index.html'),
    `<!doctype html><html><head><meta charset="utf-8"></head>
     <body style="margin:0;background:#fff"><div id="root"></div>
     <script src="bundle.js"></script></body></html>`,
  )

  const browser = await chromium.launch({ headless: true })
  const page = await browser.newPage({ viewport: { width: 1400, height: 900 } })

  // En baenk der ikke monterer skal sige HVORFOR, ikke «is not a function».
  const sideFejl: string[] = []
  page.on('pageerror', (e) => sideFejl.push(`pageerror: ${e.message}`))
  page.on('console', (m) => {
    if (m.type() === 'error') sideFejl.push(`console: ${m.text()}`)
  })

  await page.goto(pathToFileURL(join(mappe, 'index.html')).href)
  await page.waitForFunction(() => document.querySelectorAll('svg').length > 0, { timeout: 10_000 })
  if (sideFejl.length > 0) throw new Error(`baenken fejlede: ${sideFejl.join(' | ')}`)

  return {
    browser,
    page,
    rydOp: async () => {
      await browser.close()
      await rm(mappe, { recursive: true, force: true })
    },
  }
}

/** Ét maalt SVG: kroppens areal, hele billedets hash, og gruppernes viewBox-bokse. */
interface Billede {
  navn: string
  /** Hele figurens malede pixels — bruges til hashen. */
  pixels: number
  /** KUN kropsgruppen (øjnene fjernet) — nul betyder en degenereret form. */
  kropPixels: number
  hash: string
  /** Gruppernes boks i VIEWBOX-enheder, saa transform er medregnet. */
  bbox: { x: number; y: number; bredde: number; hoejde: number }[]
}

/**
 * Tegner hver SVG paa et canvas i browseren og tæller ikke-transparente pixels.
 *
 * Det er den eneste maaling der kan skelne «en path staar i DOM'en» fra «formen
 * tegner noget»: en degenereret bezier giver nul pixels, men bestaar stadig
 * som element.
 */
async function maalAlle(page: Page, selektor: string, attribut: string): Promise<Billede[]> {
  return page.evaluate(
    async ({ selektor, attribut, viewBoxMal }: { selektor: string; attribut: string; viewBoxMal: number }) => {
      const SVG_NS = 'http://www.w3.org/2000/svg'
      const resultat: Billede[] = []

      /**
       * `kunKrop` fjerner den SIDSTE gruppe (øjnene). Øjnene tegnes altid og
       * giver ~115 pixels alene, saa en tom kropsform kan ikke maales til nul
       * paa hele figuren.
       */
      const tegn = async (
        svg: SVGSVGElement,
        kunKrop = false,
      ): Promise<{ pixels: number; hash: string }> => {
        const klon = svg.cloneNode(true) as SVGSVGElement
        if (kunKrop) {
          const grupper = klon.querySelectorAll('g')
          const sidste = grupper[grupper.length - 1]
          if (sidste && grupper.length > 1) sidste.remove()
        }
        klon.setAttribute('xmlns', SVG_NS)
        // Eksplicitte maal: drawImage tegner intet af en SVG uden width/height.
        klon.setAttribute('width', '96')
        klon.setAttribute('height', '96')
        const tekst = new XMLSerializer().serializeToString(klon)
        const url = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(tekst)

        const billede = new Image()
        await new Promise<void>((klar, fejl) => {
          billede.onload = () => klar()
          billede.onerror = () => fejl(new Error('SVG kunne ikke indlaeses som billede'))
          billede.src = url
        })

        const canvas = document.createElement('canvas')
        canvas.width = 96
        canvas.height = 96
        const ctx = canvas.getContext('2d')
        if (!ctx) throw new Error('canvas-kontekst mangler')
        ctx.drawImage(billede, 0, 0, 96, 96)
        const data = ctx.getImageData(0, 0, 96, 96).data

        let pixels = 0
        let hash = 2166136261
        for (let i = 0; i < data.length; i += 4) {
          const alfa = data[i + 3] as number
          if (alfa > 8) pixels++
          hash ^= (data[i] as number) + (data[i + 1] as number) * 3 + (data[i + 2] as number) * 7 + alfa
          hash = Math.imul(hash, 16777619) >>> 0
        }
        return { pixels, hash: hash.toString(16) }
      }

      const elementer = Array.from(document.querySelectorAll<HTMLElement>(selektor))
      for (const element of elementer) {
        const svg = element.querySelector('svg')
        if (!svg) continue
        const hel = await tegn(svg as SVGSVGElement)
        const krop = await tegn(svg as SVGSVGElement, true)

        // Position maales med getBoundingClientRect, som MEDREGNER transform.
        // getBBox() goer ikke — den returnerer den lokale boks, saa en gruppe
        // skubbet ud af billedet ville se ud som om den stod stille.
        const svgRect = (svg as SVGSVGElement).getBoundingClientRect()
        const skala = svgRect.width > 0 ? viewBoxMal / svgRect.width : 1
        const bbox = Array.from(svg.querySelectorAll('g'))
          .map((g) => {
            const b = g.getBoundingClientRect()
            return {
              x: (b.left - svgRect.left) * skala,
              y: (b.top - svgRect.top) * skala,
              bredde: b.width * skala,
              hoejde: b.height * skala,
            }
          })
          .filter((b) => b.bredde > 0 || b.hoejde > 0)

        resultat.push({
          navn: element.getAttribute(attribut) ?? '?',
          pixels: hel.pixels,
          kropPixels: krop.pixels,
          hash: hel.hash,
          bbox,
        })
      }
      return resultat
    },
    { selektor, attribut, viewBoxMal: VIEWBOX_MAL },
  )
}

describe.skipIf(process.env.RUN_BROWSER_LAYOUT_MEASUREMENT !== '1')(
  'Karakter-figuren i rigtig Chromium',
  () => {
    it('tegner alle 10 former et synligt kropsareal', async () => {
      const side = await startSide()
      try {
        const former = await maalAlle(side.page, '#former [data-form]', 'data-form')
        expect(former).toHaveLength(10)

        for (const form of former) {
          // Maalt uden øjne: 0 ville betyde en form der findes som element,
          // men ikke tegner. Mindste fyldte form maalte 1921 px (heart).
          expect(
            form.kropPixels,
            `formen «${form.navn}» tegner ${form.kropPixels} krops-pixels`,
          ).toBeGreaterThan(500)
        }

        // Ingen form maa vaere en prik ved siden af en anden. Maalt baand:
        // 1921-3234 (forhold 1,68).
        const arealer = former.map((f) => f.kropPixels)
        const mindste = Math.min(...arealer)
        const stoerste = Math.max(...arealer)
        expect(stoerste / mindste, `stoerste/mindste areal = ${stoerste}/${mindste}`).toBeLessThan(4)
      } finally {
        await side.rydOp()
      }
    }, 60_000)

    it('giver de 28 karakterer mindst 20 forskellige billeder', async () => {
      const side = await startSide()
      try {
        const figurer = await maalAlle(side.page, '#karakterer [data-navn]', 'data-navn')
        expect(figurer).toHaveLength(KARAKTERER.length)

        for (const figur of figurer) {
          expect(
            figur.kropPixels,
            `«${figur.navn}» tegner ${figur.kropPixels} krops-pixels`,
          ).toBeGreaterThan(500)
        }

        // Familiens ægte spredning — ikke modellens paastand om den.
        const unikke = new Set(figurer.map((f) => f.hash))
        expect(
          unikke.size,
          `kun ${unikke.size} af ${figurer.length} figurer er forskellige`,
        ).toBeGreaterThanOrEqual(20)
      } finally {
        await side.rydOp()
      }
    }, 60_000)

    it('holder krop, tilbehoer og øjne inden for viewBox', async () => {
      const side = await startSide()
      try {
        const figurer = await maalAlle(side.page, '#karakterer [data-navn]', 'data-navn')
        expect(figurer.length).toBeGreaterThan(0)

        for (const figur of figurer) {
          // Foerste gruppe er kroppen, sidste er øjnene. En mellemgruppe er
          // tilbehoer og findes kun for de karakterer der har et.
          for (const [i, boks] of figur.bbox.entries()) {
            const hvad = i === 0 ? 'krop' : i === figur.bbox.length - 1 ? 'øjne' : 'tilbehoer'
            // 0.5 enheds tolerance for stroke og afrunding.
            expect(boks.x, `${figur.navn}/${hvad} venstre kant x=${boks.x}`).toBeGreaterThanOrEqual(-0.5)
            expect(boks.y, `${figur.navn}/${hvad} top y=${boks.y}`).toBeGreaterThanOrEqual(-0.5)
            expect(boks.x + boks.bredde, `${figur.navn}/${hvad} hoejre kant`).toBeLessThanOrEqual(
              VIEWBOX_MAL + 0.5,
            )
            expect(boks.y + boks.hoejde, `${figur.navn}/${hvad} nederste kant`).toBeLessThanOrEqual(
              VIEWBOX_MAL + 0.5,
            )
          }
        }
      } finally {
        await side.rydOp()
      }
    }, 60_000)
  },
)
