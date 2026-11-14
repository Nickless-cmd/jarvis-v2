/**
 * Hovedet skal folde UD igen når der kommer arbejde efter svar-låsen.
 *
 * Bjørn 29/10-2026: «hoved folder, streamen forsætter inde i hoved -> tom
 * skærm -> stream slut -> pace starter uden for tur hoved».
 *
 * ChatView sender `finalAnswerStarted={finalAnswerStarted || svarLaast}`, så
 * `finalAnswerStarted` er sand i hele vinduet efter låsen. Uden et separat
 * signal foldede hovedet, og det nye runs commentary-tekst lå i en foldet
 * liste indtil streamen sluttede.
 */
import { render } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { ChatFlowPresentation } from './ChatFlowPresentation'
import type { ContentBlock } from '../../lib/sseProtocol'

vi.mock('../../lib/useChatPacedBlocks', () => ({
  useChatPacedBlocks: (blocks: ContentBlock[]) => blocks,
}))

function summary(text: string, index: number): ContentBlock {
  return { type: 'tool_use_summary', summary: text, preceding_tool_use_ids: [`t${index}`] }
}

const common = {
  mode: 'living' as const,
  density: 'compact' as const,
  streaming: true,
  status: 'working' as const,
  runId: 'run-2',
}

describe('ChatFlowPresentation — arbejde efter svar-låsen', () => {
  it('holder hovedet ÅBENT når et nyt run arbejder efter det låste svar', () => {
    const { container } = render(
      <ChatFlowPresentation
        {...common}
        blocks={[summary('Læser filen', 1)]}
        finalAnswerStarted
        arbejdeEfterSvar
      />,
    )

    // VENDT 14/11-2026 (Bjørn): «gem turhoved til det foldes». Hovedet findes
    // ikke mens turen kører — så det er GRUPPEN der bærer den åbne tilstand.
    // Kravet er uændret: arbejde efter svar-låsen skal stadig være synligt.
    expect(container.querySelector('.rv-tur')).toBeNull()
    expect(container.querySelector('.chat-flow-gruppe-ydre')).toHaveAttribute('data-aaben', 'true')
  })

  it('folder stadig sammen når svaret er begyndt UDEN arbejde bagefter', () => {
    const { container } = render(
      <ChatFlowPresentation
        {...common}
        // VENDT 14/11-2026 (Bjørn): «gem turhoved til det foldes». Hovedet
        // findes først når turen er SLUT — og `common` bærer `streaming: true`,
        // så uden denne linje målte testen en levende tur hvor hovedet med
        // rette venter. Turen skal lukkes for at måle den afsluttede tilstand.
        streaming={false}
        status="done"
        blocks={[summary('Læser filen', 1)]}
        finalAnswerStarted
      />,
    )

    // Turen er slut (intet `arbejdeEfterSvar`), så hovedet findes nu — og det
    // er lukket, fordi der ikke er noget nyt arbejde at vise.
    const hoved = container.querySelector('.rv-tur')
    expect(hoved).not.toBeNull()
    expect(hoved).toHaveAttribute('aria-expanded', 'false')
  })

  it('melder «kører» til hovedet mens det nye run arbejder', () => {
    const { container } = render(
      <ChatFlowPresentation
        {...common}
        blocks={[summary('Læser filen', 1)]}
        finalAnswerStarted
        arbejdeEfterSvar
      />,
    )

    // `data-koerer` er en boolean-attribut: den står der eller står der ikke.
    // Hovedet findes ikke under det nye run, så det er gruppen der skal vise
    // at turen kører — den er åben, og rundelinjen står i den.
    expect(container.querySelector('.rv-tur')).toBeNull()
    expect(container.querySelector('.chat-flow-gruppe-ydre')).toHaveAttribute('data-aaben', 'true')
    expect(container.querySelector('[data-testid="chat-flow-round-line"]')).not.toBeNull()
  })
})
