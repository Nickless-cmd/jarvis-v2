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
import { render } from '@testing-library/react'
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
  it('code mode: der er intet hoved at folde mens turen kører', () => {
    // VENDT 15/11-2026 (Bjørn): «turhoved forsætte som det er nu men gøres
    // usynligt indtil hoved folder». Spørgsmålet om `data-koerer` overlever en
    // manuel fold bliver dermed meningsløst i code mode: hovedet findes ikke
    // mens turen kører, så der er intet at klikke på. Rundelinjen er turens
    // ansigt, og den bærer `data-koerer` selv.
    const { container, rerender } = render(
      <RaekkeTranskript blocks={arbejdeUnderTur} streaming runId="run-divergens" />,
    )
    expect(container.querySelector('.rv-tur')).toBeNull()
    expect(container.querySelector('.rv-gruppe')).not.toHaveAttribute('hidden')

    // Når turen folder, lander hovedet — foldet, med turens signal på sig.
    rerender(<RaekkeTranskript blocks={arbejdeUnderTur} streaming={false} runId="run-divergens" />)
    const hoved = container.querySelector('.rv-tur') as HTMLElement
    expect(hoved).toHaveAttribute('aria-expanded', 'false')
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
    // VENDT 18/11-2026: hovedet findes nu under turen i chat mode — og det er
    // netop derfor det kan bære `data-koerer`. Divergensen mod code mode er
    // væk: begge flader har et hoved der står gennem turen.
    const hoved = container.querySelector('.rv-tur') as HTMLElement
    expect(hoved).not.toBeNull()
    expect(hoved).toHaveAttribute('data-koerer')
    const gruppe = container.querySelector('.chat-flow-gruppe-ydre') as HTMLElement
    expect(gruppe).toHaveAttribute('data-aaben', 'true')
    expect(container.querySelector('[data-testid="chat-flow-round-line"]')).not.toBeNull()
  })
})
