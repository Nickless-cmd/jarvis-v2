/**
 * MÅLING, ikke en vagt: de to flader behandler manuel fold under arbejde
 * forskelligt — og forskellen er utestet.
 *
 * Baggrunden er fold-arbejdet 30/10-2026. Da jeg gennemgik `TurHoved`s to
 * kaldssteder fandt jeg:
 *
 *   RaekkeTranskript.tsx:475   koerer={arbejdeKoerer && aabenManuelt === null}
 *   ChatFlowPresentation.tsx   koerer={arbejdeKoerer}
 *
 * `koerer` sætter `data-koerer`, som driver `.rv-ikon-glimt` og `.shimmer`
 * (raekkevisning.css:172-183). Konsekvensen er:
 *
 *   code mode: folder du arbejdet ind under en kørende tur, STOPPER shimmeren
 *   chat mode: folder du arbejdet ind under en kørende tur, FORTSÆTTER den
 *
 * Git-historikken (e2e300652) viser at guarden er ÆLDRE end `arbejdeKoerer`:
 * den var oprindeligt `streaming && aabenManuelt === null`, og commit'en
 * byttede kun `streaming` ud med `arbejdeKoerer`. Ingen test vogter den.
 *
 * AFGJORT 30/10-2026: fladerne er ensrettet til chat-modens form, så begge
 * beholder signalet. Begrundelsen er at `koerer` beskriver TUREN, ikke folden:
 * at folde detaljerne væk stopper ikke arbejdet, og et signal der slukker
 * mens turen kører er en løgn i fladen. Guarden var desuden et levn — den
 * fandtes før `arbejdeKoerer` (e2e300652 byttede kun `streaming` ud), og
 * ingen test vogtede den.
 *
 * Filen er nu en VAGT, ikke en måling: den holder de to flader ens. Sætter
 * nogen guarden tilbage i `RaekkeTranskript`, bliver code mode-testen rød —
 * det er verificeret ved at mutere koden og se den falde.
 */
import { fireEvent, render } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { RaekkeTranskript } from './RaekkeTranskript'
import { ChatFlowPresentation } from './ChatFlowPresentation'
import type { ContentBlock } from '../../lib/sseProtocol'

const kald = (navn: string, input: Record<string, unknown> = {}): ContentBlock => ({
  type: 'tool_use',
  id: `t-${navn}`,
  name: navn,
  input,
} as ContentBlock)

/** Arbejde uden svar: turen kører og der er intet final-svar endnu. */
const arbejdeUnderTur: ContentBlock[] = [
  { type: 'thinking', thinking: 'Jeg leder.', seconds: 3 } as ContentBlock,
  kald('read_file'),
]

describe('koerer — ensrettet 30/10-2026', () => {
  it('code mode: manuel fold BEHOLDER data-koerer mens turen kører', () => {
    const { container } = render(
      <RaekkeTranskript blocks={arbejdeUnderTur} streaming runId="run-divergens" />,
    )
    const hoved = container.querySelector('.rv-tur') as HTMLElement
    expect(hoved).toHaveAttribute('data-koerer')

    fireEvent.click(hoved)

    // ENSRETTET 30/10-2026. Før stod der `arbejdeKoerer && aabenManuelt === null`
    // her, så signalet forsvandt når brugeren foldede DETALJERNE væk — selv om
    // turen kørte videre. Det var en løgn i fladen, og guarden var et levn fra
    // før `arbejdeKoerer` fandtes (e2e300652 byttede kun `streaming` ud).
    //
    // Signalet beskriver TUREN, ikke folden. Folden skjuler detaljerne;
    // den stopper ikke arbejdet.
    expect(hoved).toHaveAttribute('aria-expanded', 'false')
    expect(hoved).toHaveAttribute('data-koerer')
  })

  it('chat mode: manuel fold BEHOLDER data-koerer mens turen kører', () => {
    const { container } = render(
      <ChatFlowPresentation
        mode="living"
        density="compact"
        blocks={arbejdeUnderTur}
        streaming
        status="working"
        finalAnswerStarted={false}
        runId="run-divergens"
      />,
    )
    const hoved = container.querySelector('.rv-tur') as HTMLElement
    expect(hoved).toHaveAttribute('data-koerer')

    fireEvent.click(hoved)

    // MÅLT: folden lukker PRÆCIS som i code mode — men her er der ingen
    // guard, så «jeg arbejder»-signalet bliver stående.
    //
    // Det er den skarpe kontrast: samme brugerhandling, samme fold-tilstand
    // (`aria-expanded="false"` begge steder), forskelligt signal. Fladerne
    // er altså ikke uenige om HVAD der skete — kun om hvad det betyder.
    expect(hoved).toHaveAttribute('aria-expanded', 'false')
    expect(hoved).toHaveAttribute('data-koerer')
  })
})
