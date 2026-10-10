import { describe, it, expect } from 'vitest'
import { streamReducer, initialStreamState, liveBlokke } from './streamReducer'
import type { StreamEvent } from './sseProtocol'

const reduce = (events: StreamEvent[]) =>
  events.reduce(streamReducer, initialStreamState())

describe('streamReducer', () => {
  it('viser syntese mellem værktøjsrunder fra hver provisional delta uden dublet ved commit', () => {
    const start: StreamEvent = {
      type: 'message_start',
      message: { id: 'r1', model: 'm', provider: 'p', lane: 'primary', session_id: 's', usage: { input_tokens: 0, output_tokens: 0 } },
    }
    const system = (kind: string, payload: Record<string, unknown>): StreamEvent =>
      ({ type: 'system_event', kind, payload })
    let state = streamReducer(initialStreamState(), start)
    state = streamReducer(state, { type: 'content_block_start', index: 0,
      content_block: { type: 'tool_use', id: 'tool-1', name: 'bash', input: {} } })
    state = streamReducer(state, system('provisional_text_delta', { run_id: 'r1', delta: 'Første ' }))
    expect(liveBlokke(state).at(-1)).toEqual({ type: 'text', text: 'Første ' })
    state = streamReducer(state, system('provisional_text_delta', { run_id: 'r1', delta: 'syntese' }))
    expect(liveBlokke(state).at(-1)).toEqual({ type: 'text', text: 'Første syntese' })
    expect(streamReducer(state, system('provisional_text_delta', { run_id: 'other', delta: 'forkert' }))).toBe(state)

    state = streamReducer(state, { type: 'content_block_start', index: 1, content_block: { type: 'text', text: '' } })
    state = streamReducer(state, { type: 'content_block_delta', index: 1, delta: { type: 'text_delta', text: 'Første syntese' } })
    expect(liveBlokke(state).filter((b) => b.type === 'text')).toHaveLength(1)
    state = streamReducer(state, system('provisional_text_commit', { run_id: 'r1' }))
    expect(liveBlokke(state).filter((b) => b.type === 'text')).toEqual([{ type: 'text', text: 'Første syntese' }])
    state = streamReducer(state, system('provisional_text_delta', { run_id: 'r1', delta: 'Næste ' }))
    expect(liveBlokke(state).at(-1)).toEqual({ type: 'text', text: 'Næste ' })
    state = streamReducer(state, system('provisional_text_delta', { run_id: 'r1', delta: 'svar' }))
    state = streamReducer(state, system('final_answer_start', { run_id: 'r1' }))
    state = streamReducer(state, { type: 'content_block_start', index: 2, content_block: { type: 'text', text: '' } })
    state = streamReducer(state, { type: 'content_block_delta', index: 2, delta: { type: 'text_delta', text: 'Næste svar' } })
    expect(liveBlokke(state).filter((b) => b.type === 'text').map((b) => b.type === 'text' && b.text))
      .toEqual(['Første syntese', 'Næste svar'])
    state = streamReducer(state, { type: 'message_stop' })
    expect(liveBlokke(state).filter((b) => b.type === 'text').map((b) => b.type === 'text' && b.text))
      .toEqual(['Første syntese', 'Næste svar'])
  })

  it('genoptager en ny rundes tekst selv hvis message_start mangler efter reconnect', () => {
    const old = reduce([
      { type: 'message_start', message: { id: 'old', model: 'm', provider: 'p', lane: 'primary', session_id: 's', usage: { input_tokens: 0, output_tokens: 0 } } },
      { type: 'content_block_start', index: 0, content_block: { type: 'text', text: 'Gammelt' } },
      { type: 'message_stop' },
    ])
    const next = streamReducer(old, { type: 'system_event', kind: 'provisional_text_delta', payload: { run_id: 'new', delta: 'Nyt ' } })
    expect(next.activeRunId).toBe('new')
    expect(next.status).toBe('working')
    expect(liveBlokke(next)).toEqual([{ type: 'text', text: 'Nyt ' }])
  })

  it('folder kun på det aktuelle runs bekræftede slutsvar og nulstiller ved nyt run', () => {
    const start = (id: string): StreamEvent => ({
      type: 'message_start',
      message: { id, model: 'm', provider: 'p', lane: 'primary', session_id: 's', usage: { input_tokens: 0, output_tokens: 0 } },
    })
    const before = reduce([start('r1'), { type: 'system_event', kind: 'working_step', payload: { action: 'thinking', detail: 'Tænker videre · runde 2' } }])
    expect(before.finalAnswerStarted).toBe(false)
    expect(streamReducer(before, { type: 'system_event', kind: 'final_answer_start', payload: { run_id: 'old' } }).finalAnswerStarted).toBe(false)
    expect(streamReducer(before, { type: 'system_event', kind: 'final_answer_start', payload: {} }).finalAnswerStarted).toBe(false)
    const after = streamReducer(before, { type: 'system_event', kind: 'final_answer_start', payload: { run_id: 'r1' } })
    expect(after.finalAnswerStarted).toBe(true)
    expect(streamReducer(after, start('r2')).finalAnswerStarted).toBe(false)
  })

  it('message_start sets working + activeRunId', () => {
    const s = reduce([
      { type: 'message_start', message: { id: 'visible-9', model: 'm', provider: 'p', lane: 'primary', session_id: 's', usage: { input_tokens: 0, output_tokens: 0 } } },
    ])
    expect(s.status).toBe('working')
    expect(s.activeRunId).toBe('visible-9')
  })

  it('message_start captures the run model/provider/lane (footer-bug fix)', () => {
    const s = reduce([
      { type: 'message_start', message: { id: 'r1', model: 'glm-5.1', provider: 'ollama', lane: 'primary', session_id: 's', usage: { input_tokens: 0, output_tokens: 0 } } },
    ])
    expect(s.model).toBe('glm-5.1')
    expect(s.provider).toBe('ollama')
    expect(s.lane).toBe('primary')
  })

  it('accumulates text deltas into one block', () => {
    const s = reduce([
      { type: 'content_block_start', index: 0, content_block: { type: 'text', text: '' } },
      { type: 'content_block_delta', index: 0, delta: { type: 'text_delta', text: 'Hej ' } },
      { type: 'content_block_delta', index: 0, delta: { type: 'text_delta', text: 'Bjørn' } },
    ])
    expect(s.blocks[0]).toEqual({ type: 'text', text: 'Hej Bjørn' })
  })

  it('keeps interleaved blocks separate by index', () => {
    const s = reduce([
      { type: 'content_block_start', index: 0, content_block: { type: 'text', text: '' } },
      { type: 'content_block_delta', index: 0, delta: { type: 'text_delta', text: 'A' } },
      { type: 'content_block_start', index: 1, content_block: { type: 'thinking', thinking: '' } },
      { type: 'content_block_delta', index: 1, delta: { type: 'thinking_delta', thinking: 'hmm' } },
      { type: 'content_block_delta', index: 0, delta: { type: 'text_delta', text: 'B' } },
    ])
    expect(s.blocks[0]).toEqual({ type: 'text', text: 'AB' })
    // `startet` er klientens ur (17/9-2026) — indholdet er det testen gælder.
    expect(s.blocks[1]).toMatchObject({ type: 'thinking', thinking: 'hmm' })
  })

  it('accumulates tool_use input_json into partialJson', () => {
    const s = reduce([
      { type: 'content_block_start', index: 0, content_block: { type: 'tool_use', id: 'tu1', name: 'bash', input: {} } },
      { type: 'content_block_delta', index: 0, delta: { type: 'input_json_delta', partial_json: '{"cmd":"l' } },
      { type: 'content_block_delta', index: 0, delta: { type: 'input_json_delta', partial_json: 's"}' } },
    ])
    const b = s.blocks[0]
    expect(b).toBeDefined()
    expect(b?.type).toBe('tool_use')
    if (b && b.type === 'tool_use') {
      expect(b.partialJson).toBe('{"cmd":"ls"}')
      expect(b.status).toBe('running')
    }
  })

  it('ignores delta for index without start (no crash)', () => {
    const s = reduce([
      { type: 'content_block_delta', index: 5, delta: { type: 'text_delta', text: 'x' } },
    ])
    expect(s.blocks[5]).toBeUndefined()
    expect(s.status).toBe('idle')
  })

  it('ignores unknown system_event kind', () => {
    const s = reduce([
      { type: 'message_start', message: { id: 'r', model: 'm', provider: 'p', lane: 'primary', session_id: 's', usage: { input_tokens: 0, output_tokens: 0 } } },
      { type: 'system_event', kind: 'totally_unknown', payload: {} },
    ])
    expect(s.status).toBe('working')
  })

  it('run_recovery bliver synlig og holder segmentet i recovery', () => {
    const state = streamReducer(initialStreamState(), {
      type: 'system_event',
      kind: 'run_recovery',
      payload: {
        reason: 'pending-tool-intent',
        message: 'Jarvis havde stadig et værktøjskald klar. Jarvis fortsætter automatisk.',
        continuing: true,
      },
    })
    expect(state.recoveryNotice?.reason).toBe('pending-tool-intent')
    expect(state.recoveryNotice?.continuing).toBe(true)
    expect(state.recoveryNotice?.message).toContain('fortsætter automatisk')
  })

  // Bjørn 30/9-2026: «så forsvinder den badge ikk igen fra desk og der er ikk
  // noget hvor jeg kan trykke den væk». Varslets ENESTE ryddevej var et
  // message_delta med stop_reason end_turn/completed — og en tvungen slutrunde
  // har per definition ikke det stop_reason. Betingelsen der rejste banneret
  // udelukkede altså vejen der fjernede det.
  const medVarsel = () => streamReducer(initialStreamState(), {
    type: 'system_event',
    kind: 'run_recovery',
    payload: { reason: 'forced-finalize-unverified', message: 'En tvungen slutrunde…', continuing: true },
  } as unknown as StreamEvent)

  it('en tvungen slutrunde rydder IKKE varslet af sig selv', () => {
    const s = streamReducer(medVarsel(), {
      type: 'message_delta',
      delta: { stop_reason: 'max_tokens' },
      usage: { input_tokens: 1, output_tokens: 1 },
    } as unknown as StreamEvent)
    expect(s.recoveryNotice).toBeDefined()
  })

  it('et NYT run rydder varslet', () => {
    const s = streamReducer(medVarsel(), {
      type: 'message_start',
      message: { id: 'visible-ny', model: 'm', provider: 'p', lane: 'l', session_id: 's', usage: { input_tokens: 0, output_tokens: 0 } },
    } as unknown as StreamEvent)
    expect(s.recoveryNotice).toBeUndefined()
  })

  it('men SAMME run beholder det — en reconnect er ikke en fortsættelse', () => {
    const start = { type: 'message_start', message: { id: 'visible-1', model: 'm', provider: 'p', lane: 'l', session_id: 's', usage: { input_tokens: 0, output_tokens: 0 } } } as unknown as StreamEvent
    const varsel = { type: 'system_event', kind: 'run_recovery', payload: { reason: 'forced-finalize-unverified', message: 'En tvungen slutrunde…', continuing: true } } as unknown as StreamEvent
    // Varslet rejses MENS visible-1 kører; så kommer et replay af samme run.
    const s = [start, varsel, start].reduce(streamReducer, initialStreamState())
    expect(s.recoveryNotice).toBeDefined()
  })

  it('han kan trykke det væk', () => {
    const s = streamReducer(medVarsel(), {
      type: 'system_event',
      kind: 'run_recovery',
      payload: { ryddet: true },
    } as unknown as StreamEvent)
    expect(s.recoveryNotice).toBeUndefined()
  })

  it('message_stop sets done', () => {
    const s = reduce([
      { type: 'message_start', message: { id: 'r', model: 'm', provider: 'p', lane: 'primary', session_id: 's', usage: { input_tokens: 0, output_tokens: 0 } } },
      { type: 'message_stop' },
    ])
    expect(s.status).toBe('done')
  })

  it('empty response (start→stop, no content) → done with no blocks', () => {
    const s = reduce([
      { type: 'message_start', message: { id: 'r', model: 'm', provider: 'p', lane: 'primary', session_id: 's', usage: { input_tokens: 0, output_tokens: 0 } } },
      { type: 'message_stop' },
    ])
    expect(s.blocks).toHaveLength(0)
    expect(s.status).toBe('done')
  })

  it('working_step system_event updates matching tool_use status', () => {
    const s = reduce([
      { type: 'content_block_start', index: 0, content_block: { type: 'tool_use', id: 'tu1', name: 'bash', input: {} } },
      { type: 'system_event', kind: 'working_step', payload: { tool_id: 'tu1', status: 'done', result: 'ok' } },
    ])
    const b = s.blocks[0]
    if (b && b.type === 'tool_use') {
      expect(b.status).toBe('done')
      expect(b.result).toBe('ok')
    }
  })

  it('internt thinking-livstegn rydder sidste værktøj uden at vise runden', () => {
    const s = reduce([
      { type: 'system_event', kind: 'working_step', payload: { action: 'bash', detail: 'Bash: git status', status: 'running' } },
      { type: 'system_event', kind: 'working_step', payload: { action: 'thinking', detail: 'Tænker videre · runde 2', status: 'running' } },
    ] as StreamEvent[])
    expect(s.workingStep).toBeNull()
  })
})

