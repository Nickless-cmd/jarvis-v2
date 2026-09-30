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

/**
 * DRIFTENS RAEKKEFOELGE, maalt 28/9-2026 paa telefonen.
 *
 * `visible_runs_sse_v2._emit_tool_use_start` laegger `content_block_start` +
 * argumenterne paa koeen og sender FOERST DEREFTER `system_event(working_step)`
 * for det SAMME kald. Den rigtige blok kommer altsaa altid foerst.
 *
 * Foer denne rettelse blev den foreloebige blok alligevel bygget — og den
 * havde `input: {}` og `partialJson: ''`. To blokke for samme kald, og
 * `buildStreamingRows` beholder den SIDSTE venteflade: den tomme. Paa skaermen
 * stod `analyze_image`-animationen derfor uden navn og uden billede, mens den
 * blok der faktisk bar `image_path` blev smidt vaek.
 */
it('serverens EGEN blok kom foerst — saa bygges der ingen foreloebig oveni', () => {
  let s = initialStreamState()
  s = streamReducer(s, {
    type: 'content_block_start', index: 0,
    content_block: { type: 'tool_use', id: 'call_01', name: 'analyze_image', input: {} },
  } as never)
  s = streamReducer(s, {
    type: 'content_block_delta', index: 0,
    delta: { type: 'input_json_delta', partial_json: '{"image_path":"/x/k.png"}' },
  } as never)
  s = streamReducer(s, workingStep({ action: 'analyze_image', step: 3 }) as never)

  expect(foreloebige(s)).toHaveLength(0)
  const kald = s.blocks.filter((b) => b && b.type === 'tool_use')
  expect(kald).toHaveLength(1)
  expect(kald[0] && kald[0].type === 'tool_use' && kald[0].partialJson)
    .toBe('{"image_path":"/x/k.png"}')
})

it('er der INGEN rigtig blok endnu, staar den foreloebige stadig', () => {
  const s = streamReducer(initialStreamState(), workingStep({ action: 'analyze_image', step: 3 }) as never)
  expect(foreloebige(s)).toHaveLength(1)
})

it('et FAERDIGT kald spaerrer ikke for naeste annoncering af samme vaerktoej', () => {
  let s = initialStreamState()
  s = streamReducer(s, {
    type: 'content_block_start', index: 0,
    content_block: { type: 'tool_use', id: 'call_01', name: 'bash', input: {} },
  } as never)
  s = streamReducer(s, {
    type: 'content_block_start', index: 1,
    content_block: { type: 'tool_result', tool_use_id: 'call_01', status: 'ok', content: 'ok' },
  } as never)
  s = streamReducer(s, workingStep({ action: 'bash', step: 2 }) as never)
  expect(foreloebige(s)).toHaveLength(1)
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
  expect(s.workingStep).toBeNull()
})

/**
 * BLINKET — Bjørn 30/9-2026: «Den vises og forsvinder random under streamen.
 * Meningen er den skal vises hele tiden under streamen og væk når streamen
 * ender.»
 *
 * Det var ikke random. Serveren sender et livstegn mellem HVERT
 * værktøjskald (`visible_runs.py:2866` — «Tænker videre · runde N»), og
 * reducer'en tømte `workingStep` på hvert af dem. Arbejdslinjen blinkede af
 * og på for hver runde.
 *
 * Testen ovenfor fangede det ikke: den starter fra TOM state, så der er intet
 * at rydde. Denne starter fra en SAT linje — det er den forskel der gør
 * blinket synligt.
 */
it('et livstegn midt i streamen rydder IKKE den linje der staar', () => {
  let s = streamReducer(initialStreamState(), workingStep({
    action: 'read_file', step: 1, detail: 'Læser fil: a.py',
  }) as never)
  expect(s.workingStep).toBe('Læser fil: a.py')

  s = streamReducer(s, workingStep({
    action: 'thinking', detail: 'Tænker videre · runde 2', step: 2,
  }) as never)

  expect(s.workingStep).toBe('Læser fil: a.py')
  expect(s.workingAction).toBe('read_file')
})

