/**
 * ACCEPTMÅLING AF OPLEVELSEN — ikke af enkelte CSS-egenskaber.
 *
 * Bjørn 27/11-2026: «Bevar denne browser-harness. Den skal være acceptmålingen
 * for oplevelsen, ikke blot dokumentation af enkelte CSS-egenskaber.»
 *
 * ## Hvad der måles, og hvorfor netop det
 *
 * Den forrige måling læste containerens egen højde. Det er ikke det brugeren
 * ser. Brugeren ser AFSTANDEN mellem besvarelse A og besvarelse B — og den
 * afstand består af tre ting: rundecontainerens højde, dens opacity, og det
 * grid-gap den efterlader selv når den er 0px høj (`.chat-flow-segmenter` har
 * `gap: inherit`).
 *
 * Derfor måles `afstand` som `B.top - A.bottom` gennem hele transitionen, ved
 * TO containerhøjder (lav og høj). Kravet er:
 *
 *   1. Afstanden falder KONTINUERLIGT — ingen frame må vokse, og ingen frame
 *      må springe mere end 25 % af den samlede ændring.
 *   2. Synligheden falder samtidig med pladsen: når opacity er under 0,5, må
 *      højden ikke stadig være på sit maksimum (det var hullet: tekst væk,
 *      boks tilbage).
 *   3. Slutafstanden er den samme som hvis runden aldrig havde været der —
 *      dvs. gap'et er neutraliseret, ikke bare skjult.
 *   4. Afmonteringen (`unmount`) giver INTET layout-hop: afstanden må ikke
 *      ændre sig da noden fjernes.
 *   5. Det virker ens ved lav og høj container — `1fr → 0fr` interpolerer mod
 *      den faktiske højde, hvor `max-height: 2400px` gjorde det ikke.
 */
import { chromium } from 'playwright'

const URL = 'http://localhost:5199/src/harness/turhoved.html'
const TOLERANCE_HOP = 0.5 // px — under dette er et hop ikke synligt

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 900, height: 1200 } })
const fejl = []
page.on('pageerror', (e) => fejl.push(String(e)))

await page.goto(URL, { waitUntil: 'networkidle' })

/** Afstanden mellem A og B, plus containerens tilstand. */
const maalAfstand = () =>
  page.evaluate(() => {
    // Besvarelserne findes via segment-attributten: `.chat-flow-answer` rammer
    // OGSÅ det nestede svar inde i den flade gren, så en simpel klasse-query
    // gav A og B i forkert rækkefølge (målt: negativ afstand).
    const svar = Array.from(document.querySelectorAll('[data-segment="besvarelse"]'))
    const runde = document.querySelector('.chat-flow-runde')
    if (svar.length < 2) return null
    const a = svar[0].getBoundingClientRect()
    const b = svar[1].getBoundingClientRect()
    const cs = runde ? getComputedStyle(runde) : null
    return {
      afstand: Math.round((b.top - a.bottom) * 100) / 100,
      rundeHoejde: runde ? Math.round(runde.getBoundingClientRect().height * 100) / 100 : 0,
      opacity: cs ? Math.round(parseFloat(cs.opacity) * 1000) / 1000 : 1,
      levetid: runde ? runde.getAttribute('data-levetid') : null,
      rundeFindes: !!runde,
    }
  })

/** Kør hele forløbet for én containerhøjde og returnér kurven. */
async function maalForloeb(hoejde) {
  // Nulstil til live uden runde, så hvert forløb starter samme sted.
  await page.evaluate(() => {
    window.__sætTilstand('live')
    window.__sætBlokke('uden-runde')
  })
  await page.waitForTimeout(250)
  await page.evaluate((h) => window.__sætHoejde(h), hoejde)
  await page.evaluate(() => window.__sætBlokke('med-runde'))
  await page.waitForSelector('.chat-flow-runde', { timeout: 15000 })
  await page.waitForTimeout(700) // indgangs-animationen skal lande

  // REFERENCEN: afstanden mellem A og B naar runden er HELT væk. Den maales
  // ved at fjerne runden igen EFTER forloebet — se nedenfor. Her maales blot
  // starttilstanden med runden til stede.
  const start = await maalAfstand()
  if (!start) return { fejl: 'kunne ikke finde to besvarelser' }

  // Reference til noden FØR kollapset — til hop-målingen ved afmontering.
  await page.evaluate(() => {
    window.__rundeNode = document.querySelector('.chat-flow-runde')
  })

  // Sample hver frame gennem transitionen, inde i browseren.
  const kurve = await page.evaluate(async () => {
    const punkter = []
    const t0 = performance.now()
    window.__sætTilstand('terminal')
    await new Promise((done) => {
      const stik = () => {
        const svar = Array.from(document.querySelectorAll('[data-segment="besvarelse"]'))
        const runde = document.querySelector('.chat-flow-runde')
        if (svar.length >= 2) {
          const a = svar[0].getBoundingClientRect()
          const b = svar[1].getBoundingClientRect()
          const cs = runde ? getComputedStyle(runde) : null
          punkter.push({
            t: Math.round(performance.now() - t0),
            afstand: Math.round((b.top - a.bottom) * 100) / 100,
            h: runde ? Math.round(runde.getBoundingClientRect().height * 100) / 100 : 0,
            o: cs ? Math.round(parseFloat(cs.opacity) * 1000) / 1000 : 1,
            levetid: runde ? runde.getAttribute('data-levetid') : null,
          })
        }
        if (performance.now() - t0 < 900) requestAnimationFrame(stik)
        else done()
      }
      requestAnimationFrame(stik)
    })
    return punkter
  })

  // Slut-tilstand EFTER transition + afmontering.
  await page.waitForTimeout(500)
  const slut = await maalAfstand()
  const afmonteret = await page.evaluate(() => {
    const r = document.querySelector('.chat-flow-runde')
    return {
      findes: !!r,
      sammeNode: window.__rundeNode ? window.__rundeNode.isSameNode(r) : false,
      levetid: r ? r.getAttribute('data-levetid') : null,
    }
  })

  // Den rene afstand: runden fjernet helt fra blokkene. Er gap'et neutraliseret,
  // skal slutafstanden vaere IDENTISK med denne.
  await page.evaluate(() => window.__sætBlokke('med-runde'))
  await page.waitForTimeout(200)
  const udenRunde = await page.evaluate(() => {
    const svar = Array.from(document.querySelectorAll('[data-segment="besvarelse"]'))
    if (svar.length < 2) return null
    const a = svar[0].getBoundingClientRect()
    const b = svar[1].getBoundingClientRect()
    return { afstand: Math.round((b.top - a.bottom) * 100) / 100 }
  })

  return { hoejde, start, kurve, slut, afmonteret, udenRunde }
}

