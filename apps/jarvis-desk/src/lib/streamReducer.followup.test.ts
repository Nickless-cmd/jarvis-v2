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

  it('en SELVSTÆNDIG tur (wakeup) starter en ny besked — ikke en runde', () => {
    // Målt 11/11-2026: en wakeup lander i SAMME session som turen der lige
    // sluttede, med et nyt run-id. Uden `origin` i framen gættede reduceren
    // «runde», og wakeup'ens tekst blev hængende i den FORRIGE turs besked
    // indtil appen blev genstartet. Serveren kender svaret — den sender det nu.
    const foer = laastSvar()
    const efter = streamReducer(foer, system('run', { run_id: 'r2', origin: 'wakeup' }))
    expect(efter.svarLaast).toBe(false)
    expect(efter.blocks).toEqual([])
    expect(efter.activeRunId).toBe('r2')
    expect(efter.status).toBe('working')
  })

  it('en runde i MIN tur bærer ingen origin og bevarer svaret', () => {
    // Modprøven: uden origin er det brugerens egen tur, og låsen skal holde.
    const foer = laastSvar()
    const efter = streamReducer(foer, system('run', { run_id: 'r2', origin: '' }))
    expect(efter.svarLaast).toBe(true)
    expect(efter.blocks.length).toBe(foer.blocks.length)
  })

  it('en SELVSTÆNDIG tur rydder låsen — også når message_start kom FØRST', () => {
    // Den FAKTISKE rækkefølge i drift. Målt 11/11-2026 i sse_v2's
    // fallback-gren: `_emit_message_start_if_needed()` kaldes FØR `run`-
    // hændelsen pakkes, så klienten ser message_start først og `activeRunId`
    // er allerede skiftet når origin ankommer.
    //
    // Testen ovenfor fodrede `run` direkte efter låsen og ramte derfor en
    // rækkefølge der ikke findes. Den var grøn mens wakeup'ens arbejdslinje
    // blev flettet ind i den forrige besked — en test der ikke kunne nå den
    // gren den påstod at dække.
    const foer = laastSvar()
    const medNytRun = streamReducer(foer, msgStart('r2'))
    expect(medNytRun.activeRunId).toBe('r2')
    // message_start alene er stadig en RUNDE — den bærer ingen origin.
    expect(medNytRun.svarLaast).toBe(true)
    const efter = streamReducer(medNytRun, system('run', { run_id: 'r2', origin: 'wakeup' }))
    expect(efter.svarLaast).toBe(false)
    expect(efter.blocks).toEqual([])
    expect(efter.activeRunId).toBe('r2')
    expect(efter.selvstaendigRunId).toBe('r2')
  })

  it('en gentaget run-frame for SAMME selvstændige tur rydder ikke igen', () => {
    // Reconnect/replay må ikke nulstille en tur der allerede er begyndt.
    const foer = laastSvar()
    const medNytRun = streamReducer(foer, msgStart('r2'))
    const a = streamReducer(medNytRun, system('run', { run_id: 'r2', origin: 'wakeup' }))
    const b = streamReducer(a, system('run', { run_id: 'r2', origin: 'wakeup' }))
    expect(b.selvstaendigRunId).toBe('r2')
    expect(b.turStart).toBe(a.turStart)
    expect(b.blocks).toEqual([])
  })

  /**
   * DEN FAKTISKE RÆKKEFØLGE (11/11-2026).
   *
   * Målt på Bjørns skærm: wakeup'ens arbejdslinje stod nederst i den FORRIGE
   * besked indtil turen sluttede. Koden havde origin-feltet og grenen — men
   * `message_start` kommer FØR `run`-framen (sse_v2's fallback-gren emitter
   * den først), så `activeRunId` var allerede skiftet da origin ankom, og
   * `message_start` havde på det tidspunkt arvet den forrige turs blokke
   * fordi `svarLaast` var sand. Testen her følger den rækkefølgen.
   */
  it('message_start for en selvstændig tur arver IKKE den forrige turs blokke', () => {
    // RÆKKEFØLGEN I DRIFT: message_start kommer FØR run-framen. Her er
    // svarLaast stadig sand fra den forrige tur, og activeRunId skifter til
    // det nye id — så uden markøren arver den forrige turs blokke.
    const foer = laastSvar()
    const efter = streamReducer(foer, msgStart('w2'))
    // message_start alene kan ikke vide at w2 er selvstændig — den bærer
    // ingen origin. Derfor må den HELLER IKKE rydde: låsen skal holde indtil
    // run-framen bekræfter. Det er den kontrakt der gør fixet sikkert.
    expect(efter.svarLaast).toBe(true)
    expect(efter.blocks.length).toBe(foer.blocks.length)
    // Og når run-framen så lander, ryddes alt — inkl. det message_start arvede.
    const r = streamReducer(efter, system('run', { run_id: 'w2', origin: 'wakeup' }))
    expect(r.blocks).toEqual([])
    expect(r.svarLaast).toBe(false)
    expect(r.selvstaendigRunId).toBe('w2')
  })

  it('delta fra en selvstændig tur lægges IKKE oveni den forrige turs svar', () => {
    const foer = laastSvar()
    const r1 = streamReducer(foer, system('run', { run_id: 'w3', origin: 'wakeup' }))
    const efter = streamReducer(r1, system('provisional_text_delta', {
      run_id: 'w3', delta: 'Læser det autonome runs indhold',
    }))
    expect(efter.provisionalText).toBe('Læser det autonome runs indhold')
    expect(efter.blocks).toEqual([])
    expect(efter.arbejdeEfterSvar).toBe(false)
  })
})
