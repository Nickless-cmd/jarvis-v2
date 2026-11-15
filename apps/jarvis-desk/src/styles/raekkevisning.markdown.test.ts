import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

/**
 * MÅLT 14/11-2026: `tokens.css:298` nulstiller `* { margin: 0; padding: 0 }`.
 * `.jarvis-body p` giver chat mode luften tilbage, men rækkevisningen er sin
 * egen container — så code mode's svar og synteser fik nul margin og flød
 * sammen til én mur. Vagten her fæstner at luften findes, så den ikke kan
 * forsvinde tavst igen.
 *
 * Tallene er MÅLT i Chromium 14/11-2026 (Playwright, 14px tekst):
 *   foer:  p-afstand 9px   ul padding-left 0px   li bundmargin 2,8px
 *   efter: p-afstand 13px  ul padding-left 19,6px li bundmargin 5,6px
 * `padding-left` er ikke kosmetik: med `padding: 0` + `margin-left` hang
 * list-markøren uden for tekstboksen, og listen læste som løse linjer.
 */
const css = readFileSync(resolve(__dirname, 'raekkevisning.css'), 'utf8')

describe('markdown-struktur i rækkevisningen', () => {
  it('afsnit har bundmargin i både syntese og svar', () => {
    expect(css).toMatch(/\.raekkevisning \.rv-mellem p,[\s\S]*?margin: 0 0 0\.9em 0;/)
    // 15/11-2026: denne vagt krævede et KOMMA efter `.rv-svar p`, fordi reglen
    // dengang var sidste led i en gruppe sammen med `.rv-turTekst p`. Da den
    // døde `.rv-turTekst`-blok blev fjernet, blev `.rv-svar p` sidste led i en
    // kortere gruppe — og vagten faldt på FORMEN, ikke på adfærden, selv om
    // bundmarginen stod præcis hvor den skulle. Den måler nu at marginen står
    // på `.rv-svar p`, uanset om reglen står alene eller i en gruppe.
    expect(css).toMatch(/\.raekkevisning \.rv-svar p\b[^{}]*\{[^}]*margin: 0 0 0\.9em 0;/)
  })

  it('lister har indrykning i PADDING — ellers står punkterne uden for teksten', () => {
    expect(css).toMatch(/\.raekkevisning \.rv-mellem ul,[\s\S]*?padding-left: 1\.4em;/)
    // Den gamle form (`padding: 0` + `margin-left`) må ikke komme tilbage:
    // den måler `paddingLeft: 0px` i Chromium og efterlader prikkerne ude.
    expect(css).not.toMatch(/\.rv-mellem ul,[\s\S]{0,200}?padding: 0;/)
  })

  it('punkterne har luft til næste punkt', () => {
    expect(css).toMatch(/\.raekkevisning \.rv-mellem li,[\s\S]*?margin-bottom: 0\.4em;/)
  })

  it('overskrifter har luft over og under', () => {
    expect(css).toMatch(/margin: 0\.9em 0 0\.35em;/)
  })

  it('den globale nulstilling findes stadig — ellers er denne regel overflødig', () => {
    const tokens = readFileSync(resolve(__dirname, 'tokens.css'), 'utf8')
    expect(tokens).toMatch(/\*\s*\{[^}]*margin:\s*0/)
  })
})
