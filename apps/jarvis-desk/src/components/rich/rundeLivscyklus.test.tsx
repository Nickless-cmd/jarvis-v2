import { describe, it, expect, beforeEach } from 'vitest'
import { fireEvent, render } from '@testing-library/react'
import { RaekkeTranskript } from './RaekkeTranskript'
import { ChatFlowPresentation } from './ChatFlowPresentation'
import { SettingsProvider } from '../../contexts/SettingsContext'
import { RAEKKE_KEY } from '../../lib/visningsPref'
import type { ContentBlock } from '../../lib/sseProtocol'

/**
 * Rundernes placering (side-bfbddc76a8): en runde efter slutbeskeden hører
 * mellem synteserne — også når hovedet foldes ud efter turen. Før rettelsen
 * blev de sene runder kopieret ind i foldens arbejdsliste (smeltet sammen med de
 * tidlige) mens deres egne pladser forblev kollapsede.
 *
 * jsdom har ingen layout: rækkefølgen og tilstanden læses her; den visuelle
 * kurve måles i Chromium af `src/harness/maal-rundelivscyklus.mjs`.
 */
const tool = (id: string): ContentBlock => ({ type: 'tool_use', id, name: 'bash', input: { command: id }, status: 'done', result: 'ok' })
const text = (t: string, start = false): ContentBlock => ({
  type: 'text', text: t, phase: start ? 'final_answer' : 'commentary', code_answer_protocol: 1, code_answer_start: start,
})
const TUR: ContentBlock[] = [tool('r0'), text('SYNTESE-A', true), tool('R1'), text('SYNTESE-B'), tool('R2'), text('SYNTESE-C')]

/** Dokumentrækkefølgen af syntese-tekster og runde-labels (kun dem der findes i DOM'en). */
function raekkefoelge(c: HTMLElement): string[] {
  const out: string[] = []
  const walker = document.createTreeWalker(c, NodeFilter.SHOW_TEXT)
  for (let n = walker.nextNode(); n; n = walker.nextNode()) {
    const m = (n.textContent ?? '').match(/SYNTESE-[ABC]|Kørte (R\d)/)
    if (m && !out.includes(m[0])) out.push(m[0])
  }
  return out
}

describe('Code mode: sene runder bevarer deres plads', () => {
  beforeEach(() => { localStorage.setItem(RAEKKE_KEY, '1') })
  const tegn = () => render(<RaekkeTranskript blocks={TUR} streaming={false} svarRuller={false} finalAnswerStarted />)

  it('lukket hoved: runderne er samlet (inert), åbent hoved: de er synlige på deres egen plads', () => {
    const { container } = tegn()
    const runder = () => Array.from(container.querySelectorAll('.rv-sen-runde'))
    expect(runder()).toHaveLength(2)
    expect(runder().every((r) => r.getAttribute('data-samles') === 'true')).toBe(true)
    fireEvent.click(container.querySelector('.rv-tur')!)
    expect(runder().every((r) => r.getAttribute('data-samles') === 'false')).toBe(true)
    // Rækkefølgen i dokumentet: A, R1, B, R2, C — ikke R1/R2 samlet i bunden.
    const syn = raekkefoelge(container.querySelector('.rv-svar')!)
    expect(syn).toEqual(['SYNTESE-A', 'Kørte R1', 'SYNTESE-B', 'Kørte R2', 'SYNTESE-C'])
  })

  it('foldens egen arbejdsliste indeholder IKKE de sene runder (ingen kopi, ingen sammensmeltning)', () => {
    const { container } = tegn()
    fireEvent.click(container.querySelector('.rv-tur')!)
    const ifold = container.querySelector('.rv-gruppe')!.textContent ?? ''
    expect(ifold).not.toMatch(/R1|R2/)
  })

  it('hovedet kan foldes ud selv når ALT arbejde ligger efter svaret', () => {
    const kunSene = [text('SYNTESE-A', true), tool('R1'), text('SYNTESE-B')]
    const { container } = render(<RaekkeTranskript blocks={kunSene} streaming={false} svarRuller={false} finalAnswerStarted />)
    expect(container.querySelector('.rv-tur')).not.toBeNull()
    fireEvent.click(container.querySelector('.rv-tur')!)
    expect(container.querySelector('.rv-sen-runde')!.getAttribute('data-samles')).toBe('false')
  })
})

