import { render } from '@testing-library/react-native'
import { MessageList } from './MessageList'
import type { ChatMessage } from '../lib/types'

const msg = (over: Partial<ChatMessage>): ChatMessage => ({
  id: 'm1',
  role: 'user',
  content: 'hej',
  created_at: '2026-09-12T12:00:00Z',
  ...over
})

/**
 * Målt 12/9-2026: markøren faldt i default-grenen og blev tegnet som en
 * almindelig boble med HELE den serialiserede transcript som indhold (111k
 * tegn: `[Bjørn] …`, `[tool:tool] …`, «Use read_tool_result with result_id=…»).
 * Bjørn fandt den på sin telefon. Serveren trimmer nu indholdet; grenen her
 * sørger for at det også ser ud som det det er: intern bogholderi, ikke en
 * samtale-besked.
 */
it('kompakterings-markøren tegnes som én diskret linje — ikke en boble', async () => {
  const s = await render(
    <MessageList
      messages={[
        msg({ id: 'u1', role: 'user', content: 'hej' }),
        msg({
          id: 'c1',
          role: 'compact_marker',
          content: 'Samtalen blev komprimeret — 111.507 tegn arkiveret'
        })
      ]}
      blocks={[]}
    />
  )

  expect(s.getByTestId('compact-marker')).toBeTruthy()
  expect(
    s.getByText('Samtalen blev komprimeret — 111.507 tegn arkiveret')
  ).toBeTruthy()
})

it('markøren får ingen handlingsrække — den er ikke et svar', async () => {
  // Uden grenen ville rollen lande i MessageBubble, og et «svar» får
  // kopiér/oplæs. En intern markør skal ikke kunne kopieres som om den var
  // Jarvis' ord.
  const s = await render(
    <MessageList
      messages={[
        msg({
          id: 'c1',
          role: 'compact_marker',
          content: 'Samtalen blev komprimeret — 111.507 tegn arkiveret'
        })
      ]}
      blocks={[]}
    />
  )

  expect(s.queryByLabelText('Kopiér')).toBeNull()
})
