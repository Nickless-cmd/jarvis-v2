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

// `--pace` måler INTEGRATIONEN (den ægte ChatFlowPresentation), ikke
// mekanismen. Se `src/maaling.tsx` for hvorfor de to ikke er det samme.
const KUN_PACE = process.argv.includes('--pace')

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 900, height: 1000 }, deviceScaleFactor: 2 })

const fejl = []
page.on('console', (m) => { if (m.type() === 'error') fejl.push(m.text()) })
page.on('pageerror', (e) => fejl.push('pageerror: ' + e.message))

await page.goto(
  KUN_PACE
    ? 'http://127.0.0.1:5174/maaling.html?flade=pace'
    : 'http://127.0.0.1:5174/maaling.html',
  { waitUntil: 'networkidle' },
)

// ── INTEGRATIONS-MÅLINGEN ─────────────────────────────────────────────────
//
// GPT 26/11-2026: «Han beviser dermed, at en isoleret pacer fortsætter, mens
// en anden komponent folder. Han beviser ikke, at den pacer, der faktisk
// leverer teksten til brugerens transskript, overlever foldet.»
//
// Her er der ingen probe ved siden af: fladen mounter den ÆGTE
// `ChatFlowPresentation`, og cursoren læses ud af DOM'en. Går den baglæns
// gennem et fold, blev svaret pacet forfra — og så er folden ikke irrelevant
// for pacen, uanset hvad mekanisme-proben siger.
if (KUN_PACE) {
  await page.waitForFunction(() => typeof window.__intMaal === 'function', null, { timeout: 30000 })

  const intPace = []
  const laesInt = async (navn) => {
    const m = await page.evaluate(() => window.__intMaal())
    intPace.push({ navn, ...m })
    return m
  }

  // GYLDIGHEDSKRAV: pacingen skal faktisk være i gang. Er teksten allerede
  // færdig, beviser en stabil cursor ingenting — der var intet at afbryde.
  await page.waitForFunction(
    () => {
      const m = window.__intMaal()
      return m.vistTegn > 0 && m.vistTegn < m.targetTegn
    },
    null,
    { timeout: 30000 },
  )
  const intStart = await laesInt('0 · pacing i gang (ægte ChatFlowPresentation)')

  for (let i = 1; i <= 3; i++) {
    const r = await page.evaluate(() => window.__intFold())
    await page.waitForTimeout(250)
    await laesInt(`${i} · efter fold-toggle ${i} (udfoldet=${r.udfoldet})`)
  }

  // Uden fold: beviser at cursoren ikke frøs efter sidste toggle.
  await page.waitForTimeout(700)
  await laesInt('4 · 700 ms efter sidste fold, ingen fold')

  // MODPRØVEN: skift turens identitet. Så skifter pacing-nøglen, cursoren skal
  // FALDE. Kan den ikke det, måler målingen ikke paceren.
  await page.evaluate(() => window.__intSkiftTur('maaling-tur-int-MODPROEVE'))
  await page.waitForTimeout(400)
  const efterSkift = await laesInt('MODPRØVE · tur-id skiftet')

  const underPacing = intPace.slice(0, 4)
  const monoton = underPacing.every((p, i, a) => i === 0 || p.vistTegn >= a[i - 1].vistTegn)
  const voksede = intPace[3].vistTegn > intPace[0].vistTegn
  const pacingVarAktiv = intStart.vistTegn > 0 && intStart.vistTegn < intStart.targetTegn
  const sidsteFoerSkift = intPace[intPace.length - 2]
  const modproeveVirkede =
    sidsteFoerSkift != null && efterSkift.vistTegn < sidsteFoerSkift.vistTegn
  const GYLDIG = pacingVarAktiv && monoton && voksede && modproeveVirkede

  writeFileSync(
    `${UD}/pace-integration.json`,
    JSON.stringify({ intPace, monoton, voksede, pacingVarAktiv, modproeveVirkede }, null, 2),
  )
  console.log(JSON.stringify({
    intPace,
    dom: {
      pacingVarAktiv,
      cursorMonotonGennemFold: monoton,
      voksedeEfterFold: voksede,
      modproeveVirkede,
      GYLDIG,
    },
    fejl,
  }, null, 2))
  await page.screenshot({ path: `${UD}/pace-integration.png`, fullPage: true })
  await browser.close()
  process.exit(0)
}

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
// MODPRØVEN SKAL MÅLE NULSTILLINGEN, IKKE NØGLESKIFTET (26/11-2026).
// Før stod der `efterNoegle.vistTegn < start.vistTegn || efterNoegle.key !==
// start.key`. Nøgleskiftet er noget MÅLINGEN selv gjorde med vilje — det kan
// derfor aldrig være bevis på at cursoren nulstilles. Og `start` er den FØRSTE
// måling (5 tegn), ikke den sidste før skiftet (39), så et fald fra 39 til 18
// bestod betingelsen uden at blive opdaget. Nu sammenlignes med værdien LIGE
// FØR skiftet, og nøglen indgår kun som information.
// `pace` indeholder nu OGSÅ `efterNoegle` — den blev pushet af `laesPace`
// ovenfor. Den sidste FØR skiftet er derfor `length - 2`, ikke `length - 1`.
const sidsteFoerSkift = pace[pace.length - 2]
const modproeveVirkede =
  sidsteFoerSkift != null && efterNoegle.vistTegn < sidsteFoerSkift.vistTegn

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
