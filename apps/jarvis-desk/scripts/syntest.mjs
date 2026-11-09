#!/usr/bin/env node
/**
 * Syntest — måler hvordan Desk-fladen FAKTISK ser ud, ikke hvordan logikken opfører sig.
 *
 * HVORFOR DEN FINDES (9/11-2026): 3.218 enhedstests målte logik og var alle
 * grønne, mens fladen kunne være i stykker. Det er samme blinde plet som da
 * 577 grønne tests missede to fejl som fem minutter på telefonen fandt.
 *
 * HVAD DEN MÅLER — og hvad den IKKE måler:
 * Geometri, ikke pixels. En pixel-diff fejler på en ændret font-rendering og
 * består når hele layoutet er skredet 40 px, hvis bare det skred ensartet.
 * Disse assertions fælder derimod de fejl der gør fladen ubrugelig:
 *
 *   1. Fladen tegner overhovedet (root har børn, composeren findes)
 *   2. Composeren er INDEN FOR viewport — ikke skubbet under skærmen
 *   3. Composeren er ikke kollapset (bredde og højde over et minimum)
 *   4. Dokumentet scroller ikke horisontalt
 *   5. Composeren overlapper ikke transcriptet
 *
 * Brug: npm run syntest   (kræver dist-web — kør `npm run build:web` først)
 */
import { chromium } from 'playwright'
import { createServer } from 'node:http'
import { readFile, mkdir } from 'node:fs/promises'
import { existsSync } from 'node:fs'
import { join, extname } from 'node:path'
import { fileURLToPath } from 'node:url'

const ROD = fileURLToPath(new URL('..', import.meta.url))
const DIST = join(ROD, 'dist-web')
const PORT = Number(process.env.SYNTEST_PORT || 4178)
const SHOT_DIR = join(ROD, 'syntest-udfald')

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.json': 'application/json',
  '.webmanifest': 'application/manifest+json',
  '.woff2': 'font/woff2',
  '.png': 'image/png',
}

/** Svar appen får på ethvert /api-kald. Tomme men gyldige former — vi måler
 *  layout, ikke data. Et kald der kræver en bestemt form får den her. */
function apiSvar(sti) {
  if (sti.includes('/api/whoami')) {
    return {
      user_id: 'syntest',
      canonical_user_id: 'syntest',
      user_display_name: 'Syntest',
      role: 'owner',
    }
  }
  if (sti.includes('/api/auth/renew')) return { token: 'syntest-token' }
  if (sti.includes('/api/connectors')) return { connectors: [] }
  if (sti.includes('/api/sessions')) return { sessions: [] }
  return {}
}

function startServer() {
  const server = createServer(async (req, res) => {
    const sti = decodeURIComponent((req.url || '/').split('?')[0])
    if (process.env.SYNTEST_VERBOSE) console.log('REQ', req.method, sti)

    if (sti.startsWith('/api/')) {
      // POST med vilje accepteret: `auth/renew` er POST, og en statisk server
      // der svarer 501 på den får appen til at kaste i boot — det var præcis
      // fejlen proben fandt.
      const body = JSON.stringify(apiSvar(sti))
      res.writeHead(200, { 'content-type': 'application/json' })
      res.end(body)
      return
    }

    let fil = join(DIST, sti)
    if (sti === '/' || !extname(sti)) fil = join(DIST, 'index.html')
    if (!existsSync(fil)) fil = join(DIST, 'index.html')

    try {
      const data = await readFile(fil)
      res.writeHead(200, { 'content-type': MIME[extname(fil)] || 'application/octet-stream' })
      res.end(data)
    } catch {
      res.writeHead(404)
      res.end('ikke fundet')
    }
  })
  return new Promise((ok) => server.listen(PORT, '127.0.0.1', () => ok(server)))
}

const fejl = []
function paastand(navn, betingelse, detalje) {
  if (betingelse) {
    console.log(`  ✓ ${navn}`)
  } else {
    console.log(`  ✗ ${navn}${detalje ? ` — ${detalje}` : ''}`)
    fejl.push(navn)
  }
}

