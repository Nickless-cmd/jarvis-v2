import { fireEvent, render } from '@testing-library/react-native'
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
})
