// @vitest-environment node
/**
 * Crossfade-måling i rigtig Chromium.
 *
 * ## Hvorfor den findes
 *
 * `TurHoved.titelCrossfade.test.tsx` kører i jsdom og kan bevise at span'et
 * GENMONTERES (`key` skifter) og at `data-crossfade` sættes. Men jsdom har
 * hverken layout- eller animationsmotor, så den kan ikke se om animationen
 * faktisk fyrer — og slet ikke hvor MANGE gange.
 *
 * Det var præcis fejlen der blev rettet 18/11-2026: `vist.transition` stod i
 * `useEffect`'ens dependency-array, timeren genarmede sig selv, og der blev
 * målt **3 re-fades på 11 sekunder på uændret tekst**. Den fejl var grøn i
 * jsdom hele vejen. Denne fil måler tallet i en browser der faktisk animerer.
 *
 * ## Hvorfor den er bag et flag
 *
 * `npm test` skal kunne køre på en maskine uden Playwright-browsere. Flaget
 * `RUN_BROWSER_LAYOUT_MEASUREMENT` sættes derfor i CI, hvor
 * `npx playwright install --with-deps chromium` er kørt først — se
 * `.github/workflows/ci.yml` › desk › «Browser-målinger». Uden det step er
 * denne test en fil der aldrig fyrer; det er den fejl den selv skal undgå.
 *
 * ## Hvad der måles
 *
 * 1. Mount giver nul animationer — ingen fade uden et skift at fade til.
 * 2. Et ægte trin-skift giver præcis én `rv-titel-crossfade` på 180 ms, og
 *    opacity bevæger sig synligt fra 0,72 mod 1.
 * 3. Uændret tekst giver NUL animationer, uanset hvor mange loft-perioder
 *    der går — puls-værnet.
 * 4. Titlen hopper ikke i layout mens den fader.
 * 5. `prefers-reduced-motion` slår animationen helt fra.
 */
import { mkdtemp, rm, writeFile } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'
import { build } from 'esbuild'
import { chromium, type Browser, type Page } from 'playwright'
import { describe, expect, it } from 'vitest'

/** App-roden (`apps/jarvis-desk`) — tre niveauer op fra `src/components/rich/`. */
const APP_DIR = fileURLToPath(new URL('../../..', import.meta.url))

/**
 * Baenken monterer den ÆGTE komponent og lægger styringen paa `window`, saa
 * Playwright kan skifte trinnet uden at skulle ramme en knap.
 */
const BAENK = `
import { useEffect, useState } from 'react'
import { createRoot } from 'react-dom/client'
import { TitelCrossfade } from './src/components/rich/TurHoved'

type Styr = { tekst: string; aktiv: boolean; intervalMs: number }

function Baenk() {
  const [styr, setStyr] = useState<Styr>({
    tekst: 'Læser konfigurationen',
    aktiv: true,
    intervalMs: 400,
  })
  useEffect(() => { (window as any).__saetStyr = setStyr }, [])
  return (
    <div id="vaert">
      <TitelCrossfade tekst={styr.tekst} aktiv={styr.aktiv} intervalMs={styr.intervalMs} />
    </div>
  )
}

createRoot(document.getElementById('root')!).render(<Baenk />)
`

interface Side {
  browser: Browser
  page: Page
  rydOp: () => Promise<void>
}

