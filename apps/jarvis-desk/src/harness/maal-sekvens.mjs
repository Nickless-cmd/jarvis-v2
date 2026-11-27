/**
 * KØRER Bjørns seks trin i en rigtig browser og fotograferer hvert trin.
 *
 *   runde → syntese → fold → slutbesked → runde → syntese
 *
 * For hvert trin gemmes et skærmbillede OG en DOM-måling: hvilke rundelinjer
 * findes, hvor høje er de, står de inde i folden eller uden for, og står
 * syntesen det rigtige sted. Billedet viser hvad øjet ser; tallene viser hvorfor.
 *
 * Kør:  node src/harness/maal-sekvens.mjs
 */
import { chromium } from 'playwright'
import { mkdirSync, writeFileSync } from 'node:fs'

const URL = process.env.SEKVEN_URL ?? 'http://localhost:5199/src/harness/sekvens.html'
const UD = '/tmp/sekvens'
mkdirSync(UD, { recursive: true })

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 900, height: 1400 }, deviceScaleFactor: 2 })

page.on('console', (m) => {
  if (m.type() === 'error') console.log('  [browser-fejl]', m.text().slice(0, 300))
})
page.on('pageerror', (e) => console.log('  [side-fejl]', String(e).slice(0, 400)))

await page.goto(URL, { waitUntil: 'networkidle' })
await page.waitForSelector('.raekkevisning', { timeout: 15000 })

const antal = await page.evaluate(() => window.__antalTrin)
console.log(`TRIN: ${antal}\n`)

/** Hvad står der, hvor, og hvor højt. */
const maal = () =>
  page.evaluate(() => {
    const q = (s) => document.querySelector(s)
    const qa = (s) => Array.from(document.querySelectorAll(s))
    const h = (el) => (el ? Math.round(el.getBoundingClientRect().height) : null)
    const tekst = (el) => (el ? (el.textContent ?? '').replace(/\s+/g, ' ').trim() : '')

    const gruppeYdre = q('.rv-gruppe-ydre')
    const gruppe = q('.rv-gruppe')
    const svar = q('.rv-svar')

    // Er folden åben? `data-aaben` sættes på den ydre wrapper.
    const foldAaben = gruppeYdre?.getAttribute('data-aaben') === ''

    return {
      hoved: { findes: !!q('.rv-tur'), tekst: tekst(q('.rv-tur')).slice(0, 60), hoejde: h(q('.rv-tur')) },
      fold: { findes: !!gruppeYdre, aaben: foldAaben, hoejde: h(gruppeYdre), indreHoejde: h(gruppe) },
      rundelinjerInde: qa('.rv-gruppe .rv-arbejdsrunde').map((el) => ({
        tekst: tekst(el).slice(0, 70),
        hoejde: h(el),
        aktiv: el.hasAttribute('data-aktiv-runde'),
      })),
      rundelinjerUde: qa('.rv-svar .rv-arbejdsrunde').map((el) => ({
        tekst: tekst(el).slice(0, 70),
        hoejde: h(el),
        aktiv: el.hasAttribute('data-aktiv-runde'),
      })),
      bobbleSprogUde: {
        toolgroup: qa('.rv-svar .toolgroup').length,
        tankeLinje: qa('.rv-svar .tanke-linje').length,
        toolcard: qa('.rv-svar .toolcard').length,
      },
      svar: { findes: !!svar, tekst: tekst(svar).slice(0, 160), hoejde: h(svar) },
      // Den rå tekst, så man kan se om en syntese er havnet det forkerte sted.
      alt: tekst(q('.raekkevisning')).slice(0, 400),
    }
  })

const resultater = []
for (let i = 0; i < antal; i++) {
  await page.evaluate((n) => window.__sætTrin(n), i)
  // Fold-animationen er 260 ms; vi venter til den er faldet til ro.
  await page.waitForTimeout(700)

  const navn = await page.evaluate((n) => window.__trinNavn(n), i)
  const m = await maal()
  resultater.push({ trin: i + 1, navn, ...m })

  await page.screenshot({ path: `${UD}/trin-${i + 1}-${navn}.png`, fullPage: true })

  console.log(`── TRIN ${i + 1}: ${navn} ──`)
  console.log(`   hoved: ${m.hoved.findes ? `«${m.hoved.tekst}» ${m.hoved.hoejde}px` : 'findes IKKE'}`)
  console.log(`   fold:  ${m.fold.findes ? `${m.fold.aaben ? 'ÅBEN' : 'lukket'} ydre=${m.fold.hoejde}px indre=${m.fold.indreHoejde}px` : 'findes IKKE'}`)
  console.log(`   rundelinjer INDE i folden: ${m.rundelinjerInde.length}`)
  m.rundelinjerInde.forEach((r) => console.log(`      · ${r.hoejde}px ${r.aktiv ? '[AKTIV]' : ''} «${r.tekst}»`))
  console.log(`   rundelinjer UDEN FOR folden: ${m.rundelinjerUde.length}`)
  m.rundelinjerUde.forEach((r) => console.log(`      · ${r.hoejde}px ${r.aktiv ? '[AKTIV]' : ''} «${r.tekst}»`))
  const b = m.bobbleSprogUde
  console.log(`   bobble-sprog uden for: toolgroup=${b.toolgroup} tanke-linje=${b.tankeLinje} toolcard=${b.toolcard}`)
  console.log(`   svar: ${m.svar.hoejde}px «${m.svar.tekst.slice(0, 90)}»`)
  console.log('')
}

writeFileSync(`${UD}/resultat.json`, JSON.stringify(resultater, null, 2))
console.log(`Billeder og data: ${UD}`)
await browser.close()
