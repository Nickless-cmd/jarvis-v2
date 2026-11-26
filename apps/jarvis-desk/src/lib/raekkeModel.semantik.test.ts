/**
 * BLOKKENS SEMANTIK KOMMER FRA SERVEREN — IKKE FRA DENS PLACERING.
 *
 * Bjørn 26/11-2026: «Adskil blokkens semantiske rolle fra dens visuelle
 * placering og livscyklus.»
 *
 * ## Fejlen der blev målt
 *
 * `projektion()` udledte fasen udelukkende af positionen efter sidste
 * `tool_use`. Det virkede så længe turen havde ét svar. Men kommer der en ny
 * runde EFTER slutsvaret, flytter `sidsteKald` sig — og et allerede vist
 * slutsvar tippede tilbage i arbejdet midt i turen, mens pacen rullede.
 *
 * Samme tekstblok. Ny fase. Ny visuel række. Det er præcis den
 * «dynamiske semantiske omklassificering» kravet forbyder, og den er målt:
 * det er den «blink/hik» Bjørn beskrev.
 *
 * ## Løsningen
 *
 * `block.phase` sættes af serveren (`sse_v2_events.py`: 'commentary' |
 * 'final_answer') og er autoritativ. Den læses FØRST. En blok der har fået
 * sin fase fra serveren kan ikke omklassificeres af en senere blok.
 *
 * Positionsreglen er bevaret som FALLBACK for blokke uden `phase` — ældre
 * persisterede ture og providers der ikke sender feltet.
 */
import { describe, expect, it } from 'vitest'
import { projektion } from './raekkeModel'
import type { ContentBlock } from './sseProtocol'

const tekst = (t: string, phase?: 'commentary' | 'final_answer'): ContentBlock =>
  (phase ? { type: 'text', text: t, phase } : { type: 'text', text: t })

const kald = (id: string): ContentBlock =>
  ({ type: 'tool_use', id, name: 'bash', input: {} })

/** Faselisten for tekstblokkene, i rækkefølge — så testen kan læse den. */
function tekstFaser(blocks: ContentBlock[], underArbejde = false): string[] {
  return projektion(blocks, underArbejde).elementer
    .filter((e) => e.slags === 'blok' && e.blok.type === 'text')
    .map((e) => e.fase)
}

describe('semantikken kommer fra serveren, ikke fra placeringen', () => {
  it('KERNEN: et slutsvar med phase=final_answer bliver ALDRIG arbejde — heller ikke når en ny runde kommer efter', () => {
    // Turen er: kald → slutsvar. Så ankommer en NY runde efter svaret.
    const foer: ContentBlock[] = [kald('t1'), tekst('Svaret', 'final_answer')]
    expect(tekstFaser(foer)).toEqual(['svar'])

    const efter: ContentBlock[] = [...foer, kald('t2')]
    // Uden den autoritative fase ville 'Svaret' tippe til 'arbejde' her,
    // fordi `sidsteKald` nu peger på t2. Det er den fejl der er rettet.
    expect(tekstFaser(efter)).toEqual(['svar'])
  })

  it('KERNEN: fase-skiftet sker på det SAMME blok-objekt — ikke en kopi', () => {
    // Det er forudsætningen for at React kan genbruge DOM-noden: ændrer
    // fasen sig, skal `blok`-referencen være identisk, ellers remountes noden.
    const svar = tekst('Svaret', 'final_answer')
    const blocks: ContentBlock[] = [kald('t1'), svar]
    const p = projektion(blocks)
    const element = p.elementer.find((e) => e.slags === 'blok' && e.blok.type === 'text')
    expect(element && element.slags === 'blok' && element.blok).toBe(svar)
  })

  it('phase=commentary er arbejde uanset hvor den står — også efter sidste kald', () => {
    // En kommentar skrevet EFTER et kald er stadig kommentar. Uden den
    // autoritative fase ville positionsreglen gøre den til slutsvar.
    const blocks: ContentBlock[] = [kald('t1'), tekst('Jeg tjekker det.', 'commentary')]
    expect(tekstFaser(blocks)).toEqual(['arbejde'])
  })

  it('phase vinder over `underArbejde` — feltet må ikke omklassificere et slutsvar', () => {
    // `underArbejde` betyder «der er kommet arbejde efter svaret». Det må
    // påvirke hvordan hovedet folder, men ALDRIG hvad en blok ER.
    const blocks: ContentBlock[] = [kald('t1'), tekst('Svaret', 'final_answer')]
    expect(tekstFaser(blocks, true)).toEqual(['svar'])
  })

  it('MODPRØVE: en blok UDEN phase følger stadig positionsreglen (bagudkompatibilitet)', () => {
    // Ældre persisterede ture har ingen `phase`. De må ikke ændre adfærd.
    const foer: ContentBlock[] = [kald('t1'), tekst('Svaret')]
    expect(tekstFaser(foer)).toEqual(['svar'])

    const efter: ContentBlock[] = [...foer, kald('t2')]
    // Uden fase ER positionen den eneste kilde — så her tipper den, og det
    // er den korrekte (omend uønskede) adfærd for gamle data.
    expect(tekstFaser(efter)).toEqual(['arbejde'])
  })

  it('MODPRØVE: en kald-fri tur uden phase er stadig rent svar', () => {
    expect(tekstFaser([tekst('Hej')])).toEqual(['svar'])
    expect(tekstFaser([tekst('Hej')], true)).toEqual(['svar'])
  })

  it('blandede blokke: hver tekst følger sin EGEN fase, ikke naboens', () => {
    const blocks: ContentBlock[] = [
      kald('t1'),
      tekst('Arbejder…', 'commentary'),
      kald('t2'),
      tekst('Svaret', 'final_answer'),
      kald('t3'),
      tekst('Mere arbejde', 'commentary'),
    ]
    expect(tekstFaser(blocks)).toEqual(['arbejde', 'svar', 'arbejde'])
  })
})
