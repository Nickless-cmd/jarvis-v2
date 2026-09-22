import { describe, it, expect } from 'vitest'
import { opdel, turHoved } from './raekkeModel'
import type { ContentBlock } from './sseProtocol'

/**
 * Opdelingen er hele rækkevisningen.
 *
 * Fejler den, ser man enten et svar der forsvinder ind bag en foldet gruppe,
 * eller en narrationslinje der bliver stående som om den var svaret. Begge
 * dele er tavse: der kastes intet, og alle blokke er der stadig.
 */

const tekst = (t: string): ContentBlock => ({ type: 'text', text: t })
const kald = (navn: string): ContentBlock => ({ type: 'tool_use', id: navn, name: navn, input: {} })
const tanke = (s: number): ContentBlock => ({ type: 'thinking', thinking: '…', seconds: s })

describe('opdel', () => {
  it('lægger tekst MELLEM to kald i arbejdet, ikke i svaret', () => {
    const { arbejde, svar } = opdel([
      kald('bash'),
      tekst('Den svarer 200. Nu henter jeg kataloget.'),
      kald('bash'),
      tekst('Færdig.'),
    ])
    expect(arbejde.map((e) => e.slags)).toEqual(['blok', 'mellemsvar', 'blok'])
    expect(arbejde[1]).toEqual({ slags: 'mellemsvar', tekst: 'Den svarer 200. Nu henter jeg kataloget.' })
    expect(svar).toEqual([tekst('Færdig.')])
  })

  it('bevarer rækkefølgen — en syntese skal stå mellem DE kald den stod imellem', () => {
    const { arbejde } = opdel([
      kald('search'), tekst('A'), kald('fetch'), tekst('B'), kald('read'),
    ])
    expect(arbejde.map((e) => (e.slags === 'mellemsvar' ? e.tekst : (e.blok as { name: string }).name)))
      .toEqual(['search', 'A', 'fetch', 'B', 'read'])
  })

  it('en besked UDEN kald er rent svar — intet tomt arbejdsområde', () => {
    // Faelden: havde reglen vaeret «sidste tekstblok er svaret», ville det
    // foerste afsnit her lande i en gruppe, og der ville staa
    // «Thought for 0s · 0 tool calls» over en almindelig replik.
    const { arbejde, svar, kald: n } = opdel([tekst('Første afsnit.'), tekst('Andet afsnit.')])
    expect(arbejde).toEqual([])
    expect(svar).toHaveLength(2)
    expect(n).toBe(0)
  })

  it('lader alt efter det sidste kald være svar — også flere afsnit', () => {
    const { svar } = opdel([kald('bash'), tekst('Et.'), tekst('To.')])
    expect(svar.map((b) => (b as { text: string }).text)).toEqual(['Et.', 'To.'])
  })

  it('springer tomme tekstblokke over — de opstår før første delta', () => {
    const { arbejde } = opdel([kald('bash'), tekst('   '), kald('bash')])
    expect(arbejde.filter((e) => e.slags === 'mellemsvar')).toEqual([])
  })

  it('tæller kald og lægger tænketiden sammen', () => {
    const o = opdel([tanke(12), kald('a'), tanke(9), kald('b'), tekst('svar')])
    expect(o.kald).toBe(2)
    expect(o.sekunder).toBe(21)
  })

  it('holder en afsluttende tanke i ARBEJDET — ikke i svaret', () => {
    // Skillelinjen gaelder TEKST. En tanke er arbejde uanset hvor den staar:
    // lagde vi den i svaret, ville raa tankestroem blive tegnet som replik,
    // med tænke-raekkens indhold spredt ud som brodtekst.
    const { arbejde, svar } = opdel([kald('a'), tanke(3)])
    expect(arbejde.map((e) => e.slags)).toEqual(['blok', 'blok'])
    expect(svar).toEqual([])
  })

  it('er tom for en tom besked', () => {
    expect(opdel([])).toEqual({ arbejde: [], svar: [], kald: 0, sekunder: 0 })
  })
})

describe('turHoved', () => {
  it('skriver sekunder, ikke «a while» (Bjørn 22/9-2026)', () => {
    expect(turHoved(9, 90)).toBe('Thought for 90s · 9 tool calls')
  })
  it('bøjer ental', () => {
    expect(turHoved(1, 7)).toBe('Thought for 7s · 1 tool call')
  })
  it('siger ikke «0s» når der ikke blev tænkt', () => {
    expect(turHoved(2, 0)).toBe('Worked · 2 tool calls')
  })
})
