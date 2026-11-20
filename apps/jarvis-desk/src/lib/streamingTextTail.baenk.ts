/**
 * Fælles Chromium-bænk til ordhalens målinger (`*.maaling.test.ts`).
 *
 * Bundler den ÆGTE `MarkdownRenderer` + `chat-reading.css` + `tokens.css` og
 * åbner dem i rigtig Chromium. Ingen test-dobbelt: halen, nøglerne og CSS'en er
 * produktionskoden. Ikke en testfil — vitest samler kun `*.test.*`.
 */
import { mkdtemp, readFile, rm, writeFile } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'
import { build } from 'esbuild'
import { chromium, type Browser, type Page } from 'playwright'

const APP_DIR = fileURLToPath(new URL('../..', import.meta.url))

const BAENK = `
import { useEffect, useState } from 'react'
import { createRoot } from 'react-dom/client'
import { MarkdownRenderer } from './src/components/rich/MarkdownRenderer'

function Baenk() {
  const [tekst, setTekst] = useState('')
  const [streaming, setStreaming] = useState(true)
  useEffect(() => { (window as any).__saetTekst = setTekst; (window as any).__saetStreaming = setStreaming }, [])
  return <div className="chatview"><div id="krop" className="jarvis-body" style={{ width: 560 }}><MarkdownRenderer text={tekst} streaming={streaming} /></div></div>
}
createRoot(document.getElementById('root')!).render(<Baenk />)
`

export interface Baenk {
  page: Page
  browser: Browser
  fejl: string[]
  luk: () => Promise<void>
}

/** CSS kan overskrives pr. kald — mutationstests ændrer kilden, ikke bænken. */
export async function aabnBaenk(opts: { theme: 'dark' | 'light'; reducedMotion?: boolean } = { theme: 'dark' }): Promise<Baenk> {
  const css = (await readFile(join(APP_DIR, 'src/styles/tokens.css'), 'utf8'))
    + (await readFile(join(APP_DIR, 'src/styles/chat-reading.css'), 'utf8'))
  const res = await build({
    stdin: { contents: BAENK, resolveDir: APP_DIR, loader: 'tsx', sourcefile: 'ord-baenk.tsx' },
    bundle: true, write: false, outdir: 'out', format: 'iife', jsx: 'automatic',
    define: { 'process.env.NODE_ENV': '"production"', 'import.meta.url': '"file:///baenk/x.js"' }, logLevel: 'silent',
    loader: { '.svg': 'dataurl', '.png': 'dataurl', '.woff': 'dataurl', '.woff2': 'dataurl', '.ttf': 'dataurl' },
  })
  const js = res.outputFiles.find((f) => f.path.endsWith('.js'))
  if (!js) throw new Error('esbuild gav ingen JS')
  const mappe = await mkdtemp(join(tmpdir(), 'ord-baenk-'))
  await writeFile(join(mappe, 'bundle.js'), js.contents)
  await writeFile(join(mappe, 'index.html'),
    `<!doctype html><html data-theme="${opts.theme}"><head><meta charset="utf-8"><style>${css}</style></head>`
    + `<body style="margin:0;background:var(--page-bg,#fff)"><div id="root"></div><script src="bundle.js"></script></body></html>`)
  // Samme executable-valg som layout-målingen: headless-shell mangler nogle API'er.
  const executablePath = chromium.executablePath().replace(
    /chromium_headless_shell-([^/]+)\/chrome-headless-shell-linux64\/chrome-headless-shell$/,
    'chromium-$1/chrome-linux64/chrome',
  )
  const browser = await chromium.launch({ headless: true, executablePath })
  const page = await browser.newPage({ viewport: { width: 640, height: 480 } })
  if (opts.reducedMotion) await page.emulateMedia({ reducedMotion: 'reduce' })
  const fejl: string[] = []
  page.on('pageerror', (e) => fejl.push(e.message))
  await page.goto(pathToFileURL(join(mappe, 'index.html')).href)
  await page.waitForFunction(() => typeof (window as any).__saetTekst === 'function', null, { timeout: 5000 })
  return { page, browser, fejl, luk: async () => { await browser.close(); await rm(mappe, { recursive: true, force: true }) } }
}

export interface OrdHaendelse {
  t: number
  type: 'start' | 'end' | 'cancel'
  navn: string
  ord: string
  /** Ordets POSITION i dokumentet — stabil mens teksten vokser, i modsætning
   *  til `ord`, som under SSE kan være et halvt ord («o», «or», «ord1»). */
  nokkel: string
}

/** Lytter på animationsevents og på rAF-prøver af hvert halords farve/opacity. */
export async function installerMaaler(page: Page): Promise<void> {
  await page.evaluate(() => {
    const w = window as any
    w.__ev = [] as OrdHaendelse[]
    w.__prover = [] as { t: number; ord: string; color: string; opacity: number; x: number; y: number; w: number; h: number; klasse: string }[]
    w.__ordTid = new Map<string, number>()
    for (const type of ['start', 'end', 'cancel'] as const) {
      document.addEventListener(`animation${type}`, (e) => {
        const a = e as AnimationEvent
        const el = a.target as HTMLElement
        // Farven aflæses i CAPTURE, før React nåede at re-rendere.
        w.__ev.push({ t: performance.now(), type, navn: a.animationName.replace('streaming-word-', ''), ord: (el.textContent ?? '').trim(),
          nokkel: (el.dataset.streamPartKey ?? '').split(':')[0] ?? '',
          farve: getComputedStyle(el).color, opacity: Number(getComputedStyle(el).opacity) })
      }, true)
    }
    const prov = () => {
      const t = performance.now()
      document.querySelectorAll('#krop jarvis-stream-word, #krop span.streaming-word-tail, #krop span.streaming-word-settled').forEach((n) => {
        const el = n as HTMLElement
        const cs = getComputedStyle(el)
        const r = el.getBoundingClientRect()
        w.__prover.push({ t, ord: (el.textContent ?? '').trim(), color: cs.color, opacity: Number(cs.opacity), x: r.x, y: r.y, w: r.width, h: r.height, klasse: el.className })
      })
      requestAnimationFrame(prov)
    }
    requestAnimationFrame(prov)
  })
}

export const ordTekst = (n: number) => Array.from({ length: n }, (_, k) => `ord${k + 1}`).join(' ') + ' '
