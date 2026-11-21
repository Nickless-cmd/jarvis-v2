/**
 * MÅLING (21/11-2026). Bjørn: «Nåede ik at se det.. syntese -> runde -> slutbesked».
 *
 * Spørgsmålet er ikke om rækkefølgen er rigtig, men om hvor LÆNGE hvert led er
 * synligt. Denne fil måler synligheden gennem en hel tur og rapporterer
 * vinduerne — den er en maaling, ikke en vagt.
 */
import { describe, it, expect, beforeEach } from 'vitest'
import { render } from '@testing-library/react'
import { RaekkeTranskript } from './RaekkeTranskript'
import { RAEKKE_KEY } from '../../lib/visningsPref'
import type { ContentBlock } from '../../lib/sseProtocol'

beforeEach(() => { localStorage.setItem(RAEKKE_KEY, '1') })

const MELLEM = 'Først tjekker jeg versionen.'
const SLUT = 'Alt står rigtigt: versionen kører og bundlen serveres.'

const KALD: ContentBlock = {
  type: 'tool_use', id: 't1', name: 'bash',
  input: { command: 'git rev-parse HEAD' }, status: 'done',
  result: '118c1f9cf',
} as ContentBlock

/** Mellemtekst FØR kaldet — ellers bliver den til slutsvar, ikke syntese. */
const ARBEJDE: ContentBlock[] = [{ type: 'text', text: MELLEM }, KALD]
const MED_SVAR: ContentBlock[] = [...ARBEJDE, { type: 'text', text: SLUT }]

function synligt(el: Element | null): boolean {
  if (!el) return false
  let n: Element | null = el
  while (n) {
    if (n.hasAttribute('hidden')) return false
    n = n.parentElement
  }
  return true
}

describe('synlighed gennem en tur (maaling)', () => {
  it('rapporterer hvornaar syntese og runde er synlige', () => {
    const faser: string[] = []
    const noter = (view: ReturnType<typeof render>, navn: string) => {
      const gruppe = view.container.querySelector('.rv-gruppe')
      const syntese = view.container.querySelector('.rv-mellem')
      const runde = view.container.querySelector('.rv-arbejdsrunde')
      const hoved = view.container.querySelector('.rv-tur')
      const svar = view.container.querySelector('.rv-svar')
      const tilstand = (el: Element | null) =>
        el ? (synligt(el) ? 'synlig' : 'skjult') : 'findes ikke'
      faser.push(
        `${navn}: hoved=${tilstand(hoved)} gruppe=${tilstand(gruppe)} syntese=${tilstand(syntese)} runde=${tilstand(runde)} svar=${tilstand(svar)}`,
      )
    }

    // Fase 1: arbejdet kører, mellemteksten er landet, intet slutsvar endnu.
    const view = render(
      <RaekkeTranskript blocks={ARBEJDE} streaming svarRuller />,
    )
    noter(view, '1 arbejde + mellemtekst')

    // Fase 2: slutbeskeden begynder — `finalAnswerStarted` bliver sand.
    view.rerender(
      <RaekkeTranskript blocks={MED_SVAR} streaming finalAnswerStarted svarRuller />,
    )
    noter(view, '2 slutbesked begyndt')

    // Fase 3: paceren er færdig — `svarRuller` bliver falsk, folden lukker.
    view.rerender(
      <RaekkeTranskript blocks={MED_SVAR} streaming={false} finalAnswerStarted svarRuller={false} />,
    )
    noter(view, '3 pacing faerdig')

    // eslint-disable-next-line no-console
    console.log('=== SYNLIGHED GENNEM TUREN ===\n' + faser.join('\n'))

    expect(faser.length).toBe(3)
  })
})