async function main() {
  if (!existsSync(DIST)) {
    console.error(`dist-web findes ikke (${DIST}). Kør: npm run build:web`)
    process.exit(2)
  }

  const server = await startServer()
  const browser = await chromium.launch()
  // Service workeren skal BLOKERES, ikke afregistreres. Målt 9/11-2026: en
  // unregister i et init-script fik appen til at se en «ny version» og vise
  // `pwa-update`-prompten — så syntesten målte opdaterings-fladen i stedet for
  // chatten, og composeren dukkede aldrig op. Blokeret helt måler vi bundlen
  // der faktisk ligger i dist-web, uden cache imellem.
  const context = await browser.newContext({
    viewport: { width: 1280, height: 800 },
    serviceWorkers: 'block',
  })
  const page = await context.newPage()

  await page.addInitScript(
    ({ port }) => {
      localStorage.setItem(
        'jarvis:web-auth',
        JSON.stringify({ origin: `http://127.0.0.1:${port}`, authToken: 'syntest-token' }),
      )
    },
    { port: PORT },
  )

  const pageFejl = []
  page.on('pageerror', (e) => pageFejl.push(String(e.message || e).slice(0, 160)))

  await page.goto(`http://127.0.0.1:${PORT}/`, { waitUntil: 'domcontentloaded', timeout: 30000 })

  // AI-disclaimeren er en modal over fladen ved første visning. Den skal kunne
  // lukkes — ellers er Desk ubrugelig for enhver ny installasjon, og det er
  // netop den slags en enhedstest aldrig ser.
  const forstaet = page.getByRole('button', { name: /forstået/i })
  const havdeModal = (await forstaet.count()) > 0
  if (havdeModal) {
    await forstaet.first().click()
    await page.waitForTimeout(400)
  }

  // `attached`, ikke `visible`: Playwrights synligheds-definition afgør ikke
  // om fladen er brugbar — det gør geometrien, og det måler påstandene
  // nedenfor. En composer der findes men er 0×0 skal FEJLE, ikke give timeout.
  try {
    await page.waitForSelector('.composer', { state: 'attached', timeout: 15000 })
  } catch (e) {
    const dom = await page.evaluate(() => ({
      tekst: (document.body.innerText || '').slice(0, 300),
      rootBoern: document.getElementById('root')?.children.length ?? -1,
      klasser: [...document.querySelectorAll('[class]')].map((n) => n.className).slice(0, 15),
    }))
    console.error('Composeren dukkede ikke op. DOM:', JSON.stringify(dom, null, 1))
    throw e
  }
  await page.waitForTimeout(800)

  const mal = await page.evaluate(() => {
    const q = (s) => document.querySelector(s)
    const rect = (el) => {
      if (!el) return null
      const r = el.getBoundingClientRect()
      return { top: r.top, bottom: r.bottom, left: r.left, right: r.right, width: r.width, height: r.height }
    }
    const doc = document.documentElement
    return {
      rootBoern: q('#root')?.children.length ?? -1,
      vh: window.innerHeight,
      vw: window.innerWidth,
      scrollBredde: doc.scrollWidth,
      tomSamtale: !!q('.chatview.empty'),
      composer: rect(q('.composer')),
      transcript: rect(q('.transcript-wrap') || q('.transcript')),
      modalTilbage: !!q('[role="dialog"]'),
    }
  })

  console.log('\nSyntest — Desk-fladen (1280×800)\n')

  paastand('fladen tegner (root har børn)', mal.rootBoern > 0, `rootBoern=${mal.rootBoern}`)
  paastand('composeren findes', !!mal.composer)

  if (mal.composer) {
    paastand(
      'composeren er inden for viewport',
      mal.composer.bottom <= mal.vh + 1 && mal.composer.top >= -1,
      `top=${Math.round(mal.composer.top)} bund=${Math.round(mal.composer.bottom)} vh=${mal.vh}`,
    )
    paastand(
      'composeren er ikke kollapset',
      mal.composer.width >= 300 && mal.composer.height >= 30,
      `${Math.round(mal.composer.width)}×${Math.round(mal.composer.height)}`,
    )
    if (mal.tomSamtale) {
      // Tom samtale er den tilstand Desk booter i. Composeren skal stå i den
      // ØVRE halvdel — bliver den skubbet ned, er det fordi et tomt
      // transcript-område har fået lov at fylde.
      paastand(
        'composeren er centreret i tom samtale',
        mal.composer.top < mal.vh * 0.6,
        `top=${Math.round(mal.composer.top)} vh=${mal.vh}`,
      )
    }
  }

  paastand(
    'dokumentet scroller ikke horisontalt',
    mal.scrollBredde <= mal.vw + 1,
    `scrollWidth=${mal.scrollBredde} vw=${mal.vw}`,
  )

  if (mal.composer && mal.transcript) {
    paastand(
      'composeren overlapper ikke transcriptet',
      mal.composer.top >= mal.transcript.bottom - 1,
      `composer.top=${Math.round(mal.composer.top)} transcript.bottom=${Math.round(mal.transcript.bottom)}`,
    )
  }

  if (havdeModal) {
    paastand('AI-disclaimeren kan lukkes', !mal.modalTilbage)
  }

  paastand('ingen uhåndterede side-fejl', pageFejl.length === 0, pageFejl[0])

  if (fejl.length) {
    await mkdir(SHOT_DIR, { recursive: true })
    const sti = join(SHOT_DIR, `fejl-${Date.now()}.png`)
    await page.screenshot({ path: sti })
    console.log(`\nScreenshot af fejlen: ${sti}`)
  }

  await browser.close()
  server.close()

  console.log(fejl.length ? `\n${fejl.length} påstand(e) fejlede.` : '\nAlle påstande holdt.')
  process.exit(fejl.length ? 1 : 0)
}

main().catch((e) => {
  console.error('Syntesten kunne ikke køre:', e.message)
  process.exit(2)
})
