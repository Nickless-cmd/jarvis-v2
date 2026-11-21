import { describe, it, expect, beforeEach } from 'vitest'
import { render } from '@testing-library/react'
import { RaekkeTranskript } from './RaekkeTranskript'
import { RAEKKE_KEY } from '../../lib/visningsPref'
import type { ContentBlock } from '../../lib/sseProtocol'

/**
 * Ordhalen skal leve saa laenge TEKSTEN ruller — ogsaa efter at streamen er
 * slut og hovedet har foldet.
 *
 * MÅLT 21/11-2026 (Bjørn: «Kan det passe farven forsvinder fra ord animationen
 * efter hoveds fold?»): `MarkdownRenderer` fik kun `streaming`, som bliver falsk
 * ved `message_stop`. Paceren fortsætter bagefter, saa de sidste ord landede
 * EFTER halen var doed — uden ankomstfarve. `svarRuller` vidste det allerede,
 * men signalet blev aldrig foert ned til tekst-rendereren.
 *
 * Denne test gaar gennem `RaekkeTranskript` — ikke `MarkdownRenderer` isoleret.
 * Det er hele pointen: koblingen mellem de to er praecis det der var brudt, og
 * en test der kalder `MarkdownRenderer` direkte kan ikke se den.
 */

const kald = (navn: string): ContentBlock => ({
  type: 'tool_use', id: `${navn}-1`, name: navn, input: {},
})

const TUR: ContentBlock[] = [
  kald('bash'),
  { type: 'text', text: 'Svaret begynder her og fortsætter et stykke endnu.' },
]

beforeEach(() => { localStorage.setItem(RAEKKE_KEY, '1') })

const ankomstOrd = (c: HTMLElement) => c.querySelectorAll('.streaming-word-tail')

describe('ordhalen overlever at hovedet folder', () => {
  it('farver ordene naar streamen er slut men teksten stadig ruller', () => {
    // Praecis Bjørns tilstand: `message_stop` er kommet, hovedet er der,
    // men paceren indhenter de sidste ord. `svarRuller` er stadig sand.
    const view = render(
      <RaekkeTranskript
        blocks={TUR}
        streaming={false}
        finalAnswerStarted
        svarRuller
      />,
    )
    expect(ankomstOrd(view.container).length).toBeGreaterThan(0)
  })

  it('farver intet naar baade stream og pacing er faerdige', () => {
    const view = render(
      <RaekkeTranskript
        blocks={TUR}
        streaming={false}
        finalAnswerStarted
        svarRuller={false}
      />,
    )
    expect(ankomstOrd(view.container)).toHaveLength(0)
  })
})
