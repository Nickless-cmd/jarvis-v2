/**
 * MÅLING, ikke en vagt: overlever slutsvarets DOM-node fase-skiftet?
 *
 * ## Hvorfor denne fil findes (19/10-2026)
 *
 * Den første måling talte mounts gennem en MOCKET `BlocksRenderer`. Et
 * mount-tal fra en mock beviser kun at komponenten blev kaldt — ikke at den
 * ægte node blev genbrugt eller kasseret. Her måles det direkte:
 *
 *   1. Find det ægte DOM-element der indeholder slutsvaret FØR grænsen.
 *   2. Flyt grænsen (kun `finalAnswerStarted` ændres, blokkene er identiske).
 *   3. Find elementet igen og spørg DOM'en selv: `isSameNode`.
 *
 * Er svaret `true`, flytter noden med og der er intet spring at rette.
 * Er svaret `false`, er noden ny — og så er springet strukturelt, ikke et
 * pacing-spørgsmål, uanset hvor glat teksten ruller.
 */
import { render } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { ContentBlock } from '../../lib/sseProtocol'
import { RaekkeTranskript } from './RaekkeTranskript'

/** En tur: et værktøjskald, en syntese, og slutsvaret der lander bagefter. */
function tur(slutsvar: string): ContentBlock[] {
  return [
    { type: 'tool_use', id: 't1', name: 'bash', input: {} } as ContentBlock,
    { type: 'text', text: 'Lad mig se paa det.' } as ContentBlock,
    { type: 'text', text: slutsvar } as ContentBlock,
  ]
}

/** Det mindste element hvis tekst er præcis dette — altså tekstens egen node. */
function nodeMedTekst(root: HTMLElement, tekst: string): Element | null {
  const alle = Array.from(root.querySelectorAll('*'))
  let bedst: Element | null = null
  for (const el of alle) {
    if (!(el.textContent ?? '').includes(tekst)) continue
    if (bedst === null || (el.textContent ?? '').length < (bedst.textContent ?? '').length) bedst = el
  }
  return bedst
}

describe('RaekkeTranskript — DOM-node over fase-skiftet', () => {
  it('MAALER: er slutsvarets node den SAMME foer og efter graensen?', () => {
    const svar = 'Det er svaret.'
    const blocks = tur(svar)

    const view = render(<RaekkeTranskript blocks={blocks} streaming finalAnswerStarted={false} />)
    const foer = nodeMedTekst(view.container, svar)
    const foerForaelder = foer?.parentElement?.className ?? '(ingen)'
    const foerIArbejde = !!foer?.closest('.rv-gruppe')
    const foerISvar = !!foer?.closest('.rv-svar')

    view.rerender(<RaekkeTranskript blocks={blocks} streaming finalAnswerStarted />)
    const efter = nodeMedTekst(view.container, svar)
    const efterForaelder = efter?.parentElement?.className ?? '(ingen)'
    const efterIArbejde = !!efter?.closest('.rv-gruppe')
    const efterISvar = !!efter?.closest('.rv-svar')

    // eslint-disable-next-line no-console
    console.log(
      `[MAALING] node foer=${foer ? 'fundet' : 'MANGLER'} efter=${efter ? 'fundet' : 'MANGLER'}`
      + ` | sammeNode=${foer && efter ? foer.isSameNode(efter) : 'n/a'}`
      + ` | foer: arbejde=${foerIArbejde} svar=${foerISvar} (foraelder=${foerForaelder})`
      + ` | efter: arbejde=${efterIArbejde} svar=${efterISvar} (foraelder=${efterForaelder})`,
    )

    // Selve målingen: begge steder skal findes, ellers er der intet at sammenligne.
    expect(foer).not.toBeNull()
    expect(efter).not.toBeNull()
  })

  it('MAALER: hvor mange tekst-noder indeholder svaret foer vs efter?', () => {
    const svar = 'Det er svaret.'
    const blocks = tur(svar)
    const view = render(<RaekkeTranskript blocks={blocks} streaming finalAnswerStarted={false} />)
    const foerAntal = view.container.querySelectorAll('.rv-svar').length
    const foerArbejdeAntal = view.container.querySelectorAll('.rv-gruppe').length
    view.rerender(<RaekkeTranskript blocks={blocks} streaming finalAnswerStarted />)
    const efterAntal = view.container.querySelectorAll('.rv-svar').length
    const efterArbejdeAntal = view.container.querySelectorAll('.rv-gruppe').length

    // eslint-disable-next-line no-console
    console.log(
      `[MAALING] containere foer: svar=${foerAntal} arbejde=${foerArbejdeAntal}`
      + ` | efter: svar=${efterAntal} arbejde=${efterArbejdeAntal}`,
    )
    expect(efterAntal).toBeGreaterThanOrEqual(0)
  })
})
