import { render, within } from '@testing-library/react-native'
import { MessageList } from './MessageList'
import type { ChatMessage } from '../lib/types'
import type { ContentBlock } from '../lib/sseProtocol'

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

/**
 * Målt 12/9-2026: buildStreamingRows smeltede thinking-blokke sammen med
 * text-blokke i én boble (`textBuf += b.thinking`). Bjørn så rå CoT flyde
 * ind i svaret mens det streames. Nu skal thinking få sin egen række —
 * samme mønster som InlineToolGroup: én foldbar linje over svaret.
 */
it('thinking-blokke i stream får egen række — ikke smeltet ind i svaret', async () => {
  const blocks: ContentBlock[] = [
    { type: 'thinking', thinking: 'jeg overvejer om 2+2 er 4' },
    { type: 'text', text: 'Svaret er 4' }
  ]

  const s = await render(
    <MessageList
      messages={[msg({ id: 'u1', role: 'user', content: 'hvad er 2+2?' })]}
      blocks={blocks}
      thinking
    />
  )

  // Thinking skal være en egen linje med testID
  expect(s.getByTestId('thinking-summary')).toBeTruthy()
  // Og teksten skal være en separat boble
  expect(s.getByText('Svaret er 4')).toBeTruthy()

  // TANKESTROEMMEN STAAR OVER KOMPONISTEN, ikke i traaden. Traadens linje
  // beholder sin rolige form (ikon + «Tænker» + prikker), saa man kan laese
  // med mens han taenker; raa monolog der flimrer i traaden goer den
  // ulaeselig. Bjoern 12/9-2026.
  expect(within(s.getByTestId('thinking-label')).getByText('jeg overvejer om 2+2 er 4'))
    .toBeTruthy()
  expect(within(s.getByTestId('thinking-summary')).queryByText('jeg overvejer om 2+2 er 4'))
    .toBeNull()
})

/**
 * Bjørn 12/9-2026: «det er kun den første tænkte der bliver i chatview, dem der
 * er under forsvinder efter streamen».
 *
 * Netop EFTER streamen: den levende visning bygger rækkerne af blokkene i
 * rækkefølge og har derfor altid vist dem alle. Den gemte visning hentede
 * tænkningen med `thinkingBlock` — som er `.find()` — og filtrerede resten væk
 * i `threadBlocks`. De to visninger var uenige om den samme tur.
 */
it('en gemt tur med flere tanker beholder dem alle, på deres plads', async () => {
  const s = await render(
    <MessageList
      messages={[
        msg({ id: 'u1', role: 'user', content: 'kør noget' }),
        msg({
          id: 'a1',
          role: 'assistant',
          content: 'færdig',
          content_json: [
            { type: 'thinking', text: 'først overvejer jeg planen', seconds: 3 },
            { type: 'tool_use', name: 'bash', input: { command: 'ls' }, tool_use_id: 't1' },
            { type: 'tool_result', tool_use_id: 't1', content: 'fil.txt', status: 'ok' },
            { type: 'thinking', text: 'så ser jeg på resultatet', seconds: 9 },
            { type: 'text', text: 'færdig' }
          ]
        } as Partial<ChatMessage>)
      ]}
      blocks={[]}
    />
  )
  const taenkte = s.queryAllByText(/Tænkte/)
  expect(taenkte.length).toBe(2)
  // Og de baerer hver sin maalte tid — ikke den foerstes for dem begge.
  expect(s.queryAllByText(/Tænkte i 3 s/).length).toBe(1)
  expect(s.queryAllByText(/Tænkte i 9 s/).length).toBe(1)
})
