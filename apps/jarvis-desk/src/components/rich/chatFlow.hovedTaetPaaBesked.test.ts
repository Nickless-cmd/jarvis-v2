/**
 * VAGT — turhovedet skal stå LIGE over beskeden, ikke svæve over den.
 *
 * Bjørn 14/11-2026: «turhoved skal stå lige over starten af beskeden» — med et
 * skærmbillede hvor der var et synligt gab mellem den lille grå linje og
 * brødteksten.
 *
 * MÅLT i Chromium 14/11-2026: gappet var 21,8px fra hovedtekst til besked.
 * Årsagen var ikke luft i hovedet, men et TOMT grid-item:
 * `chat-flow-gruppe-ydre` stod mellem hovedet og svaret med højde 0, og et
 * tomt item koster stadig to grid-gaps (10,4px hver) — ét over og ét under.
 * Efter rettelsen: 11,4px, altså ét enkelt gap, som er den samme afstand der
 * er mellem alle andre blokke i samtalen.
 *
 * Denne vagt er en KILDE-vagt, ikke en render-vagt: jsdom har ingen
 * layout-motor, så den kan ikke måle pixels. Den kan derimod bevise at den
 * regel der fjerner det tomme item findes, rammer den lukkede gruppe, og
 * IKKE rammer code mode (hvor `turhoved.css` er delt og stregen skal blive).
 */
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const kilde = (fil: string) =>
  readFileSync(resolve(__dirname, '../../styles', fil), 'utf8')

