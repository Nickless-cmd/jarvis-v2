/**
 * Cross-device (Bjørn 16/11-2026): «Cross-device streaming blander ny tur med
 * tidligere besked.»
 *
 * Den PASSIVE klient følger et run via `/chat/runs/{id}/subscribe`. Dens
 * `followState` overlever mellem runs. Er det forrige svar låst (`svarLaast`)
 * og den nye tur ikke bærer `origin` (en brugertur fra den anden enhed har
 * tom origin), læser reduceren det nye run-id som en RUNDE i samme tur og
 * bevarer den forrige turs blokke → ny tekst lægges oven i gammel besked.
 *
 * Et follow-abonnement er bundet til ÉT run. Bytter `followRun` run-id, er
 * det pr. definition en ny tur — det skal reduceren have at vide via
 * `follow_start`, i stedet for at gætte ud fra `origin`/`svarLaast`.
 */
import { describe, expect, it } from 'vitest'
import { initialStreamState, streamReducer, type StreamState } from './streamReducer'

const efterLaestSvar = (): StreamState => ({
  ...initialStreamState(),
  status: 'done',
  activeRunId: 'run-A',
  finalAnswerStarted: true,
  svarLaast: true,
  blocks: [
    { type: 'text', text: 'Indledning A.', phase: 'commentary' },
    { type: 'text', text: 'Svar fra tur A.', phase: 'final_answer' },
  ],
})

const textBlocks = (s: StreamState) =>
  s.blocks.filter((b) => b?.type === 'text').map((b) => (b as { text: string }).text)

const fold = (s: StreamState, evs: unknown[]) =>
  evs.reduce<StreamState>((acc, e) => streamReducer(acc, e as never), s)

const turB = [
  { type: 'message_start', message: { id: 'run-B', model: 'm', provider: 'p', lane: 'l', origin: '', usage: { input_tokens: 0, output_tokens: 0 } } },
  { type: 'content_block_start', index: 0, content_block: { type: 'text', text: '', phase: 'final_answer' } },
  { type: 'content_block_delta', index: 0, delta: { type: 'text_delta', text: 'Svar fra tur B.' } },
]

describe('follow_start — passiv klient binder et abonnement til ét run', () => {
  it('REPRO: ny tur (tom origin) efter låst svar blandes IKKE med forrige besked', () => {
    const s = fold(efterLaestSvar(), [
      { type: 'system_event', kind: 'follow_start', payload: { run_id: 'run-B' } },
      ...turB,
    ])
    expect(textBlocks(s)).toEqual(['Svar fra tur B.'])
    expect(s.activeRunId).toBe('run-B')
    expect(s.arbejdeEfterSvar).toBe(false) // ingen arvet lås fra tur A
  })

  it('genstart af SAMME run (reconnect) bevarer det der allerede er set', () => {
    const midt = fold(initialStreamState(), [
      { type: 'system_event', kind: 'follow_start', payload: { run_id: 'run-B' } },
      ...turB,
    ])
    const efter = fold(midt, [{ type: 'system_event', kind: 'follow_start', payload: { run_id: 'run-B' } }])
    expect(efter).toBe(midt)
    // replay fra offset 0 sætter blok-indekset på ny uden dobling
    expect(textBlocks(fold(efter, turB))).toEqual(['Svar fra tur B.'])
  })

  it('tomt run_id ændrer intet', () => {
    const s = efterLaestSvar()
    expect(streamReducer(s, { type: 'system_event', kind: 'follow_start', payload: {} } as never)).toBe(s)
  })

  it('NULTILSTAND: uden follow_start blandes turene (dokumenterer fejlen på HEAD)', () => {
    const s = fold(efterLaestSvar(), turB)
    // B's blok 0 overskriver A's blok 0, men A's blok 1 står tilbage under B.
    expect(textBlocks(s)).toEqual(['Svar fra tur B.', 'Svar fra tur A.'])
  })
})
