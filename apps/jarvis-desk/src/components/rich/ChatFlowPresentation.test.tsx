import { fireEvent, render, screen, within } from '@testing-library/react'
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
  density: 'compact' as const,
  streaming: true,
  status: 'working' as const,
  finalAnswerStarted: false,
  runId: 'run-1',
}

describe('ChatFlowPresentation', () => {
  it('renders only the latest three real Living syntheses with no placeholders', () => {
    const { rerender } = render(<ChatFlowPresentation {...common} mode="living"
      blocks={['Et', 'To', 'Tre', 'Fire'].map(summary)} />)
    const rail = screen.getByTestId('chat-flow-activity')
    expect(within(rail).queryByText('Et')).not.toBeInTheDocument()
    expect(within(rail).getAllByTestId('chat-flow-synthesis')).toHaveLength(3)
    expect(within(rail).getByText('Fire')).toBeInTheDocument()

    rerender(<ChatFlowPresentation {...common} mode="living" blocks={[]} />)
    expect(screen.queryByTestId('chat-flow-synthesis')).not.toBeInTheDocument()
    expect(screen.queryByText('Jarvis tænker ...')).not.toBeInTheDocument()
  })

  it('renders only the latest Calm status and a truthful neutral fallback', () => {
    const { rerender } = render(<ChatFlowPresentation {...common} mode="calm"
      blocks={['Et', 'To', 'Tre'].map(summary)} />)
    const rail = screen.getByTestId('chat-flow-activity')
    expect(within(rail).getAllByTestId('chat-flow-synthesis')).toHaveLength(1)
    expect(within(rail).getByText('Tre')).toBeInTheDocument()
    expect(within(rail).queryByText('To')).not.toBeInTheDocument()

    rerender(<ChatFlowPresentation {...common} mode="calm" blocks={[]} />)
    expect(screen.getByText('Jarvis tænker ...')).toBeInTheDocument()
  })

  it('keeps raw tool logs out of the activity rail', () => {
    const progress: ContentBlock = { type: 'progress', tool_use_id: 't1', parent_tool_use_id: null,
      message: 'Kører kommando: git status', tool: 'bash', hint: 'git status', status: 'running' }
    render(<ChatFlowPresentation {...common} mode="calm" blocks={[progress]}
      workingStep="Kalder bash: git status" />)
    const rail = screen.getByTestId('chat-flow-activity')
    expect(within(rail).queryByText(/git status/i)).not.toBeInTheDocument()
    expect(within(rail).getByText('Jarvis tænker ...')).toBeInTheDocument()
  })

  it('shows the work disclosure before one final answer and keeps deliveries outside it', () => {
    const onWorkExpanded = vi.fn()
    const blocks: ContentBlock[] = [
      { type: 'tool_use', id: 't1', name: 'read_file', input: {}, status: 'done' },
      { type: 'image', src: 'data:image/png;base64,AA', alt: 'Rapport' },
      { type: 'text', text: 'Her er resultatet.' },
    ]
    render(<ChatFlowPresentation {...common} mode="living" blocks={blocks}
      finalAnswerStarted status="working" onWorkExpanded={onWorkExpanded} />)
    const hoved = screen.getByText('Arbejdsforløb').closest('button') as HTMLElement
    expect(hoved).not.toBeNull()
    expect(hoved).toHaveAttribute('aria-expanded', 'false')
    const gruppe = document.querySelector('.chat-flow-gruppe') as HTMLElement
    expect(gruppe).not.toBeNull()
    expect(within(gruppe).queryByText('Her er resultatet.')).not.toBeInTheDocument()
    expect(screen.getAllByText('Her er resultatet.')).toHaveLength(1)
    const delivery = screen.getByRole('img', { name: 'Rapport' })
    expect(delivery).toBeInTheDocument()
    expect(gruppe).not.toContainElement(delivery)
    fireEvent.click(hoved)
    expect(onWorkExpanded).toHaveBeenCalledTimes(1)
  })

  it('keeps confirmed answer text visible if the run returns to tool work', () => {
    const firstTool: ContentBlock = { type: 'tool_use', id: 't1', name: 'search', input: {}, status: 'done' }
    const firstAnswer: ContentBlock = { type: 'text', text: 'Første bekræftede svar.' }
    const view = render(<ChatFlowPresentation {...common} mode="living"
      blocks={[firstTool, firstAnswer]} finalAnswerStarted />)
    expect(view.container.querySelector('.chat-flow-answer')).toHaveTextContent('Første bekræftede svar.')

    const secondTool: ContentBlock = { type: 'tool_use', id: 't2', name: 'read_file', input: {}, status: 'done' }
    const secondAnswer: ContentBlock = { type: 'text', text: 'Supplerende svar.' }
    view.rerender(<ChatFlowPresentation {...common} mode="living"
      blocks={[firstTool, firstAnswer, secondTool, secondAnswer]} finalAnswerStarted />)

    const gruppe = document.querySelector('.chat-flow-gruppe') as HTMLElement
    expect(within(gruppe).queryByText('Første bekræftede svar.')).not.toBeInTheDocument()
    expect(view.container.querySelector('.chat-flow-answer')).toHaveTextContent('Første bekræftede svar.')
    expect(view.container.querySelector('.chat-flow-answer')).toHaveTextContent('Supplerende svar.')
  })

  it.each([
    ['interrupted' as const, 'Arbejdsforløb afbrudt'],
    ['error' as const, 'Arbejdsforløb fejlede'],
  ])('preserves partial text and uses honest %s copy', (status, label) => {
    render(<ChatFlowPresentation {...common} mode="living" status={status} streaming={false}
      blocks={[
        { type: 'thinking', thinking: 'arbejde' },
        { type: 'text', text: 'Et bevaret delsvar.' },
      ]} />)
    expect(screen.getByText(label)).toBeInTheDocument()
    expect(screen.getAllByText('Et bevaret delsvar.')).toHaveLength(1)
  })

  it('viser synteserne OVER arbejdsrunderne under ét turhoved — ikke som to grene', () => {
    const blocks: ContentBlock[] = [
      summary('Fandt kilden', 1),
      { type: 'tool_use', id: 't1', name: 'read_file', input: {}, status: 'done' },
      summary('Læste filen', 2),
    ]
    render(<ChatFlowPresentation {...common} mode="living" blocks={blocks} />)
    const hoved = document.querySelector('.rv-tur') as HTMLElement
    expect(hoved).not.toBeNull()
    expect(hoved).toHaveAttribute('aria-expanded', 'true')
    expect(hoved).toHaveAttribute('data-koerer')
    const gruppe = document.querySelector('.chat-flow-gruppe') as HTMLElement
    expect(gruppe).not.toBeNull()
    expect(gruppe).not.toHaveAttribute('hidden')
    const synteser = within(gruppe).getAllByTestId('chat-flow-synthesis')
    expect(synteser).toHaveLength(2)
    const detaljer = gruppe.querySelector('.chat-flow-work-details') as HTMLElement
    expect(detaljer).not.toBeNull()
    // Synteserne skal stå FØR arbejdsdetaljerne i DOM-rækkefølgen.
    expect(synteser[0]!.compareDocumentPosition(detaljer) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
  })

  it('klapper hovedet sammen når turen er ovre, så arbejdet bliver detaljer', () => {
    render(<ChatFlowPresentation {...common} mode="living" streaming={false} status="done"
      blocks={[summary('Fandt kilden', 1), { type: 'text', text: 'Svaret.' }]} />)
    const hoved = document.querySelector('.rv-tur') as HTMLElement
    expect(hoved).toHaveAttribute('aria-expanded', 'false')
    expect(hoved).not.toHaveAttribute('data-koerer')
    expect(document.querySelector('.chat-flow-gruppe')).toHaveAttribute('hidden')
  })

  it('marks its bounded activity viewport for motion-safe styling and one polite announcement', () => {
    render(<ChatFlowPresentation {...common} mode="living" blocks={[summary('Fandt svaret', 1)]} />)
    const rail = screen.getByTestId('chat-flow-activity')
    expect(rail).toHaveClass('chat-flow-activity--motion-safe')
    expect(screen.getAllByRole('status')).toHaveLength(1)
  })
})

describe('ChatFlowPresentation — turhovedet fra første ord', () => {
  // Bjørn 17/10-2026: «lige som i code mode skal turhoved vises hele tiden
  // før de første ord». Uden dette stod hovedet stille i det vindue hvor
  // turen lige var startet og intet arbejde var rapporteret endnu.
  it('viser turhovedet med det samme turen kører — også uden arbejde og synteser', () => {
    render(<ChatFlowPresentation {...common} mode="living" blocks={[]} />)
    const hoved = document.querySelector('.rv-tur') as HTMLElement
    expect(hoved).not.toBeNull()
    expect(hoved).toHaveAttribute('data-koerer')
    expect(hoved).toHaveTextContent('Working…')
  })

  it('viser ikke turhovedet på en afsluttet tur uden arbejde', () => {
    render(<ChatFlowPresentation {...common} mode="living" blocks={[]}
      streaming={false} status="done" finalAnswerStarted />)
    expect(document.querySelector('.rv-tur')).toBeNull()
  })
})
