import { act, fireEvent, render } from '@testing-library/react-native'
import { MessageList } from './MessageList'
import type { ChatMessage } from '../lib/types'

/**
 * Bjørn 19/9-2026: «+xx og -xx mangler os i mobile». Hele vejen fra en GEMT
 * besked til linjen, med kaldene formet som de ligger i `content_json` på
 * CT105 (målt i hans tråd): input som objekt, intet resultat, og broens
 * `operator_edit_file` med old_string/new_string.
 */
it('en genindlæst runde viser sine +/− — også for broens redigeringer', async () => {
  const msg = {
    id: 'a1', role: 'assistant', content: 'Rettet.',
    created_at: '2026-09-18T21:43:17Z',
    content_json: [
      { type: 'tool_use', id: 't1', name: 'edit_file', input: { path: '/a.py', old_text: 'a\nb', new_text: 'a\nB\nc' } },
      { type: 'tool_use', id: 't2', name: 'operator_edit_file', input: { path: '/b.py', old_string: 'x', new_string: 'x\ny' } },
      { type: 'text', text: 'Rettet.' },
    ],
  } as unknown as ChatMessage
  const v = await render(<MessageList messages={[msg]} blocks={[]} />)
  await act(async () => { fireEvent.press(v.getByTestId('turn-header')) })
  expect(v.getByText('+5')).toBeTruthy()
  expect(v.getByText('−3')).toBeTruthy()
})
