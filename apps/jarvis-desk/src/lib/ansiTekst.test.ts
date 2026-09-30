import { describe, it, expect } from 'vitest'
import { ryd, anvendVognretur } from './ansiTekst'

/**
 * `ansiStykker` oversaetter SGR til farver og lader alt andet staa — saa
 * `\x1b[2K` stod som «[2K» paa skaermen (spec punkt 6).
 *
 * Maalt foerst: ESC-sekvenser optraeder 11 gange paa 14 dage, `\r` 85 gange.
 * Derfor rettes de to, og ikke en kolonnebuffer med tabulatorstop og
 * dobbeltbredde — det ville vaere en terminal-emulator for en haandfuld
 * linjer om ugen.
 */

const ESC = '\x1b'

describe('vognretur', () => {
  it('en progressbar viser sin SIDSTE tilstand', () => {
    expect(anvendVognretur('10%\r20%\r30%')).toBe('30%')
  })

  it('et KORT segment lader halen af et længere stå', () => {
    // Det er dét der gør «tag sidste segment» forkert: `\r` flytter markøren,
    // den sletter ikke. En terminal viser «hejsa» — ikke «hej».
    expect(anvendVognretur('hejsa\rhej')).toBe('hejsa')
    expect(anvendVognretur('100%\r5%')).toBe('5%0%')
  })

  it('rører en linje uden vognretur slet ikke', () => {
    expect(anvendVognretur('almindelig linje')).toBe('almindelig linje')
    expect(anvendVognretur('')).toBe('')
  })
})

describe('ryd', () => {
  it('fjerner erase-in-line i stedet for at vise «[2K»', () => {
    expect(ryd(`før${ESC}[2Kefter`)).toBe('førefter')
  })

  it('fjerner markør-flytninger', () => {
    // Alle CSI'er der ikke er `m` styrer en markør vi ikke har.
    expect(ryd(`a${ESC}[3Cb${ESC}[1Ac${ESC}[2Jd`)).toBe('abcd')
  })

  it('BEVARER farve-sekvenser — dem oversætter Ansi selv', () => {
    // Fjernede vi dem her, ville farven forsvinde. Farven ER information.
    const t = `${ESC}[32mgrøn${ESC}[0m`
    expect(ryd(t)).toBe(t)
  })

  it('fjerner terminalens vinduestitel (OSC)', () => {
    expect(ryd(`${ESC}]0;min titel\x07indhold`)).toBe('indhold')
  })

  it('`\\r\\n` er en linjeslutning, ikke en overskrivning', () => {
    // Den fælde er hele grunden til at `\r\n` normaliseres først: uden det
    // ville hver eneste Windows-linje blive spist af sin efterfølger.
    expect(ryd('linje et\r\nlinje to')).toBe('linje et\nlinje to')
  })

  it('rydder FØR vognreturen — ellers tæller en usynlig sekvens med i længden', () => {
    // `\x1b[2K` er 4 tegn. Talte de med, ville segmentet se 4 tegn længere ud
    // end det er, og halen blive klippet et forkert sted.
    //
    // «lang linje her» er 14 tegn, «kort» er 4 — så halen er `.slice(4)`,
    // altså « linje her» med sit ledende mellemrum. (Min første forventning
    // her var «kortlinje her»; testen fangede min egen regnefejl, ikke kodens.)
    expect(ryd(`lang linje her\r${ESC}[2Kkort`)).toBe('kort linje her')

    // Uden rydning FØRST ville segmentet være «\x1b[2Kkort» = 8 tegn, og
    // halen begynde fire tegn for langt inde.
    expect(ryd(`lang linje her\r${ESC}[2Kkort`)).not.toBe('kortnje her')
  })

  it('en tekst uden noget af det rører sig ikke', () => {
    expect(ryd('helt almindelig\nto linjer')).toBe('helt almindelig\nto linjer')
    expect(ryd('')).toBe('')
  })

  it('tåler null og undefined', () => {
    expect(ryd(null as unknown as string)).toBe('')
    expect(ryd(undefined as unknown as string)).toBe('')
  })

  it('hver linje får sin egen vognretur — ikke hele teksten under ét', () => {
    expect(ryd('a\rb\nc\rd')).toBe('b\nd')
  })
})
