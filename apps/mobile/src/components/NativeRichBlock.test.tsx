import { fireEvent, render } from '@testing-library/react-native'
import { StyleSheet } from 'react-native'
import { NativeRichBlock, parseNativeRichSpec } from './NativeRichBlock'
import { WidgetPrompt } from './WidgetFlade'

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
