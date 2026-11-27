/**
 * MÅLING: hvad sker der i det øjeblik den ekstra runde ANKOMMER?
 *
 * Bjørn 27/11-2026: «den extra runde efter slut beskeden vises ikk eller bliver
 * klippet … det virker som om hovede folder ind og ud … runderne uden for
 * turhoved bliver ikke vist».
 *
 * Forløbet er `[slutsvar]` → `[slutsvar, runde]`, altså den ÆGTE tilføjelse:
 * samme besvarelse, én runde mere. Første version af denne måling skiftede
 * mellem `uden` (to besvarelser) og `ekstra-runde` (én) — så svar-højden
 * ændrede sig af en anden grund end runden, og forskellen blev tilskrevet
 * runden. Det er den slags målefejl der giver et rigtigt tal og en forkert
 * konklusion.
 *
 * Tre ting måles: om runden er SYNLIG (hvor som helst), om strukturen skifter
 * (fold ↔ flad gren), og om besvarelsens DOM-node overlever (`isSameNode` —
 * attributter kan ikke se et remount).
 */
import { chromium } from 'playwright'

const URL = 'http://localhost:5199/src/harness/turhoved.html'
const browser = await chromium.launch()
const page = await browser.newPage()
const fejl = []
page.on('pageerror', (e) => fejl.push(String(e)))

await page.goto(URL, { waitUntil: 'networkidle' })

// Tilstanden lige efter slutsvaret er vist, mens pacen stadig kører.
await page.evaluate(() => window.__sætBlokke('kun-svar'))
await page.evaluate(() => window.__sætTilstand('live'))
await page.waitForTimeout(400)

await page.evaluate(() => {
  window.__svarNode = document.querySelector('.chat-flow-answer')
})

const snapshot = () =>
  page.evaluate(() => {
    const gruppe = document.querySelector('.chat-flow-gruppe-ydre')
    const indre = document.querySelector('.chat-flow-gruppe')
    const svar = document.querySelector('.chat-flow-answer')
    const runder = Array.from(document.querySelectorAll('.chat-flow-runde'))
    const hoejde = (el) => (el ? Math.round(el.getBoundingClientRect().height * 100) / 100 : null)
    return {
      gruppe: !!gruppe,
      gruppeAaben: gruppe ? gruppe.getAttribute('data-aaben') : null,
      gruppeHoejde: hoejde(gruppe),
      // Foldens indhold: findes runden som blokke derinde? Det er dér den
      // vises når den flade gren ikke har overtaget.
      gruppeTekst: indre ? (indre.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 60) : null,
      gruppeHarTrin: indre ? (indre.textContent || '').includes('trin 0') : false,
      flad: !!document.querySelector('.chat-flow-segmenter[data-segmenter="flat"]'),
      runder: runder.length,
      levetid: runder.map((r) => r.getAttribute('data-levetid')).join(','),
      rundeHoejde: runder.map(hoejde).join(','),
      svarSammeNode: svar ? (window.__svarNode ? svar.isSameNode(window.__svarNode) : 'ingen-ref') : 'intet-svar',
      svarHoejde: hoejde(svar),
      svarHarSvar: svar ? (svar.textContent || '').includes('Første besvarelse') : false,
    }
  })

console.log('=== FØR: slutsvar alene, pacen kører ===')
console.log(JSON.stringify(await snapshot(), null, 2))

// NU ANKOMMER DEN EKSTRA RUNDE.
await page.evaluate(() => window.__sætBlokke('ekstra-runde'))

const kurve = []
const start = Date.now()
for (let i = 0; i < 16; i += 1) {
  kurve.push({ t: Date.now() - start, ...(await snapshot()) })
  await page.waitForTimeout(45)
}

console.log('=== 2. RUNDEN ANKOMMER (turen kører stadig) ===')
for (const k of kurve) console.log(JSON.stringify(k))

// Nu slutter turen — her må den flade gren tage over, og runderne kollapse.
await page.evaluate(() => window.__sætTilstand('terminal'))

const slut = []
const t0 = Date.now()
for (let i = 0; i < 30; i += 1) {
  slut.push({ t: Date.now() - t0, ...(await snapshot()) })
  await page.waitForTimeout(45)
}

console.log('=== 3. TUREN SLUTTER ===')
for (const k of slut) console.log(JSON.stringify(k))

console.log('=== SIDE-FEJL ===', fejl.length ? fejl : 'ingen')
await browser.close()
