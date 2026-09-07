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

describe('kilder overlever at streamen stopper', () => {
  const svar = { ...base, role: 'assistant' as const, content: 'Her er svaret.' } as ChatMessage

  it('viser kilder fra tool_result — også når svaret ikke citerer dem', async () => {
    // Kernen i fejlen målt 7/9: under streaming kunne man se kilderne, fordi
    // de levende tool-blokke blev tegnet. Bagefter faldt de væk, fordi
    // «Kilder» udelukkende læste svarteksten — og han citerer sjældent selv
    // adresserne.
    const r = await render(
      <MessageBubble
        message={svar}
        kildeBlokke={[
          { type: 'tool_use', name: 'web_search', input: { query: 'proxmox' } },
          { type: 'tool_result', content: 'Se https://pve.proxmox.com/wiki/LXC' }
        ]}
      />
    )
    expect(r.getByText('Kilder')).toBeTruthy()
    expect(r.getByText('pve.proxmox.com')).toBeTruthy()
  })

  it('uden blokke falder den tilbage til adresser i teksten', async () => {
    // Gamle beskeder har ingen content_json. De skal ikke miste det de havde.
    const r = await render(
      <MessageBubble message={{ ...svar, content: 'Læs https://dr.dk/nyt' }} />
    )
    expect(r.getByText('dr.dk')).toBeTruthy()
  })

  it('ingen kilder → ingen overskrift', async () => {
    const r = await render(<MessageBubble message={svar} kildeBlokke={[]} />)
    expect(r.queryByText('Kilder')).toBeNull()
  })

  it('brugerens egen besked får aldrig kilder', async () => {
    const r = await render(
      <MessageBubble
        message={{ ...base, role: 'user', content: 'se https://dr.dk/x' } as ChatMessage}
      />
    )
    expect(r.queryByText('Kilder')).toBeNull()
  })
})
