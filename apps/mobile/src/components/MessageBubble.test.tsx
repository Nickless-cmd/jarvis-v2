import { render } from '@testing-library/react-native'
import { MessageBubble } from './MessageBubble'
import type { ChatMessage } from '../lib/types'

const base = { id: 'm1', created_at: new Date().toISOString() }

describe('MessageBubble', () => {
  it('rendrer bruger + assistent uden crash', async () => {
    const user = { ...base, role: 'user', content: 'hej' } as ChatMessage
    const asst = { ...base, role: 'assistant', content: '**hej** verden' } as ChatMessage
    expect((await render(<MessageBubble message={user} />)).toJSON()).toBeTruthy()
    expect((await render(<MessageBubble message={asst} />)).toJSON()).toBeTruthy()
  })
})

describe('handlingsrækken hører til turens SIDSTE afsnit', () => {
  const svar = {
    id: 'a1',
    role: 'assistant' as const,
    content: 'et afsnit',
    created_at: '2026-09-02T12:00:00Z'
  }

  it('vises som standard', async () => {
    const s = await render(<MessageBubble message={svar} />)
    expect(s.getByLabelText('Kopiér')).toBeTruthy()
  })

  it('skjules på afsnit der ikke er turens sidste', async () => {
    // En tur udfoldes i flere afsnit; uden dette fik HVERT afsnit sin egen
    // kopiér/oplæs-række, og tråden blev støjende.
    const s = await render(<MessageBubble message={svar} hideActions />)
    expect(s.queryByLabelText('Kopiér')).toBeNull()
  })
})