describe('streamReducer — live tool output', () => {
  const start: StreamEvent = {
    type: 'message_start',
    message: { id: 'r1', model: 'm', provider: 'p', lane: 'primary', session_id: 's', usage: { input_tokens: 0, output_tokens: 0 } },
  }
  const toolStart: StreamEvent = {
    type: 'content_block_start', index: 0,
    content_block: { type: 'tool_use', id: 't1', name: 'bash', input: {} },
  }
  const delta = (seq: number, chunk: string, over: Record<string, unknown> = {}): StreamEvent => ({
    type: 'system_event', kind: 'tool_output_delta',
    payload: { run_id: 'r1', tool_use_id: 't1', stream: 'stdout', seq, chunk, ...over },
  })

  it('tilføjer kun stigende deltas til det matchende kørende kort', () => {
    const s = reduce([start, toolStart, delta(2, 'B'), delta(2, 'dup'), delta(1, 'old'), delta(3, 'C')])
    const card = s.blocks[0]
    expect(card?.type === 'tool_use' ? card.liveOutput : '').toBe('BC')
    expect(card?.type === 'tool_use' ? card.liveOutputSeq : 0).toBe(3)
  })

  it('ignorerer ukendt id, forkert run og output efter terminal status', () => {
    const running = reduce([start, toolStart])
    const unknown = streamReducer(running, delta(1, 'x', { tool_use_id: 'missing' }))
    const wrongRun = streamReducer(running, delta(1, 'x', { run_id: 'r2' }))
    expect(unknown).toBe(running)
    expect(wrongRun).toBe(running)

    const done = streamReducer(running, {
      type: 'system_event', kind: 'tool_result',
      payload: { tool_use_id: 't1', status: 'ok', result: 'final' },
    })
    expect(streamReducer(done, delta(2, 'late'))).toBe(done)
  })

  it('holder kun de nyeste 64 KiB og husker både klient- og servertruncation', () => {
    const tooMuch = 'a'.repeat(65_536) + 'tail'
    const s = reduce([start, toolStart, delta(1, tooMuch)])
    const card = s.blocks[0]
    expect(card?.type).toBe('tool_use')
    if (card?.type !== 'tool_use') throw new Error('toolkortet mangler')
    expect(card.liveOutput).toHaveLength(65_536)
    expect(card.liveOutput?.endsWith('tail')).toBe(true)
    expect(card.liveOutputTruncated).toBe(true)

    const server = reduce([start, toolStart, delta(1, 'partial', { truncated: true })])
    expect(server.blocks[0]?.type === 'tool_use' ? server.blocks[0].liveOutputTruncated : false).toBe(true)
  })

  it('det kanoniske slutresultat erstatter og rydder live-tilstanden', () => {
    const s = reduce([
      start, toolStart, delta(1, 'live'),
      { type: 'system_event', kind: 'tool_result', payload: { tool_use_id: 't1', status: 'ok', result: 'final' } },
    ])
    const card = s.blocks[0]
    expect(card?.type).toBe('tool_use')
    if (card?.type === 'tool_use') {
      expect(card.status).toBe('done')
      expect(card.result).toBe('final')
      expect(card.liveOutput).toBeUndefined()
      expect(card.liveOutputSeq).toBeUndefined()
      expect(card.liveOutputTruncated).toBeUndefined()
    }
  })
})

