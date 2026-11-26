/**
 * Fotograferer måle-fladen trin for trin.
 *
 * Kører mod vite på 5174 og gemmer ét billede + én geometri-måling pr. trin,
 * så folden og runden efter slutbeskeden kan SES i stedet for gættes.
 */
import { chromium } from 'playwright'
import { mkdirSync, writeFileSync } from 'node:fs'

const UD = '/tmp/maaling'
mkdirSync(UD, { recursive: true })

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 900, height: 1000 }, deviceScaleFactor: 2 })

const fejl = []
page.on('console', (m) => { if (m.type() === 'error') fejl.push(m.text()) })
page.on('pageerror', (e) => fejl.push('pageerror: ' + e.message))

await page.goto('http://127.0.0.1:5174/maaling.html', { waitUntil: 'networkidle' })
await page.waitForFunction(() => typeof window.__maal === 'function', null, { timeout: 30000 })

const antal = await page.evaluate(() => window.__antalTrin)
const maalinger = []

for (let n = 0; n < antal; n++) {
  await page.evaluate((i) => window.__trin(i), n)
  // Folden kører 300/379 ms; vent til animationen er landet.
  await page.waitForTimeout(900)
  const m = await page.evaluate(() => window.__maal())
  maalinger.push(m)
  await page.screenshot({ path: `${UD}/trin-${n + 1}.png`, fullPage: true })
}

// Trin 5 (indeks 4) er foldet. Åbn hovedet og se om runderne står på deres plads.
await page.evaluate(() => window.__trin(5))
await page.waitForTimeout(900)
const hoved = page.locator('.rv-tur').first()
if (await hoved.count()) {
  await hoved.click()
  await page.waitForTimeout(900)
  const aabent = await page.evaluate(() => window.__maal())
  maalinger.push({ ...aabent, navn: '8 · hovedet åbnet manuelt (efter kaldet)' })
  await page.screenshot({ path: `${UD}/trin-8-aabent.png`, fullPage: true })
}

writeFileSync(`${UD}/maalinger.json`, JSON.stringify(maalinger, null, 2))
console.log(JSON.stringify({ fejl, maalinger }, null, 2))
await browser.close()
