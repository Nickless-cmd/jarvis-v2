/**
 * MÅLING: hvad sker der i det øjeblik den ekstra runde ANKOMMER?
 *
 * Bjørn 27/11-2026: «den extra runde efter slut beskeden vises ikk eller bliver
 * klippet … det virker som om hovede folder ind og ud … runderne uden for
 * turhoved bliver ikke vist».
 *
 * ## Hvad der måles nu
 *
 * Målingen blev skrevet til den GAMLE binære gren (`fladtFlow`), som er
 * AFLYST. Den gren valgte mellem to indre strukturer under `.chat-flow-answer`,
 * og målingen sporede derfor `flad: true/false` som om det var fysik. Det er
 * den kobling der nu er væk, så en måling af den ville måle noget der ikke
 * findes.
 *
 * Den nye struktur har TRE uafhængige containere, og målingen kræver:
 *
 *   1. Besvarelsens node overlever (`isSameNode`) — både `.chat-flow-answer`
 *      og dens DIREKTE BARN. Det sidste er det afgørende: den gamle gren
 *      gjorde den ydre node stabil mens barnet skiftede, og så remountede
 *      besvarelsen alligevel.
 *   2. Hale-containeren `[data-runder-efter]` findes og står EFTER
 *      besvarelsen i DOM-rækkefølgen (`compareDocumentPosition`).
 *   3. Folden viser IKKE rundens blokke — dobbelt ejerskab er den fejl
 *      KONTRAKT 1b værner mod, nu målt som forekomster af indhold.
 *   4. Runden glider ind i højde frem for at poppe.
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
  const svar = document.querySelector('.chat-flow-answer')
  window.__svarNode = svar
  window.__svarBarn = svar ? svar.firstElementChild : null
})

const snapshot = () =>
  page.evaluate(() => {
    const gruppe = document.querySelector('.chat-flow-gruppe-ydre')
    const indre = document.querySelector('.chat-flow-gruppe')
    const svar = document.querySelector('.chat-flow-answer')
    const hale = document.querySelector('[data-runder-efter]')
    const runder = Array.from(document.querySelectorAll('[data-runder-efter] .chat-flow-runde'))
    const hoejde = (el) => (el ? Math.round(el.getBoundingClientRect().height * 100) / 100 : null)
    // DOM-rækkefølgen: er hale-containeren EFTER besvarelsen? `~`- og
    // `+`-reglerne i CSS afhænger af det, og en tilfældig ombytning ville
    // gøre hele strukturen forkert uden at nogen attribut viste det.
    const efterSvar = svar && hale
      ? (svar.compareDocumentPosition(hale) & Node.DOCUMENT_POSITION_FOLLOWING) !== 0
      : null
    return {
      gruppe: !!gruppe,
      gruppeAaben: gruppe ? gruppe.getAttribute('data-aaben') : null,
      gruppeHoejde: hoejde(gruppe),
      // DOBBELT EJERSKAB: står rundens kald OGSÅ i folden?
      gruppeHarTrin: indre ? (indre.textContent || '').includes('trin 0') : false,
      hale: !!hale,
      haleEfterSvar: efterSvar,
      haleHoejde: hoejde(hale),
      runder: runder.length,
      levetid: runder.map((r) => r.getAttribute('data-levetid')).join(','),
      rundeHoejde: runder.map(hoejde).join(','),
      // DE TO AFGØRENDE MÅL: overlever noden — og dens direkte barn?
      svarSammeNode: svar ? (window.__svarNode ? svar.isSameNode(window.__svarNode) : 'ingen-ref') : 'intet-svar',
      svarBarnSammeNode: svar
        ? (window.__svarBarn ? svar.firstElementChild?.isSameNode(window.__svarBarn) ?? 'intet-barn' : 'ingen-ref')
        : 'intet-svar',
      svarHoejde: hoejde(svar),
      svarHarSvar: svar ? (svar.textContent || '').includes('Første besvarelse') : false,
    }
  })

console.log('=== FØR: slutsvar alene, pacen kører ===')
console.log(JSON.stringify(await snapshot(), null, 2))

// NU ANKOMMER DEN EKSTRA RUNDE — EFTER slutsvaret.
await page.evaluate(() => window.__sætBlokke('ekstra-runde'))

const kurve = []
const start = Date.now()
for (let i = 0; i < 16; i += 1) {
  kurve.push({ t: Date.now() - start, ...(await snapshot()) })
  await page.waitForTimeout(45)
}

console.log('=== 2. RUNDEN ANKOMMER (turen kører stadig) ===')
for (const k of kurve) console.log(JSON.stringify(k))

// Nu slutter turen — her må runden kollapse og til sidst afmonteres.
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
