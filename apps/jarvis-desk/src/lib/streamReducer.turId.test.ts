/**
 * TURENS IDENTITET ER IKKE ET TIDSTEMPEL.
 *
 * Bjørn 26/11-2026: «det vigtigste er ikke at få foldet til at fungere. det
 * vigtigste er at gøre foldet irrelevant for pacens funktion.»
 *
 * ## Hvad der var galt
 *
 * Pacing-nøglen var `tur-${turStart}`. `turStart` er TID, og fem steder i
 * reduceren skrev den `Date.now()` — to af dem (`follow_start`,
 * `client_turn_start`) ubetinget. Hver gang nøglen skiftede, faldt
 * `useChatPacedBlocks`' cursor til `''` og svaret blev pacet FORFRA midt i
 * turen. Det er den fejl Bjørn beskrev som «tom skærm, og så starter slut
 * besked med at pace uden for hoved».
 *
 * ## Hvad testen værner
 *
 * `turId` sættes ÉN gang pr. tur og bevares af hver frame der hører til samme
 * tur. Kun en ægte ny tur giver et nyt id. Det er forudsætningen for at folden
 * kan være et rent præsentationslag: så længe identiteten står stille, kan
 * hverken fold, runde eller reconnect røre pacen.
 */
import { describe, expect, it } from 'vitest'
import { initialStreamState, nytTurId, streamReducer, type StreamState } from './streamReducer'
import type { StreamEvent } from './sseProtocol'

const msgStart = (runId: string): StreamEvent => ({
  type: 'message_start',
  message: { id: runId, model: 'test', usage: { input_tokens: 1, output_tokens: 0 } },
} as StreamEvent)

const system = (kind: string, payload: Record<string, unknown> = {}): StreamEvent =>
  ({ type: 'system_event', kind, payload } as StreamEvent)

/** En tur hvor slutsvaret er begyndt — altså en tur der ER i gang. */
function igangvaerendeTur(): StreamState {
  let s = streamReducer(initialStreamState(), system('client_turn_start'))
  s = streamReducer(s, msgStart('r1'))
  s = streamReducer(s, {
    type: 'content_block_start', index: 0,
    content_block: { type: 'text', text: '', phase: 'final_answer' },
  } as StreamEvent)
  return streamReducer(s, {
    type: 'content_block_delta', index: 0,
    delta: { type: 'text_delta', text: 'Svaret' },
  } as StreamEvent)
}

