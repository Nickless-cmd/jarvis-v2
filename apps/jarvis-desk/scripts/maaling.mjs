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

// ── PACE-PROBEN ────────────────────────────────────────────────────────────
//
// Bjørn 26/11-2026: «fraværet af direkte pace-operationer ved fold-toggle
// beviser ikke, at pacen er upåvirket.» Her måles det: cursoren skal vokse
// MONOTONT gennem hvert fold, og nøglen skal stå stille. Går vistTegn
// baglæns, er svaret pacet forfra — det er den fejl der er rettet.
const pace = []
const laesPace = async (navn) => {
  const m = await page.evaluate(() => window.__pace())
  pace.push({ navn, ...m })
  return m
}

await page.evaluate(() => window.__trin(5))
await page.waitForTimeout(300)

// Start pacingen FORFRA, så der faktisk er noget at afbryde. Uden dette er
// teksten færdig når vi måler, og en stabil nøgle beviser ingenting.
await page.evaluate(() => window.__startPace())
await page.waitForTimeout(120)
const start = await laesPace('0 · pacing i gang')

for (let i = 1; i <= 3; i++) {
  const h = page.locator('.rv-tur').first()
  if (await h.count()) {
    await h.click()
    await page.waitForTimeout(120)
    await laesPace(`${i} · efter fold-toggle ${i}`)
  }
}

// MODPRØVEN: skift nøglen med vilje. Cursoren SKAL nulstilles — ellers måler
// proben intet, og så er den grønne konklusion værdiløs.
await page.evaluate(() => window.__skiftNoegle(true))
await page.waitForTimeout(300)
const efterNoegle = await laesPace('MODPRØVE · nøglen skiftet')

const underPacing = pace.slice(0, 4)
const noegler = new Set(underPacing.map((p) => p.key))
const monoton = underPacing.every((p, i, a) => i === 0 || p.vistTegn >= a[i - 1].vistTegn)
// GYLDIGHEDSKRAV: målingen tæller kun hvis pacingen faktisk VAR i gang — altså
// at der blev vist mindre end hele teksten ved start.
const pacingVarAktiv = start.vistTegn < start.targetTegn
const modproeveVirkede = efterNoegle.vistTegn < start.vistTegn || efterNoegle.key !== start.key

writeFileSync(`${UD}/pace.json`, JSON.stringify({ pace, noegler: [...noegler], monoton, pacingVarAktiv, modproeveVirkede }, null, 2))
console.log(JSON.stringify({
  pace,
  dom: {
    pacingVarAktiv,
    noeglerStabileGennemFold: noegler.size === 1,
    cursorMonoton: monoton,
    modproeveVirkede,
    GYLDIG: pacingVarAktiv && noegler.size === 1 && monoton && modproeveVirkede,
  },
}, null, 2))

await browser.close()
