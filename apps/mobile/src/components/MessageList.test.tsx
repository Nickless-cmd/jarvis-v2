import { act, fireEvent, render, within } from '@testing-library/react-native'
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

it('viser turn header fra turen starter, før første blok kommer', async () => {
  const s = await render(<MessageList messages={[]} blocks={[]} working />)
  expect(s.getByTestId('turn-header')).toBeTruthy()
  expect(s.getByText('Working…')).toBeTruthy()
})

it('en ny tur starter åben, selv hvis forrige live tur blev lukket', async () => {
  const blocks: ContentBlock[] = [{ type: 'thinking', thinking: 'Undersøger.' }]
  const s = await render(<MessageList messages={[]} blocks={blocks} working />)
  expect(s.getByTestId('thinking-summary')).toBeTruthy()
  await act(async () => { fireEvent.press(s.getByTestId('turn-header')) })
  expect(s.queryByTestId('thinking-summary')).toBeNull()
  await act(async () => { s.rerender(<MessageList messages={[]} blocks={[]} working={false} />) })
  await act(async () => { s.rerender(<MessageList messages={[]} blocks={blocks} working />) })
  expect(s.getByTestId('thinking-summary')).toBeTruthy()
})

it('samler gemt arbejde bag én turn header og lader slutsvaret stå synligt', async () => {
  const s = await render(<MessageList messages={[msg({
    id: 'a1', role: 'assistant', content: 'Det er løst.',
    content_json: [
      { type: 'text', text: 'Jeg undersøger filen.' },
      { type: 'tool_use', id: 't1', name: 'read_file', input: { path: 'app.py' } },
      { type: 'text', text: 'Det er løst.' },
    ],
  })]} blocks={[]} />)
  expect(s.getByTestId('turn-header')).toBeTruthy()
  expect(s.getByText('Det er løst.')).toBeTruthy()
  expect(s.queryByText('Jeg undersøger filen.')).toBeNull()
  expect(s.queryByTestId('tool-group')).toBeNull()
  await fireEvent.press(s.getByTestId('turn-header'))
  expect(s.getByText('Jeg undersøger filen.')).toBeTruthy()
  expect(s.getByTestId('tool-group')).toBeTruthy()
})

it('åbner live arbejde ned under turn headeren og lader svaret stå synligt', async () => {
  const blocks: ContentBlock[] = [
    { type: 'thinking', thinking: 'Jeg lægger en plan.' },
    { type: 'text', text: 'Jeg finder filen.' },
    { type: 'tool_use', id: 't1', name: 'read_file', input: { path: 'app.py' }, status: 'done' },
    { type: 'text', text: 'Her er svaret.' },
  ]
  const s = await render(<MessageList messages={[]} blocks={blocks} working />)
  expect(s.getByTestId('turn-header').props.accessibilityState.expanded).toBe(true)
  expect(s.getByText('Her er svaret.')).toBeTruthy()
  expect(s.getByText('Jeg finder filen.')).toBeTruthy()
  expect(s.getByTestId('thinking-summary')).toBeTruthy()
  await act(async () => { fireEvent.press(s.getByTestId('turn-header')) })
  expect(s.queryByTestId('thinking-summary')).toBeNull()
  expect(s.getByText('Her er svaret.')).toBeTruthy()
})

it('folder arbejdet sammen ved skiftet fra stream til gemt slutsvar', async () => {
  const blocks: ContentBlock[] = [
    { type: 'thinking', thinking: 'Finder årsagen.' },
    { type: 'text', text: 'Rettet.' },
  ]
  const s = await render(<MessageList messages={[]} blocks={blocks} working />)
  expect(s.getByTestId('turn-header').props.accessibilityState.expanded).toBe(true)
  expect(s.getByTestId('thinking-summary')).toBeTruthy()

  const saved = msg({
    id: 'a1', role: 'assistant', content: 'Rettet.',
    content_json: [
      { type: 'thinking', text: 'Finder årsagen.', seconds: 2 },
      { type: 'text', text: 'Rettet.' },
    ],
  })
  await act(async () => { s.rerender(<MessageList messages={[saved]} blocks={[]} working={false} />) })
  expect(s.getByTestId('turn-header').props.accessibilityState.expanded).toBe(false)
  expect(s.queryByTestId('thinking-summary')).toBeNull()
  expect(s.getByText('Rettet.')).toBeTruthy()
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
    />
  )

  // Thinking ligger under den åbne turn header, ikke inde i selve svaret.
  expect(s.getByTestId('turn-header')).toBeTruthy()
  expect(s.getByTestId('thinking-summary')).toBeTruthy()
  // Og teksten skal være en separat boble
  expect(s.getByText('Svaret er 4')).toBeTruthy()

  // LINJEN OVER KOMPONISTEN FINDES IKKE LAENGERE (Bjørn 21/9-2026). Den bar
  // taenke-fragmenterne nederst i traaden, og desk har ingen saadan linje.
  expect(s.queryByTestId('thinking-label')).toBeNull()
})

/**
 * Bjørn 21/9-2026: «vi har en linje over composer der viser tænke fragmenter og
 * forsvinder igen efter streamen.. tænke fragmenter bør vises I tænke linjen i
 * chatview og linjen over composer væk».
 *
 * Fragmentet står nu PÅ tænke-linjen selv — samme sted som desk viser det
 * («Tænker · 4 s · Lad mig se hvor værnet sidder…»). Mobilen har intet løbende
 * ur, så kun fragmentet følger med ordet.
 */
it('tænke-fragmentet står på trådens linje mens den tænker', async () => {
  const s = await render(
    <MessageList
      messages={[msg({ id: 'u1', role: 'user', content: 'hvad er 2+2?' })]}
      // Tanken er den SIDSTE blok → rækken er live og bærer fragmentet.
      blocks={[{ type: 'thinking', thinking: 'jeg overvejer om 2+2 er 4' }]}
    />
  )
  expect(
    within(s.getByTestId('thinking-summary')).getByText(/jeg overvejer om 2\+2 er 4/)
  ).toBeTruthy()
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
  await fireEvent.press(s.getByTestId('turn-header'))
  const taenkte = s.queryAllByText(/Tænkte/)
  expect(taenkte.length).toBe(2)
  // Og de baerer hver sin maalte tid — ikke den foerstes for dem begge.
  expect(s.queryAllByText(/Tænkte i 3s/).length).toBe(1)
  expect(s.queryAllByText(/Tænkte i 9s/).length).toBe(1)
})
