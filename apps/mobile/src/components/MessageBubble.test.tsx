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

  // Kodeblokke tegnes af CodeBlock via en markdown-REGEL, ikke via en stil.
  // Regler er nemme at koble forkert (forkert nodenavn = tom blok, uden fejl),
  // og det ses ikke i et typecheck. Derfor denne: en fence skal give en
  // kopiér-knap og sprogets navn.
  it('en fence tegnes som CodeBlock med kopiér-knap', async () => {
    const screen = await render(
      <MessageBubble
        message={{
          id: 'm1',
          role: 'assistant',
          content: 'Her:\n\n```python\nprint("hej")\n```\n',
          created_at: '2026-09-02T18:00:00Z'
        }}
      />
    )
    expect(screen.getByTestId('code-copy')).toBeTruthy()
    expect(screen.getByText('python')).toBeTruthy()
  })

  it('en indrykket kodeblok uden sprog tegnes ogsaa som CodeBlock', async () => {
    const screen = await render(
      <MessageBubble
        message={{
          id: 'm2',
          role: 'assistant',
          content: 'Se:\n\n    ls -la\n',
          created_at: '2026-09-02T18:00:00Z'
        }}
      />
    )
    expect(screen.getByTestId('code-copy')).toBeTruthy()
  })

  it('viser kilde-chips naar assistentens svar indeholder links', async () => {
    const screen = await render(
      <MessageBubble
        message={{
          id: 'm3',
          role: 'assistant',
          content: 'Kilde: https://perplexity.ai/hub og https://openai.com/news',
          created_at: '2026-09-02T18:00:00Z'
        }}
      />
    )

    expect(screen.getByText('Kilder')).toBeTruthy()
    expect(screen.getByText('perplexity.ai')).toBeTruthy()
    expect(screen.getByText('openai.com')).toBeTruthy()
  })
})
