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
