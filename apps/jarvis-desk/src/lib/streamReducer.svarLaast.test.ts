/**
 * Låsen beskytter SVARET — ikke hovedets tilstand.
 *
 * Bjørn 29/10-2026: «hoved folder, streamen forsætter inde i hoved -> tom
 * skærm -> stream slut -> pace starter uden for tur hoved».
 *
 * `svarLaast` blev indført 28/10 for at et follow-up-run ikke måtte rive det
 * færdige svar op. Den virker efter hensigten. Fejlen var at klienten brugte
 * låsen som «turen er slut»: `finalAnswerStarted = finalAnswerStarted ||
 * svarLaast`, og `arbejdeKoerer = streaming && !finalAnswerStarted` foldede
 * derfor hovedet mens det nye run skrev ind i den foldede liste.
 *
 * Denne fil måler det signal der manglede: at der ER kommet arbejde efter
 * låsen. Det er dét hovedet skal folde ud efter — ikke låsen selv.
 */
import { describe, expect, it } from 'vitest'
import { initialStreamState, streamReducer, type StreamState } from './streamReducer'

/** En tur hvor slutsvaret er identificeret og låst. */
function laastTur(): StreamState {
  return {
    ...initialStreamState(),
    status: 'working',
    activeRunId: 'run-1',
    finalAnswerStarted: true,
    svarLaast: true,
    blocks: [{ type: 'text', text: 'Slutsvaret.', phase: 'final_answer' }],
  }
}

describe('streamReducer — arbejde efter svar-låsen', () => {
  it('markerer at der er kommet arbejde da et nyt run startede efter låsen', () => {
    const foer = laastTur()
    expect(foer.arbejdeEfterSvar).toBe(false)

    const efter = streamReducer(foer, {
      type: 'system_event', kind: 'run', payload: { run_id: 'run-2' },
    } as never)

    // Låsen består — svaret må ikke rives op.
    expect(efter.svarLaast).toBe(true)
    expect(efter.blocks).toHaveLength(1)
    // Men der ER arbejde i gang, og hovedet skal kunne se det.
    expect(efter.arbejdeEfterSvar).toBe(true)
  })

  it('markerer det også når det nye run annonceres via message_start', () => {
    const efter = streamReducer(laastTur(), {
      type: 'message_start',
      message: { id: 'run-2', model: 'm', provider: 'p', lane: 'l', usage: { input_tokens: 0 } },
    } as never)

    // Svaret bliver stående — låsen og blokkene røres ikke.
    expect(efter.svarLaast).toBe(true)
    expect(efter.blocks).toHaveLength(1)
    expect(efter.arbejdeEfterSvar).toBe(true)
  })

  it('beholder flaget når rundens tekst strømmer ind bagefter', () => {
    // Den rigtige rækkefølge: run-eventet åbner runden, deltaerne følger.
    // (`provisional_text_delta` afviser bevidst et delta fra et FREMMEDE run
    // mens status er `working` — se vagten i reduceren.)
    const runde = streamReducer(laastTur(), {
      type: 'system_event', kind: 'run', payload: { run_id: 'run-2' },
    } as never)
    const medTekst = streamReducer(runde, {
      type: 'system_event',
      kind: 'provisional_text_delta',
      payload: { run_id: 'run-2', delta: 'Ny tekst i runden.' },
    } as never)

    expect(medTekst.svarLaast).toBe(true)
    expect(medTekst.arbejdeEfterSvar).toBe(true)
    expect(medTekst.provisionalText).toContain('Ny tekst')
  })

  it('holder svaret låst men lader flaget falde når streamen slutter', () => {
    const koerende = streamReducer(laastTur(), {
      type: 'system_event', kind: 'run', payload: { run_id: 'run-2' },
    } as never)
    const slut = streamReducer(koerende, { type: 'message_stop' } as never)

    expect(slut.status).toBe('done')
    expect(slut.svarLaast).toBe(true)
    expect(slut.arbejdeEfterSvar).toBe(false)
  })

  it('rydder flaget ved en helt ny tur — låsen ryddes også', () => {
    const koerende = streamReducer(laastTur(), {
      type: 'system_event', kind: 'run', payload: { run_id: 'run-2' },
    } as never)
    const nyTur = streamReducer(koerende, {
      type: 'system_event', kind: 'client_turn_start', payload: {},
    } as never)

    expect(nyTur.svarLaast).toBe(false)
    expect(nyTur.arbejdeEfterSvar).toBe(false)
  })

  it('et run UDEN låst svar er ikke «arbejde efter svaret»', () => {
    const frisk: StreamState = { ...initialStreamState(), status: 'working', activeRunId: 'run-1' }
    const naeste = streamReducer(frisk, {
      type: 'system_event', kind: 'run', payload: { run_id: 'run-2' },
    } as never)

    expect(naeste.arbejdeEfterSvar).toBe(false)
  })
})
