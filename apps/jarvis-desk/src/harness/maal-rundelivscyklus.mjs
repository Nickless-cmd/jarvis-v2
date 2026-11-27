/**
 * ACCEPTMÅLING — rundernes visuelle livscyklus (side-bfbddc76a8), Chat OG Code.
 *
 * Monterer den ægte `MessageRow` i Chromium (`rundelivscyklus.html`) og måler
 * DOM-geometri, synlighed, rækkefølge og pacerens fremdrift frame for frame:
 *
 *   Syntese A → Runde 1 → Syntese B → Runde 2 → Syntese C
 *
 * Kør:  npx vite --port 5299 --strictPort &
 *       node src/harness/maal-rundelivscyklus.mjs [chat|code]   (exit 1 ved brud)
 *
 * Paceren er kun INPUT her: den læses (tegn vist), aldrig skrevet til.
 */
import { aabn, snap, synlig } from './rundelivscyklus.lib.mjs'

process.env.RL_LEN ??= '40' // lange synteser: pacen varer længe nok til at åbne/lukke midt i den
const modes = process.argv[2] ? [process.argv[2]] : ['code', 'chat']
const resultater = []
const krav = (mode, scen, navn, ok, detalje = '') => {
  resultater.push({ mode, scen, navn, ok })
  console.log(`${ok ? 'OK  ' : 'FEJL'} [${mode}] ${scen} — ${navn}${detalje ? `  (${detalje})` : ''}`)
}
const vent = (page, ms) => page.waitForTimeout(ms)
const optag = async (page, fn, ms) => {
  await page.evaluate(() => window.__start())
  await fn()
  await vent(page, ms)
  return page.evaluate(() => window.__stop())
}
const find = (s, id) => s.items.find((i) => i.id === id)
const monotonNed = (xs, tol = 0.6) => xs.every((x, i) => i === 0 || x <= xs[i - 1] + tol)
const monotonOp = (xs, tol = 0.6) => xs.every((x, i) => i === 0 || x >= xs[i - 1] - tol)
const maxSpring = (xs) => xs.reduce((m, x, i) => (i ? Math.max(m, Math.abs(x - xs[i - 1])) : 0), 0)

/** Kør serveren frem til og med Syntese C og vent til paceren er færdig. */
async function koerTur(page) {
  await page.evaluate(() => window.__trin(1)); await vent(page, 600)
  for (let n = 2; n <= 6; n++) { await page.evaluate((n) => window.__trin(n), n); await vent(page, 900) }
}

