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
  it('fjerner den LUKKEDE gruppe fra grid-flowet', () => {
    const css = kilde('chat-flow.css')
    // Den præcise selektor — ikke en delstreng der også matcher en mutation.
    expect(css).toContain(
      ".chat-flow > .chat-flow-gruppe-ydre[data-aaben='false']",
    )
    // Og den skal faktisk fjerne den, ikke bare style den.
    const blok = css.slice(
      css.indexOf(".chat-flow > .chat-flow-gruppe-ydre[data-aaben='false']"),
    )
    expect(blok.slice(0, 200)).toContain('display: none')
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
    const blok = css.slice(css.indexOf('.chat-flow .rv-tur,'))
    expect(blok.slice(0, 1200)).toContain('font-family: -apple-system')
    expect(blok.slice(0, 1200)).toContain('font-size: 13px')
  })

  it('rører IKKE code mode — turhoved.css er delt mellem de to flader', () => {
    // Reglen skal være scopet til `.chat-flow`. Uden scopet ville den også
    // ramme code mode, hvor stregen og de 33px er turens eneste markør.
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
})