it('en NY koersel rydder den forrige turs linje', () => {
  // Modstykket: uden dette ville den forrige turs sidste linje kort stå ved en
  // ny turs start, netop fordi livstegnene ikke længere rydder den.
  let s = streamReducer(initialStreamState(), workingStep({
    action: 'read_file', step: 1, detail: 'Læser fil: a.py',
  }) as never)
  s = streamReducer(s, {
    type: 'message_start',
    message: {
      id: 'run-2', model: 'm', provider: 'p', lane: 'l',
      usage: { input_tokens: 1, output_tokens: 0 },
    },
  } as never)
  expect(s.workingStep).toBeNull()
  expect(s.workingAction).toBeNull()
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

// ── serverens system_event-faldback ────────────────────────────────────────

const sysResultat = (o: Record<string, unknown>) => ({
  type: 'system_event' as const, kind: 'tool_result' as const,
  payload: { tool_use_id: 'b1', tool: 'bash', status: 'ok', result: 'ok', ...o },
})
const ægteKald = (id = 'b1', navn = 'bash', index = 0) => ({
  type: 'content_block_start' as const, index,
  content_block: { type: 'tool_use' as const, id, name: navn, input: {} },
})

it('system_event ALENE afslutter kaldet', () => {
  // Serveren sender udfaldet BAADE som system_event (altid) og som
  // content-blok (bag et flag). Reduceren foldede kun blokken - var flaget
  // slukket, stod raekken og koerte for evigt.
  let s = streamReducer(initialStreamState(), ægteKald() as never)
  s = streamReducer(s, sysResultat({}) as never)
  const b = s.blocks[0]
  expect(b && b.type === 'tool_use' && b.status).toBe('done')
  expect(b && b.type === 'tool_use' && b.result).toBe('ok')
})

it('en FEJL foldes som fejl', () => {
  let s = streamReducer(initialStreamState(), ægteKald() as never)
  s = streamReducer(s, sysResultat({ status: 'denied', result: 'afvist' }) as never)
  const b = s.blocks[0]
  expect(b && b.type === 'tool_use' && b.status).toBe('error')
})

it('en FORELOEBIG raekke ryddes af system_event — paa NAVN', () => {
  // Den har intet id fra serveren. Uden navne-matchet ville den blive
  // staaende og koere mens resultatet allerede var kommet.
  let s = streamReducer(initialStreamState(), workingStep({}) as never)
  s = streamReducer(s, sysResultat({ tool_use_id: 'noget-andet' }) as never)
  expect(foreloebige(s)).toHaveLength(0)
})

it('foldningen er IDEMPOTENT — begge veje giver det samme', () => {
  let s = streamReducer(initialStreamState(), ægteKald() as never)
  s = streamReducer(s, sysResultat({}) as never)
  s = streamReducer(s, {
    type: 'content_block_start', index: 1,
    content_block: { type: 'tool_result', tool_use_id: 'b1', status: 'ok', content: 'ok' },
  } as never)
  const b = s.blocks[0]
  expect(b && b.type === 'tool_use' && b.status).toBe('done')
})

it('et resultat for et UKENDT kald aendrer ingenting', () => {
  const s0 = streamReducer(initialStreamState(), ægteKald() as never)
  const s1 = streamReducer(s0, sysResultat({ tool_use_id: 'x', tool: 'ukendt' }) as never)
  expect(s1).toBe(s0)
})

// ─────────────────────────────────────────────────────────────────────────
// Runde-etiketten (14/9-2026)
//
// «Rettede fejl i login» — hvad runden UDRETTEDE, skrevet af en lille lokal
// model på serveren. Den mekaniske linje («Kørte en kommando og redigerede
// 2 filer +12 −4») siger hvad der SKETE og bliver stående UNDER etiketten.
//
// Etiketten bærer `tool_use_ids` og hæfter sig på DEM — ikke på en plads i
// strømmen. Det er samme greb som Claude Codes `preceding_tool_use_ids`: en
// etiket der kommer sent, eller en tråd der genopbygges i en anden rækkefølge,
// ville ellers sætte sig over de forkerte kald.
// ─────────────────────────────────────────────────────────────────────────

describe('tool_round_label', () => {
  it('gemmer etiketten under sine tool-id-er', () => {
    const s = streamReducer(initialStreamState(), {
      type: 'tool_round_label', run_id: 'r', round: 1,
      etiket: 'Rettede fejl i login', tool_use_ids: ['t1', 't2']
    } as never)
    expect(s.rundeEtiketter?.t1).toBe('Rettede fejl i login')
    expect(s.rundeEtiketter?.t2).toBe('Rettede fejl i login')
  })

  it('en etiket UDEN id-er gemmes ikke', () => {
    // Uden id-er er der intet at hæfte den på, og en etiket der svæver ville
    // sætte sig over det forkerte.
    const s = streamReducer(initialStreamState(), {
      type: 'tool_round_label', run_id: 'r', round: 1,
      etiket: 'Noget', tool_use_ids: []
    } as never)
    expect(s.rundeEtiketter ?? {}).toEqual({})
  })

  it('en TOM etiket gemmes ikke', () => {
    const s = streamReducer(initialStreamState(), {
      type: 'tool_round_label', run_id: 'r', round: 1,
      etiket: '   ', tool_use_ids: ['t1']
    } as never)
    expect(s.rundeEtiketter ?? {}).toEqual({})
  })

  it('flere runder lever side om side', () => {
    let s = streamReducer(initialStreamState(), {
      type: 'tool_round_label', run_id: 'r', round: 1,
      etiket: 'Læste config.json', tool_use_ids: ['a']
    } as never)
    s = streamReducer(s, {
      type: 'tool_round_label', run_id: 'r', round: 2,
      etiket: 'Kørte fejlende tests', tool_use_ids: ['b']
    } as never)
    expect(s.rundeEtiketter?.a).toBe('Læste config.json')
    expect(s.rundeEtiketter?.b).toBe('Kørte fejlende tests')
  })

  it('roerer ikke blokkene', () => {
    // Etiketten er en overskrift. Ændrede den strømmen, kunne en sen etiket
    // flytte rundt på det der allerede står på skærmen.
    const foer = streamReducer(initialStreamState(), { type: 'content_block_start', index: 0,
      content_block: { type: 'text', text: 'hej' } } as never)
    const efter = streamReducer(foer, {
      type: 'tool_round_label', run_id: 'r', round: 1,
      etiket: 'x', tool_use_ids: ['t1']
    } as never)
    expect(efter.blocks).toEqual(foer.blocks)
    expect(efter.status).toBe(foer.status)
  })
})

// ─────────────────────────────────────────────────────────────────────────
// Etiketten kommer som system_event (14/9-2026, maalt i produktion)
//
// Serveren sender `event: tool_round_label`, men SSE-v2 oversaetter den gamle
// stroem og pakker UKENDTE event-navne som `system_event` med
// `kind = event_name`. Reducerens `case 'tool_round_label'` fyrede derfor
// aldrig — Bjoern saa ingen etiketter paa en telefon der HAVDE den nye klient.
//
// Samme v1/v2-asymmetri som gjorde at `retry` virkede i desk og ikke paa
// mobilen. Begge former haandteres nu: den direkte for v1, og den indpakkede
// for v2.
// ─────────────────────────────────────────────────────────────────────────

describe('tool_round_label via system_event (SSE-v2)', () => {
  it('den INDPAKKEDE form gemmes ogsaa', () => {
    const s = streamReducer(initialStreamState(), {
      type: 'system_event',
      kind: 'tool_round_label',
      payload: { run_id: 'r', round: 1, etiket: 'Rettede fejl i login', tool_use_ids: ['t1'] }
    } as never)
    expect(s.rundeEtiketter?.t1).toBe('Rettede fejl i login')
  })

  it('et andet system_event roerer ikke etiketterne', () => {
    const s = streamReducer(initialStreamState(), {
      type: 'system_event', kind: 'working_step', payload: { detail: 'x' }
    } as never)
    expect(s.rundeEtiketter ?? {}).toEqual({})
  })

  it('en indpakket etiket UDEN id-er kasseres ogsaa', () => {
    const s = streamReducer(initialStreamState(), {
      type: 'system_event', kind: 'tool_round_label',
      payload: { run_id: 'r', round: 1, etiket: 'Noget', tool_use_ids: [] }
    } as never)
    expect(s.rundeEtiketter ?? {}).toEqual({})
  })
})

describe('billedet i den levende stream (27/9-2026)', () => {
  // Indtil nu lagde billedværktøjet en note fra sig under turen, og blokken
  // blev først bygget når svaret blev gemt. Under kørslen var der intet at
  // tegne — animationen er sin egen komponent, billedet havde ingen blok.
  //
  // `src` var PÅKRÆVET i protokollen, så et billede der kun har en reference
  // kunne slet ikke udtrykkes. `MessageAttachments.tegnBillede` har kunnet
  // begge dele hele tiden: `b.src` hvis den er der, ellers `blokUrl(...)`.
  const start = (cb: Record<string, unknown>) =>
    streamReducer(initialStreamState(), {
      type: 'content_block_start', index: 0, content_block: cb,
    } as never)

  it('en LIVE-blok med data-URL lander paa sit index', () => {
    const s = start({
      type: 'image', src: 'data:image/png;base64,AAA', filename: 'k.png',
      tool_use_id: 'tu-1', kilde: 'generated',
    })
    expect(s.blocks[0]).toMatchObject({
      type: 'image', src: 'data:image/png;base64,AAA', tool_use_id: 'tu-1',
    })
  })

  it('en blok UDEN src beholder sin reference', () => {
    const s = start({
      type: 'image', attachment_id: 'att-77', filename: 'stor.png',
      mime_type: 'image/png', kilde: 'generated', tool_use_id: 'tu-2',
    })
    expect(s.blocks[0]).toMatchObject({ type: 'image', attachment_id: 'att-77' })
    expect((s.blocks[0] as { src?: string }).src).toBeUndefined()
  })

  it('tool_use_id foelger med — ankeret der gør at billedet ikke hopper', () => {
    const s = start({ type: 'image', src: 'data:image/png;base64,B', tool_use_id: 'tu-3' })
    expect((s.blocks[0] as { tool_use_id?: string }).tool_use_id).toBe('tu-3')
  })
})