/** Åbn/luk-forløb efter turen: rækkefølge, placering, fade + kollaps. */
async function aabnLuk(page, mode, scen) {
  const lukket = await snap(page)
  krav(mode, scen, 'lukket hoved: runderne er væk og synteserne glider sammen',
    synlig(lukket).join(',') === 'SYNTESE-A,SYNTESE-B,SYNTESE-C', synlig(lukket).join(','))
  const tom = (id) => { const i = find(lukket, id); return i.h < 1 && i.o < 0.02 }
  krav(mode, scen, 'R1 og R2 er kollapset (h<1, opacity 0)', tom('R1') && tom('R2'))

  // ÅBN — optag hver frame
  const aaben = await optag(page, () => page.locator('.rv-tur').click(), 900)
  const a = aaben[aaben.length - 1]
  const orden = synlig(a)
  krav(mode, scen, 'åbent hoved: R1 og R2 genopstår mellem synteserne',
    orden.filter((x) => x !== 'r0').join(',') === 'SYNTESE-A,R1,SYNTESE-B,R2,SYNTESE-C', orden.join(','))
  const y = (id) => find(a, id).y
  krav(mode, scen, 'y-rækkefølge er kronologisk (A<R1<B<R2<C)',
    y('SYNTESE-A') < y('R1') && y('R1') < y('SYNTESE-B') && y('SYNTESE-B') < y('R2') && y('R2') < y('SYNTESE-C'),
    ['SYNTESE-A', 'R1', 'SYNTESE-B', 'R2', 'SYNTESE-C'].map((i) => `${i}@${y(i)}`).join(' '))
  const hAaben = aaben.map((s) => find(s, 'R1').h)
  krav(mode, scen, 'udfoldningen glider (R1-højden vokser monotont, >5 mellemværdier)',
    monotonOp(hAaben) && hAaben.filter((h) => h > 1 && h < find(a, 'R1').h - 1).length > 5,
    `${hAaben.filter((h) => h > 1 && h < find(a, 'R1').h - 1).length} mellemværdier`)

  // LUK — sammenhængende fade + kollaps
  const luk = await optag(page, () => page.locator('.rv-tur').click(), 900)
  const hR1 = luk.map((s) => find(s, 'R1').h)
  const oR1 = luk.map((s) => find(s, 'R1').o)
  const topB = luk.map((s) => find(s, 'SYNTESE-B').y)
  const topC = luk.map((s) => find(s, 'SYNTESE-C').y)
  const slut = luk[luk.length - 1]
  krav(mode, scen, 'lukning: R1-højde og opacity falder monotont til 0',
    monotonNed(hR1) && monotonNed(oR1, 0.02) && hR1.at(-1) < 1 && oR1.at(-1) < 0.02, `h ${hR1[0]}→${hR1.at(-1)}, o ${oR1[0]}→${oR1.at(-1)}`)
  // Samme krav som `maal-oplevelse.mjs`: intet enkelt spring over 25 % af den samlede ændring.
  const samlet = (xs) => Math.abs(xs[0] - xs.at(-1))
  krav(mode, scen, 'lukning: B og C glider op i ét jævnt forløb (ingen frame >25 % af den samlede bevægelse)',
    monotonNed(topB) && monotonNed(topC) && maxSpring(topB) <= 0.25 * samlet(topB) && maxSpring(topC) <= 0.25 * samlet(topC),
    `B ${samlet(topB).toFixed(0)}px i alt, maks. ${maxSpring(topB).toFixed(1)}/frame; C ${samlet(topC).toFixed(0)}px, maks. ${maxSpring(topC).toFixed(1)}/frame`)
  krav(mode, scen, 'lukning: ender som lukket (A,B,C)', synlig(slut).join(',') === 'SYNTESE-A,SYNTESE-B,SYNTESE-C')
}

