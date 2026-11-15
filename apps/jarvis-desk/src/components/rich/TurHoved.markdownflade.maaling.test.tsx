// @vitest-environment jsdom
import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { render } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { TurHoved } from './TurHoved'
import { turFortalt } from '../../lib/raekkeModel'
import { deriveChatFlow, type ChatFlowInput } from '../../lib/chatFlowModel'
import type { ContentBlock } from '../../lib/sseProtocol'

/**
 * MÅLING, ikke en vagt: kan markdown overhovedet nå turens hoved?
 *
 * Baggrund (15/11-2026): side-opgaven hævdede at `TurHoved.tsx:80` skriver
 * `{tekst}` i et bart `<span className="rv-turTekst">` — «samme fejlform som
 * SynteseLinje», hvor rå tekst i et span kollapsede `\n\n` til ét mellemrum.
 *
 * Ligheden er reel i FORMEN, men ikke i KONSEKVENSEN: SynteseLinje fik
 * Jarvis' egen syntese, som er markdown. Hovedet får et af otte faste ord
 * (chat) eller en sætning bygget af `FRASER`-tabellen (code). Der er ingen
 * tredje indgang.
 *
 * ## Hvorfor det ikke er nok at læse koden
 *
 * `hovedTekst` er ikke eksporteret — den nås kun gennem `deriveChatFlow`. En
 * gennemlæsning kan se rigtig ud og alligevel tage fejl af hvilke grene der
 * kan rammes. Målingen enumererer derfor ALLE producerbare outputs og
 * renderer dem, så påstanden hviler på det komponenten faktisk fik, ikke på
 * hvad jeg mener at have læst.
 *
 * ## Hvad den IKKE påstår
 *
 * At hovedet er en markdown-flade. Det er det ikke, og det skal det ikke
 * være: `.rv-turTekst` er `white-space: nowrap` + ellipse (målt nedenfor), så
 * et afsnit ville blive klippet på én linje uanset renderer. Sender man
 * markdown herind, er det derfor en fejl i KALDSTEDET — ikke i komponenten.
 */

const MARKDOWN = /\*\*|__|[\r\n]|^#{1,6}\s|`|\]\(/m

const base: ChatFlowInput = {
  blocks: [],
  workingStep: null,
  rundeEtiketter: {},
  tankeResumeer: {},
  finalAnswerStarted: false,
  status: 'working',
}

const vaerktoej: ContentBlock = {
  type: 'tool_use', id: 't1', name: 'read_file', input: {}, status: 'done',
}
const tekst: ContentBlock = { type: 'text', text: 'Et rent svar.' }

/** Alle otte grene i `hovedTekst`: {arbejde, tanke} × {kører, completed, interrupted, failed}. */
function alleChatHoveder(): string[] {
  const ud: string[] = []
  for (const [status, blocks] of [
    ['working', [vaerktoej]],
    ['working', []],
    ['done', [vaerktoej, tekst]],
    ['done', [tekst]],
    ['interrupted', [vaerktoej]],
    ['interrupted', [tekst]],
    ['error', [vaerktoej]],
    ['error', [tekst]],
  ] as const) {
    ud.push(deriveChatFlow({ ...base, status, blocks: [...blocks] }).hovedTekst)
  }
  return ud
}

