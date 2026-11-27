import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { join } from 'node:path'

/**
 * Faden skal ARVE foldens tal — ikke have sit eget (26/11-2026).
 *
 * Bjørn: «timingen på faden skal være mere ala hoveds animation». Målt før
 * rettelsen: folden kørte 300 ms `ease-out` (chat) / 379 ms `ease-fold`
 * (code), mens faden havde et hardcodet 160 ms `ease-in`. Runden var derfor
 * væk når folden var 53 % / 42 % gennemført — og resten af foldets rejse
 * lukkede en TOM boks sammen. Det er blinket: ikke en animation der fejler,
 * men to der ikke er færdige samtidig.
 *
 * Vagtens vigtigste påstand er den sidste: et nyt hardcodet tal i fade-reglen
 * må ikke kunne snige sig ind. Uden den kan nogen «justere lidt» og genskabe
 * præcis den divergens rettelsen fjernede — og de to ville drive fra hinanden
 * næste gang foldens tal ændres, som de allerede gjorde 15/11 og 18/11.
 */

const udenKommentarer = (s: string) => s.replace(/\/\*[\s\S]*?\*\//g, '')

function regel(css: string, selektor: string): string {
  const escaped = selektor.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  return css.match(new RegExp(`^${escaped} \\{([^}]*)\\}`, 'm'))?.[1] ?? ''
}

const chat = udenKommentarer(readFileSync(join(__dirname, 'chat-flow.css'), 'utf8'))
const code = udenKommentarer(readFileSync(join(__dirname, 'raekkevisning.css'), 'utf8'))

describe('faden arver foldens varighed og kurve', () => {
  it('chat mode: variablen er defineret på containeren med foldens værdi', () => {
    const r = regel(chat, '.chat-flow')
    expect(r).toMatch(/--fold-varighed:\s*var\(--dur-fold\)/)
    expect(r).toMatch(/--fold-kurve:\s*var\(--ease-fold\)/)
  })

  it('code mode: variablen er defineret på containeren med foldens værdi', () => {
    const r = regel(code, '.raekkevisning')
    expect(r).toMatch(/--fold-varighed:\s*var\(--dur-fold\)/)
    expect(r).toMatch(/--fold-kurve:\s*var\(--ease-fold\)/)
  })

  it('chat mode: faden læser variablen, ikke et eget tal', () => {
    const r = regel(chat, '.chat-flow-round[data-pacing-skjult]')
    expect(r).toMatch(/transition-duration:\s*var\(--fold-varighed\)/)
    expect(r).toMatch(/transition-timing-function:\s*var\(--fold-kurve\)/)
  })

  it('code mode: faden læser variablen, ikke et eget tal', () => {
    const r = regel(code, '.raekkevisning .rv-arbejdsrunde[data-pacing-skjult]')
    expect(r).toMatch(/transition-duration:\s*var\(--fold-varighed\)/)
    expect(r).toMatch(/transition-timing-function:\s*var\(--fold-kurve\)/)
  })

  it('fold-reglen i begge flader læser SAMME variabel som faden', () => {
    expect(regel(chat, '.chat-flow-gruppe-ydre'))
      .toMatch(/grid-template-rows var\(--fold-varighed\) var\(--fold-kurve\)/)
    expect(regel(code, '.raekkevisning .rv-gruppe-ydre'))
      .toMatch(/grid-template-rows var\(--fold-varighed\) var\(--fold-kurve\)/)
  })

  it('den gamle kontrakt må ikke komme tilbage: ingen eget tal i faden', () => {
    const par: Array<[string, string]> = [
      ['chat', regel(chat, '.chat-flow-round[data-pacing-skjult]')],
      ['code', regel(code, '.raekkevisning .rv-arbejdsrunde[data-pacing-skjult]')],
    ]
    for (const [navn, r] of par) {
      expect(r, `${navn}: faden har fået sit eget ms-tal igen`).not.toMatch(/transition-duration:\s*\d/)
      expect(r, `${navn}: faden har fået sin egen kurve igen`)
        .not.toMatch(/transition-timing-function:\s*(ease|linear|cubic-bezier)/)
    }
  })
})