describe('streamReducer — tool_result status (Phase 2)', () => {
  it('tool_result system_event sætter tool_use-blok status til done', () => {
    const s = reduce([
      { type: 'content_block_start', index: 0, content_block: { type: 'tool_use', id: 'cap_1', name: 'read_file', input: {} } },
      { type: 'content_block_stop', index: 0 },
      { type: 'system_event', kind: 'tool_result', payload: { tool_use_id: 'cap_1', tool: 'read_file', status: 'ok' } },
    ] as StreamEvent[])
    const b = s.blocks[0]
    expect(b?.type).toBe('tool_use')
    if (b && b.type === 'tool_use') expect(b.status).toBe('done')
  })

  it('tool_result med status error sætter error', () => {
    const s = reduce([
      { type: 'content_block_start', index: 0, content_block: { type: 'tool_use', id: 'cap_2', name: 'bash', input: {} } },
      { type: 'system_event', kind: 'tool_result', payload: { tool_use_id: 'cap_2', status: 'failed' } },
    ] as StreamEvent[])
    const b = s.blocks[0]
    if (b && b.type === 'tool_use') expect(b.status).toBe('error')
  })

  it('tool_result for ukendt id ignoreres gracefully', () => {
    const s = reduce([
      { type: 'content_block_start', index: 0, content_block: { type: 'text', text: 'hej' } },
      { type: 'system_event', kind: 'tool_result', payload: { tool_use_id: 'mangler', status: 'ok' } },
    ] as StreamEvent[])
    expect(s.blocks[0]).toEqual({ type: 'text', text: 'hej' })
  })
})

