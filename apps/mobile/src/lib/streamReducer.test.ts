import { initialStreamState, streamReducer, type StreamState } from './streamReducer'
import { denseBlocks } from './blockHelpers'
import type { ContentBlock } from './sseProtocol'

it('accumulates streamed text', () => {
  let state = streamReducer(initialStreamState(), {
    type: 'message_start',
    message: {
      id: 'm1',
      model: 'deepseek',
      provider: 'ollama',
      lane: 'primary',
      session_id: 's1',
      usage: { input_tokens: 3, output_tokens: 0 }
    }
  })

  state = streamReducer(state, {
    type: 'content_block_start',
    index: 0,
    content_block: { type: 'text', text: '' }
  })

  state = streamReducer(state, {
    type: 'content_block_delta',
    index: 0,
    delta: { type: 'text_delta', text: 'Hej' }
  })

  expect(state.blocks).toEqual([{ type: 'text', text: 'Hej' }])
  expect(state.status).toBe('working')
})

it('captures run id from system event', () => {
  const state = streamReducer(initialStreamState(), {
    type: 'system_event',
    kind: 'run',
    payload: { run_id: 'visible-1' }
  })

  expect(state.activeRunId).toBe('visible-1')
})

it('reducerer additive research-events til separat UI-state', () => {
  let state = streamReducer(initialStreamState(), {
    type: 'system_event', kind: 'research_started',
    payload: { research_run_id: 'research-1', tier: 'orchestrated' }
  })
  state = streamReducer(state, {
    type: 'system_event', kind: 'research_plan',
    payload: { tasks: [{}, {}, {}] }
  })
  state = streamReducer(state, {
    type: 'system_event', kind: 'research_progress',
    payload: { phase: 'researching', completed_tasks: 2, total_tasks: 3, sources: 4 }
  })
  expect(state.research).toMatchObject({
    runId: 'research-1', tier: 'orchestrated', phase: 'researching',
    completedTasks: 2, totalTasks: 3, sources: 4,
  })
})

it('bevarer research-resultatet til næste message_start', () => {
  let state = streamReducer(initialStreamState(), {
    type: 'system_event', kind: 'research_started',
    payload: { research_run_id: 'r1', tier: 'inline' }
  })
  state = streamReducer(state, {
    type: 'system_event', kind: 'research_completed',
    payload: { quality: 'passed', sources: 5 }
  })
  state = streamReducer(state, { type: 'message_stop' })
  expect(state.research).toMatchObject({ phase: 'completed', quality: 'passed', sources: 5 })
})

// Regression (samme bug som desk, sort skærm): en tool_result-content-blok må
// ALDRIG efterlade et undefined-hul i blocks, og konsumenter må ikke crashe når
// arrayet ER sparsomt.
describe('tool_result content-block (hole-safety)', () => {
  function withToolUse(): StreamState {
    let s = streamReducer(initialStreamState(), {
      type: 'message_start',
      message: {
        id: 'm1', model: 'deepseek', provider: 'ollama', lane: 'primary',
        session_id: 's1', usage: { input_tokens: 1, output_tokens: 0 }
      }
    })
    s = streamReducer(s, {
      type: 'content_block_start', index: 0,
      content_block: { type: 'tool_use', id: 'tu-1', name: 'bash', input: {} }
    })
    return s
  }

  it('folds tool_result onto its tool_use by tool_use_id (no new index)', () => {
    let s = withToolUse()
    s = streamReducer(s, {
      type: 'content_block_start', index: 1,
      content_block: { type: 'tool_result', tool_use_id: 'tu-1', status: 'ok', content: 'done!' }
    })
    // Ét block (foldet), IKKE et hul på index 1.
    expect(s.blocks.length).toBe(1)
    const b = s.blocks[0]
    expect(b?.type).toBe('tool_use')
    if (b && b.type === 'tool_use') {
      expect(b.status).toBe('done')
      expect(b.result).toBe('done!')
    }
  })

  it('marks tool_use status=error when tool_result is_error', () => {
    let s = withToolUse()
    s = streamReducer(s, {
      type: 'content_block_start', index: 1,
      content_block: { type: 'tool_result', tool_use_id: 'tu-1', is_error: true, content: 'boom' }
    })
    const b = s.blocks[0]
    if (b && b.type === 'tool_use') expect(b.status).toBe('error')
  })

  it('does NOT create an undefined hole; a later text block stays dense-safe', () => {
    let s = withToolUse()
    // tool_result på index 1 folder ind (fylder ikke index 1)…
    s = streamReducer(s, {
      type: 'content_block_start', index: 1,
      content_block: { type: 'tool_result', tool_use_id: 'tu-1', status: 'ok', content: 'x' }
    })
    // …og en efterfølgende tekst-blok lander på index 2 → hul på index 1.
    s = streamReducer(s, {
      type: 'content_block_start', index: 2,
      content_block: { type: 'text', text: 'efter' }
    })
    // Der ER et hul i det rå array (index-alignment bevaret)…
    expect(s.blocks[1]).toBeUndefined()
    // …men denseBlocks + .map crasher ALDRIG på block.type.
    expect(() =>
      denseBlocks(s.blocks).map((block: ContentBlock) => (block.type === 'text' ? block.text : ''))
    ).not.toThrow()
    expect(denseBlocks(s.blocks).map((b: ContentBlock) => b.type)).toEqual(['tool_use', 'text'])
  })

  it('ignores tool_result whose tool_use_id has no match (no throw, no hole)', () => {
    let s = withToolUse()
    s = streamReducer(s, {
      type: 'content_block_start', index: 1,
      content_block: { type: 'tool_result', tool_use_id: 'nope', status: 'ok', content: 'y' }
    })
    expect(s.blocks.length).toBe(1)
    expect(s.blocks[0]?.type).toBe('tool_use')
  })
})

