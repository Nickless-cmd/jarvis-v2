import { fireEvent, render, screen, within } from '@testing-library/react'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
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
  it('viser output-tokens i turhovedet — ikke i rundelinjen', () => {
    // RETTET 14/11-2026 (Bjørn): «du har blandet turhoved ind i rundelinjen i
    // stedet for at lade dem være adskilt». Tallet hører i hovedet — det er
    // turens RESULTAT. Rundelinjen siger hvad der sker nu; hovedet hvad turen
    // kostede. De skal ikke bære det samme.
    const arbejde: ContentBlock = { type: 'tool_use', id: 't1', name: 'read_file', input: {}, status: 'done' }
    const { container } = render(<ChatFlowPresentation {...common} mode="living" streaming={false}
      status="done" blocks={[arbejde]} tokens={321} varighedSekunder={12} />)
    expect(container.querySelector('.rv-turMeta .rullende')).toHaveAttribute('aria-label', '321')
    expect(container.querySelector('.rv-turMeta')).toHaveTextContent('output')
    expect(container.querySelector('.chat-flow-round-tokens')).toBeNull()
    expect(container.querySelector('.chat-flow-round-tid')).toBeNull()

    // Rækkefølgen ER kontrakten (Bjørn 14/11-2026: tallet «hørte til i enden af
    // turhoved»). Uret beskriver VARIGHEDEN og står derfor først; token-tallet
    // beskriver RESULTATET og står i enden. Stod det omvendt, læste linjen som
    // om tallet var en del af tiden.
    const tid = container.querySelector('.rv-turTid')
    const meta = container.querySelector('.rv-turMeta')
    expect(tid).not.toBeNull()
    expect(meta).not.toBeNull()
    expect(tid!.compareDocumentPosition(meta!) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
  })

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
    // OVERLEVERINGEN (14/11-2026): uden runder bærer rundelinjen hovedets ord,
    // så der er én linje og ikke to. Den gamle fallback («Jarvis tænker ...»)
    // var en anden sætning om det samme — den er væk.
    expect(within(screen.getByTestId('chat-flow-round-line')).getByText('Tænker')).toBeInTheDocument()
    expect(screen.queryByText('Jarvis tænker ...')).not.toBeInTheDocument()
  })

  it('viser den levende status i rundelinjen — uden et turhoved over den', () => {
    // VENDT 14/11-2026 (Bjørn): mens turen kører er rundelinjen turens ansigt.
    // Hovedet findes ikke endnu, så der er ingen «åben header» at lægge
    // statusen i — den står i gruppen, som stadig er åben.
    render(<ChatFlowPresentation {...common} mode="living" streaming status="working"
      blocks={[summary('Samler svaret', 1)]} />)

    expect(document.querySelector('.rv-tur')).toBeNull()
    const gruppe = document.querySelector('.chat-flow-gruppe') as HTMLElement
    expect(gruppe.closest('.chat-flow-gruppe-ydre')).toHaveAttribute('data-aaben', 'true')
    expect(within(gruppe).getByTestId('chat-flow-round-label')).toHaveTextContent('Samler svaret')
  })

  it.each(['Arbejder', 'Arbejder…', 'Arbejder...'])(
    'viser Tænker i rundelinjen ved den generiske mellemtilstand %s',
    (workingStep) => {
      render(<ChatFlowPresentation {...common} mode="living"
        blocks={[{ type: 'tool_use', id: 't1', name: 'read_file', input: {}, status: 'done' }]}
        workingStep={workingStep} />)

      // Hovedet findes ikke mens turen kører (14/11-2026), så der er ingen
      // «Arbejder»-etiket at sammenligne med — kun rundelinjens eget ord.
      expect(document.querySelector('.rv-tur')).toBeNull()
      const runde = screen.getByTestId('chat-flow-round-line')
      expect(within(runde).getByText('Tænker')).toBeInTheDocument()
      expect(within(runde).queryByText(/^Arbejder/)).not.toBeInTheDocument()
    },
  )

  it('bevarer konkrete faseforklaringer i rundelinjen', () => {
    render(<ChatFlowPresentation {...common} mode="living"
      blocks={[{ type: 'tool_use', id: 't1', name: 'read_file', input: {}, status: 'done' }]}
      workingStep="Læser konfigurationen" />)

    const runde = screen.getByTestId('chat-flow-round-line')
    expect(within(runde).getByText('Læser konfigurationen')).toBeInTheDocument()
    expect(within(runde).queryByText('Tænker')).not.toBeInTheDocument()
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
    // VENDT 14/11-2026 (Bjørn): hovedet findes først når turen er slut, så
    // der er ingen «Arbejdet»-knap at folde ud under streamen. Folden bor nu
    // på rundelinjen, som ER turens ansigt indtil turen slutter.
    expect(screen.queryByText('Arbejdet')).not.toBeInTheDocument()
    const gruppe = document.querySelector('.chat-flow-gruppe') as HTMLElement
    expect(gruppe).not.toBeNull()
    expect(within(gruppe).queryByText('Her er resultatet.')).not.toBeInTheDocument()
    expect(screen.getAllByText('Her er resultatet.')).toHaveLength(1)
    const delivery = screen.getByRole('img', { name: 'Rapport' })
    expect(delivery).toBeInTheDocument()
    expect(gruppe).not.toContainElement(delivery)
  })

  it('renders split stream blocks as one markdown answer without breaking a word', () => {
    render(<ChatFlowPresentation {...common} mode="living" finalAnswerStarted blocks={[
      { type: 'text', text: 'L', phase: 'final_answer' },
      { type: 'text', text: 'ukket — du bekræftede selv leveringen.', phase: 'final_answer' },
    ]} />)

    const answer = document.querySelector('.chat-flow-answer') as HTMLElement
    expect(answer).toHaveTextContent('Lukket — du bekræftede selv leveringen.')
    expect(answer.querySelectorAll('p')).toHaveLength(1)
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
    // VENDT 14/11-2026: teksten må ikke stå som ARBEJDSDETALJE (foldet indhold)
    // — den hører i svar-lanen. Den kan stadig stå i den levende synteselinje,
    // som er turens ansigt mens den kører; det er en anden flade med en anden
    // rolle, og den forsvinder når turen slutter.
    expect(gruppe.querySelector('.chat-flow-work-details')).toBeNull()
    expect(view.container.querySelector('.chat-flow-answer')).toHaveTextContent('Første bekræftede svar.')
    expect(view.container.querySelector('.chat-flow-answer')).toHaveTextContent('Supplerende svar.')
  })

  it.each([
    ['interrupted' as const, 'Afbrudt'],
    ['error' as const, 'Fejlede'],
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
    render(<ChatFlowPresentation {...common} mode="living" streaming status="working" blocks={blocks} />)
    // VENDT 14/11-2026 (Bjørn): hovedet findes først når turen er slut, så
    // der er intet hoved at folde ud under streamen — gruppen står åben af
    // sig selv, fordi rundelinjen ER turens ansigt.
    expect(document.querySelector('.rv-tur')).toBeNull()
    const gruppe = document.querySelector('.chat-flow-gruppe') as HTMLElement
    expect(gruppe).not.toBeNull()
    expect(gruppe.closest('.chat-flow-gruppe-ydre')).toHaveAttribute('data-aaben', 'true')
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
    expect(within(runde).getByText('Læste konfigurationen')).toBeInTheDocument()
    expect(runde.querySelector('[data-testid="chat-flow-presence"] .jarvis-pulse.is-working')).toBeInTheDocument()
    expect(within(runde).queryByText('Tænker')).not.toBeInTheDocument()
    expect(within(runde).queryByText('|')).not.toBeInTheDocument()
    expect(syntese.compareDocumentPosition(runde) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    // Hverken hoved eller ur findes mens turen kører (14/11-2026): hovedet er
    // resultatet, og rundelinjen bærer ikke hovedets tal. De to linjer er
    // adskilte — rundelinjen er ikke en kopi af hovedet.
    expect(document.querySelector('.rv-tur')).toBeNull()
    expect(runde.querySelector('.chat-flow-round-tid')).toBeNull()
    expect(within(runde).queryByText('Læste konfigurationen')).toBeInTheDocument()
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
    expect(runde.querySelector('[data-testid="chat-flow-presence"] .jarvis-pulse.is-working')).toBeInTheDocument()
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

  it('viser hele den levende syntese uden et trelinjers loft', () => {
    const lang = 'En lang syntese '.repeat(40)
    render(<ChatFlowPresentation {...common} mode="living" blocks={[
      { type: 'tool_use', id: 't1', name: 'read_file', input: {}, status: 'done' },
      { type: 'text', text: lang },
    ]} />)
    expect(screen.getByTestId('chat-flow-live-synthesis')).toHaveTextContent(lang.trim())
    const css = readFileSync(resolve(__dirname, '../../styles/chat-flow.css'), 'utf8')
    const live = css.match(/\.chat-flow-live-synthesis\s*\{([^}]*)\}/)?.[1] ?? ''
    expect(live).not.toMatch(/max-height|overflow:\s*hidden/)
    expect(css).not.toMatch(/\.chat-flow-live-synthesis \.ls-tekst\s*\{[^}]*line-clamp/s)
  })

  it('rundelinjen har en fold-pil der folder arbejdet ud UNDER streaming', () => {
    // Bjørn 17/10-2026: «runde linjen under streaming bør have > i ende og
    // kunne foldes ud under streaming». Foldet sammen som udgangspunkt —
    // den levende linje er nok — men pilen lover et indhold der findes.
    const blocks: ContentBlock[] = [
      { type: 'tool_use', id: 't1', name: 'read_file', input: {}, status: 'done' },
      { type: 'text', text: 'Jeg læser videre' },
    ]
    render(<ChatFlowPresentation {...common} mode="living" streaming status="working" blocks={blocks}
      rundeEtiketter={{ t1: 'Læser konfigurationen' }} />)

    const fold = screen.getByTestId('chat-flow-round-fold')
    expect(fold).toHaveAttribute('aria-expanded', 'false')
    expect(document.querySelector('.chat-flow-work-details')).toBeNull()

    fireEvent.click(fold)
    expect(document.querySelector('.chat-flow-work-details')).not.toBeNull()
    // Udfoldet tilstand ER den levende kronologiske visning. Den kompakte
    // statusrail må ikke fortsætte ovenover og vise samme syntese to steder.
    //
    // VENDT 14/11-2026: containeren bliver stående — den bærer fold-pilen, og
    // uden den var der ingen vej tilbage (målt: knappen forsvandt i samme
    // frame som man foldede ud). Det er SYNTESEN og rundelinjen der skal vige,
    // ikke knappen.
    expect(screen.queryByTestId('chat-flow-live-synthesis')).not.toBeInTheDocument()
    expect(screen.queryByTestId('chat-flow-round')).not.toBeInTheDocument()
    expect(screen.getByTestId('chat-flow-round-fold')).toHaveAttribute('aria-expanded', 'true')
    expect(document.querySelector('.chat-flow-work-details')).toHaveTextContent('Jeg læser videre')

    fireEvent.click(document.querySelector('.chat-flow-round-fold') as HTMLElement)
    // VENDT 14/11-2026 (Bjørn): «gem turhoved til det foldes». Folden følger
    // nu TUREN, ikke det manuelle valg: så længe turen kører, bliver gruppen
    // åben — det er rundelinjen der er turens ansigt. Det manuelle valg styrer
    // stadig om ARBEJDSDETALJERNE vises, og det er hvad der måles her.
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
    expect(document.querySelector('.chat-flow-gruppe-ydre')).toHaveAttribute('data-aaben', 'false')
  })

  it('viser turens levende ur i hovedet — sekunder, og minutter efter et minut', () => {
    // Cifrene er delt i lodrette strimler, så den flade tekst læses fra
    // `aria-label` — det er også den skærmlæserne får.
    // RETTET 14/11-2026 (Bjørn): uret bor i hovedet, ikke i rundelinjen. Det
    // kan derfor kun måles på den afsluttede tur — som er præcis der hovedet
    // findes nu. Et værktøjskald sikrer at der er et hoved at måle på.
    const blokkeMedRunde: ContentBlock[] = [
      { type: 'tool_use', id: 't1', name: 'read_file', input: {}, status: 'done' },
      summary('Fandt kilden', 1),
    ]
    const ur = () => document.querySelector('.rv-turTid')?.getAttribute('aria-label')
    const { rerender } = render(<ChatFlowPresentation {...common} mode="living" streaming={false}
      status="done" turStart={Date.now() - 12_000} blocks={blokkeMedRunde} />)
    expect(ur()).toMatch(/^1[12]s$/)

    rerender(<ChatFlowPresentation {...common} mode="living" streaming={false}
      status="done" turStart={Date.now() - 72_000} blocks={blokkeMedRunde} />)
    expect(ur()).toMatch(/^1m 1[12]s$/)
  })

  it('fjerner uret når strømmen er forbi — men beholder hovedet', () => {
    // VENDT IGEN 14/11-2026, tredje gang samme dag (Bjørn): «gem turhoved til
    // det foldes». Formiddagens regel var at tallet skulle forsvinde når turen
    // sluttede — den passede til en model hvor hovedet var en STATUS under
    // turen, og et stille tal derfor var et minde om noget forgangent. Med den
    // nye regel er hovedet turens RESULTAT: det findes først når turen er slut,
    // og tallet er dét resultatet koster. Fjernede vi det, ville hovedet stå
    // tomt i præcis den fase det ejer.
    //
    // Kontrasten er stadig pointen: hovedet bliver stående fordi der er et
    // værktøjskald at folde ud — og nu bærer det også sin varighed.
    const start = Date.now() - 95_000
    const { container } = render(<ChatFlowPresentation {...common} mode="living" streaming={false} status="done"
      finalAnswerStarted turStart={start} turSlut={start + 95_000} blocks={[summary('Fandt kilden', 1)]} />)
    expect(container.querySelector('.rv-tur')).not.toBeNull()
    expect(container.querySelector('.rv-turTid')).not.toBeNull()
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
    expect(gruppe.closest('.chat-flow-gruppe-ydre')).toHaveAttribute('data-aaben', 'true')
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
  // VENDT 14/11-2026 (Bjørn): «turhoved skjules, og kun den aktive rundelinje
  // vises … og så når rundelinjen forsvinder morpher turhoved — som har kørt
  // hele tiden — ind». Den gamle regel (17/10-2026: «lige som i code mode
  // skal turhoved vises hele tiden før de første ord») satte hovedet først,
  // men dengang var der ingen rundelinje at give scenen til. Resultatet var
  // en død etiket over en puls der sagde præcis det samme.
  it('viser rundelinjen med det samme turen kører — hovedet venter', () => {
    render(<ChatFlowPresentation {...common} mode="living" blocks={[]} />)
    expect(document.querySelector('.rv-tur')).toBeNull()
    const runde = screen.getByTestId('chat-flow-round-line')
    expect(runde).toHaveTextContent('Tænker')
  })

  it('holder skillelinjen slukket gennem hele chat-streamen', () => {
    // Modsat code mode, hvor stregen taendes af en gate. Chat mode har ingen
    // streg i nogen fase — så der er intet at animere og intet at glemme.
    const view = render(<ChatFlowPresentation {...common} mode="living" blocks={[]} />)
    // Fase 1 af overleveringen: hovedet venter, så der er intet element at
    // sætte en streg på. Det er den stærkeste form for «ingen skillelinje».
    expect(document.querySelector('.rv-tur')).toBeNull()

    view.rerender(<ChatFlowPresentation {...common} mode="living" blocks={[
      { type: 'text', text: 'Mellemstatus', phase: 'commentary' },
    ]} />)
    expect(document.querySelector('.rv-tur')).toBeNull()

    // VENDT 14/11-2026 (Bjørn): «gem turhoved til det foldes». Hovedet findes
    // først når turen er slut — så mens svaret skriver sig er der stadig intet
    // hoved, og dermed intet at sætte en streg på.
    view.rerender(<ChatFlowPresentation {...common} mode="living" streaming status="working" blocks={[
      { type: 'text', text: 'Svaret', phase: 'final_answer' },
    ]} finalAnswerStarted />)
    expect(document.querySelector('.rv-tur')).toBeNull()

    // Den afsluttede tur uden runder har intet hoved (målt: `harRunder` falsk
    // og ingen varighed) — så der er stadig intet at sætte en streg på.
    view.rerender(<ChatFlowPresentation {...common} mode="living" blocks={[
      { type: 'text', text: 'Svaret', phase: 'final_answer' },
    ]} finalAnswerStarted />)
    expect(document.querySelector('.rv-tur')).toBeNull()
  })

  it('viser intet hoved på en afsluttet tur uden værktøjskald', () => {
    // VENDT 14/11-2026 (Bjørn): «hvis ingen runder er kørt i turen bør
    // turhoved forsvinde når beskeden starter». Den tidligere test bekræftede
    // det modsatte (17/10-2026: «det skal være der osse uden tool kald») — men
    // dengang handlede det om at hovedet manglede MENS turen kørte. Her er
    // turen færdig, der er intet at folde ud, og et «Tænkte 12s» over et
    // direkte svar er en label uden indhold.
    //
    // Varigheden alene bærer den ikke: `varighedSekunder` er stadig sat, så
    // testen beviser at det er fraværet af runder — ikke fraværet af et ur —
    // der fjerner hovedet.
    const { container } = render(<ChatFlowPresentation {...common} mode="living"
      blocks={[{ type: 'text', text: 'Et rent svar.' }]}
      streaming={false} status="done" finalAnswerStarted varighedSekunder={12} />)
    expect(container.querySelector('.rv-tur')).toBeNull()
  })

  it('beholder hovedet — men ikke uret — når turen HAR kaldt runder', () => {
    // Modstykket til testen ovenfor: samme afsluttede tur, men med ét
    // værktøjskald. Så er der noget at folde ud, og hovedet bliver stående.
    const { container } = render(<ChatFlowPresentation {...common} mode="living"
      blocks={[
        { type: 'tool_use', id: 't1', name: 'read_file', input: {}, status: 'done' },
        { type: 'text', text: 'Et rent svar.', phase: 'final_answer' },
      ]}
      streaming={false} status="done" finalAnswerStarted varighedSekunder={12} />)
    const hoved = container.querySelector('.rv-tur') as HTMLElement
    expect(hoved).not.toBeNull()
    // Intet at folde i denne fixture? Jo — `tool_use` gør den foldbar.
    expect(hoved.tagName).toBe('BUTTON')
    // Uret STÅR nu (VENDT 14/11-2026, Bjørn: «gem turhoved til det foldes»).
    // Hovedet er turens RESULTAT og findes først når turen er slut — netop dér
    // hvor `streaming` er falsk. Bandt vi tallet til streamen, ville hovedet
    // stå uden ur præcis i den fase det nu ejer. Den tidligere regel («sekunder
    // Xs skal forsvinde når turen er slut») hørte til den model hvor hovedet
    // var en status under turen; det er det ikke længere.
    expect(container.querySelector('.rv-turTid')).not.toBeNull()
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
