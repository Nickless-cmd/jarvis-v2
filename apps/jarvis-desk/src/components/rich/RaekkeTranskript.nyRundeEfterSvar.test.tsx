import { describe, it, expect, beforeEach } from 'vitest'
import { render } from '@testing-library/react'
import { fireEvent } from '@testing-library/react'
import { RaekkeTranskript } from './RaekkeTranskript'
import { RAEKKE_KEY } from '../../lib/visningsPref'
import type { ContentBlock } from '../../lib/sseProtocol'

/**
 * Et NYT run efter svaret må ikke rive folden op igen.
 *
 * MÅLT 20/11-2026 (Bjørn: «Hoved foldet fejlet så snart du kører en runde efter
 * slut beskeden»): når svaret var rullet ud, stod hovedet foldet sammen over
 * arbejdet. Så startede et nyt run (`arbejdeEfterSvar`), og `aaben` faldt
 * tilbage på `arbejdeKoerer` — som var sand — så folden sprang OP af sig selv.
 * Havde brugeren selv foldet sammen, skete det modsatte: `aabenManuelt=false`
 * vandt, arbejdet forblev skjult, og `visTurhoved` blev falsk af `!arbejdeKoerer`.
 * Tilbage var en TOM flade — hverken arbejde eller hoved.
 *
 * Reglen: brugerens fold er et valg om SVARET, og den skal holdes. Et nyt run
 * må ikke åbne den, men det skal stadig have et ansigt — hovedet bliver stående
 * som den knap der viser at der arbejdes.
 */

const kald = (navn: string): ContentBlock => ({
  type: 'tool_use', id: `${navn}-1`, name: navn, input: {},
})

/** Arbejde FØR svaret — så hovedet har noget at folde ud. */
const TUR: ContentBlock[] = [
  kald('bash'),
  { type: 'text', text: 'Svaret er rullet ud og læst færdigt.' },
]

beforeEach(() => { localStorage.setItem(RAEKKE_KEY, '1') })

// 21/11-2026: folden er ikke laengere `hidden` (display:none) — den er en
// grid-raekke der glider `1fr → 0fr`, saa tilstanden laeses af `data-aaben`.
const gruppeSkjult = (c: HTMLElement) =>
  c.querySelector('.rv-gruppe-ydre')?.getAttribute('data-aaben') === 'false'
const hoved = (c: HTMLElement) => c.querySelector('.rv-tur')

describe('et nyt run efter slutbeskeden', () => {
  it('aabner IKKE folden igen — svaret er allerede laest', () => {
    const view = render(
      <RaekkeTranskript blocks={TUR} streaming finalAnswerStarted svarRuller={false} />,
    )
    // Udgangspunktet: svaret er rullet ud, hovedet staar foldet sammen.
    expect(gruppeSkjult(view.container)).toBe(true)
    expect(hoved(view.container)).not.toBeNull()

    // Så starter et nyt run — serveren melder arbejde efter svaret.
    view.rerender(
      <RaekkeTranskript
        blocks={TUR} streaming finalAnswerStarted svarRuller={false} arbejdeEfterSvar
      />,
    )

    // Folden skal blive, hvor brugeren efterlod den.
    expect(gruppeSkjult(view.container)).toBe(true)
  })

  it('beholder hovedet som livstegn naar folden bliver lukket', () => {
    const view = render(
      <RaekkeTranskript blocks={TUR} streaming finalAnswerStarted svarRuller={false} />,
    )
    expect(hoved(view.container)).not.toBeNull()

    view.rerender(
      <RaekkeTranskript
        blocks={TUR} streaming finalAnswerStarted svarRuller={false} arbejdeEfterSvar
      />,
    )

    // Den tomme flade: uden hovedet er der intet at se og intet at klikke paa.
    expect(hoved(view.container)).not.toBeNull()
  })

  it('holder brugerens sammenfoldning naar runden starter', () => {
    const view = render(
      <RaekkeTranskript blocks={TUR} streaming finalAnswerStarted svarRuller={false} />,
    )
    const knap = hoved(view.container)
    expect(knap).toBeTruthy()

    // Brugeren folder arbejdet UD og derefter SAMMEN igen — det er et valg.
    fireEvent.click(knap!)
    fireEvent.click(knap!)
    expect(gruppeSkjult(view.container)).toBe(true)

    view.rerender(
      <RaekkeTranskript
        blocks={TUR} streaming finalAnswerStarted svarRuller={false} arbejdeEfterSvar
      />,
    )

    // Et nyt run maa ikke overrule det valg.
    expect(gruppeSkjult(view.container)).toBe(true)
    expect(hoved(view.container)).not.toBeNull()
  })

  it('lukker folden igen naar det nye run er slut', () => {
    const view = render(
      <RaekkeTranskript
        blocks={TUR} streaming finalAnswerStarted svarRuller={false} arbejdeEfterSvar
      />,
    )
    expect(gruppeSkjult(view.container)).toBe(true)
    expect(hoved(view.container)).not.toBeNull()

    // Runden er slut: hovedet bliver, folden bliver lukket.
    view.rerender(
      <RaekkeTranskript blocks={TUR} streaming={false} finalAnswerStarted svarRuller={false} />,
    )

    expect(gruppeSkjult(view.container)).toBe(true)
    expect(hoved(view.container)).not.toBeNull()
  })

  // Den utætte kant: naar det nye run STREAMER, er `svarRuller` sand igen — saa
  // er det alene brugerens `aabenManuelt` der afgoer folden. Uden denne gren
  // forsvandt hovedet netop i det vindue, fordi `arbejdeKoerer` var sand.
  it('beholder hovedet ogsaa naar det nye run streamer med folden lukket', () => {
    const view = render(
      <RaekkeTranskript blocks={TUR} streaming finalAnswerStarted svarRuller={false} />,
    )
    const knap = hoved(view.container)
    expect(knap).toBeTruthy()
    // Brugeren folder UD og SAMMEN: et valg om svaret.
    fireEvent.click(knap!)
    fireEvent.click(knap!)
    expect(gruppeSkjult(view.container)).toBe(true)

    // Det nye run leverer nu data — `svarRuller` er sand, og `arbejdeEfterSvar`
    // staar stadig. Folden skal blive lukket, og hovedet skal blive.
    view.rerender(
      <RaekkeTranskript
        blocks={TUR} streaming finalAnswerStarted svarRuller arbejdeEfterSvar
      />,
    )

    expect(gruppeSkjult(view.container)).toBe(true)
    expect(hoved(view.container)).not.toBeNull()
  })
})