describe('TurHoved — kan markdown nå hovedet?', () => {
  it('kontrol: regex og producenter er ikke tomme — ellers måler vagten intet', () => {
    // Uden denne ville alle `not.toMatch` nedenfor være grønne på tomme
    // strenge og på en død regex. Det er fælden hvor vagten består fordi
    // tærsklen matchede alt.
    expect('**fed**\n\nto afsnit').toMatch(MARKDOWN)
    expect('en `kode` her').toMatch(MARKDOWN)
    expect('Arbejder').not.toMatch(MARKDOWN)
    // `turFortalt` skal faktisk producere den sætning FRASER lover.
    // `familier` er én post PR. VÆRKTØJSKALD — flertalsformen nås kun ved at
    // gentage familien. Det kostede en fejlet kontrol at finde ud af.
    expect(turFortalt(['fil', 'fil', 'fil'], 3, 0)).toContain('Læste 3 filer')
    expect(turFortalt(['spoergsmaal'], 1, 0)).toContain('Spurgte dig')
  })

  it('chat mode: alle otte hovedtekster er faste ord uden markdown', () => {
    const hoveder = alleChatHoveder()
    // Otte grene, og de skal være otte FORSKELLIGE ord — ellers måler vi
    // færre grene end vi tror.
    expect(new Set(hoveder).size).toBe(8)
    for (const h of hoveder) {
      expect(h, `hovedtekst «${h}»`).not.toMatch(MARKDOWN)
      expect(h.length).toBeGreaterThan(0)
    }
  })

  it('code mode: turFortalt er én linje uden markdown for alle familier og tal', () => {
    const familier = [
      'fil', 'liste', 'terminal', 'skriv', 'diff',
      'web', 'billede', 'spoergsmaal', 'opgave', 'fald', 'ukendt-familie',
    ]
    let maalt = 0
    for (const f of familier) {
      for (let n = 1; n <= 5; n += 1) {
        for (const sekunder of [0, 42]) {
          const linje = turFortalt(Array<string>(n).fill(f), n, sekunder)
          expect(linje, `${f}×${n} @${sekunder}s`).not.toMatch(MARKDOWN)
          expect(linje.length, `${f}×${n} er tom`).toBeGreaterThan(0)
          maalt += 1
        }
      }
    }
    // Kombinationer med flere led — det er her `led()` og «mere» kommer ind.
    for (const sekunder of [0, 42]) {
      const flerled = turFortalt(['fil', 'fil', 'terminal', 'web', 'diff'], 5, sekunder)
      expect(flerled).not.toMatch(MARKDOWN)
      maalt += 1
    }
    expect(maalt).toBeGreaterThan(100)
  })

  it('renderet: hovedets span bærer teksten ordret og uden afsnit', () => {
    for (const h of alleChatHoveder()) {
      const { container, unmount } = render(
        <TurHoved tekst={h} aaben={false} onToggle={() => {}} />,
      )
      const span = container.querySelector('.rv-turTekst')
      expect(span, `span for «${h}»`).not.toBeNull()
      expect(span!.textContent).toBe(h)
      expect(span!.textContent).not.toMatch(MARKDOWN)
      unmount()
    }
  })

  it('CSS-kontrakten: .rv-turTekst er nupris én linje — aldrig et afsnit', () => {
    // Det er den regel der gør spørgsmålet akademisk: selv hvis en kalder
    // sendte to afsnit ind, ville de blive klippet på én linje med ellipse.
    const css = readFileSync(join(__dirname, '../../styles/turhoved.css'), 'utf8')
    const regel = /\.rv-turTekst\s*\{([^}]*)\}/.exec(css)?.[1] ?? ''
    expect(regel).toContain('white-space: nowrap')
    expect(regel).toContain('text-overflow: ellipsis')
    expect(regel).toContain('overflow: hidden')
  })

  it('mekanismen: markdown sendt ind i hovedet står RÅT — det er ikke en markdown-flade', () => {
    // Beviser at komponenten ikke renderer markdown. Det er ikke en fejl der
    // skal rettes: hovedet er en ét-linjes etiket. Testen står her så den
    // næste der får lyst til at sende Jarvis' prosa herind kan se hvad der sker.
    const { container } = render(
      <TurHoved tekst={'**fed**\n\nto afsnit'} aaben={false} onToggle={() => {}} />,
    )
    const span = container.querySelector('.rv-turTekst')!
    expect(span.textContent).toContain('**fed**')
    expect(span.querySelector('strong')).toBeNull()
  })
})