describe('streamReducer — usage.input fra message_delta (context-ring #9)', () => {
  it('fanger input_tokens fra message_delta', () => {
    const s = reduce([
      { type: 'message_start', message: { id: 'r', model: 'm', provider: 'p', lane: 'l', session_id: 's', usage: { input_tokens: 0, output_tokens: 0 } } },
      { type: 'message_delta', delta: { stop_reason: 'end_turn' }, usage: { input_tokens: 120000, output_tokens: 50, cache_hit_tokens: 8000, cache_miss_tokens: 0 } },
    ] as StreamEvent[])
    expect(s.usage.input).toBe(120000)
    expect(s.usage.cacheHit).toBe(8000)
  })

  it('system_event tool_result sets result + status on the tool_use block', () => {
    const s = reduce([
      { type: 'content_block_start', index: 0, content_block: { type: 'tool_use', id: 't1', name: 'web_search', input: { query: 'vejr' } } },
      { type: 'system_event', kind: 'tool_result', payload: { tool_use_id: 't1', status: 'ok', result: '3 resultater' } },
    ] as StreamEvent[])
    const b = s.blocks[0]
    expect(b?.type).toBe('tool_use')
    if (b?.type === 'tool_use') {
      expect(b.status).toBe('done')
      expect(b.result).toBe('3 resultater')
    }
  })
})

  it('preserves blocks on a second message_start for the SAME run (reconnect/replay)', () => {
    // Byg en tur med en tool-blok + tekst, som brugeren allerede har set.
    let s = streamReducer(initialStreamState(), { type: 'message_start', message: { id: 'visible-same', model: 'm', provider: 'p', lane: 'primary', session_id: 's', usage: { input_tokens: 0, output_tokens: 0 } } } as any)
    s = streamReducer(s, { type: 'content_block_start', index: 0, content_block: { type: 'tool_use', id: 't1', name: 'db_query', input: {} } } as any)
    s = streamReducer(s, { type: 'content_block_start', index: 1, content_block: { type: 'text', text: 'Første linje' } } as any)
    expect(s.blocks.length).toBe(2)
    // Reconnect/relay-replay sender message_start igen med SAMME run-id.
    const s2 = streamReducer(s, { type: 'message_start', message: { id: 'visible-same', model: 'm', provider: 'p', lane: 'primary', session_id: 's', usage: { input_tokens: 0, output_tokens: 0 } } } as any)
    // Tool-blok + tekst må IKKE forsvinde.
    expect(s2.blocks.length).toBe(2)
    expect(s2.blocks[0]).toMatchObject({ type: 'tool_use', id: 't1' })
  })

  it('resets blocks on a message_start for a DIFFERENT run', () => {
    let s = streamReducer(initialStreamState(), { type: 'message_start', message: { id: 'run-a', model: 'm', provider: 'p', lane: 'primary', session_id: 's', usage: { input_tokens: 0, output_tokens: 0 } } } as any)
    s = streamReducer(s, { type: 'content_block_start', index: 0, content_block: { type: 'text', text: 'gammelt' } } as any)
    const s2 = streamReducer(s, { type: 'message_start', message: { id: 'run-b', model: 'm', provider: 'p', lane: 'primary', session_id: 's', usage: { input_tokens: 0, output_tokens: 0 } } } as any)
    expect(s2.blocks.length).toBe(0)
  })

