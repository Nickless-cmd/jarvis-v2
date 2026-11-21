import { describe, it, expect, beforeEach } from 'vitest'
import { render } from '@testing-library/react'
import { RaekkeTranskript } from './RaekkeTranskript'
import { RAEKKE_KEY } from '../../lib/visningsPref'
import type { ContentBlock } from '../../lib/sseProtocol'

/**
 * Folden lukker naar SVARET FINDES — ikke naar det er rullet ud.
 *
 * VENDT 21/11-2026 (Bjørn: «Hoved folder foerst naar beskeden er faerdig..
 * Det skal ske naar slutbeskeden fortsaetter? Hvad goer GPT?»).
 *
 * Den FORRIGE regel blev skrevet 20/11 for at undgaa en tom flade: folden
 * lukkede i samme frame som `finalAnswerStarted` blev sand, hovedet dukkede op
 * over ingenting, og paceren dumpede resten ind bagefter. Løsningen blev at
 * binde folden til `svarRuller` — sand til det sidste tegn var vist.
 *
 * Det flyttede problemet: arbejdet blev revet vaek i praecis den frame teksten
 * landede, saa oejeblikket hvor turen gik fra «arbejde» til «resultat» blev et
 * hop. GPT goer det modsatte — deres `completed` afledes af om der FINDES
 * assistent-indhold, ikke af om streamen er slut. Hovedet folder i det oejeblik
 * svaret begynder, og teksten ruller videre inde i det faerdige hoved.
 *
 * Den tomme flade kan ikke komme tilbage herfra: `svarLaas` i `opdel` sørger
 * for at teksten bliver i `svar` naar den foerst er begyndt, saa der ER et
 * svar at folde om. Det er den vagt (`svarLaast.test.tsx`), ikke denne.
 */

const kald = (navn: string): ContentBlock => ({
  type: 'tool_use', id: `${navn}-1`, name: navn, input: {},
})

/** En tur med arbejde og et svar — nok til at hoved og gruppe begge findes. */
const TUR: ContentBlock[] = [
  kald('bash'),
  { type: 'text', text: 'Svaret begynder her og fortsætter et stykke endnu.' },
]

beforeEach(() => { localStorage.setItem(RAEKKE_KEY, '1') })

const gruppeSkjult = (c: HTMLElement) =>
  c.querySelector('.rv-gruppe')?.hasAttribute('hidden') ?? null

describe('code-modens fold lukker naar svaret findes', () => {
  it('lukker folden naar svaret er begyndt — ogsaa mens det ruller', () => {
    // Praecis den tilstand GPT folder i: svaret er begyndt, men der er stadig
    // tekst tilbage at rulle. Hovedet er turens ansigt fra nu af.
    const view = render(
      <RaekkeTranskript blocks={TUR} streaming finalAnswerStarted svarRuller />,
    )

    expect(gruppeSkjult(view.container)).toBe(true)
    expect(view.container.querySelector('.rv-tur')).toHaveAttribute('aria-expanded', 'false')
    // …og svaret staar uden for folden, saa ord-animationen ruller uforstyrret.
    expect(view.container.querySelector('.rv-svar')).not.toBeNull()
  })

  it('ser ens ud foer og efter rullingen er faerdig — ingen hop', () => {
    // Det er hele pointen: fasen «ruller» og fasen «faerdig» skal se ens ud.
    // Foer flyttede arbejdet sig vaek praecis her, og det var hoppet Bjørn saa.
    const view = render(
      <RaekkeTranskript blocks={TUR} streaming finalAnswerStarted svarRuller />,
    )
    const foerSkjult = gruppeSkjult(view.container)
    const foerHoved = view.container.querySelector('.rv-tur')?.getAttribute('aria-expanded')

    view.rerender(
      <RaekkeTranskript blocks={TUR} streaming finalAnswerStarted svarRuller={false} />,
    )

    expect(gruppeSkjult(view.container)).toBe(foerSkjult)
    expect(view.container.querySelector('.rv-tur')?.getAttribute('aria-expanded')).toBe(foerHoved)
    expect(gruppeSkjult(view.container)).toBe(true)
  })

  it('er ogsaa lukket naar strommen er slut men paceren stadig indhenter', () => {
    // `streaming` er falsk efter `message_stop`, men der er stadig efterslæb.
    // Folden er ligeglad med begge dele — svaret findes.
    const view = render(
      <RaekkeTranskript blocks={TUR} streaming={false} finalAnswerStarted svarRuller />,
    )
    expect(gruppeSkjult(view.container)).toBe(true)
    expect(view.container.querySelector('.rv-tur')).not.toBeNull()
  })

  it('falder tilbage til den gamle regel naar signalet ikke er givet', () => {
    // Kald uden `svarRuller` (fx andre flader) skal opfoere sig uaendret:
    // arbejde koerer naar strommen er i gang og svaret ikke er begyndt.
    const view = render(<RaekkeTranskript blocks={TUR} streaming />)
    expect(gruppeSkjult(view.container)).toBe(false)
  })
})
