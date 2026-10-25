import { describe, expect, it } from 'vitest'
import { fallbackTokens } from './kodeFallback'

/**
 * Fallback-farvning til kodeblokke uden (eller med ukendt) sprog-tag.
 *
 * MÅLT 24/10-2026: 41 % af alle kodeblokke havde ingen sprog-tag og 4 % et
 * sprog shiki ikke kender. Begge endte som ensfarvet rå tekst, mens mobilen
 * farvede alt. Bjørn: «uden sprog tag er den vi har her og det er lort.. farver».
 */

const flad = (code: string) => fallbackTokens(code).flat()
const farver = (code: string) =>
  new Set(flad(code).map((t) => t.htmlStyle['--shiki-dark']))

describe('kodeFallback', () => {
  it('farver nøgleord, streng, kommentar og tal', () => {
    const tokens = flad('def hent(x):  # kommentar\n  return "hej" + 42')
    const farvet = (tekst: string) =>
      tokens.find((t) => t.content.includes(tekst))?.htmlStyle['--shiki-dark']

    expect(farvet('def')).toBe('#F97583') // keyword
    expect(farvet('"hej"')).toBe('#9ECBFF') // streng
    expect(farvet('# kommentar')).toBe('#6A737D') // kommentar
    expect(farvet('42')).toBe('#79B8FF') // tal
  })

  it('giver mere end én farve på ren kode uden sprog-tag', () => {
    // Kernen i fejlen: før var hele blokken `--fg-1`, altså én farve.
    expect(farver('const x = 1\nif (x) return "ja" // note').size).toBeGreaterThan(2)
  })

  it('deler på linjer som shiki, så render-stien kan indsætte \\n', () => {
    const linjer = fallbackTokens('a = 1\nb = 2\nc = 3')
    expect(linjer).toHaveLength(3)
    expect(linjer[1]?.map((t) => t.content).join('')).toBe('b = 2')
  })

  it('sætter både lys og mørk farve, så tema-skift virker', () => {
    for (const token of flad('return 1')) {
      expect(token.htmlStyle['--shiki-light']).toMatch(/^#[0-9A-F]{6}$/i)
      expect(token.htmlStyle['--shiki-dark']).toMatch(/^#[0-9A-F]{6}$/i)
    }
  })

  it('tåler tom og manglende kode uden at kaste', () => {
    expect(() => fallbackTokens('')).not.toThrow()
    expect(fallbackTokens('')).toHaveLength(1)
  })

  it('farver et ord inde i en streng som streng, ikke som nøgleord', () => {
    // Rækkefølgen i scanneren er betydningsbærende: strenge vinder over ord.
    const token = flad('x = "return"').find((t) => t.content.includes('return'))
    expect(token?.htmlStyle?.['--shiki-dark']).toBe('#9ECBFF')
  })
})
