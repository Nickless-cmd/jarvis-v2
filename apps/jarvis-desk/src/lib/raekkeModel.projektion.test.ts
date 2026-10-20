/**
 * MÅLING: giver fase-projektionen samme svar som `opdel` — og holder den
 * blokken på sin plads?
 *
 * ## Hvorfor (19/10-2026)
 *
 * `opdel` returnerer to arrays, og grænsen mellem dem er indekset for det
 * SIDSTE `tool_use`. Den flytter sig derfor når et nyt kald lander — en
 * syntese kan vandre frem OG tilbage mellem arbejde og svar.
 *
 * `projektion` skal give PRÆCIS samme fordeling (ellers ændrer vi hvad der
 * vises), men som én liste hvor rækkefølgen er blokkens egen. Det er den
 * egenskab der gør at rendereren kan lade blokken blive i én container.
 *
 * ## Den anden halvdel — og den er den vigtige
 *
 * En stabil container er ikke nok. Elementet skal også være den SAMME TYPE
 * og den SAMME blok-reference før og efter grænsen, ellers ser React to
 * forskellige komponenter og bygger en ny node uanset hvad containeren gør.
 *
 * Første udgave kopierede arbejdsteksten ud i `{ slags: 'mellemsvar' }`, så
 * fase-skiftet blev et type-skift. Målt 19/10-2026 er det nu en `blok` hele
 * turen — derfor kan testen nedenfor kræve `toBe()` på blok-objektet.
 */
import { describe, it, expect } from 'vitest'
import { opdel, projektion } from './raekkeModel'
import type { ContentBlock } from './sseProtocol'

const tekst = (t: string): ContentBlock => ({ type: 'text', text: t })
const kald = (navn: string): ContentBlock => ({ type: 'tool_use', id: navn, name: navn, input: {} })
const tanke = (s: number): ContentBlock => ({ type: 'thinking', thinking: '…', seconds: s })
const p = (m: string): ContentBlock => ({ type: 'progress', tool_use_id: 't', parent_tool_use_id: null, tool: 'bash', message: m, status: 'running' })
const billede: ContentBlock = { type: 'image', src: 'x' }

/** De samme blokke, kørt gennem begge projektioner. */
function begge(blocks: ContentBlock[], underArbejde = false) {
  return { gammel: opdel(blocks, underArbejde), ny: projektion(blocks, underArbejde) }
}

/**
 * `opdel` kalder en arbejdstekst for `mellemsvar`; projektionen lader den
 * være den `blok` den er. Til sammenligning af FORDELING foldes de to navne
 * derfor sammen — det er fordelingen der er kontrakten, ikke etiketten.
 */
const somFordeling = (slags: string) => (slags === 'mellemsvar' ? 'blok' : slags)

describe('projektion — samme fordeling som opdel', () => {
  it('giver samme arbejde/svar-fordeling på alle kerneformer', () => {
    const former: ContentBlock[][] = [
      [],
      [tekst('Første afsnit.'), tekst('Andet afsnit.')],
      [kald('bash'), tekst('Et.'), tekst('To.')],
      [kald('bash'), tekst('   '), kald('bash')],
      [kald('bash'), tekst('Den svarer 200. Nu henter jeg kataloget.'), kald('bash'), tekst('Færdig.')],
      [kald('search'), tekst('A'), kald('fetch'), tekst('B'), kald('read')],
      [tanke(12), kald('a'), tanke(9), kald('b'), tekst('svar')],
      [kald('a'), tanke(3)],
      [kald('publish_file'), billede, kald('bash'), tekst('Klar.')],
      [kald('done'), billede, tekst('senere')],
      [kald('a'), p('et'), p('to'), p('tre'), tekst('svar')],
      [kald('a'), p('et'), kald('b'), p('to'), tekst('svar')],
    ]
    for (const blocks of former) {
      for (const underArbejde of [false, true]) {
        const { gammel, ny } = begge(blocks, underArbejde)
        // Arbejdsdelen: samme slags-rækkefølge (mellemsvar ≡ blok).
        expect(ny.elementer.filter((e) => e.fase === 'arbejde').map((e) => somFordeling(e.slags)))
          .toEqual(gammel.arbejde.map((e) => somFordeling(e.slags)))
        // Svardelen: samme blokke i samme rækkefølge.
        expect(ny.elementer.filter((e) => e.fase === 'svar').map((e) => e.slags === 'blok' ? e.blok : e.slags))
          .toEqual(gammel.svar)
        // Tællingerne til turens hoved.
        expect(ny.kald).toBe(gammel.kald)
        expect(ny.sekunder).toBe(gammel.sekunder)
        expect(ny.harArbejde).toBe(gammel.arbejde.length > 0)
      }
    }
  })

  it('bevarer blokkenes oprindelige rækkefølge — intet flyttes', () => {
    const blocks = [kald('search'), tekst('A'), kald('fetch'), tekst('B'), kald('read'), tekst('Svar.')]
    const { ny } = begge(blocks)
    const raekkefoelge = ny.elementer.map((e) => {
      if (e.slags === 'spor') return 'spor'
      return (e.blok as { name?: string; text?: string }).name ?? (e.blok as { text?: string }).text
    })
    expect(raekkefoelge).toEqual(['search', 'A', 'fetch', 'B', 'read', 'Svar.'])
  })
})

