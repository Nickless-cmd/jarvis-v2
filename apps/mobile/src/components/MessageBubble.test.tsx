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
