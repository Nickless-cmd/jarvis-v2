import { fireEvent, render, waitFor } from '@testing-library/react-native'
import { StyleSheet } from 'react-native'
import { NativeRichBlock, parseNativeRichSpec } from './NativeRichBlock'
import { WidgetPrompt } from './WidgetFlade'
import { FladeDeferredTurnContext } from '../lib/fladeDeferredTurn'

describe('NativeRichBlock', () => {
  it('validerer og begrænser modeldata', () => {
    expect(parseNativeRichSpec('{')).toBeNull()
    expect(parseNativeRichSpec('{"type":"chart"}')).toBeNull()
    const spec = parseNativeRichSpec(JSON.stringify({
      type: 'timeline', items: Array.from({ length: 30 }, (_, i) => ({ title: `Trin ${i}` })),
    }))
    expect(spec?.type).toBe('timeline')
    if (spec?.type === 'timeline') expect(spec.items).toHaveLength(12)
  })

  it.each([
    [{ type: 'callout', tone: 'warning', title: 'Pas på', body: 'Noget vigtigt' }, 'Noget vigtigt'],
    [{ type: 'stats', title: 'Tal', items: [{ label: 'Fart', value: '42' }] }, '42'],
    [{ type: 'timeline', title: 'Plan', items: [{ title: 'Byg', status: 'current' }] }, 'Byg'],
    [{ type: 'comparison', title: 'Valg', columns: ['A', 'B'], rows: [{ label: 'Pris', values: ['1', '2'] }] }, 'Pris'],
    [{ type: 'location', title: 'Her', address: 'København' }, 'Åbn kort'],
  ])('renderer %s', async (spec, expected) => {
    const screen = await render(<NativeRichBlock code={JSON.stringify(spec)} />)
    expect(screen.getByText(expected)).toBeTruthy()
  })

  it('sender valg med synligt oprindelsesmærke', async () => {
    const send = jest.fn()
    const screen = await render(<WidgetPrompt.Provider value={send}><NativeRichBlock code={JSON.stringify({
      type: 'choices', title: 'Vælg', options: [{ label: 'Fortsæt', prompt: 'gør det' }],
    })} /></WidgetPrompt.Provider>)
    fireEvent.press(screen.getByLabelText('Fortsæt'))
    expect(send).toHaveBeenCalledWith('[fra valgkort] gør det')
  })

  it('tool-fladen får resultatet ind i sig selv og reviderer adressen', async () => {
    const run = jest.fn(async (request) => ({
      status: 'delivered' as const, retryable: false as const,
      result: { temperature: 12 }, address: { ...request.address, contentRevision: 1 },
    }))
    const screen = await render(<FladeDeferredTurnContext.Provider value={{
      accountId: 'owner-1', conversationId: 'chat-1', sourceMessageId: 'msg-1', run,
    }}><NativeRichBlock code={JSON.stringify({
      type: 'tool', title: 'Vejret', tool: 'weather',
      arguments: { location: 'Svendborg' }, label: 'Hent vejret',
    })} /></FladeDeferredTurnContext.Provider>)
    fireEvent.press(screen.getByLabelText('Hent vejret'))
    await waitFor(() => expect(screen.getByText(/temperature/)).toBeTruthy())
    expect(run.mock.calls[0]?.[0].address).toMatchObject({ contentRevision: 0 })
  })

  it('retryable tool-fejl kan prøves igen', async () => {
    const run = jest.fn(async (request) => ({
      status: 'failed' as const, kode: 'tool_failed' as const, besked: 'netværk', retryable: true, address: request.address,
    }))
    const screen = await render(<FladeDeferredTurnContext.Provider value={{
      accountId: '', conversationId: 'chat-1', sourceMessageId: 'msg-1', run,
    }}><NativeRichBlock code={JSON.stringify({
      type: 'tool', title: 'Vejret', tool: 'weather', arguments: {}, label: 'Hent',
    })} /></FladeDeferredTurnContext.Provider>)
    fireEvent.press(screen.getByLabelText('Hent'))
    await waitFor(() => expect(screen.getByLabelText('Prøv igen')).toBeTruthy())
    fireEvent.press(screen.getByLabelText('Prøv igen'))
    expect(run).toHaveBeenCalledTimes(2)
  })

  // (14/11-2026) Udfaldet: en flade der ikke kan handle må SIGE det. Før var
  // begge veje tavse — «ingen lytter» og «det gik galt» endte som intet, og en
  // aktiv knap der intet gjorde er præcis den fejlform Bjørn kalder teater.
  it('en afvist handling siger hvorfor i stedet for at tie', async () => {
    const send = jest.fn(() => ({ status: 'failed' as const, kode: 'component_unavailable' as const, besked: '', retryable: false }))
    const screen = await render(<WidgetPrompt.Provider value={send}><NativeRichBlock code={JSON.stringify({
      type: 'choices', title: 'Vælg', options: [{ label: 'Fortsæt', prompt: 'gør det' }],
    })} /></WidgetPrompt.Provider>)
    fireEvent.press(screen.getByLabelText('Fortsæt'))
    await waitFor(() => expect(screen.getByText('kan ikke sende herfra')).toBeTruthy())
  })

  it('en afleveret handling viser intet — turen fortsætter i tråden', async () => {
    const send = jest.fn(() => ({ status: 'delivered' as const, retryable: false as const }))
    const screen = await render(<WidgetPrompt.Provider value={send}><NativeRichBlock code={JSON.stringify({
      type: 'choices', title: 'Vælg', options: [{ label: 'Fortsæt', prompt: 'gør det' }],
    })} /></WidgetPrompt.Provider>)
    fireEvent.press(screen.getByLabelText('Fortsæt'))
    await waitFor(() => expect(send).toHaveBeenCalled())
    expect(screen.queryByText('kan ikke sende herfra')).toBeNull()
    expect(screen.queryByText('kunne ikke sende')).toBeNull()
  })

  it('en kastende afsendelse bliver en fejlnote, ikke et styrt', async () => {
    const send = jest.fn(() => { throw new Error('netværk') })
    const screen = await render(<WidgetPrompt.Provider value={send}><NativeRichBlock code={JSON.stringify({
      type: 'choices', title: 'Vælg', options: [{ label: 'Fortsæt', prompt: 'gør det' }],
    })} /></WidgetPrompt.Provider>)
    fireEvent.press(screen.getByLabelText('Fortsæt'))
    await waitFor(() => expect(screen.getByText('kunne ikke sende')).toBeTruthy())
  })

  it('uden modtager er knappen trykbar og siger at den ikke kan sende', async () => {
    // Den gamle gren returnerede tavst her. Testen findes for at den ikke
    // kommer tilbage: en aktiv knap der intet gør er værre end en død.
    const screen = await render(<NativeRichBlock code={JSON.stringify({
      type: 'choices', title: 'Vælg', options: [{ label: 'Fortsæt', prompt: 'gør det' }],
    })} />)
    fireEvent.press(screen.getByLabelText('Fortsæt'))
    await waitFor(() => expect(screen.getByText('kan ikke sende herfra')).toBeTruthy())
  })

  // `control` (14/11-2026): et lille håndtag midt i teksten, ikke et valgkort.
  // Forskellen til `choices` er ikke kosmetisk: et valgkort besvarer et
  // spørgsmål Jarvis stillede, et håndtag gør noget ved samtalen.
  // `control` er den FØRSTE flade med lokal state (14/11-2026). Pointen er at
  // slideren rykker UDEN at noget modelkald går ud — state bor i komponenten.
  // Testen fejler hvis nogen binder feltet til `send`.
  it('slideren rykker lokalt — uden at sende noget til modellen', async () => {
    const send = jest.fn()
    const screen = await render(<WidgetPrompt.Provider value={send}><NativeRichBlock code={JSON.stringify({
      type: 'control', title: 'Styrke',
      fields: [{ kind: 'slider', bind: 'styrke', label: 'Styrke', min: 0, max: 10, step: 5, value: 0 }],
    })} /></WidgetPrompt.Provider>)
    fireEvent.press(screen.getByLabelText('Styrke: 10'))
    expect(send).not.toHaveBeenCalled()
  })

  it('kræver mindst én slider — tekst alene er ingen kontrol', () => {
    expect(parseNativeRichSpec(JSON.stringify({ type: 'control', fields: [] }))).toBeNull()
    expect(parseNativeRichSpec(JSON.stringify({
      type: 'control', fields: [{ kind: 'text', text: 'hej' }],
    }))).toBeNull()
    // Ugyldigt interval er ikke en slider.
    expect(parseNativeRichSpec(JSON.stringify({
      type: 'control', fields: [{ kind: 'slider', bind: 'a', label: 'A', min: 10, max: 2, step: 1, value: 5 }],
    }))).toBeNull()
    const ok = parseNativeRichSpec(JSON.stringify({
      type: 'control', fields: [{ kind: 'slider', bind: 'a', label: 'A', min: 0, max: 10, step: 1, value: 5 }],
    }))
    expect(ok?.type).toBe('control')
  })

  // Målt 14/11-2026: mobilen KASSEREDE rækker hvis `values` var kortere end
  // `columns`, mens desk padder dem (rettelse 30/10-2026). Samme flade så
  // derfor rigtig ud i desk og død ud på telefonen — en række forsvandt
  // sporløst i stedet for at få en tom celle. Testen fejler på den gamle kode.
  it('padder korte rækker i stedet for at kassere dem — samme regel som desk', () => {
    const spec = parseNativeRichSpec(JSON.stringify({
      type: 'comparison', title: 'T', columns: ['A', 'B', 'C'], rows: [{ label: 'R', values: ['1'] }],
    }))
    expect(spec?.type).toBe('comparison')
    if (spec?.type === 'comparison') {
      expect(spec.rows).toHaveLength(1)
      expect(spec.rows[0]?.values).toEqual(['1', '', ''])
    }
  })

  // Målt 24/10-2026: boksen fik alle seks flader til at skære sig ud af
  // brødteksten. Data (comparison/timeline/stats) skal ligge i tekstens
  // materiale; kun objekter (callout/choices/location) skal skille sig ud.
  it.each([
    [{ type: 'callout', body: 'B' }, 'Bemærkning', true],
    [{ type: 'choices', options: [{ label: 'A', prompt: 'a' }] }, 'Valgmuligheder', true],
    [{ type: 'location', address: 'K' }, 'Lokation', true],
    [{ type: 'stats', items: [{ label: 'L', value: 'V' }] }, 'Nøgletal', false],
    [{ type: 'timeline', items: [{ title: 'X' }] }, 'Tidslinje', false],
    [{ type: 'comparison', columns: ['A', 'B'], rows: [{ label: 'R', values: ['1', '2'] }] }, 'Sammenligning', false],
  ])('boks kun på objekter: %s', async (spec, label, boxed) => {
    const screen = await render(<NativeRichBlock code={JSON.stringify(spec)} />)
    const flat = StyleSheet.flatten(screen.getByLabelText(label).props.style) ?? {}
    expect(Boolean(flat.borderWidth)).toBe(boxed)
  })
})
