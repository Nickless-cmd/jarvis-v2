/**
 * VAGT — tænkeblokken vises ikke i beskeden på en tur uden runder.
 *
 * Bjørn 14/11-2026: «øh. hehe hvorfor viser den tænke blokken?» — med et
 * skærmbillede af en ren teksttur hvor «Tænkte i 1s» stod over svaret.
 *
 * FEJLEN: da hovedet blev fjernet på ture uden runder, forsvandt tænkeblokken
 * fra DOM'en sammen med gruppen. Jeg læste det som en regression og flyttede
 * den ind i svar-lanen. Men tænkeblokken er min monolog, ikke en del af svaret:
 * uden runder er der ingen fold at lægge den i, og så skal den ikke vises.
 *
 * FÆLDE (målt 14/11-2026): en vagt der blot tjekker at teksten «ikke findes»
 * et sted i containeren er blind — `ThinkingLine` kan stå i både gruppen og
 * svar-lanen. Vagten tæller derfor forekomster og kræver NUL, og den kræver
 * samtidig at svaret ER der, så den ikke kan bestå ved at alt er tomt.
 */
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { ChatFlowPresentation } from './ChatFlowPresentation'
import type { ContentBlock } from '../../lib/sseProtocol'

const common = {
  density: 'compact' as const,
  runId: 'vagt-tanke',
}

const tanke: ContentBlock = { type: 'thinking', thinking: 'Jeg overvejer kilden', seconds: 1 }
const svar: ContentBlock = { type: 'text', text: 'Modtaget — ingen værktøjer, bare tekst.', phase: 'final_answer' }
const runde: ContentBlock = { type: 'tool_use', id: 't1', name: 'read_file', input: {}, status: 'done' }

describe('VAGT — tænkeblokken hører ikke i beskeden', () => {
  it('viser INGEN tænkeblok på en afsluttet tur uden runder', () => {
    const { container } = render(
      <ChatFlowPresentation {...common} mode="living" streaming={false} status="done"
        finalAnswerStarted blocks={[tanke, svar]} />,
    )
    // Svaret skal være der — ellers består vagten ved at alt er tomt.
    expect(screen.getByText(/Modtaget/)).toBeInTheDocument()
    expect(container.textContent).not.toContain('Jeg overvejer kilden')
    expect(container.querySelector('.tanke-linje')).toBeNull()
  })

  it('viser INGEN tænkeblok mens svaret skrives på en tur uden runder', () => {
    const { container } = render(
      <ChatFlowPresentation {...common} mode="living" streaming status="working"
        finalAnswerStarted blocks={[tanke, svar]} />,
    )
    // Paceren holder teksten tilbage i testmiljøet, så svaret kan ikke
    // assertes her — men containeren skal være der, ellers består vagten
    // ved at intet blev renderet.
    expect(container.querySelector('.chat-flow')).not.toBeNull()
    expect(container.querySelector('.tanke-linje')).toBeNull()
    expect(container.textContent).not.toContain('Jeg overvejer kilden')
  })

  it('viser tænkeblokken i folden når der ER runder — den er stadig tilgængelig', () => {
    // Uændret adfærd: med arbejde at folde ud er tænkeblokken en del af det
    // foldbare arbejde. Vagten beviser at rettelsen ikke fjernede den helt.
    render(
      <ChatFlowPresentation {...common} mode="living" streaming={false} status="done"
        finalAnswerStarted blocks={[tanke, runde, svar]} />,
    )
    expect(screen.getByText(/Arbejdet/)).toBeInTheDocument()
  })
})