describe('VAGT — hovedet hænger sammen med beskeden', () => {
  it('giver den LUKKEDE gruppe nul plads — uden at fjerne den fra layoutet', () => {
    const css = kilde('chat-flow.css')
    // Den præcise selektor — ikke en delstreng der også matcher en mutation.
    expect(css).toContain(
      ".chat-flow > .chat-flow-gruppe-ydre[data-aaben='false']",
    )
    // 18/11-2026: nul-pladsen kommer fra `0fr` + nulstillet `padding-top` +
    // gap-kompensation på svaret — ikke fra `display: none`. `display: none`
    // blev målt og forkastet: den giver ganske vist nul plads, men et element
    // uden box har ingen før-tilstand, så ÅBNINGEN hoppede 10,4px (ét
    // grid-gap) før glidningen begyndte. Målt tre gange i Chromium.
    const blok = css.slice(
      css.indexOf(".chat-flow > .chat-flow-gruppe-ydre[data-aaben='false']"),
    )
    expect(blok.slice(0, 200)).toContain('grid-template-rows: 0fr')
    expect(blok.slice(0, 200)).not.toContain('display: none')
    // Uden `align-self: start` strækkes elementet som grid-item, og så bliver
    // den lukkede gruppe højere end nul (målt 16,78px).
    expect(css).toContain('align-self: start')
  })

  it('bruger ikke :empty — gruppen har altid et indre barn', () => {
    // MÅLT 14/11-2026: `:empty` ramte nul elementer, fordi gruppen altid
    // indeholder et `div`-barn. En regel der aldrig matcher er teater.
    const css = kilde('chat-flow.css')
    expect(css).not.toContain('.chat-flow-gruppe-ydre:empty')
  })

  it('sætter hovedets font eksplicit — inherit faldt tilbage til serif', () => {
    // MÅLT 14/11-2026: `font-family: inherit` gav "Times New Roman" ved 14px
    // fordi chatvisningen ikke altid ligger i den container der sætter fonten.
    const css = kilde('chat-flow.css')
    // Blokken udtrækkes fra selektoren til dens afsluttende `}` — ikke et
    // fast tegnvindue. MÅLT 14/11-2026: med `slice(0, 1200)` faldt
    // `font-size` ud af vinduet så snart kommentaren blev længere, og vagten
    // fejlede på sin egen formatering i stedet for på fonten.
    const start = css.indexOf('.chat-flow .rv-tur,')
    const blok = css.slice(start, css.indexOf('}', start))
    expect(blok).toContain('font-family: -apple-system')
    // Bjørn 14/11-2026: «lige som i code mode skal font være lige så stor som
    // runde linjens font størrelse». Vagten tjekker BEGGE sider — ellers
    // beviste den kun at der står et tal, ikke at det matcher.
    expect(blok).toContain('font-size: 14px')
    const raekke = readFileSync(resolve(__dirname, '../../styles/raekkevisning.css'), 'utf8')
    // Ankret på selektoren MED krølleparentes: uden den rammer `indexOf` en
    // senere variant (`.rv-arbejdsknap[data-koerer]`) og måler en anden blok.
    const rStart = raekke.indexOf('.raekkevisning .rv-arbejdsknap {')
    const arbejdsknap = raekke.slice(rStart, raekke.indexOf('}', rStart))
    expect(arbejdsknap).toContain('font-size: 14px')
  })

  it('rører IKKE code mode — turhoved.css er delt mellem de to flader', () => {
    // Reglen skal være scopet til `.chat-flow`. Uden scopet ville den også
    // ramme code mode, hvis typografi og luft ejes af `turhoved.css`.
    const css = kilde('chat-flow.css')
    const linjer = css.split('\n')
    const udenScope = linjer.filter(
      (l) =>
        l.includes('rv-tur') &&
        !l.includes('.chat-flow') &&
        !l.trim().startsWith('*') &&
        !l.trim().startsWith('/*'),
    )
    expect(udenScope).toEqual([])
  })

  it('det UDFOLDEDE hoved hænger også sammen med beskeden', () => {
    // Bjørn 15/11-2026: «kun gapet mellem det udfoldet hoved og besked
    // mangler». MÅLT i Chromium: 16px fra hoved til første arbejdsrække PLUS
    // gruppens 8px `padding-top` = 24px. To kilder til samme luft kan ikke
    // justeres hver for sig, så paddingen er 0 og marginen bærer hele
    // afstanden.
    // Derefter samme dag, anden runde: 8px var stadig for meget. Bjørn kaldte
    // de 2px ved det FOLDEDE hoved «perfekt», og hovedet er den samme label
    // hvad enten folden er åben eller lukket. MÅLT efter rettelsen: 2px fra
    // hoved til første arbejdsrække.
    const raekke = kilde('raekkevisning.css')

    const gStart = raekke.indexOf('.raekkevisning .rv-gruppe {')
    const gruppe = raekke.slice(gStart, raekke.indexOf('}', gStart))
    expect(gruppe).toContain('padding-top: 0')
    // Eksplicit margin: uden den arves 16px fra `.raekkevisning > * + *`.
    expect(gruppe).toContain('margin-top: 2px')

    const sStart = raekke.indexOf(
      '.raekkevisning .rv-tur ~ .rv-gruppe:not([hidden]) ~ .rv-svar:not(:empty)',
    )
    expect(sStart).toBeGreaterThan(-1)
    const svar = raekke.slice(sStart, raekke.indexOf('}', sStart))
    expect(svar).toContain('margin-top: 8px')
    expect(svar).not.toContain('var(--rv-enhed)')
  })

  it('ser hen over gruppe-elementet — `+` matcher aldrig i den ægte DOM', () => {
    // MÅLT 15/11-2026: begge flader brugte `+` (nabo) til at stramme
    // hoved→svar. Men `.rv-gruppe` / `.chat-flow-gruppe-ydre` ligger MELLEM
    // dem, så selektoren matchede nul elementer — også når gruppen er
    // `display: none`, fordi `+` ser på DOM'en og ikke på layoutet.
    // Resultatet var 28px i code mode og et helt grid-gap i chat mode, mens
    // reglen så ud som om den virkede. `~` ser hen over gruppen.
    const chat = kilde('chat-flow.css')
    expect(chat).toContain('.chat-flow > .rv-tur ~ .chat-flow-answer')
    expect(chat).not.toContain('.chat-flow > .rv-tur + .chat-flow-answer')

    const raekke = kilde('raekkevisning.css')
    expect(raekke).toContain('.raekkevisning .rv-tur ~ .rv-svar')
    expect(raekke).not.toContain(".raekkevisning .rv-tur[aria-expanded='false'] + .rv-svar")
  })

  it('kompensationen for det ekstra gap ligger på SVARET — og glider', () => {
    // MÅLT 18/11-2026 i Chromium, tre varianter, samme DOM:
    //   display: none + allow-discrete  → lukket -6,41px, HOP 10,39px i frame 0
    //   negativ margin på GRUPPEN       → lukket 14,39px uanset hvor meget den
    //                                     blev trukket op (rækken clampes til 0,
    //                                     så gap'et under den blev stående)
    //   negativ margin på SVARET        → lukket 3,98px, HOP 0px
    //
    // Den tredje er den der gælder. Uden denne test er det ikke bundet: fjerner
    // nogen reglen nedenfor, står den lukkede afstand på 14,39px igen — og
    // testen ovenfor ville stadig være grøn, fordi den kun ser på gruppen.
    const css = kilde('chat-flow.css')
    const selektor =
      ".chat-flow > .rv-tur ~ .chat-flow-gruppe-ydre[data-aaben='false'] ~ .chat-flow-answer"
    const start = css.indexOf(selektor)
    expect(start).toBeGreaterThan(-1)
    const blok = css.slice(start, css.indexOf('}', start))
    expect(blok).toContain('calc(-0.65rem - 6.4px)')

    // Og den skal transitionere, ellers hopper svaret når gruppen åbner.
    // Ankret på `{`, så `indexOf` ikke rammer den delte selektor ovenfor.
    const sStart = css.indexOf('.chat-flow > .rv-tur ~ .chat-flow-answer {')
    expect(sStart).toBeGreaterThan(-1)
    const svar = css.slice(sStart, css.indexOf('}', sStart))
    expect(svar).toContain('transition: margin-top')
  })
})
