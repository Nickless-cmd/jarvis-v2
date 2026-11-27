/**
 * MÅLING: afmonteres HVER runde-container på sit eget transitionend?
 *
 * GPT, 27/11-2026: «Han bruger én fælles reference … tildeles samtlige
 * rundecontainere. Dermed kan referencen kun pege på én container ad gangen.
 * Når dens transition afsluttes, sættes den fælles `afmonteret`-tilstand, og
 * alle rundecontainere fjernes.»
 *
 * Denne måling kan afgøre om det er rigtigt. Den kræver to selvstændige
 * runde-containere, hvilket `to-runder`-fasen giver (`[runde, A, runde]`).
 *
 * Det der måles:
 *   1. Hvor mange `.chat-flow-runde` findes der før terminal-tilstanden?
 *   2. Hvilken node peger `kollapsRef` på — den første eller den sidste?
 *   3. Forsvinder de SAMTIDIGT (fælles boolean) eller hver for sig?
 *   4. Hvor lang tid tager det for hver af dem? En container hvis
 *      `transitionend` aldrig lyttes på falder tilbage på loftet (1200 ms).
 *
 * Køres med `npx vite --port 5199` og `node src/harness/maal-to-runder.mjs`.
 */
import { chromium } from 'playwright'

const URL = 'http://localhost:5199/src/harness/turhoved.html'

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 900, height: 900 } })
const fejl = []
page.on('pageerror', (e) => fejl.push(String(e)))

await page.goto(URL, { waitUntil: 'networkidle' })

// To runder, adskilt af en besvarelse. Sættes FØR der ventes på containeren:
// harnessen starter i `uden`-fasen, som kun har besvarelser og derfor ingen
// `.chat-flow-runde` — ventede man først, ville man vente for evigt.
await page.evaluate(() => window.__sætBlokke('to-runder'))
await page.waitForSelector('.chat-flow-runde', { timeout: 15000 })
await page.waitForTimeout(900) // lad indgangs-animationerne lande

const foer = await page.evaluate(() => {
  const noder = [...document.querySelectorAll('.chat-flow-runde')]
  // Fast reference til HVER node, så vi kan se om det er de samme der forsvinder.
  window.__noder = noder
  return {
    antal: noder.length,
    hoejder: noder.map((n) => Math.round(n.getBoundingClientRect().height * 100) / 100),
    levetider: noder.map((n) => n.getAttribute('data-levetid')),
    segmentIder: noder.map((n) => n.getAttribute('data-segment-id')),
  }
})

if (foer.antal < 2) {
  console.log('=== KAN IKKE MÅLE ===')
  console.log(`Kun ${foer.antal} runde-container(e) — fejlen kræver to.`)
  console.log(JSON.stringify(foer))
  await browser.close()
  process.exit(1)
}

// Tidsstempler for hver containers forsvinden, samplet hver frame.
//
// DE TO CONTAINERE SKAL IKKE KUNNE AFMONTERES SAMTIDIGT AF EN FÆLLES TILSTAND.
// Derfor tvinges de fra hinanden: den anden får en dobbelt så lang
// `--fold-varighed`. Er tilstanden fælles, forsvinder den første stadig efter
// ~300 ms og den anden efter ~600 — men de ville begge være væk når den
// HURTIGSTE var færdig. Er den per container, forsvinder de hver især på sit
// eget ur. Uden denne forskel kan målingen ikke skelne de to tilstande: to ens
// transitions i takt ser identiske ud med én fælles boolean.
await page.evaluate(() => {
  const noder = [...document.querySelectorAll('.chat-flow-runde')]
  if (noder[1]) noder[1].style.setProperty('--fold-varighed', '600ms')
})
await page.waitForTimeout(100)

const t0 = Date.now()
await page.evaluate(() => window.__sætTilstand('terminal'))

const forsvinden = await page.evaluate(async () => {
  const noder = window.__noder
  const start = performance.now()
  const tider = new Array(noder.length).fill(null)
  const vent = () => new Promise((r) => requestAnimationFrame(r))
  while (performance.now() - start < 2000) {
    for (let i = 0; i < noder.length; i += 1) {
      if (tider[i] === null && !noder[i].isConnected) {
        tider[i] = Math.round(performance.now() - start)
      }
    }
    if (tider.every((t) => t !== null)) break
    await vent()
  }
  return tider
})

const varighed = Date.now() - t0

console.log('=== FØR (live) ===')
console.log(JSON.stringify(foer, null, 2))
console.log('=== HVORNÅR FORSVANDT HVER CONTAINER (ms efter terminal) ===')
forsvinden.forEach((t, i) => {
  const dom = t === null ? 'FORTSAT TIL STEDE (hænger)' : `${t} ms`
  console.log(`  container ${i} (${foer.segmentIder[i]}): ${dom}`)
})
console.log('=== SAMLET MÅLEVINDUE ===', `${varighed} ms`)
console.log('=== SIDE-FEJL ===', fejl.length ? fejl.join(' | ') : 'ingen')

// Dommen: forsvandt de samtidigt, eller hver for sig?
const satte = forsvinden.filter((t) => t !== null)
const samtidig = satte.length === forsvinden.length && new Set(satte).size === 1
console.log('=== SAMTIDIG AFMONTERING? ===', samtidig ? 'JA (fælles tilstand)' : 'NEJ (per container)')

await browser.close()
