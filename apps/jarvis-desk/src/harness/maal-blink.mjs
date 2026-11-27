/**
 * MÅLING 2: er faden jævn, og blinker besvarelsen når rendereren skifter?
 *
 * To spørgsmål, samme monterede komponent:
 *
 *  A. KURVEN — samples gennem transitionen. Et spring i højde eller opacity
 *     mellem to frames ER det hak brugeren ser, uanset hvad slutværdien er.
 *
 *  B. BLINKET — besvarelsens tekst-node holdes fast med `isSameNode` mens
 *     `fladtFlow` skifter fra falsk til sand (runden ankommer efter svaret).
 *     Overlever noden ikke, er det et remount, og remountet ER blinket.
 */
import { chromium } from 'playwright'

const URL = 'http://localhost:5199/src/harness/turhoved.html'
const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 900, height: 900 } })
const fejl = []
page.on('pageerror', (e) => fejl.push(String(e)))

await page.goto(URL, { waitUntil: 'networkidle' })
// Harnessen starter UDEN runde (blink-scenariet). Runden skal ind først,
// ellers er der ingen container at måle kollapset på.
await page.evaluate(() => window.__sætBlokke('med-runde'))
await page.waitForSelector('.chat-flow-runde', { timeout: 15000 })
await page.waitForTimeout(700)

// ── A. KURVEN ────────────────────────────────────────────────────────────
// Sample hver animationsframe gennem transitionen. Samplerne samles INDE i
// browseren, så der ikke går tid med rundture mellem hver måling.
const kurve = await page.evaluate(async () => {
  const r = document.querySelector('.chat-flow-runde')
  const punkter = []
  const t0 = performance.now()
  window.__sætTilstand('terminal')
  await new Promise((done) => {
    const stik = () => {
      const cs = getComputedStyle(r)
      punkter.push({
        t: Math.round(performance.now() - t0),
        h: Math.round(r.getBoundingClientRect().height * 100) / 100,
        o: Math.round(parseFloat(cs.opacity) * 1000) / 1000,
      })
      if (performance.now() - t0 < 700) requestAnimationFrame(stik)
      else done()
    }
    requestAnimationFrame(stik)
  })
  return punkter
})

const hak = []
for (let i = 1; i < kurve.length; i++) {
  const dh = Math.abs(kurve[i].h - kurve[i - 1].h)
  const do_ = Math.abs(kurve[i].o - kurve[i - 1].o)
  if (dh > 20 || do_ > 0.5) hak.push({ ...kurve[i], dh, do: do_ })
}

console.log('=== A. KURVEN GENNEM KOLLAPSET ===')
console.log('frames:', kurve.length, '| varighed:', kurve.at(-1).t, 'ms')
console.log('første:', JSON.stringify(kurve[0]), '| sidste:', JSON.stringify(kurve.at(-1)))
console.log('største spring mellem to frames:', JSON.stringify(
  kurve.reduce((v, p, i) => (i === 0 ? v : Math.abs(p.h - kurve[i - 1].h) > v ? Math.abs(p.h - kurve[i - 1].h) : v), 0),
))
console.log('hak (spring > 20px eller > 0.5 opacity):', hak.length ? JSON.stringify(hak.slice(0, 5)) : 'ingen')
console.log('midtpunkter:', JSON.stringify(kurve.filter((_, i) => i % 4 === 0).slice(0, 8)))

// ── B. BLINKET ───────────────────────────────────────────────────────────
await page.evaluate(() => window.__sætTilstand('live'))
await page.waitForTimeout(400)
await page.evaluate(() => window.__sætBlokke('uden-runde'))
await page.waitForTimeout(500)

const foerBlink = await page.evaluate(() => {
  const svar = document.querySelector('.chat-flow-answer')
  if (!svar) return null
  const tekst = svar.textContent || ''
  window.__svarNode = svar
  window.__tekstNode = svar.querySelector('p') || svar.firstElementChild
  window.__barnNode = svar.firstElementChild
  return {
    tekst: tekst.slice(0, 60),
    barn: window.__barnNode ? window.__barnNode.className || window.__barnNode.tagName : null,
    segmenter: !!document.querySelector('[data-segmenter="flat"]'),
  }
})

await page.evaluate(() => window.__sætBlokke('med-runde'))
await page.waitForTimeout(600)

const efterBlink = await page.evaluate(() => {
  const svar = document.querySelector('.chat-flow-answer')
  const barn = svar ? svar.firstElementChild : null
  return {
    svarSammeNode: window.__svarNode ? window.__svarNode.isSameNode(svar) : false,
    barnSammeNode: window.__barnNode && barn ? window.__barnNode.isSameNode(barn) : false,
    barn: barn ? barn.className || barn.tagName : null,
    segmenter: !!document.querySelector('[data-segmenter="flat"]'),
    tekst: svar ? (svar.textContent || '').slice(0, 60) : null,
  }
})

console.log('=== B. BLINKET VED RENDERER-SKIFTET ===')
console.log('før :', JSON.stringify(foerBlink))
console.log('efter:', JSON.stringify(efterBlink))
console.log('besvarelsen remountes?', foerBlink && efterBlink.barnSammeNode === false ? 'JA — det er blinket' : 'nej')
console.log('=== SIDE-FEJL ===', fejl.length ? fejl.join(' | ') : 'ingen')

await browser.close()
