/**
 * MÅLING: kollapser runde-containeren faktisk, når turen bliver terminal?
 *
 * Måler på den SAMME monterede komponent. Højde og opacity læses i en rigtig
 * Chromium-layout-motor, før og efter `data-levetid` skifter til `kollapset`,
 * og DOM-nodens identitet holdes fast med `isSameNode` for at bevise at der
 * ikke er sket et remount undervejs.
 */
import { chromium } from 'playwright'

const URL = 'http://localhost:5199/src/harness/turhoved.html'

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 900, height: 900 } })
const fejl = []
page.on('pageerror', (e) => fejl.push(String(e)))

await page.goto(URL, { waitUntil: 'networkidle' })
await page.waitForSelector('.chat-flow-runde', { timeout: 15000 })
await page.waitForTimeout(600) // lad indgangs-animationen lande

const maal = () =>
  page.evaluate(() => {
    const r = document.querySelector('.chat-flow-runde')
    if (!r) return null
    const cs = getComputedStyle(r)
    const rect = r.getBoundingClientRect()
    return {
      levetid: r.getAttribute('data-levetid'),
      hoejde: Math.round(rect.height * 100) / 100,
      maxHeight: cs.maxHeight,
      opacity: Math.round(parseFloat(cs.opacity) * 1000) / 1000,
      marginTop: cs.marginTop,
    }
  })

const foer = await maal()
if (!foer) {
  console.log('FEJL: ingen .chat-flow-runde fundet')
  await browser.close()
  process.exit(1)
}

// Fast reference til noden FØR tilstandsskiftet.
await page.evaluate(() => {
  ;(window).__node = document.querySelector('.chat-flow-runde')
})

await page.evaluate(() => (window).__sætTilstand('terminal'))
await page.waitForTimeout(900) // transitionen skal være færdig (--fold-varighed)

const efter = await maal()
const sammeNode = await page.evaluate(() =>
  (window).__node.isSameNode(document.querySelector('.chat-flow-runde')),
)

const pct = (a, b) => (a === 0 ? 0 : Math.round(((b - a) / a) * 1000) / 10)

console.log('=== FØR (live) ===')
console.log(JSON.stringify(foer))
console.log('=== EFTER (terminal) ===')
console.log(JSON.stringify(efter))
console.log('=== SAMME DOM-NODE? ===', sammeNode)
console.log('=== HØJDEÆNDRING ===', `${foer.hoejde} → ${efter.hoejde} px (${pct(foer.hoejde, efter.hoejde)} %)`)
console.log('=== OPACITYÆNDRING ===', `${foer.opacity} → ${efter.opacity}`)
console.log('=== SIDE-FEJL ===', fejl.length ? fejl.join(' | ') : 'ingen')

await browser.close()
