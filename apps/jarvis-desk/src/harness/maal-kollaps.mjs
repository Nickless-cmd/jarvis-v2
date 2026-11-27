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

// Fasen sættes FØR der ventes på containeren: harnessen starter i `uden`, som
// kun har besvarelser og derfor ingen `.chat-flow-runde`. Ventede man først,
// ville man vente for evigt — målt 27/11-2026.
await page.evaluate(() => window.__sætBlokke('med-runde'))
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

// `maal()` returnerer `null` når containeren er AFMONTERET — og det er nu det
// forventede udfald, ikke en fejl: fixet fjerner noden når dens egen
// `transitionend` har fyret (~300 ms), altså før de 900 ms er gået. Før
// antog målingen at noden stadig stod der, og kastede `TypeError` på `null`.
const efter = await maal()
const sammeNode = await page.evaluate(() =>
  (window).__node.isSameNode(document.querySelector('.chat-flow-runde')),
)

const pct = (a, b) => (a === 0 ? 0 : Math.round(((b - a) / a) * 1000) / 10)

console.log('=== FØR (live) ===')
console.log(JSON.stringify(foer))
console.log('=== EFTER (terminal) ===')
console.log(efter ? JSON.stringify(efter) : 'afmonteret (noden er væk — forventet)')
console.log('=== SAMME DOM-NODE? ===', sammeNode)
if (efter) {
  console.log('=== HØJDEÆNDRING ===', `${foer.hoejde} → ${efter.hoejde} px (${pct(foer.hoejde, efter.hoejde)} %)`)
  console.log('=== OPACITYÆNDRING ===', `${foer.opacity} → ${efter.opacity}`)
} else {
  console.log('=== HØJDEÆNDRING ===', `${foer.hoejde} → 0 px (afmonteret, 100 %)`)
}
console.log('=== SIDE-FEJL ===', fejl.length ? fejl.join(' | ') : 'ingen')

await browser.close()