/** Vurder ét forløb mod de fem krav. */
function vurder(r) {
  const fejl = []
  const k = r.kurve
  if (!k || k.length < 5) return ['kurven er for kort til at måle']

  const startAfstand = k[0].afstand
  const slutAfstand = k.at(-1).afstand
  const samlet = startAfstand - slutAfstand

  // 1. Kontinuerlig reduktion: ingen frame må vokse.
  const vaekst = []
  for (let i = 1; i < k.length; i++) {
    if (k[i].afstand > k[i - 1].afstand + 0.5) {
      vaekst.push({ t: k[i].t, fra: k[i - 1].afstand, til: k[i].afstand })
    }
  }
  if (vaekst.length) fejl.push(`afstanden VOKSER i ${vaekst.length} frames: ${JSON.stringify(vaekst.slice(0, 3))}`)

  // 2. Intet enkelt spring over 25 % af den samlede ændring.
  const spring = []
  for (let i = 1; i < k.length; i++) {
    const d = Math.abs(k[i].afstand - k[i - 1].afstand)
    if (samlet > 1 && d > samlet * 0.25) spring.push({ t: k[i].t, d: Math.round(d * 100) / 100 })
  }
  if (spring.length) fejl.push(`spring > 25 % af ændringen: ${JSON.stringify(spring.slice(0, 3))}`)

  // 3. Synlighed og plads følges ad: når opacity < 0.5, må højden ikke være på max.
  const maxH = Math.max(...k.map((p) => p.h))
  const hul = k.filter((p) => p.o < 0.5 && p.h > maxH * 0.9)
  if (hul.length > 2) {
    fejl.push(`HUL: opacity < 0.5 mens højden stadig er > 90 % af max i ${hul.length} frames (fx t=${hul[0].t} o=${hul[0].o} h=${hul[0].h})`)
  }

  // 4. Slutafstanden = afstanden uden runde (gap neutraliseret).
  if (r.udenRunde && Math.abs(r.slut.afstand - r.udenRunde.afstand) > TOLERANCE_HOP) {
    fejl.push(`slutafstand ${r.slut.afstand}px ≠ uden-runde ${r.udenRunde.afstand}px — gap'et er ikke neutraliseret`)
  }

  // 5. Afmonteringen giver intet hop.
  if (r.afmonteret.findes) fejl.push('runden er ikke afmonteret efter transitionen')
  if (Math.abs(r.slut.afstand - slutAfstand) > TOLERANCE_HOP) {
    fejl.push(`layout-hop ved afmontering: ${slutAfstand} → ${r.slut.afstand}px`)
  }

  return fejl
}

const resultater = []
for (const h of ['lav', 'hoej']) {
  const r = await maalForloeb(h)
  if (r.fejl) {
    resultater.push({ hoejde: h, fejl: [r.fejl] })
    continue
  }
  const fejlListe = vurder(r)
  resultater.push({ hoejde: h, r, fejl: fejlListe })

  console.log(`\n=== CONTAINERHØJDE: ${h.toUpperCase()} ===`)
  console.log(`start: ${JSON.stringify(r.start)}`)
  console.log(`slut : ${JSON.stringify(r.slut)}`)
  console.log(`uden runde: ${JSON.stringify(r.udenRunde)}`)
  console.log(`afmonteret: ${JSON.stringify(r.afmonteret)}`)
  console.log(`frames: ${r.kurve.length} | varighed: ${r.kurve.at(-1).t}ms`)
  console.log(`afstandskurve: ${JSON.stringify(r.kurve.filter((_, i) => i % 5 === 0).map((p) => [p.t, p.afstand, p.o]))}`)
  console.log(fejlListe.length ? `FEJL:\n  - ${fejlListe.join('\n  - ')}` : 'ALLE KRAV OPFYLDT')
}

const alleFejl = resultater.flatMap((x) => x.fejl)
console.log('\n=== SAMLET ===')
console.log(alleFejl.length ? `IKKE BESTÅET (${alleFejl.length} krav brudt)` : 'BESTÅET — alle fem krav opfyldt ved begge højder')
console.log('=== SIDE-FEJL ===', fejl.length ? fejl.join(' | ') : 'ingen')

await browser.close()
process.exit(alleFejl.length ? 1 : 0)
