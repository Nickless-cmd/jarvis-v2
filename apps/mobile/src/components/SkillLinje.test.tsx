import { act, fireEvent, render } from '@testing-library/react-native'
import { MessageList } from './MessageList'
import { streamReducer, initialStreamState } from '../lib/streamReducer'
import type { StreamEvent } from '../lib/sseProtocol'
import type { ChatMessage } from '../lib/types'

/**
 * Bjørn 19/9-2026: «ja port skill linje». Skill-kald stod på telefonen som
 * runde-linjer («Brugte skill_gate»); nu har de deres egen linje som på desk.
 * Formerne er målt på CT105: kaldet uden resultat, resultatet i en
 * `tool_result`-blok, og `skill_surface` som egen blok.
 */
const gemt = (content_json: unknown[]) => ({
  id: 'a1', role: 'assistant', content: 'Svar.', created_at: '2026-09-19T00:00:00Z', content_json,
}) as unknown as ChatMessage

it('et gemt skill_gate-kald får sin egen linje med score og indlæsning', async () => {
  const s = await render(<MessageList messages={[gemt([
    { type: 'tool_use', id: 'c1', name: 'skill_gate', input: { query: 'regneark' } },
    { type: 'tool_result', tool_use_id: 'c1', status: 'done', content: JSON.stringify({
      gate_result: 'invoked', skill_name: 'xlsx', score: 0.82, mode: 'auto_use', instructions_full_length: 4213,
      all_matches: [{ name: 'xlsx', score: 0.82 }, { name: 'csv', score: 0.4 }] }) },
    { type: 'text', text: 'Svar.' },
  ])]} blocks={[]} />)
  expect(s.getByText('Skill-gate: xlsx')).toBeTruthy()
  expect(s.getByText(' · 0,82 · indlæst · 4,2k tegn')).toBeTruthy()
  // Ikke også som en runde-linje.
  expect(s.queryByText(/skill_gate/)).toBeNull()
  // Matches bag caret'en.
  expect(s.queryByText('csv')).toBeNull()
  await act(async () => { fireEvent.press(s.getByTestId('skill-linje')) })
  expect(s.getByText('csv')).toBeTruthy()
})

it('en gemt skill_surface-blok bliver til en skill-linje', async () => {
  const s = await render(<MessageList messages={[gemt([
    { type: 'skill_surface', matches: [{ name: 'code-review', score: 0.753, primary: false }], primary: false },
    { type: 'text', text: 'Svar.' },
  ])]} blocks={[]} />)
  expect(s.getByText('Skills foreslået: code-review')).toBeTruthy()
  expect(s.getByText(' · bedst 0,75')).toBeTruthy()
})

it('et skill-kald der kører: nutid, prikker, egen linje', async () => {
  const s = await render(<MessageList messages={[]} blocks={[
    { type: 'tool_use', id: 'c1', name: 'skill_gate', input: { query: 'lav et regneark' }, status: 'running' },
  ]} />)
  expect(s.getByText('Tjekker skills for «lav et regneark»')).toBeTruthy()
  expect(s.getByTestId('prikker', { includeHiddenElements: true })).toBeTruthy()
})

it('strømmens skill_surface — også indpakket som system_event — står øverst i turen', async () => {
  const E = (e: unknown) => e as StreamEvent
  let st = initialStreamState()
  st = streamReducer(st, E({ type: 'message_start', message: { id: 'run1', usage: { input_tokens: 0 } } }))
  st = streamReducer(st, E({ type: 'system_event', kind: 'skill_surface', payload: { matches: [{ name: 'xlsx', score: 0.81, primary: true }], primary: true } }))
  st = streamReducer(st, E({ type: 'content_block_start', index: 0, content_block: { type: 'text', text: '' } }))
  st = streamReducer(st, E({ type: 'content_block_delta', index: 0, delta: { type: 'text_delta', text: 'Hej' } }))
  expect(st.skillFlade?.matches[0]?.name).toBe('xlsx')
  const s = await render(<MessageList messages={[]} blocks={st.blocks} skillFlade={st.skillFlade} />)
  expect(s.getByText('Skill-match: xlsx')).toBeTruthy()
  // En NY kørsel nulstiller den.
  st = streamReducer(st, E({ type: 'message_start', message: { id: 'run2', usage: { input_tokens: 0 } } }))
  expect(st.skillFlade).toBeUndefined()
})