describe('projektion — grænsen flytter sig, men blokken gør ikke', () => {
  it('MAALER: en syntese vandrer i opdel, men staar stille i projektionen', () => {
    // Kald 1, syntese, så kald 2. Mens turen kører (underArbejde=true) er
    // syntesen et mellemsvar. Når kald 2 lander, rykker sidsteKald frem.
    const foer = [kald('bash'), tekst('Jeg fandt den.')]
    const efter = [kald('bash'), tekst('Jeg fandt den.'), kald('bash')]

    const gammelFoer = opdel(foer, true)
    const gammelEfter = opdel(efter, true)
    const nyFoer = projektion(foer, true)
    const nyEfter = projektion(efter, true)

    // Gammel vej: teksten ligger i arbejdet begge gange — men dens POSITION
    // i arbejdslisten er ny, fordi et nyt element kom efter den.
    expect(gammelFoer.arbejde.map((e) => e.slags)).toEqual(['blok', 'mellemsvar'])
    expect(gammelEfter.arbejde.map((e) => e.slags)).toEqual(['blok', 'mellemsvar', 'blok'])

    // Ny vej: teksten er det SAMME element paa den SAMME plads (indeks 1).
    const tekstFoer = nyFoer.elementer.findIndex((e) => e.slags === 'blok' && e.blok.type === 'text')
    const tekstEfter = nyEfter.elementer.findIndex((e) => e.slags === 'blok' && e.blok.type === 'text')
    expect(tekstFoer).toBe(1)
    expect(tekstEfter).toBe(1)
    expect(nyFoer.elementer[1]?.fase).toBe('arbejde')
    expect(nyEfter.elementer[1]?.fase).toBe('arbejde')
  })

  it('MAALER: naar graensen falder, skifter KUN fasen — blokken er det SAMME objekt', () => {
    const svar = tekst('Det er svaret.')
    const blocks = [kald('bash'), svar]
    const under = projektion(blocks, true)
    const efter = projektion(blocks, false)

    // Samme element, samme plads, samme type.
    expect(under.elementer).toHaveLength(2)
    expect(efter.elementer).toHaveLength(2)
    expect(under.elementer[1]?.slags).toBe('blok')
    expect(efter.elementer[1]?.slags).toBe('blok')
    expect(under.elementer[1]?.fase).toBe('arbejde')
    expect(efter.elementer[1]?.fase).toBe('svar')

    // DET AFGØRENDE: ikke en kopi — samme objekt-reference. Uden dette ville
    // rendereren se en ny blok og bygge en ny DOM-node, uanset containeren.
    const underBlok = under.elementer[1]?.slags === 'blok' ? under.elementer[1].blok : null
    const efterBlok = efter.elementer[1]?.slags === 'blok' ? efter.elementer[1].blok : null
    expect(underBlok).toBe(svar)
    expect(efterBlok).toBe(svar)
  })

  it('en besked uden kald er rent svar — intet tomt arbejdsomraade', () => {
    const { ny } = begge([tekst('Første afsnit.'), tekst('Andet afsnit.')])
    expect(ny.harArbejde).toBe(false)
    expect(ny.elementer.every((e) => e.fase === 'svar')).toBe(true)
    expect(ny.kald).toBe(0)
  })

  it('leverancen loeftes ud af arbejdet — ogsaa i den flade liste', () => {
    const { ny } = begge([kald('publish_file'), billede, kald('bash'), tekst('Klar.')])
    const billedIndeks = ny.elementer.findIndex((e) => e.slags === 'blok' && e.blok.type === 'image')
    expect(billedIndeks).toBeGreaterThan(-1)
    expect(ny.elementer[billedIndeks]?.fase).toBe('svar')
  })

  it('et spor hoerer ALTID til arbejdet — ogsaa efter sidste kald', () => {
    // Maalt 19/10-2026: `opdel`s progress-gren har ingen fase-betingelse, saa
    // et spor efter sidste kald ligger i arbejdet. Projektionen foelger den
    // regel, ellers ville de to fordele forskelligt.
    const { ny } = begge([kald('a'), p('et'), p('to'), kald('b'), p('tre')])
    const spor = ny.elementer.filter((e) => e.slags === 'spor')
    expect(spor).toHaveLength(2)
    expect(spor.every((e) => e.fase === 'arbejde')).toBe(true)
    expect(spor[0]?.slags === 'spor' && spor[0].trin).toHaveLength(2)
  })
})