// ── vaerktoejer der KOERER staar INLINE i traaden ────────────────────────

const workingStep = (o: Record<string, unknown>) => ({
  type: 'system_event' as const, kind: 'working_step' as const,
  payload: { action: 'bash', detail: 'bash: npm test', step: 1, status: 'running', ...o },
})

/** De foreloebige blokke — dem der staar mens vaerktoejet koerer. */
const foreloebige = (s: ReturnType<typeof initialStreamState>) =>
  s.blocks.filter((b) => b && b.type === 'tool_use' && b.foreloebig)

it('et annonceret vaerktoej staar i TRAADEN med det samme', () => {
  // Bjoern: «i stedet for at bruge dem der er inline i chatview». Det er de
  // SAMME raekker MessageList tegner for faerdige vaerktoejer - de skal bare
  // findes fra annonceringen.
  const s = streamReducer(initialStreamState(), workingStep({}) as never)
  const b = foreloebige(s)[0]
  expect(b && b.type === 'tool_use' && b.name).toBe('bash')
  expect(b && b.type === 'tool_use' && b.status).toBe('running')
})

it('«Taenker videre · runde N» er IKKE et vaerktoej', () => {
  // DEN FEJL: `working_step` bruges ogsaa til livstegn med action="thinking".
  // De faar aldrig en rigtig blok der kan rydde dem - ti runder blev til ti
  // raekker. Min mutationstest fangede det ikke, fordi jeg kun proevede med
  // et rigtigt vaerktoejsnavn.
  let s = initialStreamState()
  for (let r = 2; r <= 10; r++) {
    s = streamReducer(s, workingStep({
      action: 'thinking', detail: `Tænker videre · runde ${r}`, step: r,
    }) as never)
  }
  expect(foreloebige(s)).toHaveLength(0)
  expect(s.workingStep).toBe('Tænker videre · runde 10')
})

it('serverens eget flag vinder over navne-gaettet', () => {
  const s = streamReducer(initialStreamState(), workingStep({
    action: 'thinking', er_vaerktoej: true, step: 1,
  }) as never)
  expect(foreloebige(s)).toHaveLength(1)
})

it('et flag der siger NEJ holder raekken vaek, selv med et vaerktoejsnavn', () => {
  const s = streamReducer(initialStreamState(), workingStep({
    action: 'bash', er_vaerktoej: false, step: 1,
  }) as never)
  expect(foreloebige(s)).toHaveLength(0)
})

it('et BLOKERET skridt bliver ikke en raekke', () => {
  const s = streamReducer(initialStreamState(), workingStep({ status: 'blocked' }) as never)
  expect(foreloebige(s)).toHaveLength(0)
  expect(s.workingStep).toBe('bash: npm test')
})

it('SAMME skridt annonceret igen laegger ikke en raekke til', () => {
  let s = streamReducer(initialStreamState(), workingStep({}) as never)
  s = streamReducer(s, workingStep({}) as never)
  expect(foreloebige(s)).toHaveLength(1)
})

it('den RIGTIGE blok erstatter den foreloebige — ikke to raekker', () => {
  let s = streamReducer(initialStreamState(), workingStep({}) as never)
  s = streamReducer(s, {
    type: 'content_block_start', index: 5,
    content_block: { type: 'tool_use', id: 'bash-1', name: 'bash', input: {} },
  } as never)
  expect(foreloebige(s)).toHaveLength(0)
  const rigtige = s.blocks.filter((b) => b && b.type === 'tool_use')
  expect(rigtige).toHaveLength(1)
  expect(rigtige[0] && rigtige[0].type === 'tool_use' && rigtige[0].id).toBe('bash-1')
})

it('et ANDET vaerktoejs raekke roeres ikke', () => {
  let s = streamReducer(initialStreamState(), workingStep({}) as never)
  s = streamReducer(s, workingStep({ action: 'read_file', step: 2, detail: 'læser a.py' }) as never)
  s = streamReducer(s, {
    type: 'content_block_start', index: 5,
    content_block: { type: 'tool_use', id: 'bash-1', name: 'bash', input: {} },
  } as never)
  expect(foreloebige(s).map((b) => b && b.type === 'tool_use' && b.name)).toEqual(['read_file'])
})

it('message_stop rydder foreloebige der aldrig blev til noget', () => {
  let s = streamReducer(initialStreamState(), workingStep({}) as never)
  s = streamReducer(s, { type: 'message_stop' } as never)
  expect(foreloebige(s)).toHaveLength(0)
  expect(s.status).toBe('done')
})
