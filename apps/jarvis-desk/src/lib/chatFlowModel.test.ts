import { describe, expect, it } from 'vitest'
import { chooseAdaptiveMode, deriveChatFlow, type ChatFlowInput } from './chatFlowModel'
import type { ContentBlock } from './sseProtocol'

const base: ChatFlowInput = {
  blocks: [],
  workingStep: null,
  rundeEtiketter: {},
  tankeResumeer: {},
  finalAnswerStarted: false,
  status: 'working',
}

function summaries(lines: string[]): ContentBlock[] {
  return lines.map((summary, index) => ({
    type: 'tool_use_summary' as const,
    summary,
    preceding_tool_use_ids: [`tool-${index}`],
  }))
}

describe('deriveChatFlow', () => {
  // Regression 15/10-2026: `synthesisLines` læste `block.type` uden værn, mens
  // resten af filen værner (`if (block && …)`). Et sparsomt blok-array — et
  // sprunget SSE-indeks efter en gen-tilslutning — kastede derfor i produktion.
  it('taaler et sparsomt blok-array uden at kaste', () => {
    const sparsom: ContentBlock[] = []
    sparsom[2] = { type: 'text', text: 'halen' }
    const model = deriveChatFlow({ ...base, blocks: sparsom })
    // Rækkefølgen er det afgørende: kastede den, nåede vi aldrig hertil.
    expect(model.workBlocks).toEqual([{ type: 'text', text: 'halen' }])
    expect(model.finalBlocks).toEqual([])
    expect(model.allSynthesis).toEqual([])
  })

  it('en tool_use_summary efter et hul bliver laest alligevel', () => {
    const sparsom: ContentBlock[] = []
    sparsom[3] = { type: 'tool_use_summary', summary: 'Fandt fejlen', preceding_tool_use_ids: ['t1'] }
    expect(deriveChatFlow({ ...base, blocks: sparsom }).allSynthesis).toEqual(['Fandt fejlen'])
  })

  it.each([
    [['Et'], ['Et']],
    [['Et', 'To'], ['Et', 'To']],
    [['Et', 'To', 'Tre'], ['Et', 'To', 'Tre']],
    [['Et', 'To', 'Tre', 'Fire'], ['To', 'Tre', 'Fire']],
  ])('keeps at most the latest three synthesis lines from %j', (input, expected) => {
    expect(deriveChatFlow({ ...base, blocks: summaries(input) }).visibleSynthesis).toEqual(expected)
  })

  it('deduplicates normalized synthesis without resetting at round boundaries', () => {
    const model = deriveChatFlow({
      ...base,
      blocks: summaries(['  Fandt   fejlen ', 'Rettede fejlen']),
      rundeEtiketter: { a: 'Fandt fejlen', b: 'Kørte testen' },
      tankeResumeer: { b: 'Rettede   fejlen', c: 'Alt er grønt' },
    })
    expect(model.allSynthesis).toEqual(['Fandt fejlen', 'Rettede fejlen', 'Kørte testen', 'Alt er grønt'])
    expect(model.visibleSynthesis).toEqual(['Rettede fejlen', 'Kørte testen', 'Alt er grønt'])
    expect(model.calmStatus).toBe('Alt er grønt')
  })

  it('uses a neutral Calm fallback and never promotes raw tool logs to main status', () => {
    const model = deriveChatFlow({
      ...base,
      blocks: [{ type: 'progress', tool_use_id: 't1', parent_tool_use_id: null,
        message: 'Kører kommando: git status', tool: 'bash', hint: 'git status', status: 'running' }],
      workingStep: 'Kalder bash: git status',
    })
    expect(model.visibleSynthesis).toEqual([])
    expect(model.calmStatus).toBe('Jarvis tænker ...')
  })

  it('does not treat the first text delta as a final answer', () => {
    const text = { type: 'text' as const, text: 'foreløbig' }
    const model = deriveChatFlow({ ...base, blocks: [text], finalAnswerStarted: false })
    expect(model.finalBlocks).toEqual([])
    expect(model.workBlocks).toContainEqual(text)
  })

  it('uses the final transition as authoritative and retains work details and deliveries', () => {
    const work: ContentBlock = { type: 'tool_use', id: 't1', name: 'read_file', input: {}, status: 'done' }
    const image: ContentBlock = { type: 'image', src: 'data:image/png;base64,AA', alt: 'Resultat' }
    const answer: ContentBlock = { type: 'text', text: 'Her er svaret.' }
    const model = deriveChatFlow({ ...base, blocks: [work, image, answer], finalAnswerStarted: true })
    expect(model.workBlocks).toEqual([work])
    expect(model.finalBlocks).toEqual([image, answer])
    expect(model.hasObservableWork).toBe(true)
  })

  it('does not create an empty work summary for a direct answer', () => {
    const answer: ContentBlock = { type: 'text', text: 'Hej Bjørn.' }
    const model = deriveChatFlow({ ...base, blocks: [answer], finalAnswerStarted: true })
    expect(model.workBlocks).toEqual([])
    expect(model.finalBlocks).toEqual([answer])
    expect(model.hasObservableWork).toBe(false)
  })

  it.each([
    ['done' as const, 'completed' as const, 'Arbejdsforløb'],
    ['interrupted' as const, 'interrupted' as const, 'Arbejdsforløb afbrudt'],
    ['error' as const, 'failed' as const, 'Arbejdsforløb fejlede'],
  ])('promotes retained text exactly once on terminal %s fallback', (status, terminalState, label) => {
    const first: ContentBlock = { type: 'text', text: 'Første del. ' }
    const second: ContentBlock = { type: 'text', text: 'Anden del.' }
    const work: ContentBlock = { type: 'thinking', thinking: 'intern tanke' }
    const model = deriveChatFlow({ ...base, status, blocks: [work, first, second] })
    expect(model.finalBlocks).toEqual([first, second])
    expect(model.workBlocks).toEqual([work])
    expect(model.terminalState).toBe(terminalState)
    expect(model.terminalLabel).toBe(label)
  })

  it('keeps a generated file visible while a run is still active', () => {
    const file: ContentBlock = { type: 'file', filename: 'rapport.pdf', url: '/files/rapport.pdf' }
    const model = deriveChatFlow({ ...base, blocks: [file] })
    expect(model.finalBlocks).toEqual([file])
    expect(model.workBlocks).toEqual([])
  })
})

