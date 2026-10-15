import type { ContentBlock } from './sseProtocol'
import type { StreamStatus } from './streamReducer'

export interface ChatFlowInput {
  blocks: readonly ContentBlock[]
  workingStep?: string | null
  rundeEtiketter?: Readonly<Record<string, string>>
  tankeResumeer?: Readonly<Record<string, string>>
  finalAnswerStarted: boolean
  status: StreamStatus
}

export type ChatFlowTerminalState = 'active' | 'completed' | 'interrupted' | 'failed'

export interface ChatFlowModel {
  allSynthesis: string[]
  visibleSynthesis: string[]
  calmStatus: string
  workBlocks: ContentBlock[]
  finalBlocks: ContentBlock[]
  hasObservableWork: boolean
  terminalState: ChatFlowTerminalState
  terminalLabel: string
}

export interface AdaptiveSnapshot {
  shortDirectRuns: number
  multiStepRuns: number
  workExpansions: number
  livingOverrides: number
  calmOverrides: number
}

const WORK_TYPES = new Set<ContentBlock['type']>([
  'thinking', 'skill_surface', 'tool_use_summary', 'tool_use', 'progress',
])

function normalizeLine(value: string | null | undefined): string {
  return (value ?? '').replace(/\s+/g, ' ').trim()
}

/** Mechanical tool output belongs in the disclosure, never in Chat's status rail. */
function isMeaningfulStatus(value: string): boolean {
  if (!value) return false
  return !/^(?:kalder|kører kommando|koerer kommando|bash\b|edit_file\b)/i.test(value)
}

function terminal(status: StreamStatus): Pick<ChatFlowModel, 'terminalState' | 'terminalLabel'> {
  if (status === 'done') return { terminalState: 'completed', terminalLabel: 'Arbejdsforløb' }
  if (status === 'interrupted') return { terminalState: 'interrupted', terminalLabel: 'Arbejdsforløb afbrudt' }
  if (status === 'error') return { terminalState: 'failed', terminalLabel: 'Arbejdsforløb fejlede' }
  return { terminalState: 'active', terminalLabel: 'Arbejdsforløb' }
}

function isDelivery(block: ContentBlock): boolean {
  return block.type === 'image' || block.type === 'video' || block.type === 'file'
}

function synthesisLines(input: ChatFlowInput): string[] {
  const candidates: string[] = []
  for (const block of input.blocks) {
    if (block.type === 'tool_use_summary') candidates.push(block.summary)
  }
  candidates.push(...Object.values(input.rundeEtiketter ?? {}))
  candidates.push(...Object.values(input.tankeResumeer ?? {}))
  const step = normalizeLine(input.workingStep)
  if (isMeaningfulStatus(step)) candidates.push(step)

  const seen = new Set<string>()
  const result: string[] = []
  for (const candidate of candidates) {
    const normalized = normalizeLine(candidate)
    if (!normalized || seen.has(normalized)) continue
    seen.add(normalized)
    result.push(normalized)
  }
  return result
}

/** Derives Chat presentation without changing or generating the underlying run data. */
export function deriveChatFlow(input: ChatFlowInput): ChatFlowModel {
  const allSynthesis = synthesisLines(input)
  const visibleSynthesis = allSynthesis.slice(-3)
  const end = terminal(input.status)
  const terminalFallback = end.terminalState !== 'active' && !input.finalAnswerStarted

  let lastWorkIndex = -1
  for (let index = 0; index < input.blocks.length; index += 1) {
    const block = input.blocks[index]
    if (block && WORK_TYPES.has(block.type)) lastWorkIndex = index
  }

  const workBlocks: ContentBlock[] = []
  const finalBlocks: ContentBlock[] = []
  for (let index = 0; index < input.blocks.length; index += 1) {
    const block = input.blocks[index]
    if (!block) continue
    if (isDelivery(block)) {
      finalBlocks.push(block)
    } else if (block.type === 'text') {
      const isFinal = terminalFallback || (input.finalAnswerStarted && index > lastWorkIndex)
      ;(isFinal ? finalBlocks : workBlocks).push(block)
    } else {
      workBlocks.push(block)
    }
  }

  const hasObservableWork = workBlocks.some((block) => block.type !== 'text') || allSynthesis.length > 0
  return {
    allSynthesis,
    visibleSynthesis,
    calmStatus: visibleSynthesis.at(-1) ?? 'Jarvis tænker ...',
    workBlocks,
    finalBlocks,
    hasObservableWork,
    ...end,
  }
}

/** Deterministic and intentionally conservative; callers cache this once per run. */
export function chooseAdaptiveMode(snapshot: AdaptiveSnapshot): 'living' | 'calm' {
  if (snapshot.workExpansions + snapshot.livingOverrides >= snapshot.calmOverrides + 2) {
    return 'living'
  }
  if (
    snapshot.shortDirectRuns >= 4
    && snapshot.shortDirectRuns >= snapshot.multiStepRuns * 2
    && snapshot.calmOverrides >= snapshot.livingOverrides
  ) {
    return 'calm'
  }
  return 'living'
}
