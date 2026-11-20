// @vitest-environment node
/**
 * Ordhalen skal animere HVERT ord — målt som antal `animationstart` i Chromium.
 *
 * react-markdown giver børn nøglen `<tagName>-<antal>`; med ét tagName genbruges
 * de samme tre spans for hele svaret, så en genbrugt span aldrig starter sin
 * CSS-animation forfra. Målt før rettelsen: 81 ord gav 6 starter af opacity.
 * jsdom har ingen animationsmotor, så tallet kan kun måles her.
 */
import { mkdtemp, readFile, rm, writeFile } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'
import { build } from 'esbuild'
import { chromium } from 'playwright'
import { describe, expect, it } from 'vitest'

const APP_DIR = fileURLToPath(new URL('../..', import.meta.url))
const ORD = 81

const BAENK = `
import { useEffect, useState } from 'react'
import { createRoot } from 'react-dom/client'
import { MarkdownRenderer } from './src/components/rich/MarkdownRenderer'

function Baenk() {
  const [tekst, setTekst] = useState('')
  useEffect(() => { (window as any).__saetTekst = setTekst }, [])
  return <MarkdownRenderer text={tekst} streaming={true} />
}
createRoot(document.getElementById('root')!).render(<Baenk />)
`

describe.skipIf(process.env.RUN_BROWSER_LAYOUT_MEASUREMENT !== '1')(
  'ordhalens animationstart i Chromium',
  () => {
    it(`starter opacity-animationen for hvert af ${ORD} ord`, async () => {
      const css = await readFile(new URL('../styles/chat-reading.css', import.meta.url), 'utf8')
      const res = await build({
        stdin: { contents: BAENK, resolveDir: APP_DIR, loader: 'tsx', sourcefile: 'ord-baenk.tsx' },
        bundle: true, write: false, outdir: 'out', format: 'iife', jsx: 'automatic',
        define: { 'process.env.NODE_ENV': '"production"', 'import.meta.url': '"file:///baenk/x.js"' }, logLevel: 'silent',
        loader: { '.svg': 'dataurl', '.png': 'dataurl', '.woff': 'dataurl', '.woff2': 'dataurl', '.ttf': 'dataurl' },
      })
      const js = res.outputFiles.find((f) => f.path.endsWith('.js'))
      if (!js) throw new Error('esbuild gav ingen JS')
      const mappe = await mkdtemp(join(tmpdir(), 'ord-maal-'))
      await writeFile(join(mappe, 'bundle.js'), js.contents)
      await writeFile(join(mappe, 'index.html'),
        `<!doctype html><html><head><meta charset="utf-8"><style>${css}</style></head><body><div id="root"></div><script src="bundle.js"></script></body></html>`)
      // Samme executable-valg som den fælles bænk: den hårdkodede
      // `/usr/bin/google-chrome` findes ikke på alle værter, og så fejler
      // målingen på miljøet i stedet for på det den måler.
      const executablePath = process.env.CHROME_PATH || chromium.executablePath().replace(
        /chromium_headless_shell-([^/]+)\/chrome-headless-shell-linux64\/chrome-headless-shell$/,
        'chromium-$1/chrome-linux64/chrome',
      )
      const browser = await chromium.launch({ headless: true, executablePath })
      try {
        const page = await browser.newPage({ viewport: { width: 640, height: 480 } })
        const fejl: string[] = []
        page.on('pageerror', (e) => fejl.push(e.message))
        await page.goto(pathToFileURL(join(mappe, 'index.html')).href)
        await page.waitForFunction(() => typeof (window as any).__saetTekst === 'function', null, { timeout: 5000 })
          .catch(() => { throw new Error(`baenk ikke monteret: ${fejl.join(' | ')}`) })
        await page.evaluate(() => {
          ;(window as any).__start = [] as string[]
          ;(window as any).__add = 0
          new MutationObserver((ms) => { for (const m of ms) m.addedNodes.forEach((n) => { if ((n as Element).classList?.contains('streaming-word-tail')) (window as any).__add++ }) })
            .observe(document.getElementById('root')!, { childList: true, subtree: true })
          document.addEventListener('animationstart', (e) => {
            ;(window as any).__start.push((e as AnimationEvent).animationName)
          }, true)
        })
        // Ét ord ad gangen, afsluttet med mellemrum, med tid imellem så React committer.
        for (let i = 1; i <= ORD; i++) {
          const tekst = Array.from({ length: i }, (_, k) => `ord${k + 1}`).join(' ') + ' '
          await page.evaluate((t) => (window as any).__saetTekst(t), tekst)
          await page.waitForTimeout(80)
        }
        await page.waitForTimeout(500)
        const starter: string[] = await page.evaluate(() => (window as any).__start)
        const opacity = starter.filter((n) => n === 'streaming-word-opacity').length
        console.info('[ANIMATIONSTART-MÅLING]', { ord: ORD, opacity, alle: starter.length })
        expect(fejl).toEqual([])
        // Halen er tre ord; hvert nyt ord skal starte sin egen animation.
        // Ord 1..ORD bliver alle til hale-ord på et tidspunkt.
        expect(opacity).toBeGreaterThanOrEqual(ORD)
      } finally {
        await browser.close()
        await rm(mappe, { recursive: true, force: true })
      }
    }, 90_000)
  },
)
