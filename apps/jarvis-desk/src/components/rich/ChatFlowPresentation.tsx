import { useRef } from 'react'
import type { ApiConfig } from '../../lib/api'
import { deriveChatFlow } from '../../lib/chatFlowModel'
import type { ContentBlock } from '../../lib/sseProtocol'
import type { StreamStatus } from '../../lib/streamReducer'
import { useChatPacedBlocks } from '../../lib/useChatPacedBlocks'
import '../../styles/chat-flow.css'
import { BlocksRenderer } from './BlocksRenderer'

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
  const showActivity = streaming && !finalAnswerStarted && model.terminalState === 'active'
  const activeLine = mode === 'calm'
    ? model.calmStatus
    : model.visibleSynthesis.at(-1)
  const showDisclosure = model.hasObservableWork
    && (finalAnswerStarted || model.terminalState !== 'active')
  const showTurnHeader = showActivity || showDisclosure

  return (
    <div className="chat-flow" data-chat-flow-mode={mode}>
      {showTurnHeader ? (
        <details className={`chat-flow-work chat-flow-work--${model.terminalState}`}
          open={showActivity}
          onToggle={(event) => {
            if (!showActivity && event.currentTarget.open) onWorkExpanded?.()
          }}>
          <summary>{model.terminalLabel}</summary>
          {showActivity && activeLine ? (
            <div className={`chat-flow-activity chat-flow-activity--${mode} chat-flow-activity--motion-safe`}
              data-testid="chat-flow-activity" role="status" aria-live="polite" aria-atomic="true"
              aria-label={activeLine}>
              <div className="chat-flow-synthesis" data-testid="chat-flow-synthesis"
                key={activeLine} aria-hidden="true">
                {activeLine}
              </div>
            </div>
          ) : null}
          {showDisclosure ? (
            <div className="chat-flow-work-details">
              <BlocksRenderer blocks={retainedWork} density={density} streaming={streaming}
                rundeEtiketter={rundeEtiketter} tankeResumeer={tankeResumeer}
                beskedId={beskedId} config={config} />
            </div>
          ) : null}
        </details>
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
