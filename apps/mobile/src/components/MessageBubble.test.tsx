import { act, fireEvent, render } from '@testing-library/react-native'
import { MessageBubble } from './MessageBubble'
import type { ChatMessage } from '../lib/types'
import { Animated } from 'react-native'

// Boblen kan nu bære Jarvis' EGNE filer, og `MessageAttachments` henter sin
// konfiguration gennem `useAuth` — som kaster uden for en AuthProvider. Samme
// mock som `MessageAttachments.test.tsx` bruger; resten af modulet holdes ægte,
// så en fremtidig eksport ikke skal tilføjes her.
jest.mock('../state/AuthContext', () => {
  const config = { apiBaseUrl: 'https://api.srvlab.dk/', authToken: 'token' }
  return {
    ...jest.requireActual('../state/AuthContext'),
    useAuth: () => ({ config }),
    useAuthOptional: () => ({ config }),
  }
})

const base = { id: 'm1', created_at: new Date().toISOString() }

describe('MessageBubble', () => {
  it('giver ombrudt assistenttekst en kompakt linjehøjde på selve Text-elementet', async () => {
    const screen = await render(<MessageBubble message={{
      ...base, role: 'assistant',
      content: 'Den gjorde det tre. Så enten overlever tælleren ikke mellem runderne, eller også starter hver af mine tekstblokke en ny tur.'
    } as ChatMessage} />)
    const text = screen.getByText(/Den gjorde det tre/)
    const textgroup = text.parent!
    expect(textgroup.type).toBe('Text')
    expect(textgroup.props.style).toEqual(expect.objectContaining({
      fontSize: 15,
      lineHeight: 19,
      includeFontPadding: false,
    }))
  })

  it('stream og gemt svar bruger samme kompakte afsnitsafstand', async () => {
    const content = 'Første sætning.\n\nAnden sætning.\n\nTredje sætning.'
    const a = await render(<MessageBubble message={{ ...base, id: 'stream-1', role: 'assistant', content } as ChatMessage} />)
    const b = await render(<MessageBubble message={{ ...base, id: 'm1', role: 'assistant', content } as ChatMessage} />)
    const margins = (root: any) => {
      const out: number[] = []
      const walk = (node: any) => {
        if (!node || typeof node !== 'object') return
        if (node.props?.style?.width === '100%' && node.props.style.marginBottom !== undefined) {
          out.push(node.props.style.marginBottom)
        }
        for (const child of node.children ?? []) walk(child)
      }
      walk(root)
      return out
    }
    expect(margins(a.toJSON())).toEqual(margins(b.toJSON()))
    expect(margins(b.toJSON())).toHaveLength(3)
    expect(Math.max(...margins(b.toJSON()))).toBeLessThanOrEqual(3)
  })

  it('starter ikke indgangsanimationen igen når streamen bliver gemt', async () => {
    const spring = jest.spyOn(Animated, 'spring')
    try {
      await render(<MessageBubble message={{
        ...base, id: 'saved-assistant', role: 'assistant', content: 'Færdigt svar.',
      } as ChatMessage} />)
      expect(spring).not.toHaveBeenCalled()
      await render(<MessageBubble message={{
        ...base, id: 'stream-assistant', role: 'assistant', content: 'Live svar.',
      } as ChatMessage} />)
      expect(spring).toHaveBeenCalled()
    } finally {
      spring.mockRestore()
    }
  })
  it('rendrer bruger + assistent uden crash', async () => {
    const user = { ...base, role: 'user', content: 'hej' } as ChatMessage
    const asst = { ...base, role: 'assistant', content: '**hej** verden' } as ChatMessage
    expect((await render(<MessageBubble message={user} />)).toJSON()).toBeTruthy()
    expect((await render(<MessageBubble message={asst} />)).toJSON()).toBeTruthy()
  })

  it('viser Jarvis’ 1 · punkter som én nummereret liste', async () => {
    const screen = await render(<MessageBubble message={{
      ...base,
      role: 'assistant',
      content: '**1 · Skill-testen.**\nDen er stadig rød.\n\n**2 · Doc-drift.** To kommentarer er forældede.'
    } as ChatMessage} />)
    expect(screen.getByText('1.')).toBeTruthy()
    expect(screen.getByText('2.')).toBeTruthy()
  })

  it('færdige svar opløser referencelinks på tværs af afsnit', async () => {
    const screen = await render(<MessageBubble message={{
      ...base, role: 'assistant',
      content: 'Se [dokumentet][ref].\n\nEt andet afsnit.\n\n[ref]: https://example.com/docs',
    } as ChatMessage} />)
    expect(screen.getByText('dokumentet').parent?.props.onPress).toBeDefined()
  })

  it.each(['stream-1', 'm1'])('bevarer fede listeetiketter i svar %s', async (id) => {
    const content = '- **Fil:** src/lib/x.ts\n- **Linje:** 42\n- **Status:** rettet'
    const screen = await render(<MessageBubble message={{
      ...base, id, role: 'assistant', content,
    } as ChatMessage} />)
    expect(screen.getByText('Fil:')).toBeTruthy()
    expect(screen.getByText('Linje:')).toBeTruthy()
    expect(screen.getByText('Status:')).toBeTruthy()
  })

  it.each(['stream-1', 'm1'])('bevarer en fed etiket i prosa %s', async (id) => {
    const screen = await render(<MessageBubble message={{
      ...base, id, role: 'assistant', content: 'Intro. **Hvad det er:** noget indhold her',
    } as ChatMessage} />)
    expect(screen.getByText('Hvad det er:')).toBeTruthy()
    expect(screen.getByText('noget indhold her')).toBeTruthy()
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
    // Kopiér bor under «...» nu; oplæsning staar stadig i raekken.
    const s = await render(<MessageBubble message={svar} />)
    expect(s.getByLabelText('Læs op')).toBeTruthy()
    expect(s.getByLabelText('Flere handlinger')).toBeTruthy()
  })

  it('skjules på afsnit der ikke er turens sidste', async () => {
    // En tur udfoldes i flere afsnit; uden dette fik HVERT afsnit sin egen
    // kopiér/oplæs-række, og tråden blev støjende.
    const s = await render(<MessageBubble message={svar} hideActions />)
    expect(s.queryByLabelText('Læs op')).toBeNull()
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

describe('tilbagemeldinger', () => {
  const svar2 = {
    id: 'm-9', role: 'assistant' as const,
    content: 'et svar', created_at: '2026-09-12T12:00:00Z',
  }

  it('kopier og tommelfingre bor under «...» — ikke i raekken', async () => {
    // Seks ikoner i en raekke koster seks pladser, og det man vaelger ÉN gang
    // om maaneden skal ikke have en fast plads.
    const s = await render(<MessageBubble message={svar2} />)
    expect(s.queryByLabelText('God besvarelse')).toBeNull()
    await fireEvent.press(s.getByLabelText('Flere handlinger'))
    expect(s.getByTestId('msg-copy')).toBeTruthy()
    expect(s.getByTestId('msg-vote-up')).toBeTruthy()
    expect(s.getByTestId('msg-vote-down')).toBeTruthy()
  })

  it('en stemme MARKERES med det samme', async () => {
    // Et tryk der venter paa et netvaerkssvar foeles som et tryk der ikke
    // virkede - samme regel som godkendelseskortet.
    const s = await render(<MessageBubble message={svar2} />)
    await fireEvent.press(s.getByLabelText('Flere handlinger'))
    await fireEvent.press(s.getByTestId('msg-vote-up'))
    await fireEvent.press(s.getByLabelText('Flere handlinger'))
    expect(s.getByText('God besvarelse ✓')).toBeTruthy()
  })

  it('samme stemme igen FORTRYDER', async () => {
    const s = await render(<MessageBubble message={svar2} />)
    await fireEvent.press(s.getByLabelText('Flere handlinger'))
    await fireEvent.press(s.getByTestId('msg-vote-up'))
    await fireEvent.press(s.getByLabelText('Flere handlinger'))
    await fireEvent.press(s.getByTestId('msg-vote-up'))
    await fireEvent.press(s.getByLabelText('Flere handlinger'))
    expect(s.getByText('God besvarelse')).toBeTruthy()
  })
})

/**
 * Rækkefølgen i det tegnede træ, som testID'er og tilgængeligheds-labels.
 *
 * `getAllByTestId` kan ikke svare på «hvad kommer først» på tværs af
 * FORSKELLIGE id'er — og netop dét er hele spørgsmålet her: står billedet før
 * eller efter handlingsrækken? Derfor læses træet i dokument-rækkefølge.
 */
const raekkefoelge = (node: unknown, ud: string[] = []): string[] => {
  if (Array.isArray(node)) {
    node.forEach((n) => raekkefoelge(n, ud))
    return ud
  }
  if (!node || typeof node !== 'object') return ud
  const n = node as { props?: Record<string, unknown>; children?: unknown }
  const p = n.props ?? {}
  if (typeof p.testID === 'string') ud.push(p.testID)
  if (typeof p.accessibilityLabel === 'string') ud.push(p.accessibilityLabel)
  raekkefoelge(n.children, ud)
  return ud
}

describe("Jarvis' eget billede hører til beskeden", () => {
  const svar = {
    id: 'a1',
    role: 'assistant' as const,
    content: 'Her er billedet.',
    created_at: '2026-09-27T09:00:00Z'
  }

  it('billedet står OVER teksten — samme rækkefølge som desk', async () => {
    // Bjørn, 27/9-2026 om aftenen, efter at live-billedet kom til at virke:
    // «det eneste der mangler er at billederne bliver vist over hans besked,
    // ligesom i desk». I desk lander billedblokken i svaret i den orden den
    // kom — altså før den afsluttende tekst — og hele pointen med at sende den
    // live er at den står dér hvor den blev lavet.
    const s = await render(
      <MessageBubble
        message={svar}
        vedhaeftninger={[{ type: 'image', attachment_id: 'i0', filename: 'a.png' }]}
      />
    )
    const json = JSON.stringify(s.toJSON())
    expect(json.indexOf('attachment-wrap')).toBeGreaterThan(-1)
    expect(json.indexOf('Her er billedet.')).toBeGreaterThan(-1)
    expect(json.indexOf('attachment-wrap')).toBeLessThan(json.indexOf('Her er billedet.'))
  })

  it('billedet står FØR handlingsrækken — ikke efter svaret', async () => {
    // Målt 27/9-2026 på Bjørns telefon: filen lå i sin EGEN række efter boblen,
    // altså neden for kopiér/oplæs-ikonerne, og så ud som om den kom bagefter
    // svaret i stedet for at være en del af det. Rækkefølgen er nu
    // billede → tekst → handlinger.
    const s = await render(
      <MessageBubble
        message={svar}
        vedhaeftninger={[{ type: 'image', attachment_id: 'i1', filename: 'a.png' }]}
      />
    )
    expect(s.getByTestId('attachment-wrap')).toBeTruthy()
    const orden = raekkefoelge(s.toJSON())
    expect(orden.indexOf('attachment-wrap')).toBeGreaterThan(-1)
    expect(orden.indexOf('Læs op')).toBeGreaterThan(-1)
    expect(orden.indexOf('attachment-wrap')).toBeLessThan(orden.indexOf('Læs op'))
  })

  it('uden filer er rækkefølgen uændret', async () => {
    const s = await render(<MessageBubble message={svar} />)
    expect(s.queryByTestId('attachment-wrap')).toBeNull()
    expect(s.getByLabelText('Læs op')).toBeTruthy()
  })

  it('dine EGNE uploads går ikke gennem boblen', async () => {
    // De har ingen handlingsrække imellem sig og boblen og ligger allerede
    // rigtigt over den — se `MessageList`.
    const s = await render(
      <MessageBubble
        message={{ ...svar, role: 'user', content: 'se her' }}
        vedhaeftninger={[{ type: 'image', attachment_id: 'i2', filename: 'b.png' }]}
      />
    )
    expect(s.queryByTestId('attachment-wrap')).toBeNull()
  })
})
