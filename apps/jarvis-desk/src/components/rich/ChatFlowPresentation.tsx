import { useEffect, useRef, useState } from 'react'
import { Brain, Code2 } from 'lucide-react'
import type { ApiConfig } from '../../lib/api'
import { deriveChatFlow } from '../../lib/chatFlowModel'
import type { ContentBlock } from '../../lib/sseProtocol'
import type { StreamStatus } from '../../lib/streamReducer'
import { useChatPacedBlocks } from '../../lib/useChatPacedBlocks'
import { formaterTurTid, useTankeSekunder, useTurSekunder } from '../../lib/turTid'
import '../../styles/chat-flow.css'
import { BlocksRenderer } from './BlocksRenderer'
import { LabelSkift, SynteseLinje } from './LabelSkift'
import { RullendeTid } from './RullendeTid'
import { FoldPil, TurHoved } from './TurHoved'

export interface ChatFlowPresentationProps {
  blocks: ContentBlock[]
  mode: 'living' | 'calm'
  density: 'compact' | 'full'
  streaming: boolean
  status: StreamStatus
  finalAnswerStarted: boolean
  runId?: string | null
  /** Turens starttid (ms epoch) — uret måler turen, ikke komponentens montering. */
  turStart?: number | null
  /** Turens sluttid (ms epoch) — uret fryser her og bliver stående efter turen. */
  turSlut?: number | null
  /** Turens varighed udledt af transskriptet. Bruges på persisterede ture, hvor
   *  stream-tilstanden (og dermed `turStart`/`turSlut`) ikke findes længere. */
  varighedSekunder?: number | null
  workingStep?: string | null
  rundeEtiketter?: Record<string, string>
  tankeResumeer?: Record<string, string>
  beskedId?: string
  config?: ApiConfig
  onWorkExpanded?: () => void
  /** Hold slutsvarets visuelle pacing i live efter message_stop, indtil den
   *  persisterede besked kan overtage uden et dump. */
  paceFinalAnswer?: boolean
  onAnswerPaced?: () => void
}

