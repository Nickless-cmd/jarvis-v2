import { describe, it, expect } from 'vitest'
import { streamReducer, initialStreamState } from './streamReducer'
import type { StreamEvent } from './sseProtocol'

/**
 * SVARET RIVES IKKE NED AF EN EKSTRA RUNDE (Bjørn 28/10-2026).
 *
 * Bjørn: «hoved ud → agentiske runder → runder slut → hoved ind → pace
 * forsætter … men fordi du kalder en extra runde så fortsætter det der skulle
 * have været svaret plus den nye runde inde i hoved ind til du er helt færdig
 * → tom skærm → og så starter slut besked med at pace uden for hoved».
 *
 * Tre steder wipede state ved et nyt run-id: `message_start`, `run`-framen
 * (fuld initialStreamState) og `provisional_text_delta`. Alle tre er RUNDER i
 * samme tur. `client_turn_start` — brugerens send — er den eneste autoritative
 * turgrænse, og kun den må rydde.
 */

const msgStart = (id: string): StreamEvent => ({
  type: 'message_start',
  message: { id, model: 'm', provider: 'p', lane: 'primary', session_id: 's',
    usage: { input_tokens: 0, output_tokens: 0 } },
})
const system = (kind: string, payload: Record<string, unknown>): StreamEvent =>
  ({ type: 'system_event', kind, payload })

/** En tur hvor slutsvaret er begyndt — altså låst. */
function laastSvar() {
  let s = streamReducer(initialStreamState(), msgStart('r1'))
  s = streamReducer(s, { type: 'content_block_start', index: 0,
    content_block: { type: 'text', text: '', phase: 'final_answer' } } as StreamEvent)
  s = streamReducer(s, { type: 'content_block_delta', index: 0,
    delta: { type: 'text_delta', text: 'Svaret' } })
  return s
}

describe('en ekstra runde river ikke svaret ned', () => {
  it('message_start med NYT run-id bevarer blokke, lås og turStart', () => {
    const foer = laastSvar()
    expect(foer.svarLaast).toBe(true)
    const efter = streamReducer(foer, msgStart('r2'))
    expect(efter.svarLaast).toBe(true)
    expect(efter.blocks.length).toBe(foer.blocks.length)
    expect(efter.turStart).toBe(foer.turStart)
  })

  it('run-framen med NYT run-id bevarer blokke og turStart', () => {
    const foer = laastSvar()
    const efter = streamReducer(foer, system('run', { run_id: 'r2' }))
    expect(efter.svarLaast).toBe(true)
    expect(efter.blocks.length).toBe(foer.blocks.length)
    expect(efter.turStart).toBe(foer.turStart)
    expect(efter.activeRunId).toBe('r2')
  })

  it('en ny runde lægger tekst TIL — den rydder ikke den tekst der står', () => {
    // Den faktiske sekvens: `message_start` med det nye id kommer FØRST, derefter
    // deltas. Et delta med et ukendt run-id afvises af vagten i reduceren, så
    // testen følger den vej der faktisk sker i drift.
    const foer = laastSvar()
    const medNytRun = streamReducer(foer, msgStart('r2'))
    const efter = streamReducer(medNytRun, system('provisional_text_delta', { run_id: 'r2', delta: 'Fortsat' }))
    expect(efter.provisionalText).toContain('Fortsat')
    expect(efter.blocks.length).toBe(foer.blocks.length)
    expect(efter.svarLaast).toBe(true)
    expect(efter.turStart).toBe(foer.turStart)
  })

  it('MODPRØVE: en NY TUR rydder alt — låsen må ikke lække mellem ture', () => {
    const foer = laastSvar()
    const efter = streamReducer(foer, system('client_turn_start', {}))
    expect(efter.svarLaast).toBe(false)
    expect(efter.blocks).toEqual([])
    expect(efter.activeRunId).toBeNull()
  })
})
