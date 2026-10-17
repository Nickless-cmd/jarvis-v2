import { useRef, useState } from 'react'
import type { ApiConfig } from '../../lib/api'
import { deriveChatFlow } from '../../lib/chatFlowModel'
import type { ContentBlock } from '../../lib/sseProtocol'
import type { StreamStatus } from '../../lib/streamReducer'
import { useChatPacedBlocks } from '../../lib/useChatPacedBlocks'
import '../../styles/chat-flow.css'
import { BlocksRenderer } from './BlocksRenderer'
import { TurHoved } from './TurHoved'

export interface ChatFlowPresentationProps {
  blocks: ContentBlock[]
  mode: 'living' | 'calm'
  density: 'compact' | 'full'
  streaming: boolean
  status: StreamStatus
  finalAnswerStarted: boolean
  runId?: string | null
  workingStep?: string | null
  rundeEtiketter?: Record<string, string>
  tankeResumeer?: Record<string, string>
  beskedId?: string
  config?: ApiConfig
  onWorkExpanded?: () => void
}

export function ChatFlowPresentation({
  blocks,
  mode,
  density,
  streaming,
  status,
  finalAnswerStarted,
  runId,
  workingStep,
  rundeEtiketter,
  tankeResumeer,
  beskedId,
  config,
  onWorkExpanded,
}: ChatFlowPresentationProps) {
  const model = deriveChatFlow({
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
    for (const block of model.finalBlocks) {
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
  const currentFinalText = new Set(model.finalBlocks
    .filter((block): block is Extract<ContentBlock, { type: 'text' }> => block.type === 'text')
    .map((block) => block.text))
  const restoredText = finalAnswerStarted
    ? confirmedTexts.filter((text) => !currentFinalText.has(text)).map((text): ContentBlock => ({ type: 'text', text }))
    : []
  const answerBlocks = [...restoredText, ...model.finalBlocks]
  const answer = useChatPacedBlocks(answerBlocks, {
    live: streaming,
    finalAnswerStarted,
    runId,
  })

  // «Aktiv» er arbejdsfasen: Jarvis kører og har ikke begyndt at svare endnu.
  // Uden for den er turen enten afsluttet eller svaret er begyndt — og så
  // klapper hovedet sammen og arbejdet lægger sig som detaljer.
  const aktiv = streaming && !finalAnswerStarted && model.terminalState === 'active'
  const lines = mode === 'calm'
    ? [model.calmStatus]
    : model.visibleSynthesis
  const visTurhoved = model.hasObservableWork || aktiv

  // Åbent mens der arbejdes, sammenklappet når turen er ovre — medmindre
  // Bjørn selv har foldet. `null` betyder «følg fasen».
  const [aabenManuelt, setAabenManuelt] = useState<boolean | null>(null)
  const aaben = aabenManuelt ?? aktiv

  return (
    <div className="chat-flow" data-chat-flow-mode={mode}>
      {visTurhoved ? (
        <>
          <TurHoved
            aaben={aaben}
            koerer={aktiv}
            tekst={aktiv ? 'Working…' : model.terminalLabel}
            onToggle={() => {
              const naeste = !aaben
              setAabenManuelt(naeste)
              if (naeste) onWorkExpanded?.()
            }}
          />
          {/* Synteserne står ØVERST i gruppen — over de runde linjer de hører
              til — så de ikke længere er skilt fra dem (Bjørn 17/10-2026).
              Ved sammenklap bliver de liggende som en del af arbejdsforløbet
              og følger med ned i den afsluttede besked. */}
          <div className="chat-flow-gruppe" hidden={!aaben}>
            {aktiv && lines.length > 0 ? (
              <div className={`chat-flow-activity chat-flow-activity--${mode} chat-flow-activity--motion-safe`}
                data-testid="chat-flow-activity" role="status" aria-live="polite" aria-atomic="true"
                aria-label={lines.at(-1)}>
                {lines.map((line) => (
                  <div className="chat-flow-synthesis" data-testid="chat-flow-synthesis" key={line} aria-hidden="true">
                    {line}
                  </div>
                ))}
              </div>
            ) : null}

            {retainedWork.length > 0 ? (
              <div className="chat-flow-work-details">
                <BlocksRenderer blocks={retainedWork} density={density} streaming={streaming}
                  rundeEtiketter={rundeEtiketter} tankeResumeer={tankeResumeer}
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
