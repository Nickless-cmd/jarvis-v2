import { act, fireEvent, render } from '@testing-library/react-native'
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

describe('teksten kan markeres', () => {
  /** Find alle Text-noder med selectable i det renderede træ. */
  function markerbare(node: unknown, fundet: unknown[] = []): unknown[] {
    if (!node || typeof node !== 'object') return fundet
    const n = node as { props?: Record<string, unknown>; children?: unknown[] }
    if (n.props?.selectable) fundet.push(n)
    for (const b of n.children ?? []) markerbare(b, fundet)
    return fundet
  }

  it('brugerens egen besked kan markeres', async () => {
    // Kunne ikke før: kopiér-knappen tog HELE beskeden, og der var ingen vej
    // til en enkelt sætning, et tal eller en sti.
    const r = await render(
      <MessageBubble message={{ ...base, role: 'user', content: 'min sti er /opt/x' } as ChatMessage} />
    )
    expect(markerbare(r.toJSON())).not.toHaveLength(0)
  })

  it('hans svar markeres gennem hold-inde, ikke afsnit for afsnit', async () => {
    // Hed før «hans svar kan markeres — også gennem markdown» og hævdede at
    // `textgroup` var selectable. Det VAR den, og det var netop problemet:
    // Androids markering kan ikke krydse søskende-elementer, så hold-inde
    // fangede ét afsnit og nægtede at trække videre. Målt hos Bjørn 7/9.
    //
    // Nu giver hold-inde hele svaret som ét felt i stedet.
    const r = await render(
      <MessageBubble message={{ ...base, role: 'assistant', content: 'se **her**: /etc/hosts' } as ChatMessage} />
    )
    expect(markerbare(r.toJSON())).toHaveLength(0)
    await act(async () => { fireEvent(r.getByTestId('msg-body'), 'longPress') })
    expect(markerbare(r.toJSON())).not.toHaveLength(0)
  })

})

describe('markér hele beskeden', () => {
  const langt = {
    ...base,
    role: 'assistant' as const,
    content: '# Overskrift\n\n- punkt et\n- punkt to\n\n```\n  indrykket linje\n```\n\nsidste afsnit'
  } as ChatMessage

  it('menuen tilbyder at markere teksten', async () => {
    const r = await render(<MessageBubble message={langt} />)
    await act(async () => { fireEvent.press(r.getByLabelText('Flere handlinger')) })
    expect(r.getByTestId('msg-select-text')).toBeTruthy()
  })

  it('markerings-tilstand viser HELE beskeden som ét felt', async () => {
    // Kernen: React Natives markering kan ikke krydse søskende-elementer, og
    // markdown tegner overskrift, liste, kodeblok og afsnit hver for sig. Man
    // kunne derfor kun tage én linje. Her er alt ét felt, så et træk hen over
    // det hele virker — og indrykningen står som den er.
    const r = await render(<MessageBubble message={langt} />)
    await act(async () => { fireEvent.press(r.getByLabelText('Flere handlinger')) })
    await act(async () => { fireEvent.press(r.getByTestId('msg-select-text')) })

    expect(r.getByText(langt.content)).toBeTruthy()
    expect(r.getByTestId('msg-select-done')).toBeTruthy()
  })

  it('hold inde på svaret markerer det HELE — uden menu-omvej', async () => {
    // Den naturlige bevægelse skal gøre det rigtige. Bjørn prøvede at holde
    // inde og trække, og Android gav ham ét afsnit og nægtede at gå videre.
    const r = await render(<MessageBubble message={langt} />)
    await act(async () => { fireEvent(r.getByTestId('msg-body'), 'longPress') })
    expect(r.getByText(langt.content)).toBeTruthy()
    expect(r.getByTestId('msg-select-done')).toBeTruthy()
  })

  it('brugerens egen besked markeres stadig direkte', async () => {
    // Én Text uden blokke — dér er der intet at krydse, og den indbyggede
    // markering er den korteste vej.
    const r = await render(
      <MessageBubble message={{ ...base, role: 'user', content: 'min sti' } as ChatMessage} />
    )
    expect(r.queryByTestId('msg-body')).toBeNull()
  })

  it('Færdig lukker tilstanden igen', async () => {
    const r = await render(<MessageBubble message={langt} />)
    await act(async () => { fireEvent.press(r.getByLabelText('Flere handlinger')) })
    await act(async () => { fireEvent.press(r.getByTestId('msg-select-text')) })
    await act(async () => { fireEvent.press(r.getByTestId('msg-select-done')) })
    expect(r.queryByTestId('msg-select-done')).toBeNull()
  })
})