/** Bundler baenken, skriver den til en temp-mappe og starter Chromium paa den. */
async function startSide(reducedMotion = false): Promise<Side> {
  const resultat = await build({
    stdin: { contents: BAENK, resolveDir: APP_DIR, loader: 'tsx', sourcefile: 'crossfade-baenk.tsx' },
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
  const css = resultat.outputFiles.find((f) => f.path.endsWith('.css'))
  if (!js) throw new Error('esbuild gav ingen JS — baenken kunne ikke bundles')

  const mappe = await mkdtemp(join(tmpdir(), 'crossfade-maal-'))
  await writeFile(join(mappe, 'bundle.js'), js.contents)
  await writeFile(
    join(mappe, 'index.html'),
    `<!doctype html><html><head><meta charset="utf-8">
     ${css ? `<style>${css.text}</style>` : ''}
     </head><body><div id="root"></div><script src="bundle.js"></script></body></html>`,
  )

  const browser = await chromium.launch({ headless: true })
  const page = await browser.newPage({ viewport: { width: 640, height: 240 } })

  // En baenk der ikke monterer skal sige HVORFOR. Uden dette bliver en
  // JS-fejl i bundlen til «__saetStyr is not a function» otte linjer senere.
  const sideFejl: string[] = []
  page.on('pageerror', (e) => sideFejl.push(`pageerror: ${e.message}`))
  page.on('console', (m) => {
    if (m.type() === 'error') sideFejl.push(`console: ${m.text()}`)
  })

  if (reducedMotion) await page.emulateMedia({ reducedMotion: 'reduce' })
  await page.goto(pathToFileURL(join(mappe, 'index.html')).href)

  const monteret = await page.evaluate(
    () => typeof (window as unknown as { __saetStyr?: unknown }).__saetStyr === 'function',
  )
  if (!monteret) {
    await browser.close()
    await rm(mappe, { recursive: true, force: true })
    throw new Error(`baenken blev ikke monteret. ${sideFejl.join(' | ') || 'ingen side-fejl fanget'}`)
  }

  return {
    browser,
    page,
    rydOp: async () => {
      await browser.close()
      await rm(mappe, { recursive: true, force: true })
    },
  }
}

/** Lytter paa `animationstart` (bobler ikke — derfor capture) og rydder listen. */
async function lytEfterAnimationer(page: Page): Promise<void> {
  await page.evaluate(() => {
    ;(window as unknown as { __anim: unknown[] }).__anim = []
    document.addEventListener(
      'animationstart',
      (e) => {
        const ev = e as AnimationEvent
        ;(window as unknown as { __anim: unknown[] }).__anim.push({
          navn: ev.animationName,
          tid: Math.round(performance.now()),
        })
      },
      true,
    )
  })
}

const hentAnimationer = (page: Page) =>
  page.evaluate(() => (window as unknown as { __anim: { navn: string; tid: number }[] }).__anim)

describe.skipIf(process.env.RUN_BROWSER_LAYOUT_MEASUREMENT !== '1')(
  'TitelCrossfade i rigtig Chromium',
  () => {
    it('fader præcis én gang ved et ægte trin-skift — og fadet er synligt', async () => {
      const side = await startSide()
      try {
        await lytEfterAnimationer(side.page)

        // 1) Mount: ingen fade. Der er intet skift at fade til.
        await side.page.waitForTimeout(120)
        expect(await hentAnimationer(side.page)).toEqual([])

        const foer = await side.page.locator('#vaert').evaluate((n) => {
          const { x, y, width, height } = n.getBoundingClientRect()
          return { x, y, width, height }
        })

        // 2) Ægte skift — skift OG sampling i ét kald, så forløbet ikke når
        //    at løbe mens vi venter på et roundtrip.
        const forloeb = await side.page.evaluate(async (nyTekst: string) => {
          const w = window as unknown as {
            __saetStyr: (s: { tekst: string; aktiv: boolean; intervalMs: number }) => void
            __anim: { navn: string; tid: number }[]
          }
          w.__anim = []
          w.__saetStyr({ tekst: nyTekst, aktiv: true, intervalMs: 400 })
          await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)))

          const el = document.querySelector('.rv-titelCrossfadeTekst')
          if (!el) throw new Error('titlen blev ikke genmonteret ved skiftet')

          // Fang animationen MENS den lever. Efter 280 ms er de 180 ms løbet,
          // og så er den fjernet fra getAnimations() — det gav `null` første gang.
          const animation = el.getAnimations()[0]
          const varighed = animation
            ? (animation.effect?.getTiming().duration as number)
            : Math.round(parseFloat(getComputedStyle(el).animationDuration) * 1000)

          const prover: [number, number][] = []
          const t0 = performance.now()
          while (performance.now() - t0 < 280) {
            prover.push([Math.round(performance.now() - t0), parseFloat(getComputedStyle(el).opacity)])
            await new Promise((r) => setTimeout(r, 20))
          }
          return {
            prover,
            anim: w.__anim,
            tekst: el.textContent,
            varighed,
            slutOpacity: parseFloat(getComputedStyle(el).opacity),
          }
        }, 'Bygger billed-grid')

        // Præcis én animation, og det er crossfaden.
        expect(forloeb.anim).toHaveLength(1)
        expect(forloeb.anim.map((a) => a.navn)).toEqual(['rv-titel-crossfade'])
        expect(forloeb.varighed).toBe(180)
        expect(forloeb.tekst).toBe('Bygger billed-grid')

        // Fadet er synligt: starter under 1, stiger, slutter praecis paa 1.
        const opaciteter = forloeb.prover.map(([, o]) => o)
        expect(opaciteter.length).toBeGreaterThan(5)
        expect(opaciteter.at(0)).toBeLessThan(1)
        expect(opaciteter.at(0)).toBeGreaterThanOrEqual(0.7)
        expect(opaciteter.at(-1)).toBe(1)
        expect(forloeb.slutOpacity).toBe(1)

        // 3) Layout staar stille under og efter skiftet.
        const efter = await side.page.locator('#vaert').evaluate((n) => {
          const { x, y, width, height } = n.getBoundingClientRect()
          return { x, y, width, height }
        })
        expect(efter.y).toBe(foer.y)
        expect(efter.height).toBe(foer.height)
      } finally {
        await side.rydOp()
      }
    }, 30_000)

    // ── Puls-værnet ────────────────────────────────────────────────────
    // Den fejl der blev maalt 18/11-2026: `vist.transition` i dependency-
    // arrayet genarmede timeren, saa fade'en genstartede hvert 3,5 s paa
    // UAENDRET tekst — 3 re-fades paa 11 s. Bjørn: «Kun ved ægte
    // trin-skift — loftet som rent værn, ingen puls.»
    it('fader ALDRIG på uændret tekst, uanset hvor mange loft-perioder der går', async () => {
      const side = await startSide()
      try {
        await lytEfterAnimationer(side.page)

        // Ti loft-perioder (400 ms × 10 = 4 s) paa samme tekst. En
        // selvgenarmende timer ville have fyret ti gange her.
        await side.page.waitForTimeout(4000)

        expect(await hentAnimationer(side.page)).toEqual([])
        expect(await side.page.locator('.rv-titelCrossfadeTekst').count()).toBe(1)
        expect(await side.page.locator('.rv-titelCrossfadeTekst').textContent()).toBe(
          'Læser konfigurationen',
        )
      } finally {
        await side.rydOp()
      }
    }, 20_000)

    it('skifter stadig naar trinnet skifter EFTER loftet er loebet', async () => {
      const side = await startSide()
      try {
        await lytEfterAnimationer(side.page)
        await side.page.waitForTimeout(1200)

        const anim = await side.page.evaluate(async () => {
          const w = window as unknown as {
            __saetStyr: (s: { tekst: string; aktiv: boolean; intervalMs: number }) => void
            __anim: { navn: string }[]
          }
          w.__anim = []
          w.__saetStyr({ tekst: 'Skriver filen', aktiv: true, intervalMs: 400 })
          await new Promise((r) => setTimeout(r, 300))
          return w.__anim
        })

        expect(anim).toHaveLength(1)
        expect(anim.map((a) => a.navn)).toEqual(['rv-titel-crossfade'])
      } finally {
        await side.rydOp()
      }
    }, 20_000)

    it('fader ikke naar brugeren har bedt om reduceret bevaegelse', async () => {
      const side = await startSide(true)
      try {
        await lytEfterAnimationer(side.page)

        const anim = await side.page.evaluate(async () => {
          const w = window as unknown as {
            __saetStyr: (s: { tekst: string; aktiv: boolean; intervalMs: number }) => void
            __anim: { navn: string }[]
          }
          w.__anim = []
          w.__saetStyr({ tekst: 'Bygger billed-grid', aktiv: true, intervalMs: 400 })
          await new Promise((r) => setTimeout(r, 400))
          return w.__anim
        })

        expect(anim).toEqual([])
        expect(await side.page.locator('.rv-titelCrossfadeTekst').textContent()).toBe(
          'Bygger billed-grid',
        )
      } finally {
        await side.rydOp()
      }
    }, 20_000)
  },
)