describe('Chat mode: sene runder bevarer deres plads', () => {
  const tegn = () => render(
    <SettingsProvider>
      <ChatFlowPresentation blocks={TUR} mode="living" density="compact" streaming={false} status="done"
        finalAnswerStarted runId="rl" beskedId="rl" />
    </SettingsProvider>,
  )
  const runder = (c: HTMLElement) => Array.from(c.querySelectorAll('.chat-flow-answer > .chat-flow-runde'))

  it('lukket: kollapset; åbent: åben på pladsen mellem synteserne i orden', () => {
    const { container } = tegn()
    expect(runder(container)).toHaveLength(2)
    expect(runder(container).every((r) => r.getAttribute('data-levetid') === 'kollapset')).toBe(true)
    fireEvent.click(container.querySelector('.rv-tur')!)
    expect(runder(container).every((r) => r.getAttribute('data-levetid') === 'aaben')).toBe(true)
    expect(runder(container).every((r) => !r.hasAttribute('inert'))).toBe(true)
    const syn = raekkefoelge(container.querySelector('.chat-flow-answer')!)
    expect(syn.filter((x) => x.startsWith('SYNTESE'))).toEqual(['SYNTESE-A', 'SYNTESE-B', 'SYNTESE-C'])
    // R1 står mellem A og B (direkte søskende-rækkefølge i svar-containeren).
    const born = Array.from(container.querySelector('.chat-flow-answer')!.children)
    expect(born.map((b) => b.classList.contains('chat-flow-runde') ? 'R' : 'S').join('')).toBe('SRSRS')
  })

  it('foldens arbejdsliste indeholder ikke de sene runder', () => {
    const { container } = tegn()
    fireEvent.click(container.querySelector('.rv-tur')!)
    const ifold = container.querySelector('.chat-flow-work-details')?.textContent ?? ''
    expect(ifold).not.toMatch(/R1|R2/)
  })
})

/**
 * UDEN `code_answer_protocol` — den anden halvdel af fladen.
 *
 * MÅLT 27/11-2026: alle vagter ovenfor bærer `code_answer_protocol: 1`, og det
 * er præcis den markør der lukkede `foldWork`s ekstra gren. Uden den stod
 * R1/R2 stadig smeltet sammen i foldens arbejdslog, og deres egen container gik
 * `live → kollapset → unmount` uden en `'aaben'`-tilstand: udfoldet hoved viste
 * dem aldrig på deres plads. Bjørn så det i PWA'en som «når jeg trykker foldet
 * ud så opstår de ikk på der position».
 */
describe('Uden code_answer_protocol: samme kontrakt', () => {
  const t = (id: string): ContentBlock => ({ type: 'tool_use', id, name: 'bash', input: { command: id }, status: 'done', result: 'ok' })
  // Bemærk: ingen `code_answer_protocol` og ingen `code_answer_start`.
  const x = (tekst: string, start = false): ContentBlock => ({
    type: 'text', text: tekst, phase: start ? 'final_answer' : 'commentary',
  })
  const TUR_UORDNET: ContentBlock[] = [t('r0'), x('SYNTESE-A', true), t('R1'), x('SYNTESE-B'), t('R2'), x('SYNTESE-C')]
  const tegn = () => render(
    <SettingsProvider>
      <ChatFlowPresentation blocks={TUR_UORDNET} mode="living" density="compact" streaming={false}
        status="done" finalAnswerStarted runId="uordnet" beskedId="uordnet" />
    </SettingsProvider>,
  )

  it('folden indeholder ikke de sene runder — de er ikke kopieret ind', () => {
    const { container } = tegn()
    fireEvent.click(container.querySelector('.rv-tur')!)
    const ifold = container.querySelector('.chat-flow-work-details')?.textContent ?? ''
    expect(ifold).not.toMatch(/R1|R2/)
  })

  it('udfoldet hoved ÅBNER hale-runderne i stedet for at lade dem kollapse', () => {
    const { container } = tegn()
    const hale = () => Array.from(container.querySelectorAll('[data-plassering="efter"]'))
    expect(hale().length).toBeGreaterThan(0)
    expect(hale().every((r) => r.getAttribute('data-levetid') === 'kollapset')).toBe(true)
    fireEvent.click(container.querySelector('.rv-tur')!)
    expect(hale().every((r) => r.getAttribute('data-levetid') === 'aaben')).toBe(true)
  })

  it('de sene runder staar mellem synteserne, ikke samlet i bunden', () => {
    const { container } = tegn()
    fireEvent.click(container.querySelector('.rv-tur')!)
    const syn = raekkefoelge(container)
    const i = (n: string) => syn.indexOf(n)
    expect(i('Kørte R1')).toBeGreaterThan(i('SYNTESE-A'))
    expect(i('Kørte R1')).toBeLessThan(i('SYNTESE-B'))
    expect(i('Kørte R2')).toBeGreaterThan(i('SYNTESE-B'))
    expect(i('Kørte R2')).toBeLessThan(i('SYNTESE-C'))
  })
})