export function ChatFlowPresentation({
  blocks,
  mode,
  density,
  streaming,
  status,
  finalAnswerStarted,
  runId,
  turStart,
  turSlut,
  varighedSekunder,
  workingStep,
  rundeEtiketter,
  tankeResumeer,
  beskedId,
  config,
  onWorkExpanded,
  paceFinalAnswer = false,
  onAnswerPaced,
}: ChatFlowPresentationProps) {
  // Pace fra FØRSTE levende teksttegn, ikke først efter final_answer_start.
  // No-tool-svar får ingen sådan grænse fra relæet og kunne derfor arve
  // providerens store bidder, mens autonome follow-runs så fine ud. Samme
  // cursor følger nu teksten gennem syntese → slutsvar → message_stop.
  const pacingFinal = finalAnswerStarted || (paceFinalAnswer && status === 'done')
  const pacedBlocks = useChatPacedBlocks(blocks, {
    live: streaming || paceFinalAnswer,
    finalAnswerStarted: pacingFinal,
    paceAllText: streaming,
    runId,
  })
  const model = deriveChatFlow({
    blocks: pacedBlocks,
    workingStep,
    rundeEtiketter,
    tankeResumeer,
    finalAnswerStarted,
    status,
  })
  const targetModel = deriveChatFlow({
    blocks,
    workingStep,
    rundeEtiketter,
    tankeResumeer,
    finalAnswerStarted,
    status,
  })
  const confirmedRef = useRef<{ runKey: string; texts: string[] }>({ runKey: '', texts: [] })
  const runKey = runId ?? '__historical-message__'
  const priorConfirmed = confirmedRef.current.runKey === runKey ? confirmedRef.current.texts : []
  let confirmedTexts = priorConfirmed
  if (finalAnswerStarted) {
    confirmedTexts = [...priorConfirmed]
    for (const block of targetModel.finalBlocks) {
      if (block.type !== 'text' || !block.text) continue
      const related = confirmedTexts.findIndex((text) => text.startsWith(block.text) || block.text.startsWith(text))
      if (related < 0) confirmedTexts.push(block.text)
      else if (block.text.length > confirmedTexts[related]!.length) confirmedTexts[related] = block.text
    }
    confirmedRef.current = { runKey, texts: confirmedTexts }
  } else if (confirmedRef.current.runKey !== runKey) {
    confirmedRef.current = { runKey, texts: [] }
  }
  const retainedWork = finalAnswerStarted && confirmedTexts.length > 0
    ? model.workBlocks.filter((block) => block.type !== 'text'
        || !confirmedTexts.some((text) => text === block.text || text.startsWith(block.text) || block.text.startsWith(text)))
    : model.workBlocks
  const currentFinalText = new Set(targetModel.finalBlocks
    .filter((block): block is Extract<ContentBlock, { type: 'text' }> => block.type === 'text')
    .map((block) => block.text))
  const restoredText = finalAnswerStarted
    ? confirmedTexts.filter((text) => !currentFinalText.has(text)).map((text): ContentBlock => ({ type: 'text', text }))
    : []
  const answerBlocks = [...restoredText, ...model.finalBlocks]
  const answer = answerBlocks
  const targetSvar = blocks.flatMap((block) => block.type === 'text' ? [block.text] : []).join('')
  const vistSvar = pacedBlocks.flatMap((block) => block.type === 'text' ? [block.text] : []).join('')
  const svarFaerdigPacet = targetSvar.length > 0 && targetSvar === vistSvar
  useEffect(() => {
    if (paceFinalAnswer && svarFaerdigPacet) onAnswerPaced?.()
  }, [onAnswerPaced, paceFinalAnswer, svarFaerdigPacet])
  // «Aktiv» er arbejdsfasen: Jarvis kører og har ikke begyndt at svare endnu.
  // Uden for den er turen enten afsluttet eller svaret er begyndt — og så
  // klapper hovedet sammen og arbejdet lægger sig som detaljer.
  const aktiv = streaming && !finalAnswerStarted && model.terminalState === 'active'
  const activeLine = mode === 'calm'
    ? model.calmStatus
    : model.visibleSynthesis.at(-1)
  // Den levende syntese er den seneste tekstblok i arbejdet — men kun hvis
  // den HAR indhold. En ny tekstblok starter tom, og det tidligere
  // `…?.text.trim() || null` rev linjen ned i netop det øjeblik: den gamle
  // forsvandt, der blev et glip, og den næste kom streamende bagefter
  // (Bjørn 17/10-2026). Vi springer tomme blokke over, så den forrige tekst
  // står stille indtil den nye har noget at vise.
  //
  // `noegle` er blokkens indeks i arbejdet. Det skifter KUN når syntesen
  // erstattes — ikke mens teksten vokser — så visningen kan opdatere på
  // stedet i stedet for at krydsfade ved hvert tegn.
  const levendeSyntese = (() => {
    if (mode !== 'living') return null
    for (let i = model.workBlocks.length - 1; i >= 0; i--) {
      const blok = model.workBlocks[i]
      if (blok && blok.type === 'text' && blok.text.trim()) {
        return { tekst: blok.text.trim(), noegle: i }
      }
    }
    return null
  })()
  const activeSynthesis = levendeSyntese?.tekst ?? null
  // Hovedet skal stå fra FØRSTE ord — også i det vindue hvor turen lige er
  // startet og der endnu ikke er rapporteret arbejde eller synteser.
  // (Bjørn 17/10-2026: «lige som i code mode skal turhoved vises hele tiden
  // før de første ord».) Uden `streaming` her manglede hovedet netop i det
  // øjeblik turen begyndte, og dukkede først op bagefter.
  // Uret: sekunder mens turen kører, frosset når den slutter. Bjørn
  // 17/10-2026: «timer for turen Xm Xs startende med Xs og så Xm osv» — og
  // «ueret skal osse når strømmen er forbi». Derfor måles der til `turSlut`
  // (sat ved `message_stop`), ikke til `aktiv` som bliver falsk allerede når
  // svaret begynder.
  //
  // Persisterede ture har ingen stream-tilstand tilbage. Deres varighed er
  // udledt af transskriptet, så uret også står der (17/10-2026).
  const sekunder = useTurSekunder(turStart, turSlut) ?? varighedSekunder ?? null
  const tankeSekunder = useTankeSekunder(blocks)
  const tankeTekst = typeof tankeSekunder === 'number'
    ? `Tænker ${formaterTurTid(tankeSekunder)}`
    : 'Tænker'

  // Hovedet er turens skillestreg — ikke en overskrift for værktøjskald.
  // (Bjørn 17/10-2026: «tur hoved vises ikke hvis han ikk kalder tools… det
  // skal være der osse uden tool kald».) Derfor bæres det af tre ting: der er
  // arbejde at folde, turen kører, eller vi kender dens varighed.
  const harArbejde = model.hasObservableWork
  const visTurhoved = harArbejde || streaming || sekunder !== null
  // Rundelinjen må aldrig vise et internt tool-navn. Modellen filtrerer de
  // rå working_step-værdier; indtil den menneskelige etiket er klar, står en
  // rolig fallback i samme stabile celle UNDER syntesen — ikke i turhovedet.
  const rundeTekst = harArbejde ? (activeLine || 'Arbejder…') : null

  // Åbent mens der arbejdes, sammenklappet når turen er ovre — medmindre
  // Bjørn selv har foldet. `null` betyder «følg fasen».
  const [aabenManuelt, setAabenManuelt] = useState<boolean | null>(null)
  const aaben = aabenManuelt ?? (streaming && !finalAnswerStarted)
  // Arbejdsdetaljerne under rundelinjen. Mens der arbejdes er de foldet
  // sammen som udgangspunkt — den levende linje er nok — men Bjørn kan folde
  // dem ud UNDER streaming (17/10-2026: «runde linjen under streaming bør
  // have > i ende og kunne foldes ud»). Efter turen følger de turhovedets
  // fold, som før.
  const arbejdeAabent = aktiv ? aabenManuelt === true : aaben
  const visArbejdsdetaljer = retainedWork.length > 0 && arbejdeAabent

  return (
    <div className="chat-flow" data-chat-flow-mode={mode}>
      {visTurhoved ? (
        <>
          <TurHoved
            aaben={aaben}
            foldbar={harArbejde}
            koerer={streaming && !finalAnswerStarted}
            sekunder={sekunder}
            tekst={model.hovedTekst}
            skillelinje
            onToggle={() => {
              const naeste = !aaben
              setAabenManuelt(naeste)
              if (naeste) onWorkExpanded?.()
            }}
          />
          {/* Chat mode viser én levende statuslinje ad gangen. Den erstattes
              på stedet under turhovedets streg og forsvinder, når svaret
              begynder. De fulde arbejdsdetaljer er fortsat tilgængelige ved
              at folde en afsluttet tur ud. */}
          <div className="chat-flow-gruppe" hidden={!aaben}>
            {aktiv && !arbejdeAabent && (activeSynthesis || rundeTekst) ? (
              <div className={`chat-flow-activity chat-flow-activity--${mode} chat-flow-activity--motion-safe`}
                data-testid="chat-flow-activity" role="status" aria-live="polite" aria-atomic="true"
                aria-label={[activeSynthesis, tankeTekst,
                  rundeTekst].filter(Boolean).join('. ')}>
                {levendeSyntese ? (
                  <div className="chat-flow-live-synthesis" data-testid="chat-flow-live-synthesis"
                    aria-hidden="true">
                    <SynteseLinje tekst={levendeSyntese.tekst} noegle={levendeSyntese.noegle} />
                  </div>
                ) : null}
                {rundeTekst ? (
                  <div className="chat-flow-round" data-testid="chat-flow-round">
                    <div className="chat-flow-round-line" data-testid="chat-flow-round-line"
                      aria-hidden="true">
                      <Brain className="chat-flow-thinking-icon" data-testid="chat-flow-thinking-icon"
                        size={15} strokeWidth={1.8} />
                      <span className="chat-flow-thinking-label">Tænker</span>
                      {typeof tankeSekunder === 'number' ? (
                        <RullendeTid tekst={formaterTurTid(tankeSekunder)} />
                      ) : null}
                      <span className="chat-flow-round-divider">|</span>
                      <Code2 className="chat-flow-round-icon" data-testid="chat-flow-round-icon"
                        size={15} strokeWidth={1.8} />
                      <span className="chat-flow-round-label" data-testid="chat-flow-round-label">
                        <LabelSkift tekst={rundeTekst} arbejder className="shimmer" fastIkon />
                      </span>
                    </div>
                    {retainedWork.length > 0 ? (
                      <button
                        type="button"
                        className="chat-flow-round-fold"
                        data-testid="chat-flow-round-fold"
                        aria-expanded={arbejdeAabent}
                        aria-label={arbejdeAabent ? 'Skjul arbejdet' : 'Vis arbejdet'}
                        onClick={() => setAabenManuelt(!arbejdeAabent)}
                      >
                        <FoldPil aaben={arbejdeAabent} />
                      </button>
                    ) : null}
                  </div>
                ) : null}
              </div>
            ) : null}

            {visArbejdsdetaljer ? (
              <div className="chat-flow-work-details">
                <BlocksRenderer blocks={retainedWork} density={density} streaming={streaming}
                  rundeEtiketter={rundeEtiketter} tankeResumeer={tankeResumeer}
                  visTankeResumeer
                  beskedId={beskedId} config={config} />
              </div>
            ) : null}
          </div>
        </>
      ) : null}

      {answer.length > 0 ? (
        <div className="chat-flow-answer">
          <BlocksRenderer blocks={answer} density={density} streaming={streaming}
            beskedId={beskedId} config={config} />
        </div>
      ) : null}
    </div>
  )
}