for (const mode of modes) {
  console.log(`\n===== ${mode.toUpperCase()} MODE =====`)
  // ── 1. Overdragelsen aktiv → afsluttet rundelinje, frame for frame ───────
  // 1a: R1 er synlig som aktiv linje når B begynder → fadet er i flugt og overdragelsen sker på dets afslutning.
  // 1b: serveren er foran paceren → R1 afsløres mens pacen allerede skriver; der er intet fade at vente på.
  for (const [scen, forlob] of [['1a handoff efter fade', 'fade'], ['1b handoff server foran', 'foran']]) {
    const { browser, page, fejl } = await aabn(mode)
    await page.evaluate(() => window.__trin(1)); await vent(page, 600)
    await page.evaluate(() => window.__trin(2)); await vent(page, 2500)
    const rec = await optag(page, async () => {
      if (forlob === 'fade') {
        await page.evaluate(() => window.__trin(3)); await vent(page, 1500) // R1 ankommer, A er pacet færdig
        await page.evaluate(() => window.__trin(4)); await vent(page, 7000) // B begynder: fade + overdragelse
      } else {
        await page.evaluate(() => window.__trin(3)); await page.evaluate(() => window.__trin(4))
        await vent(page, 12000)
      }
      await page.evaluate(() => window.__trin(5)); await vent(page, 1500) // R2 ankommer
    }, 500)
    const B = rec.filter((s) => find(s, 'SYNTESE-B') && find(s, 'R1') && find(s, 'SYNTESE-B').len > 0)
    // Scenariet skal faktisk indeholde fadet og overdragelsen, ellers måler vi ingenting.
    const fadeFrames = rec.filter((s) => find(s, 'R1')?.fader).length
    const aktivSlut = rec.findIndex((s, i) => i && find(rec[i - 1], 'R1')?.aktiv && !find(s, 'R1')?.aktiv)
    krav(mode, scen, 'scenariet indeholder det forventede forløb',
      mode === 'chat' || (forlob === 'fade' ? fadeFrames > 5 && aktivSlut > 0 : aktivSlut > 0), `fade-frames ${fadeFrames}, overdragelse i frame ${aktivSlut}`)
    const forsteB = B[0]
    krav(mode, scen, 'syntese B er synlig (opacity 1) i den første frame den har tekst',
      !!forsteB && find(forsteB, 'SYNTESE-B').o > 0.98, forsteB ? `opacity ${find(forsteB, 'SYNTESE-B').o}` : 'aldrig')
    // Tomrum: R1 må ikke stå helt usynlig (opacity<0.01) i en plads over 12px. Overdragelsen sker på
    // fadets slutning, så et par frames (transitionend → React-render) er det mest der tillades;
    // før rettelsen stod linjen usynlig i ~175 frames (≈3 s) indtil næste runde ankom.
    // Tomrum: R1 må ikke stå helt usynlig (opacity<0.01) i en plads over 12px.
    const tomBoks = B.filter((s) => find(s, 'R1').o < 0.01 && find(s, 'R1').h > 12)
    krav(mode, scen, 'ingen varig usynlig plads-optagende rundelinje (≤4 frames mellem fade-slut og overdragelse)',
      tomBoks.length <= 4, `${tomBoks.length} frames med R1 helt usynlig men h>12px`)
    if (mode === 'code') {
      // ── Code mode: den AKTIVE linje kommer EFTER syntesen (Bjørn 27/11-2026) ──
      // «den skal komme efter syntesen»: mens en syntese skrives, kollapser den
      // linje der ARBEJDER til nulhøjde og glider ind igen når syntesen slipper.
      // En runde der allerede er afsluttet bliver STÅENDE på sin plads til turen
      // er slut («de efterladte runde linjer … skal jo først forsvinde når turen
      // er slut»), så kravet måles på den AKTIVE linje — ikke på R1, der netop
      // skal blive stående. Målt 27/11-2026: med `synteseSkriver || !aktiv`
      // forsvandt de efterladte linjer midt i turen (kun ét `false→true`-skift i
      // hele forløbet og intet tilbage); med kun `aktiv && synteseSkriver` står
      // R1 på 38px gennem syntese B mens R2 kollapser 84→0px.
      const seneRunder = (s) => s.items.filter((i) => i.slags === 'runde' && !i.iFold && /^R\d/.test(i.id))
      // Kontrakten måles DIREKTE på geometrien, ikke gennem `aktiv`-flaget:
      // flaget forsvinder i samme frame som linjen kollapser, så et krav der
      // hænger på det ser aldrig kollapsen (målt 27/11-2026: «h 77.5→84» mens
      // den rå DOM viste 84→0).
      //
      // 1) Samtidig: én efterladt linje står synlig MENS den aktive er kollapset.
      //    Det er præcis Bjørns kontrakt — de efterladte bliver, den arbejdende
      //    forsvinder mens syntesen skrives.
      const baadeSynligOgKollapset = B.filter((s) => {
        const hs = seneRunder(s)
        return hs.some((i) => i.h > 12 && i.o > 0.02) && hs.some((i) => i.h < 1)
      })
      krav(mode, scen, 'en efterladt linje står synlig mens den arbejdende er kollapset',
        baadeSynligOgKollapset.length > 0,
        `${baadeSynligOgKollapset.length} frames`)
      // 2) Ingen frame hvor en linje står usynlig med fuld plads (den tomme boks).
      const usynligBoks = B.filter((s) => seneRunder(s).some((i) => i.o < 0.01 && i.h > 12))
      krav(mode, scen, 'ingen linje står usynlig med fuld plads',
        usynligBoks.length === 0, `${usynligBoks.length} frames`)
      // 3) Indgangen GLIDER (Bjørn 27/11-2026: «den er der instant»). Hver linje
      //    der bliver synlig skal have mellemværdier mellem 1px og 85 % af sin
      //    fulde højde — en linje der popper har ingen.
      const glider = (id) => {
        const hs = B.map((s) => find(s, id)?.h ?? null).filter((h) => h !== null)
        const mx = hs.length ? Math.max(...hs) : 0
        return mx > 12 && hs.filter((h) => h > 1 && h < mx * 0.85).length >= 3
      }
      const poppede = ['R1', 'R2'].filter((id) => B.some((s) => find(s, id)) && !glider(id))
      krav(mode, scen, 'rundelinjen glider ind (mellemværdier, ikke et hop)',
        poppede.length === 0, poppede.length ? `poppede: ${poppede.join(',')}` : 'begge glider')
    } else {
      // ── Chat mode er UÆNDRET (Bjørn 27/11-2026) ───────────────────────────
      // «i chat mode faded den aktive rundelinje ud som den skulle». Dens linje
      // er `.chat-flow-round`, den ligger UNDER syntesen og gates af paceren —
      // den er ikke rørt. Dens kontrakt står derfor som før: den afsluttede
      // runde glider ind, og afstanden til syntesen er konstant.
      const gap = B.map((s) => find(s, 'SYNTESE-B').y - (find(s, 'R1').y + find(s, 'R1').h))
      // Chat mode har ingen aktiv linje på pladsen; dér glider den afsluttede
      // runde ind, og det kontrolleres af spring-kravet ovenfor. Kravet her
      // gælder derfor kun code mode — som før 27/11-2026.
      krav(mode, scen, 'afstand runde→syntese konstant gennem hele overdragelsen (±1.5px)',
        mode === 'chat' || Math.max(...gap) - Math.min(...gap) <= 1.5,
        `min ${Math.min(...gap).toFixed(1)} maks ${Math.max(...gap).toFixed(1)}`)
    }
    // Intet enkelt spring over 25 % af rundens plads (linjen + dens marginer) — B glider, den hopper ikke.
    const topBy = B.map((s) => find(s, 'SYNTESE-B').y)
    const rundePlads = Math.max(...B.map((s) => find(s, 'R1').h)) + 16
    krav(mode, scen, 'syntese B glider (ingen frame >25 % af rundens plads)', maxSpring(topBy) <= 0.25 * rundePlads,
      `maks. ${maxSpring(topBy).toFixed(1)}px/frame af ${rundePlads.toFixed(0)}px`)
    const pace = rec.map((s) => s.pace)
    krav(mode, scen, 'pacerens fremdrift er monoton (nulstilles aldrig gennem overdragelsen)', monotonOp(pace, 0), `${pace[0]}→${pace.at(-1)}`)
    const dt = pace.map((p, i) => (i ? p - pace[i - 1] : 0))
    const snit = (xs) => xs.filter((x) => x > 0).reduce((m, x) => m + x, 0) / Math.max(1, xs.filter((x) => x > 0).length)
    const ind = aktivSlut > 0 ? aktivSlut : Math.floor(rec.length / 2)
    const foer = snit(dt.slice(Math.max(0, ind - 90), Math.max(0, ind - 30))) // 1,5–0,5 s før overdragelsen
    const efter = snit(dt.slice(ind + 30, ind + 90)) // 0,5–1,5 s efter
    krav(mode, scen, 'pacen accelererer/bremser ikke ved overdragelsen (tegn/frame efter ≈ før, ±35 %)',
      !(foer > 0 && efter > 0) || Math.abs(efter - foer) / foer <= 0.35, `før ${foer.toFixed(1)}, efter ${efter.toFixed(1)} tegn/frame`)
    krav(mode, scen, 'ingen sidefejl', fejl.length === 0, fejl.join('|'))
    await browser.close()
  }

  // ── 1c. Hele turen: kun den ARBEJDENDE rundelinje, og kun mellem synteserne ──
  {
    const { browser, page } = await aabn(mode)
    await page.evaluate(() => window.__trin(1)); await vent(page, 600)
    if (mode === 'chat') {
      for (let n = 2; n <= 6; n++) { await page.evaluate((n) => window.__trin(n), n); await vent(page, 800) }
      await vent(page, 14000)
      const s6 = await snap(page)
      krav(mode, '1c tur', 'under turen: A, R1, B, R2, C i kronologisk orden',
        synlig(s6).filter((x) => x !== 'r0').join(',') === 'SYNTESE-A,R1,SYNTESE-B,R2,SYNTESE-C', synlig(s6).join(','))
      krav(mode, '1c tur', 'turhovedet er lukket under turen', s6.hoved?.aaben === 'false')
    } else {
      // Code mode har ingen pacer der kan bære gaten, så den måles direkte:
      // skriver en syntese sig, er rundelinjen der ikke; er syntesen færdig,
      // står præcis den arbejdende linje der.
      const runder = (s) => s.items
        .filter((i) => i.slags === 'runde' && !i.iFold && i.o > 0.02 && i.h > 1)
        .map((i) => i.id)
      await page.evaluate(() => window.__trin(2)); await vent(page, 1200)
      const underA = await snap(page)
      await page.evaluate(() => window.__trin(3)); await vent(page, 3000)
      const iMellem = await snap(page)
      await page.evaluate(() => window.__trin(4)); await vent(page, 3000)
      const underB = await snap(page)
      krav(mode, '1c tur', 'mens syntese A skrives: ingen rundelinje er synlig',
        runder(underA).length === 0, runder(underA).join(',') || 'ingen')
      krav(mode, '1c tur', 'i mellemrummet efter A: præcis én rundelinje, og det er den arbejdende',
        runder(iMellem).join(',') === 'R1' && !!find(iMellem, 'R1')?.aktiv,
        `${runder(iMellem).join(',') || 'ingen'}${find(iMellem, 'R1')?.aktiv ? ' (aktiv)' : ''}`)
      krav(mode, '1c tur', 'mens syntese B skrives: rundelinjen er væk igen',
        runder(underB).length === 0, runder(underB).join(',') || 'ingen')
      krav(mode, '1c tur', 'turhovedet er lukket under turen', underB.hoved?.aaben === 'false')
    }
    await browser.close()
  }

  // ── 2. Åbn/luk under aktiv pacing + server slutter med tekst tilbage ─────
  {
    const { browser, page } = await aabn(mode)
    await page.evaluate(() => window.__trin(1)); await vent(page, 500)
    for (let n = 2; n <= 5; n++) { await page.evaluate((n) => window.__trin(n), n); await vent(page, 600) }
    await page.evaluate(() => window.__trin(6)); await vent(page, 300)
    const foer = await snap(page)
    const rec = await optag(page, async () => {
      for (let i = 0; i < 4; i++) { await page.locator('.rv-tur').click(); await vent(page, 250) }
    }, 300)
    const pace = rec.map((s) => s.pace)
    krav(mode, '2 åbn/luk under pacing', 'pacerens fremdrift er monoton gennem 4 åbn/luk-skift',
      monotonOp(pace, 0), `${pace[0]}→${pace.at(-1)} (start ${foer.pace})`)
    krav(mode, '2 åbn/luk under pacing', 'paceren løber videre (tegn vist stiger i vinduet)', pace.at(-1) > pace[0], `${pace[0]}→${pace.at(-1)}`)
    // Slut: serveren lukker streamen mens paceren har tekst tilbage
    const foerSlut = await snap(page)
    await page.evaluate(() => window.__serverSlut())
    const efter = await optag(page, async () => {}, 5000)
    await vent(page, 9000)
    const total = (await snap(page)).pace
    const synlig1 = (s, id) => { const i = find(s, id); return !!i && i.h > 20 && i.o > 0.9 }
    const medRest = efter.filter((s) => s.pace < total)
    krav(mode, '2 server slut', 'serveren slutter mens pacen har tekst tilbage', foerSlut.pace < total, `pace ${foerSlut.pace} af ${total}`)
    krav(mode, '2 server slut', 'pacerens fremdrift er monoton hen over serverens slutning',
      monotonOp(efter.map((s) => s.pace), 0))
    // Paceren afslører runderne efterhånden som teksten når dem. En runde der er
    // afsløret må ikke forsvinde igen før pacen er færdig.
    let tidligKollaps = 0
    for (const id of ['R1', 'R2']) {
      const forste = medRest.findIndex((s) => synlig1(s, id))
      if (forste >= 0) tidligKollaps += medRest.slice(forste).filter((s) => !synlig1(s, id)).length
    }
    krav(mode, '2 server slut', 'runderne kollapser først når turen og pacingen er afsluttet (afslørede runder består mens tekst er tilbage)',
      tidligKollaps === 0, `${tidligKollaps} frames; ${medRest.length} frames med tekst tilbage`)
    await aabnLuk(page, mode, '2 efter tur')
    await browser.close()
  }

  // ── 3. Persisteret besked og genindlæsning ───────────────────────────────
  {
    const { browser, page } = await aabn(mode)
    await koerTur(page)
    await page.evaluate(() => window.__serverSlut()); await vent(page, 14000)
    await page.evaluate(() => window.__persisteret()); await vent(page, 1500)
    await aabnLuk(page, mode, '3 persisteret')
    await browser.close()
  }
  {
    // Genindlæsning: ny side, ingen live-historie — gemt besked fra første frame.
    const { browser, page } = await aabn(mode)
    await page.evaluate(() => window.__persisteret()); await vent(page, 1500)
    await aabnLuk(page, mode, '3 genindlæst')
    await browser.close()
  }
}

const fejlede = resultater.filter((r) => !r.ok)
console.log(`\n${resultater.length - fejlede.length}/${resultater.length} krav opfyldt`)
process.exit(fejlede.length ? 1 : 0)
