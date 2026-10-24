import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { NativeRichBlock, parseNativeRichSpec } from './NativeRichBlock'
import { WidgetPrompt } from './WidgetBlock'

describe('NativeRichBlock', () => {
  it('afviser ukendt, ugyldig og for stor struktur', () => {
    expect(parseNativeRichSpec('{')).toBeNull()
    expect(parseNativeRichSpec('{"type":"chart"}')).toBeNull()
    const spec = parseNativeRichSpec(JSON.stringify({
      type: 'stats', items: Array.from({ length: 20 }, (_, i) => ({ label: `L${i}`, value: `${i}` })),
    }))
    expect(spec?.type).toBe('stats')
    if (spec?.type === 'stats') expect(spec.items).toHaveLength(8)
  })

  it.each([
    [{ type: 'callout', tone: 'warning', title: 'Pas på', body: 'Noget vigtigt' }, 'Noget vigtigt'],
    [{ type: 'stats', title: 'Tal', items: [{ label: 'Fart', value: '42', detail: 'ms' }] }, '42'],
    [{ type: 'timeline', title: 'Plan', items: [{ time: 'Nu', title: 'Byg', detail: 'Først', status: 'current' }] }, 'Byg'],
    [{ type: 'comparison', title: 'Valg', columns: ['A', 'B'], rows: [{ label: 'Pris', values: ['1', '2'] }] }, 'Pris'],
    [{ type: 'location', title: 'Her', address: 'København' }, 'Åbn kort'],
  ])('renderer %s', (spec, expected) => {
    render(<NativeRichBlock code={JSON.stringify(spec)} />)
    expect(screen.getByText(expected)).toBeInTheDocument()
  })

  it('sender valg med synligt oprindelsesmærke', () => {
    const send = vi.fn()
    render(<WidgetPrompt.Provider value={send}><NativeRichBlock code={JSON.stringify({
      type: 'choices', title: 'Vælg', options: [{ label: 'Fortsæt', prompt: 'gør det' }],
    })} /></WidgetPrompt.Provider>)
    fireEvent.click(screen.getByRole('button', { name: 'Fortsæt' }))
    expect(send).toHaveBeenCalledWith('[fra valgkort] gør det')
  })

  // Målt 24/10-2026: boksen fik alle seks flader til at skære sig ud af
  // brødteksten. Data (comparison/timeline/stats) skal ligge i tekstens
  // materiale; kun objekter (callout/choices/location) skal skille sig ud.
  it.each([
    [{ type: 'callout', title: 'T', body: 'B' }, true],
    [{ type: 'choices', title: 'T', options: [{ label: 'A', prompt: 'a' }] }, true],
    [{ type: 'location', title: 'T', address: 'K' }, true],
    [{ type: 'stats', title: 'T', items: [{ label: 'L', value: 'V' }] }, false],
    [{ type: 'timeline', title: 'T', items: [{ title: 'X' }] }, false],
    [{ type: 'comparison', title: 'T', columns: ['A', 'B'], rows: [{ label: 'R', values: ['1', '2'] }] }, false],
  ])('boks kun på objekter: %s', (spec, boxed) => {
    const { container } = render(<NativeRichBlock code={JSON.stringify(spec)} />)
    const el = container.querySelector('.native-rich')
    expect(el).toBeInTheDocument()
    expect(el!.classList.contains('native-card')).toBe(boxed)
  })
})
