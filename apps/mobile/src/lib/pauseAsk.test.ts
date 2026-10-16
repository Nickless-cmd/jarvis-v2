import { activePauseAsk, withoutPauseAsk } from './pauseAsk'
import type { ChatMessage } from './types'
import type { ContentBlock } from './sseProtocol'

const result = JSON.stringify({ kind: 'pause_and_ask', question: 'Hvilke flader?', options: ['Desk', 'Mobil'], allow_multiple: true })
const assistant: ChatMessage = {
  id: 'a1', role: 'assistant', content: '', created_at: '2026-10-09T00:00:00Z',
  content_json: [{ type: 'tool_use', name: 'pause_and_ask', result }],
}

test('viser seneste ubesvarede spørgsmål fra en gemt samtale', () => {
  expect(activePauseAsk([assistant], [])).toEqual({
    question: 'Hvilke flader?', options: ['Desk', 'Mobil'], allowMultiple: true,
    context: '', urgency: 'normal',
  })
})

test('bevarer spørgsmålet når den PERSISTEREDE tur overtager efter streamen', () => {
  // Målt 15/10-2026: i mobilen forsvandt kortet i det øjeblik streamen sluttede.
  // Årsagen er form-forskellen mellem de to visninger af samme tur: live folder
  // reduceren `tool_result` ind på sin tool_use (så `result` findes), men den
  // gemte `content_json` bærer dem som TO blokke — og der står INTET `result` på
  // tool_use-blokken. Verificeret mod DB'en: alle tool_use-blokke i en persisteret
  // tur har har-result-felt=False, og svaret ligger som streng i tool_result.
  const gemt: ChatMessage = {
    id: 'a2', role: 'assistant', content: 'Spørgsmålet står i dit felt.',
    created_at: '2026-10-15T20:40:00Z',
    content_json: [
      { type: 'text', text: 'Spørgsmålet står i dit felt.' },
      { type: 'tool_use', id: 'ask-9', name: 'pause_and_ask', input: {} },
      { type: 'tool_result', tool_use_id: 'ask-9', content: result },
    ],
  }
  expect(activePauseAsk([gemt], [])?.question).toBe('Hvilke flader?')
})

test('finder spørgsmålet når kaldet gik gennem TRANSPORTEN call_loaded_tool', () => {
  // Målt 16/10-2026 — den ÆGTE form i `content_json`, læst ud af DB'en på en
  // rigtig pause_and_ask-tur. Værktøjet var ikke loadet i runden, så kaldet gik
  // gennem transporten, og navnet står i `input.navn` — ikke på `block.name`.
  //
  // Det første fix (15/10) løste `result`-forskellen men ledte stadig efter
  // `pause_and_ask` på `block.name`, så det sprang blokken over. Kortet døde
  // derfor igen ved stream-slut, og testen ovenfor fangede det ikke: den byggede
  // på en form (`name: 'pause_and_ask'` på den gemte tur) der ikke findes i
  // produktionen. En test der bruger en form virkeligheden ikke har, beviser
  // kun at koden matcher testen.
  const gemt: ChatMessage = {
    id: 'a3', role: 'assistant', content: '',
    created_at: '2026-10-16T04:20:00Z',
    content_json: [
      { type: 'text', text: 'Jeg stiller dig et rigtigt spørgsmål.' },
      {
        type: 'tool_use', id: 'call_00_AFdy97tiCFxAHCGIlupM9414',
        name: 'call_loaded_tool',
        input: { navn: 'pause_and_ask', argumenter: { kind: 'pause_and_ask', question: 'Hvilke flader?' } },
      },
      {
        type: 'tool_result', tool_use_id: 'call_00_AFdy97tiCFxAHCGIlupM9414',
        status: 'done', content: result,
      },
    ],
  }
  expect(activePauseAsk([gemt], [])?.question).toBe('Hvilke flader?')
})

test('skjuler også transport-formen af spørgsmålet fra tråden', () => {
  const blocks = [
    { type: 'text', text: 'Venter på dit svar.' },
    { type: 'tool_use', id: 'ask-t', name: 'call_loaded_tool', input: { navn: 'pause_and_ask' } },
    { type: 'tool_result', tool_use_id: 'ask-t', content: result },
    { type: 'tool_use', id: 'read-1', name: 'read_file' },
    { type: 'tool_result', tool_use_id: 'read-1', content: 'ok' },
  ]
  expect(withoutPauseAsk(blocks)).toEqual([blocks[0], blocks[3], blocks[4]])
})

test('skjuler det besvarede spørgsmål efter en brugerbesked', () => {
  const user: ChatMessage = { id: 'u2', role: 'user', content: 'Desk', created_at: '2026-10-09T00:01:00Z' }
  expect(activePauseAsk([assistant, user], [])).toBeNull()
})

test('viser nyt live-spørgsmål efter det første svar', () => {
  const user: ChatMessage = { id: 'u2', role: 'user', content: 'Desk', created_at: '2026-10-09T00:01:00Z' }
  const live = [{ type: 'tool_use' as const, id: 't2', name: 'pause_and_ask', input: {}, result: JSON.stringify({ kind: 'pause_and_ask', question: 'Vis resultat?', options: ['Ja', 'Nej'] }) }]
  expect(activePauseAsk([assistant, user], live)?.question).toBe('Vis resultat?')
})

test('viser live-spørgsmålet selv om streamen har et tomt blokindeks', () => {
  const live: ContentBlock[] = []
  live[0] = { type: 'text', text: 'Et værktøj er færdigt.' }
  live[2] = {
    type: 'tool_use', id: 'ask-2', name: 'pause_and_ask', input: {}, result,
  }
  expect(activePauseAsk([], live)?.question).toBe('Hvilke flader?')
})

test('fjerner spørgsmål og tilhørende tool-resultat fra samtalen', () => {
  const blocks = [
    { type: 'text', text: 'Jeg har brug for dit valg.' },
    { type: 'tool_use', name: 'pause_and_ask', id: 'ask-1', result },
    { type: 'tool_result', tool_use_id: 'ask-1', content: result },
    { type: 'tool_use', name: 'read_file', id: 'read-1' },
    { type: 'tool_result', tool_use_id: 'read-1', content: 'ok' },
  ]
  expect(withoutPauseAsk(blocks)).toEqual([blocks[0], blocks[3], blocks[4]])
})

test('viser øvrige live-blokke når listen har et tomt indeks og et spørgsmål', () => {
  // visibleStreamBlocks spreder et sparsomt array, når foreløbig tekst tilføjes.
  // Hullet bliver da et eksplicit undefined-element.
  const live = [
    { type: 'text', text: 'Venter på dit svar.' },
    undefined,
    { type: 'tool_use', id: 'ask-2', name: 'pause_and_ask', input: {}, result },
  ] as ContentBlock[]
  expect(withoutPauseAsk(live)).toEqual([{ type: 'text', text: 'Venter på dit svar.' }])
})

test('viser øvrige live-blokke når listen har et tomt indeks uden spørgsmål', () => {
  const live: ContentBlock[] = []
  live[0] = { type: 'text', text: 'Før' }
  live[2] = { type: 'text', text: 'Efter' }
  expect(withoutPauseAsk(live)).toEqual([
    { type: 'text', text: 'Før' },
    { type: 'text', text: 'Efter' },
  ])
})