describe('chooseAdaptiveMode', () => {
  const uncertain = {
    shortDirectRuns: 0,
    multiStepRuns: 0,
    workExpansions: 0,
    livingOverrides: 0,
    calmOverrides: 0,
  }

  it('defaults to Living when prior evidence is uncertain or only one exchange is short', () => {
    expect(chooseAdaptiveMode(uncertain)).toBe('living')
    expect(chooseAdaptiveMode({ ...uncertain, shortDirectRuns: 1 })).toBe('living')
  })

  it('selects Calm only after repeated prior direct low-work runs', () => {
    expect(chooseAdaptiveMode({ ...uncertain, shortDirectRuns: 4, multiStepRuns: 1 })).toBe('calm')
  })

  it('selects Living after repeated detail expansion or Living overrides', () => {
    expect(chooseAdaptiveMode({ ...uncertain, workExpansions: 2 })).toBe('living')
    expect(chooseAdaptiveMode({ ...uncertain, livingOverrides: 3, calmOverrides: 1 })).toBe('living')
  })

  it('is a pure run-start decision that cannot change when the snapshot object later mutates', () => {
    const snapshot = { ...uncertain, shortDirectRuns: 5 }
    const selected = chooseAdaptiveMode(snapshot)
    snapshot.multiStepRuns = 8
    snapshot.workExpansions = 8
    expect(selected).toBe('calm')
  })
})