describe('streamReducer tool_result content-blok', () => {
  it('folder tool_result-content-blok ind på matchende tool_use', () => {
    let s = initialStreamState()
    s = streamReducer(s, { type: 'content_block_start', index: 0, content_block: { type: 'tool_use', id: 'toolu_1', name: 'bash', input: {} } } as any)
    s = streamReducer(s, { type: 'content_block_start', index: 1, content_block: { type: 'tool_result', tool_use_id: 'toolu_1', status: 'done', content: 'ok' } } as any)
    const tu = s.blocks.find((b) => b && b.type === 'tool_use') as any
    expect(tu.status).toBe('done')
    expect(tu.result).toBe('ok')
    expect(s.blocks.filter(Boolean).some((b: any) => b.type === 'tool_result')).toBe(false)
  })
  it('bevarer den gamle system_event tool_result-sti (dual-read)', () => {
    let s = initialStreamState()
    s = streamReducer(s, { type: 'content_block_start', index: 0, content_block: { type: 'tool_use', id: 'toolu_9', name: 'bash', input: {} } } as any)
    s = streamReducer(s, { type: 'system_event', kind: 'tool_result', payload: { tool_use_id: 'toolu_9', status: 'ok', result: 'via-legacy' } } as any)
    const tu = s.blocks.find((b) => b && b.type === 'tool_use') as any
    expect(tu.result).toBe('via-legacy')
  })
})

