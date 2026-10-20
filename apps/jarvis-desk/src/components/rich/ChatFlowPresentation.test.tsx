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
  it('replaces the Living status in place instead of accumulating a list', () => {
    const { rerender } = render(<ChatFlowPresentation {...common} mode="living"
      blocks={['Et', 'To', 'Tre', 'Fire'].map(summary)} />)
    const rail = screen.getByTestId('chat-flow-activity')
    expect(within(rail).queryByText('Et')).not.toBeInTheDocument()
    expect(within(rail).queryByText('To')).not.toBeInTheDocument()
    expect(within(rail).queryByText('Tre')).not.toBeInTheDocument()
    expect(within(rail).getAllByTestId('chat-flow-round-label')).toHaveLength(1)
    expect(within(rail).getByText('Fire')).toBeInTheDocument()

    rerender(<ChatFlowPresentation {...common} mode="living" blocks={[]} />)
    expect(screen.queryByTestId('chat-flow-round-label')).not.toBeInTheDocument()
    expect(screen.queryByText('Jarvis tænker ...')).not.toBeInTheDocument()
  })

  it('shows the live status inside the one open work header while streaming', () => {
    render(<ChatFlowPresentation {...common} mode="living" blocks={[summary('Samler svaret', 1)]} />)

    const hoved = document.querySelector('.rv-tur') as HTMLElement
    expect(hoved).toBeInTheDocument()
    expect(hoved).toHaveAttribute('aria-expanded', 'true')
    const gruppe = document.querySelector('.chat-flow-gruppe') as HTMLElement
    expect(gruppe).not.toHaveAttribute('hidden')
    expect(within(gruppe).getByTestId('chat-flow-round-label')).toHaveTextContent('Samler svaret')
    expect(within(hoved).queryByText('Samler svaret')).not.toBeInTheDocument()
  })

  it('renders only the latest Calm status and a truthful neutral fallback', () => {
    const { rerender } = render(<ChatFlowPresentation {...common} mode="calm"
      blocks={['Et', 'To', 'Tre'].map(summary)} />)
    const rail = screen.getByTestId('chat-flow-activity')
    expect(within(rail).getAllByTestId('chat-flow-round-label')).toHaveLength(1)
    expect(within(rail).getByText('Tre')).toBeInTheDocument()
    expect(within(rail).queryByText('To')).not.toBeInTheDocument()

    rerender(<ChatFlowPresentation {...common} mode="calm" blocks={[]} />)
    expect(screen.getByText('Tænker')).toBeInTheDocument()
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
    const hoved = screen.getByText('Arbejdet').closest('button') as HTMLElement
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
    ['interrupted' as const, 'Arbejdet afbrudt'],
    ['error' as const, 'Arbejdet fejlede'],
  ])('preserves partial text and uses honest %s copy', (status, label) => {
    render(<ChatFlowPresentation {...common} mode="living" status={status} streaming={false}
      blocks={[
        { type: 'thinking', thinking: 'arbejde' },
        { type: 'text', text: 'Et bevaret delsvar.' },
      ]} />)
    expect(screen.getByText(label)).toBeInTheDocument()
    expect(screen.getAllByText('Et bevaret delsvar.')).toHaveLength(1)
  })

  it('viser kun den nyeste levende syntese under turhovedet — uden rækkevisning', () => {
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
    const synteser = within(gruppe).getAllByTestId('chat-flow-round-label')
    expect(synteser).toHaveLength(1)
    expect(synteser[0]).toHaveTextContent('Læste filen')
    expect(within(gruppe).queryByText('Fandt kilden')).not.toBeInTheDocument()
    expect(gruppe.querySelector('.chat-flow-work-details')).toBeNull()
  })

  it('viser både den levende syntese og rundelinjen under turhovedet', () => {
    const blocks: ContentBlock[] = [
      { type: 'thinking', thinking: 'Jeg overvejer kilden', seconds: 3 },
      { type: 'tool_use', id: 't1', name: 'read_file', input: {}, status: 'done' },
      { type: 'text', text: 'Jeg fandt årsagen og undersøger næste led.' },
    ]
    render(<ChatFlowPresentation {...common} mode="living" blocks={blocks}
      rundeEtiketter={{ t1: 'Læste konfigurationen' }} varighedSekunder={7} />)

    const live = screen.getByTestId('chat-flow-activity')
    const syntese = within(live).getByTestId('chat-flow-live-synthesis')
    const runde = within(live).getByTestId('chat-flow-round-line')
    expect(syntese).toHaveTextContent('Jeg fandt årsagen og undersøger næste led.')
    expect(within(runde).getByText('Tænker')).toBeInTheDocument()
    expect(runde.querySelector('.rv-turTid')).toHaveAttribute('aria-label', '3s')
    expect(within(runde).getByText('|')).toBeInTheDocument()
    expect(within(runde).getByText('Læste konfigurationen')).toBeInTheDocument()
    expect(runde.querySelector('[data-testid="chat-flow-thinking-icon"]')).toBeInTheDocument()
    expect(syntese.compareDocumentPosition(runde) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    const hoved = document.querySelector('.rv-tur') as HTMLElement
    expect(hoved.querySelector('.rv-turTid')).toHaveAttribute('aria-label', '7s')
    expect(hoved.querySelector('.rv-turIndhold')).toHaveClass('shimmer')
    expect(hoved.querySelector('.rv-turTid')).not.toHaveClass('shimmer')
    expect(runde.querySelector('.rv-turTid')).not.toHaveClass('shimmer')
    expect(within(hoved).queryByText('Læste konfigurationen')).not.toBeInTheDocument()
    expect(document.querySelector('.chat-flow-answer')).toBeNull()
  })

  it('opdaterer levende syntese uden genmontering og morpher rundelinjen med ikon og shimmer', () => {
    const blocks: ContentBlock[] = [
      { type: 'tool_use', id: 't1', name: 'read_file', input: {}, status: 'done' },
      { type: 'text', text: 'Jeg læser' },
    ]
    const view = render(<ChatFlowPresentation {...common} mode="living" blocks={blocks}
      rundeEtiketter={{ t1: 'Læser konfigurationen' }} />)

    const synteseFoer = screen.getByTestId('chat-flow-live-synthesis')
    const runde = screen.getByTestId('chat-flow-round-line')
    expect(runde.querySelector('[data-testid="chat-flow-round-icon"]')).toBeInTheDocument()
    expect(runde.querySelector('.linje-titel')).toHaveClass('shimmer')
    // Syntesen er indhold, ikke aktivitet: intet shimmer på den (Bjørn
    // 17/10-2026). Shimmeret maler gradient ind i teksten og gjorde den grå.
    expect(synteseFoer.querySelector('.linje-titel')).not.toHaveClass('shimmer')

    view.rerender(<ChatFlowPresentation {...common} mode="living" blocks={[
      blocks[0]!, { type: 'text', text: 'Jeg læser videre uden at hoppe' },
    ]} rundeEtiketter={{ t1: 'Tester løsningen' }} />)

    expect(screen.getByTestId('chat-flow-live-synthesis')).toBe(synteseFoer)
    expect(synteseFoer).toHaveTextContent('Jeg læser videre uden at hoppe')
    expect(within(screen.getByTestId('chat-flow-round-line')).getByText('Læser konfigurationen'))
      .toHaveAttribute('aria-hidden', 'true')
    // Animationen bor nu i det indre tekst-lag, og shimmeret på det stabile
    // lag udenom — så sweepet ikke starter forfra ved hvert skift
    // (Bjørn 17/10-2026: «shimmeren staller»).
    const nytLabel = within(screen.getByTestId('chat-flow-round-line')).getByText('Tester løsningen')
    expect(nytLabel).toHaveClass('ls-ind')
    expect(nytLabel.closest('.linje-titel')).toHaveClass('shimmer')
  })

  it('rundelinjen har en fold-pil der folder arbejdet ud UNDER streaming', () => {
    // Bjørn 17/10-2026: «runde linjen under streaming bør have > i ende og
    // kunne foldes ud under streaming». Foldet sammen som udgangspunkt —
    // den levende linje er nok — men pilen lover et indhold der findes.
    const blocks: ContentBlock[] = [
      { type: 'tool_use', id: 't1', name: 'read_file', input: {}, status: 'done' },
      { type: 'text', text: 'Jeg læser videre' },
    ]
    render(<ChatFlowPresentation {...common} mode="living" blocks={blocks}
      rundeEtiketter={{ t1: 'Læser konfigurationen' }} />)

    const fold = screen.getByTestId('chat-flow-round-fold')
    expect(fold).toHaveAttribute('aria-expanded', 'false')
    expect(document.querySelector('.chat-flow-work-details')).toBeNull()

    fireEvent.click(fold)
    expect(document.querySelector('.chat-flow-work-details')).not.toBeNull()
    // Udfoldet tilstand ER den levende kronologiske visning. Den kompakte
    // statusrail må ikke fortsætte ovenover og vise samme syntese to steder.
    expect(screen.queryByTestId('chat-flow-activity')).not.toBeInTheDocument()
    expect(document.querySelector('.chat-flow-work-details')).toHaveTextContent('Jeg læser videre')

    fireEvent.click(document.querySelector('.rv-tur') as HTMLElement)
    expect(document.querySelector('.chat-flow-gruppe')).toHaveAttribute('hidden')
    expect(document.querySelector('.chat-flow-work-details')).toBeNull()
  })

  it('holder den forrige syntese stående mens den næste blok er tom — intet glip', () => {
    // Bjørn 17/10-2026: «når syntese linjen forsvinder den første og et glip
    // og så streames den næste». En ny tekstblok starter tom; den gamle skal
    // blive stående indtil den nye har indhold.
    const blocks: ContentBlock[] = [
      { type: 'tool_use', id: 't1', name: 'read_file', input: {}, status: 'done' },
      { type: 'text', text: 'Fandt kilden' },
    ]
    const view = render(<ChatFlowPresentation {...common} mode="living" blocks={blocks} />)
    const syntese = screen.getByTestId('chat-flow-live-synthesis')
    expect(syntese).toHaveTextContent('Fandt kilden')

    view.rerender(<ChatFlowPresentation {...common} mode="living" blocks={[
      blocks[0]!,
      { type: 'text', text: 'Fandt kilden' },
      { type: 'tool_use', id: 't2', name: 'bash', input: {}, status: 'running' },
      { type: 'text', text: '' },
    ]} />)

    expect(screen.getByTestId('chat-flow-live-synthesis')).toBe(syntese)
    expect(syntese).toHaveTextContent('Fandt kilden')
  })

  it('en ny syntese krydsfader i stedet for at hoppe', () => {
    const blocks: ContentBlock[] = [
      { type: 'tool_use', id: 't1', name: 'read_file', input: {}, status: 'done' },
      { type: 'text', text: 'Fandt kilden' },
    ]
    const view = render(<ChatFlowPresentation {...common} mode="living" blocks={blocks} />)
    view.rerender(<ChatFlowPresentation {...common} mode="living" blocks={[
      blocks[0]!,
      { type: 'text', text: 'Fandt kilden' },
      { type: 'tool_use', id: 't2', name: 'bash', input: {}, status: 'done' },
      { type: 'text', text: 'Læste filen' },
    ]} />)

    const linje = screen.getByTestId('chat-flow-live-synthesis')
    // Den gamle står stadig (på vej ud) oveni den nye — der er ingen frame
    // hvor linjen er tom.
    expect(within(linje).getByTestId('syntese-gammel')).toHaveTextContent('Fandt kilden')
    expect(within(linje).getByText('Læste filen')).toBeInTheDocument()
  })

  it('klapper hovedet sammen når turen er ovre, så arbejdet bliver detaljer', () => {
    render(<ChatFlowPresentation {...common} mode="living" streaming={false} status="done"
      blocks={[summary('Fandt kilden', 1), { type: 'text', text: 'Svaret.' }]} />)
    const hoved = document.querySelector('.rv-tur') as HTMLElement
    expect(hoved).toHaveAttribute('aria-expanded', 'false')
    expect(hoved).not.toHaveAttribute('data-koerer')
    expect(document.querySelector('.chat-flow-gruppe')).toHaveAttribute('hidden')
  })

  it('viser turens ur i hovedet — sekunder, og minutter efter et minut', () => {
    const blokke = [summary('Fandt kilden', 1)]
    // Cifrene er delt i lodrette strimler, så den flade tekst læses fra
    // `aria-label` — det er også den skærmlæserne får.
    const ur = () => document.querySelector('.rv-turTid')?.getAttribute('aria-label')
    const { rerender } = render(<ChatFlowPresentation {...common} mode="living" streaming={false}
      status="done" finalAnswerStarted turStart={Date.now() - 12_000} blocks={blokke} />)
    expect(ur()).toMatch(/^1[12]s$/)

    rerender(<ChatFlowPresentation {...common} mode="living" streaming={false}
      status="done" finalAnswerStarted turStart={Date.now() - 72_000} blocks={blokke} />)
    expect(ur()).toMatch(/^1m 1[12]s$/)
  })

  it('beholder uret når strømmen er forbi — det fryser på turens sluttid', () => {
    const start = Date.now() - 95_000
    render(<ChatFlowPresentation {...common} mode="living" streaming={false} status="done"
      finalAnswerStarted turStart={start} turSlut={start + 95_000} blocks={[summary('Fandt kilden', 1)]} />)
    // 95 sekunder, målt fra start til slut — ikke fra start til nu.
    expect(document.querySelector('.rv-turTid')?.getAttribute('aria-label')).toBe('1m 35s')
  })

  it('fjerner den levende syntese efter turen, men bevarer arbejdsdetaljerne', () => {
    render(<ChatFlowPresentation {...common} mode="living" streaming={false} status="done"
      finalAnswerStarted blocks={[
        summary('Fandt kilden', 1),
        { type: 'tool_use', id: 't1', name: 'read_file', input: {}, status: 'done' },
        { type: 'text', text: 'Svaret.' },
      ]} />)
    const hoved = document.querySelector('.rv-tur') as HTMLElement
    expect(hoved).toHaveAttribute('aria-expanded', 'false')

    fireEvent.click(hoved)
    const gruppe = document.querySelector('.chat-flow-gruppe') as HTMLElement
    expect(gruppe).not.toHaveAttribute('hidden')
    expect(within(gruppe).queryByTestId('chat-flow-synthesis')).not.toBeInTheDocument()
    expect(gruppe.querySelector('.chat-flow-work-details')).not.toBeNull()

    // Og den afsluttede besked bærer den ikke som brødtekst.
    const svar = document.querySelector('.chat-flow-answer') as HTMLElement
    expect(within(svar).queryByText('Fandt kilden')).not.toBeInTheDocument()
  })

  it('holder syntesen ved dens runde i udfoldningen og ude af slutsvaret', () => {
    const blocks: ContentBlock[] = [
      { type: 'tool_use', id: 't1', name: 'read_file', input: {}, status: 'done' },
      { type: 'text', text: 'Jeg fandt årsagen og går videre.' },
      { type: 'tool_use_summary', summary: 'Læste konfigurationen',
        preceding_tool_use_ids: ['t1'], thinking_summary: 'Mistænkte en gammel indstilling' },
      { type: 'tool_use', id: 't2', name: 'bash', input: { command: 'npm test' }, status: 'done' },
      { type: 'text', text: 'Alt er rettet.' },
    ]
    render(<ChatFlowPresentation {...common} mode="living" blocks={blocks}
      streaming={false} status="done" finalAnswerStarted />)

    const hoved = document.querySelector('.rv-tur') as HTMLElement
    fireEvent.click(hoved)
    const gruppe = document.querySelector('.chat-flow-gruppe') as HTMLElement
    expect(within(gruppe).getByText('Jeg fandt årsagen og går videre.')).toBeInTheDocument()
    expect(within(gruppe).getByText('Læste konfigurationen')).toBeInTheDocument()
    expect(within(gruppe).getByText('Mistænkte en gammel indstilling')).toBeInTheDocument()

    const svar = document.querySelector('.chat-flow-answer') as HTMLElement
    expect(within(svar).getByText('Alt er rettet.')).toBeInTheDocument()
    expect(within(svar).queryByText('Jeg fandt årsagen og går videre.')).not.toBeInTheDocument()
    expect(within(svar).queryByText('Læste konfigurationen')).not.toBeInTheDocument()
  })

  it('viser historiske synteser i folden selv om final_answer_start ikke genindlæses', () => {
    const blocks: ContentBlock[] = [
      { type: 'text', text: 'Jeg tjekker først repoet.' },
      { type: 'tool_use', id: 't1', name: 'bash', input: {}, status: 'done' },
      { type: 'text', text: 'Nu tjekker jeg visningen.' },
      { type: 'tool_use', id: 't2', name: 'bash', input: {}, status: 'done' },
      { type: 'tool_use_summary', summary: 'Genbyggede desk-web’en', preceding_tool_use_ids: ['t2'] },
      { type: 'text', text: 'Kørt to runder. Her er resultatet.' },
      { type: 'progress', tool_use_id: 't2', parent_tool_use_id: null,
        message: 'Kører kommando', tool: 'bash', hint: '', status: 'done' },
    ]
    render(<ChatFlowPresentation {...common} mode="living" blocks={blocks}
      streaming={false} status="done" finalAnswerStarted={false} />)

    fireEvent.click(document.querySelector('.rv-tur') as HTMLElement)
    const gruppe = document.querySelector('.chat-flow-gruppe') as HTMLElement
    expect(within(gruppe).getByText('Jeg tjekker først repoet.')).toBeInTheDocument()
    expect(within(gruppe).getByText('Nu tjekker jeg visningen.')).toBeInTheDocument()

    const svar = document.querySelector('.chat-flow-answer') as HTMLElement
    expect(within(svar).getByText('Kørt to runder. Her er resultatet.')).toBeInTheDocument()
    expect(within(svar).queryByText('Jeg tjekker først repoet.')).not.toBeInTheDocument()
    expect(within(svar).queryByText('Nu tjekker jeg visningen.')).not.toBeInTheDocument()
  })

  it('marks its bounded activity viewport for motion-safe styling and one polite announcement', () => {
    render(<ChatFlowPresentation {...common} mode="living" blocks={[
      { type: 'tool_use', id: 't1', name: 'read_file', input: {}, status: 'done' },
      { type: 'text', text: 'Jeg samler svaret.' },
    ]} />)
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
    expect(hoved).toHaveTextContent('Tænker')
    expect(hoved).toHaveAttribute('data-skillelinje')
  })

  it('beholder skillelinjen gennem hele chat-streamen', () => {
    const view = render(<ChatFlowPresentation {...common} mode="living" blocks={[]} />)
    expect(document.querySelector('.rv-tur')).toHaveAttribute('data-skillelinje')

    view.rerender(<ChatFlowPresentation {...common} mode="living" blocks={[
      { type: 'text', text: 'Mellemstatus', phase: 'commentary' },
    ]} />)
    expect(document.querySelector('.rv-tur')).toHaveAttribute('data-skillelinje')

    view.rerender(<ChatFlowPresentation {...common} mode="living" blocks={[
      { type: 'text', text: 'Svaret', phase: 'final_answer' },
    ]} finalAnswerStarted />)
    expect(document.querySelector('.rv-tur')).toHaveAttribute('data-skillelinje')
  })

  it('beholder hovedet og uret på en tur uden værktøjskald', () => {
    // Bjørn 17/10-2026: «tur hoved vises ikke hvis han ikk kalder tools…
    // det skal være der osse uden tool kald». Hovedet er turens skillestreg,
    // ikke en overskrift for værktøjskald.
    const { container } = render(<ChatFlowPresentation {...common} mode="living"
      blocks={[{ type: 'text', text: 'Et rent svar.' }]}
      streaming={false} status="done" finalAnswerStarted varighedSekunder={12} />)
    const hoved = container.querySelector('.rv-tur') as HTMLElement
    expect(hoved).not.toBeNull()
    // Intet at folde → hovedet er ikke en knap, og pilen er væk.
    expect(hoved.tagName).toBe('DIV')
    expect(container.querySelector('.rv-turC')).toBeNull()
    expect(container.querySelector('.rv-turTid')?.getAttribute('aria-label')).toBe('12s')
  })

  it('tegner intet hoved når der hverken er arbejde, kørsel eller varighed', () => {
    render(<ChatFlowPresentation {...common} mode="living" blocks={[]}
      streaming={false} status="done" finalAnswerStarted />)
    expect(document.querySelector('.rv-tur')).toBeNull()
  })

  it('melder først den afsluttede live-række klar til persisteret overtagelse', () => {
    const onAnswerPaced = vi.fn()
    render(<ChatFlowPresentation {...common} mode="living"
      blocks={[
        { type: 'tool_use', id: 't1', name: 'bash', input: {}, status: 'done' },
        { type: 'text', text: 'Det færdige svar.' },
      ]}
      streaming={false} status="done" finalAnswerStarted paceFinalAnswer
      onAnswerPaced={onAnswerPaced} />)

    expect(onAnswerPaced).toHaveBeenCalledOnce()
  })
})