describe('turId er turens identitet, ikke dens ur', () => {
  it('sættes ved client_turn_start', () => {
    const s = streamReducer(initialStreamState(), system('client_turn_start'))
    expect(s.turId).toBeTruthy()
    expect(s.turId).toMatch(/^tur-/)
  })

  it('DEN FØRSTE message_start efter client_turn_start må ikke skifte id’et', () => {
    // MÅLT HUL 26/11-2026: `client_turn_start` sætter et id, men intet run er
    // bundet (`activeRunId === null`). Turens FØRSTE `message_start` bærer et
    // run-id klienten ikke kender → `_sameRun` falsk → `_bevar` falsk → NYT
    // id, præcis i det øjeblik pacen begynder. De øvrige tests her starter fra
    // en tur der allerede ER i gang og kunne derfor ikke se hullet.
    const aabnet = streamReducer(initialStreamState(), system('client_turn_start'))
    expect(aabnet.activeRunId).toBeNull()
    const foerste = streamReducer(aabnet, msgStart('r1'))
    expect(foerste.turId).toBe(aabnet.turId)
    expect(foerste.turStart).toBe(aabnet.turStart)
    // Uden låst svar er der intet at komme EFTER — hovedet må ikke folde ud.
    expect(foerste.arbejdeEfterSvar).toBe(false)
  })

  it('MODPRØVE: en fremmed tur med origin skifter id’et, også når klienten har åbnet en tur', () => {
    const aabnet = streamReducer(initialStreamState(), system('client_turn_start'))
    const efter = streamReducer(aabnet, {
      type: 'message_start',
      message: { id: 'x1', model: 'test', origin: 'wakeup', usage: { input_tokens: 1, output_tokens: 0 } },
    } as StreamEvent)
    expect(efter.turId).toBeTruthy()
    expect(efter.turId).not.toBe(aabnet.turId)
  })

  it('overlever message_start med NYT run-id — det er en runde, ikke en ny tur', () => {
    const foer = igangvaerendeTur()
    const efter = streamReducer(foer, msgStart('r2'))
    expect(efter.turId).toBe(foer.turId)
    // Blokke og lås bevares også — det er den samme tur.
    expect(efter.blocks.length).toBe(foer.blocks.length)
    expect(efter.svarLaast).toBe(true)
  })

  it('overlever run-framen med NYT run-id', () => {
    const foer = igangvaerendeTur()
    const efter = streamReducer(foer, system('run', { run_id: 'r2' }))
    expect(efter.turId).toBe(foer.turId)
    expect(efter.activeRunId).toBe('r2')
  })

  it('overlever en reconnect af SAMME run', () => {
    const foer = igangvaerendeTur()
    const efter = streamReducer(foer, msgStart('r1'))
    expect(efter.turId).toBe(foer.turId)
  })

  it('MODPRØVE: en ægte ny tur giver et NYT id', () => {
    const foer = igangvaerendeTur()
    const efter = streamReducer(foer, system('client_turn_start'))
    expect(efter.turId).toBeTruthy()
    expect(efter.turId).not.toBe(foer.turId)
  })

  // ── ÅBEN BEGRÆNSNING, MÅLT 26/11-2026 ───────────────────────────────────
  //
  // `follow_start` er KLIENT-lokal: den dispatches fra `CodeView.tsx` når et
  // baggrunds-run skal følges — serveren sender den aldrig (grep i apps/ og
  // core/ giver nul Python-kilder). At «nyt run-id = ny tur» er derfor vores
  // EGEN heuristik, ikke en server-kontrakt.
  //
  // Den er rigtig i cross-device-tilfældet (16/11-2026: en passiv klient
  // blandede en ny tur med den forrige besked), men den er ikke bevist rigtig
  // når det nye run er en FORTSÆTTELSE af den tur klienten allerede viser.
  // Forskellen kan ikke afgøres af run-id alene — den kræver at `follow_start`
  // bærer turens identitet, og det gør payloaden ikke i dag.
  //
  // Testen nedenfor fastholder den nuværende adfærd. Bliver `follow_start`
  // udvidet med et tur-id, skal den her test ændres til at bevare `turId` når
  // id'et matcher — ikke slettes.
  it('MODPRØVE: follow_start med et andet run-id er en ny tur', () => {
    const foer = igangvaerendeTur()
    const efter = streamReducer(foer, system('follow_start', { run_id: 'r9' }))
    expect(efter.turId).toBeTruthy()
    expect(efter.turId).not.toBe(foer.turId)
  })

  it('follow_start med SAMME run-id er en no-op — id’et må ikke skifte', () => {
    const foer = igangvaerendeTur()
    const efter = streamReducer(foer, system('follow_start', { run_id: 'r1' }))
    expect(efter.turId).toBe(foer.turId)
  })

  it('en selvstændig tur (origin) får sit eget id', () => {
    const foer = igangvaerendeTur()
    const efter = streamReducer(foer, system('run', { run_id: 'w1', origin: 'wakeup' }))
    expect(efter.turId).toBeTruthy()
    expect(efter.turId).not.toBe(foer.turId)
  })

  it('to ture i samme millisekund deler ikke identitet', () => {
    // `turStart` kan være identisk for to hurtige ture; `turId` må ikke.
    const a = nytTurId()
    const b = nytTurId()
    expect(a).not.toBe(b)
  })

  it('initialStreamState har intet id — en tur der ikke er startet har ingen identitet', () => {
    expect(initialStreamState().turId).toBeNull()
  })
})
