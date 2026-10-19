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
    expect(model.finalBlocks).toEqual([{ type: 'text', text: 'halen' }])
    expect(model.workBlocks).toEqual([])
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

  it.each(['operator_bash', 'operator_bash: git status', 'search_memory']) (
    'skjuler det rå tool-navn %s mens den menneskelige etiket er på vej',
    (workingStep) => {
      const model = deriveChatFlow({ ...base, workingStep })
      expect(model.visibleSynthesis).toEqual([])
      expect(model.calmStatus).toBe('Jarvis tænker ...')
    },
  )

  // Ændret 15/10-2026 (Bjørn): spec'ens §6 bandt visningen af svaret til
  // `finalAnswerStarted` alene, og serveren sender først signalet i sin
  // `done`-handler. Målt konsekvens: svar-fladen stod TOM hele kørslen, og hele
  // svaret landede i ét hug til sidst. Tekst efter det seneste arbejde er det
  // svar der skrives nu og vises derfor mens det kommer.
  it('viser tekst efter det seneste arbejde som svar efter final_answer_start', () => {
    const work: ContentBlock = { type: 'tool_use', id: 't1', name: 'read_file', input: {}, status: 'done' }
    const text = { type: 'text' as const, text: 'Svaret skrives nu.' }
    const model = deriveChatFlow({ ...base, blocks: [work, text], finalAnswerStarted: true })
    expect(model.finalBlocks).toEqual([text])
    expect(model.workBlocks).toEqual([work])
  })

  it('holder en levende syntese i arbejdet indtil final_answer_start', () => {
    const work: ContentBlock = { type: 'tool_use', id: 't1', name: 'read_file', input: {}, status: 'done' }
    const synthesis: ContentBlock = { type: 'text', text: 'Jeg fandt årsagen og undersøger næste led.' }
    const model = deriveChatFlow({ ...base, blocks: [work, synthesis], finalAnswerStarted: false })

    expect(model.workBlocks).toEqual([work, synthesis])
    expect(model.finalBlocks).toEqual([])
  })

  it('bevarer runde-metadata i arbejdsblokkene, så den kan kobles ved udfoldning', () => {
    const work: ContentBlock = { type: 'tool_use', id: 't1', name: 'read_file', input: {}, status: 'done' }
    const metadata: ContentBlock = {
      type: 'tool_use_summary',
      summary: 'Læste filen',
      preceding_tool_use_ids: ['t1'],
      thinking_summary: 'Ville kontrollere den mistænkte sti',
    }
    const model = deriveChatFlow({ ...base, blocks: [work, metadata], finalAnswerStarted: true })

    expect(model.workBlocks).toEqual([work, metadata])
    expect(model.finalBlocks).toEqual([])
  })

  it('lader tekst før det seneste arbejde blive i arbejds-detaljerne', () => {
    const mellemregning = { type: 'text' as const, text: 'Mellemregning.' }
    const work: ContentBlock = { type: 'tool_use', id: 't1', name: 'read_file', input: {}, status: 'done' }
    const svar = { type: 'text' as const, text: 'Svaret.' }
    const model = deriveChatFlow({ ...base, blocks: [mellemregning, work, svar], finalAnswerStarted: true })
    expect(model.finalBlocks).toEqual([svar])
    expect(model.workBlocks).toEqual([mellemregning, work])
  })

  it('gendanner gemte synteser ved deres runder og holder kun slutsvaret udenfor folden', () => {
    // Produktionsformen 17/10-2026: hver syntese står før næste værktøjsrunde,
    // det egentlige svar står efter sidste runde-resumé, og progress-projektioner
    // bliver lagt sidst i content_json. Historiske beskeder har ikke det live
    // `final_answer_start`-flag, så rækkefølgen er deres persistente grænse.
    const syntese1: ContentBlock = { type: 'text', text: 'Jeg tjekker først repoet.' }
    const tool1: ContentBlock = { type: 'tool_use', id: 't1', name: 'bash', input: {}, status: 'done' }
    const syntese2: ContentBlock = { type: 'text', text: 'Nu tjekker jeg visningen.' }
    const tool2: ContentBlock = { type: 'tool_use', id: 't2', name: 'bash', input: {}, status: 'done' }
    const summary: ContentBlock = {
      type: 'tool_use_summary', summary: 'Genbyggede desk-web’en', preceding_tool_use_ids: ['t2'],
    }
    const answer: ContentBlock = { type: 'text', text: 'Kørt to runder. Her er resultatet.' }
    const progress: ContentBlock = {
      type: 'progress', tool_use_id: 't2', parent_tool_use_id: null,
      message: 'Kører kommando', tool: 'bash', hint: '', status: 'done',
    }

    const model = deriveChatFlow({
      ...base,
      status: 'done',
      blocks: [syntese1, tool1, syntese2, tool2, summary, answer, progress],
    })

    expect(model.workBlocks).toEqual([syntese1, tool1, syntese2, tool2, summary, progress])
    expect(model.finalBlocks).toEqual([answer])
  })

  it('viser et direkte svar mens det skrives, uden en tom arbejds-overskrift', () => {
    const answer = { type: 'text' as const, text: 'Hej Bjørn.' }
    const model = deriveChatFlow({ ...base, blocks: [answer], finalAnswerStarted: false })
    expect(model.finalBlocks).toEqual([answer])
    expect(model.workBlocks).toEqual([])
    expect(model.hasObservableWork).toBe(false)
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
    ['done' as const, 'completed' as const, 'Arbejdet'],
    ['interrupted' as const, 'interrupted' as const, 'Arbejdet afbrudt'],
    ['error' as const, 'failed' as const, 'Arbejdet fejlede'],
  ])('promotes retained text exactly once on terminal %s fallback', (status, terminalState, label) => {
    const first: ContentBlock = { type: 'text', text: 'Første del. ' }
    const second: ContentBlock = { type: 'text', text: 'Anden del.' }
    const work: ContentBlock = { type: 'thinking', thinking: 'intern tanke' }
    const model = deriveChatFlow({ ...base, status, blocks: [work, first, second] })
    expect(model.finalBlocks).toEqual([first, second])
    expect(model.workBlocks).toEqual([work])
    expect(model.terminalState).toBe(terminalState)
    expect(model.hovedTekst).toBe(label)
  })

  it('bøjer turens hoved i tid og skelner arbejde fra tanke', () => {
    // Bjørn 17/10-2026: «istedet for arbejdsorløb så bare arbejder under
    // kørslen og arbejdet når den er færdig. og hvis det er tekst uden tool
    // kald så tænker under kørsel og tænkte efter.»
    const vaerktoej: ContentBlock = { type: 'tool_use', id: 't1', name: 'read_file', input: {}, status: 'done' }
    const tekst: ContentBlock = { type: 'text', text: 'Et rent svar.' }

    expect(deriveChatFlow({ ...base, blocks: [vaerktoej] }).hovedTekst).toBe('Arbejder')
    expect(deriveChatFlow({ ...base, blocks: [tekst] }).hovedTekst).toBe('Tænker')
    expect(deriveChatFlow({ ...base, status: 'done', blocks: [vaerktoej, tekst] }).hovedTekst).toBe('Arbejdet')
    expect(deriveChatFlow({ ...base, status: 'done', blocks: [tekst] }).hovedTekst).toBe('Tænkte')
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
