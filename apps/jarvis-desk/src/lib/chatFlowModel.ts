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
  /** Turens hoved som ord — «Arbejder» mens den kører, «Arbejdet» når den er
   *  færdig, og «Tænker»/«Tænkte» på en tur uden værktøjskald (17/10-2026). */
  hovedTekst: string
}

export interface AdaptiveSnapshot {
  shortDirectRuns: number
  multiStepRuns: number
  workExpansions: number
  livingOverrides: number
  calmOverrides: number
}

// `progress` er en projektion af værktøjskaldet, og ved persistens bliver de
// blokke samlet sidst i content_json — også efter det egentlige slutsvar. De
// er arbejde i folden, men kan derfor ikke bruges som svargrænse. De øvrige
// typer følger turens kronologiske rækkefølge og markerer sidste arbejdsrunde.
const ANSWER_BOUNDARY_TYPES = new Set<ContentBlock['type']>([
  'thinking', 'skill_surface', 'tool_use_summary', 'tool_use',
])

function normalizeLine(value: string | null | undefined): string {
  return (value ?? '').replace(/\s+/g, ' ').trim()
}

/** Mechanical tool output belongs in the disclosure, never in Chat's status rail. */
function isMeaningfulStatus(value: string): boolean {
  if (!value) return false
  if (/^(?:kalder|kører kommando|koerer kommando|bash\b|edit_file\b)/i.test(value)) return false
  // working_step kommer før den asynkrone menneskelige rundeetiket. Interne
  // navne som `operator_bash` og `search_memory` må ikke blinke frem i det
  // tidsvindue; behold den seneste gode etiket eller brug UI'ens fallback.
  if (/\b(?:operator|mcp|tool)_[a-z0-9_]+\b/i.test(value)) return false
  if (/^[a-z][a-z0-9]*(?:_[a-z0-9]+)+(?:\s*[:(].*)?$/i.test(value)) return false
  return true
}

function terminal(status: StreamStatus): Pick<ChatFlowModel, 'terminalState'> {
  if (status === 'done') return { terminalState: 'completed' }
  if (status === 'interrupted') return { terminalState: 'interrupted' }
  if (status === 'error') return { terminalState: 'failed' }
  return { terminalState: 'active' }
}

/**
 * Turens hoved som ord — hvad den laver NU, eller hvad den gjorde.
 *
 * Bjørn 17/10-2026: «istedet for arbejdsorløb så bare arbejder under kørslen og
 * arbejdet når den er færdig. og hvis det er tekst uden tool kald så tænker
 * under kørsel og tænkte efter.» Ordet bøjes altså i tid frem for at beskrive
 * et forløb, og det skelner en tur der rørte værktøjer fra en der kun tænkte.
 * Før stod der «Arbejdsforløb» i alle faser, hvilket hverken sagde hvad der
 * foregik eller om den var ovre.
 */
function hovedTekst(state: ChatFlowTerminalState, harArbejde: boolean, koerer: boolean): string {
  if (koerer) return harArbejde ? 'Arbejder' : 'Tænker'
  if (state === 'interrupted') return harArbejde ? 'Arbejdet afbrudt' : 'Afbrudt'
  if (state === 'failed') return harArbejde ? 'Arbejdet fejlede' : 'Fejlede'
  return harArbejde ? 'Arbejdet' : 'Tænkte'
}

function isDelivery(block: ContentBlock): boolean {
  return block.type === 'image' || block.type === 'video' || block.type === 'file'
}

function synthesisLines(input: ChatFlowInput): string[] {
  const candidates: string[] = []
  for (const block of input.blocks) {
    // `blocks` kan være sparsomt: SSE'en adresserer blokke med et eksplicit
    // indeks, og falder et indeks ud (gen-tilslutning midt i et run), står der
    // et hul — og `for…of` gør et hul til `undefined`. De øvrige læsninger i
    // denne fil værner allerede (`if (block && …)`, `if (!block) continue`);
    // denne manglede, og krasjede i produktion 15/10-2026 med
    // «can't access property "type", s is undefined».
    if (block && block.type === 'tool_use_summary') candidates.push(block.summary)
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
    if (block && ANSWER_BOUNDARY_TYPES.has(block.type)) lastWorkIndex = index
  }

  const workBlocks: ContentBlock[] = []
  const finalBlocks: ContentBlock[] = []
  for (let index = 0; index < input.blocks.length; index += 1) {
    const block = input.blocks[index]
    if (!block) continue
    if (isDelivery(block)) {
      finalBlocks.push(block)
    } else if (block.type === 'text') {
      // Efter et værktøj kan tekst være enten en mellemliggende syntese eller
      // slutsvaret. Placeringen alene kan ikke skelne dem: mens syntesen
      // streamer, er den midlertidigt også teksten efter det seneste kald.
      // Serveren sender `final_answer_start` FØR første synlige slutdelta, så
      // dét signal er grænsen. Et direkte svar uden værktøj kan derimod vises
      // med det samme.
      const isFinal = block.phase === 'final_answer'
        || (block.phase !== 'commentary' && (lastWorkIndex < 0
          || (index > lastWorkIndex && (input.finalAnswerStarted || terminalFallback))))
      ;(isFinal ? finalBlocks : workBlocks).push(block)
    } else {
      workBlocks.push(block)
    }
  }

  const hasObservableWork = workBlocks.some((block) => (
    block.type !== 'text' || block.phase === 'commentary'
  )) || allSynthesis.length > 0
  return {
    allSynthesis,
    visibleSynthesis,
    calmStatus: visibleSynthesis.at(-1) ?? 'Jarvis tænker ...',
    // Runde-metadataen skal blive sammen med arbejdet. `BlocksRenderer`
    // fjerner selve metadata-blokken fra output og bruger dens ids til at
    // placere etiketten og tænke-resuméet ved den rigtige værktøjsrunde.
    workBlocks,
    finalBlocks,
    hasObservableWork,
    ...end,
    // «Kører» er arbejdsfasen: status er working og svaret er ikke bekræftet
    // endnu. Det er samme betingelse som visningen bruger for `aktiv`.
    hovedTekst: hovedTekst(end.terminalState, hasObservableWork, input.status === 'working' && !input.finalAnswerStarted),
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
