import { describe, it, expect, beforeEach } from 'vitest'
import { render } from '@testing-library/react'
import { RaekkeTranskript } from './RaekkeTranskript'
import { RAEKKE_KEY } from '../../lib/visningsPref'
import type { ContentBlock } from '../../lib/sseProtocol'

/**
 * Folden i code mode må ikke lukke før svaret er RULLET UD.
 *
 * MÅLT 20/11-2026 (Bjørn: «foldet i code mode sker ikk, retter det folder og
 * saa tom skærm og saa dumper den det hele ind»): `arbejdeKoerer` brugte
 * `finalAnswerStarted` — altså «svaret er BEGYNDT» — som om det betød «svaret
 * er FÆRDIGT». I samme frame som det første delta landede, lukkede folden,
 * turhovedet dukkede op over en tom flade, og paceren dumpede resten ind
 * bagefter.
 *
 * `svarRuller` er det ærlige signal: sand til det sidste tegn er vist, ogsaa
 * efter `message_stop`. Testene her vogter at folden følger DET og ikke
 * `finalAnswerStarted`.
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

describe('code-modens fold lukker først når svaret er rullet ud', () => {
  it('holder folden AABEN naar svaret er begyndt men ikke faerdigt', () => {
    // Praecis den tilstand der fejlede: svaret er begyndt
    // (`finalAnswerStarted`), men der er stadig tekst tilbage at rulle.
    const view = render(
      <RaekkeTranskript blocks={TUR} streaming finalAnswerStarted svarRuller />,
    )

    expect(gruppeSkjult(view.container)).toBe(false)
    // Turhovedet er turens RESULTAT og maa ikke staa over en tom flade.
    expect(view.container.querySelector('.rv-tur')).toBeNull()
  })

  it('lukker folden og viser hovedet naar rullingen er faerdig', () => {
    const view = render(
      <RaekkeTranskript blocks={TUR} streaming finalAnswerStarted svarRuller />,
    )
    expect(gruppeSkjult(view.container)).toBe(false)

    view.rerender(
      <RaekkeTranskript blocks={TUR} streaming finalAnswerStarted svarRuller={false} />,
    )

    expect(gruppeSkjult(view.container)).toBe(true)
    expect(view.container.querySelector('.rv-tur')).not.toBeNull()
  })

  it('lukker ogsaa naar strommen er slut men paceren stadig indhenter', () => {
    // `streaming` er falsk efter `message_stop`, men der er stadig efterslæb.
    // Blev folden bundet til `streaming`, ville den lukke her — og resten
    // lande i ét hug. Det er netop «dumper den det hele ind».
    const view = render(
      <RaekkeTranskript blocks={TUR} streaming={false} finalAnswerStarted svarRuller />,
    )
    expect(gruppeSkjult(view.container)).toBe(false)
    expect(view.container.querySelector('.rv-tur')).toBeNull()
  })

  it('falder tilbage til den gamle regel naar signalet ikke er givet', () => {
    // Kald uden `svarRuller` (fx andre flader) skal opfoere sig uaendret:
    // arbejde koerer naar strommen er i gang og svaret ikke er begyndt.
    const view = render(<RaekkeTranskript blocks={TUR} streaming />)
    expect(gruppeSkjult(view.container)).toBe(false)
  })
})