describe('billedet i den levende stream (27/9-2026)', () => {
  // Indtil nu lagde billedværktøjet en note fra sig under turen, og blokken
  // blev først bygget når svaret blev gemt. Under kørslen var der intet at
  // tegne. Renderen har haft grenen hele tiden (`BlocksRenderer`: `block.src ?
  // <ImageBlock/> : …`) — den fik bare aldrig noget.
  const start = (cb: Record<string, unknown>): StreamEvent =>
    ({ type: 'content_block_start', index: 0, content_block: cb } as StreamEvent)

  it('en LIVE-blok med data-URL lander på sit index og kan tegnes', () => {
    const s = reduce([start({
      type: 'image', src: 'data:image/png;base64,AAA', filename: 'k.png',
      tool_use_id: 'tu-1', kilde: 'generated',
    })])
    expect(s.blocks[0]).toMatchObject({
      type: 'image', src: 'data:image/png;base64,AAA', tool_use_id: 'tu-1',
    })
  })

  it('en blok UDEN src beholder sin reference — billedet hentes med token', () => {
    // Er billedet for stort til en data-URL, sender serveren attachment_id
    // alene. Attachment'en er allerede registreret, så adressen virker straks.
    const s = reduce([start({
      type: 'image', attachment_id: 'att-77', filename: 'stor.png',
      mime_type: 'image/png', kilde: 'generated', tool_use_id: 'tu-2',
    })])
    expect(s.blocks[0]).toMatchObject({ type: 'image', attachment_id: 'att-77' })
    expect((s.blocks[0] as { src?: string }).src).toBeUndefined()
  })

  it('tool_use_id følger med — det er ANKERET', () => {
    // Den gemte blok får samme tool_use_id, så billedet lander samme sted før
    // og efter turen. Ingen mellemstation, intet hop.
    const s = reduce([start({ type: 'image', src: 'data:image/png;base64,B', tool_use_id: 'tu-3' })])
    expect((s.blocks[0] as { tool_use_id?: string }).tool_use_id).toBe('tu-3')
  })

  it('billedblokken fortrænger ikke en tool_use på et andet index', () => {
    const s = reduce([
      { type: 'content_block_start', index: 0, content_block: { type: 'tool_use', id: 'tu-4', name: 'openrouter_image', input: {} } },
      { type: 'content_block_start', index: 1, content_block: { type: 'image', src: 'data:image/png;base64,C', tool_use_id: 'tu-4' } },
    ] as StreamEvent[])
    expect(s.blocks[0]).toMatchObject({ type: 'tool_use', id: 'tu-4' })
    expect(s.blocks[1]).toMatchObject({ type: 'image' })
  })
})

// ── Udgivet fil/video i den levende strøm (7/10-2026) ─────────────────────
//
// Grenen fandtes ikke, og udsenderen sendte heller ikke blokken. En widget er
// `text/html` → typen `file`; den faldt derfor til jorden i den levende strøm
// og dukkede først op når tråden blev genindlæst fra `content_json`.

describe('udgivet fil i den levende strøm (7/10-2026)', () => {
  const start = (cb: Record<string, unknown>) => reduce([
    { type: 'content_block_start', index: 0, content_block: cb } as StreamEvent,
  ])

  it('en widget-blok (file + attachment_id + generated) lander i blocks', () => {
    const s = start({
      type: 'file', filename: 'widget-20261007T063003248515.html',
      mime_type: 'text/html', attachment_id: 'att-w1', kilde: 'generated',
    })
    expect(s.blocks[0]).toMatchObject({
      type: 'file', attachment_id: 'att-w1', kilde: 'generated',
    })
  })

  it('en almindelig udgivet fil bevares ogsaa — den er ikke kun for widgets', () => {
    const s = start({
      type: 'file', filename: 'rapport.pdf', mime_type: 'application/pdf',
      url: 'https://jarvis.srvlab.dk/rapport.pdf', kilde: 'published',
    })
    expect(s.blocks[0]).toMatchObject({ type: 'file', kilde: 'published' })
  })

  it('en video-blok lander ogsaa — samme hul ramte den', () => {
    const s = start({
      type: 'video', filename: 'k.mp4', mime_type: 'video/mp4',
      attachment_id: 'att-v1', kilde: 'generated',
    })
    expect(s.blocks[0]).toMatchObject({ type: 'video', attachment_id: 'att-v1' })
  })
})
