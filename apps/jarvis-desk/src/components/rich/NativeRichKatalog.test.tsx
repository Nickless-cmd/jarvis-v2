import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { NativeRichBlock, parseNativeRichSpec } from './NativeRichBlock'

// Katalogudvidelsen (14/11-2026). Hver test måler BÅDE at den gyldige form
// vises og at den tomme kasseres — en parser der siger ja til alt giver en
// grøn vagt og en tom flade, hvilket er husets dyreste fejlklasse.
const spec = (o: unknown) => JSON.stringify(o)
const vis = (o: unknown) => render(<NativeRichBlock code={spec(o)} />)

describe('fladekatalog', () => {
  it('keyvalue viser nøgle og værdi', () => {
    vis({ type: 'keyvalue', title: 'Fakta', items: [{ key: 'PID', value: '1234' }] })
    expect(screen.getByText('PID')).toBeInTheDocument()
    expect(screen.getByText('1234')).toBeInTheDocument()
  })

  it('keyvalue uden value kasseres helt', () => {
    expect(parseNativeRichSpec(spec({ type: 'keyvalue', items: [{ key: 'PID' }] }))).toBeNull()
  })

  it('progress viser bjælken med den rigtige andel', () => {
    const { container } = vis({
      type: 'progress', title: 'Disk', items: [{ label: 'Brugt', value: 7, max: 10 }],
    })
    expect(screen.getByText('7 / 10')).toBeInTheDocument()
    const bjaelke = container.querySelector('.native-progress-bjaelke > span') as HTMLElement
    expect(bjaelke.style.width).toBe('70%')
  })

  it('progress med max 0 kasseres — ellers blev bredden NaN', () => {
    expect(parseNativeRichSpec(spec({ type: 'progress', items: [{ label: 'D', value: 1, max: 0 }] }))).toBeNull()
  })

  it('progress med NaN kasseres', () => {
    // JSON kan ikke bære NaN, så vejen ind er en manglende værdi.
    expect(parseNativeRichSpec(spec({ type: 'progress', items: [{ label: 'D', max: 10 }] }))).toBeNull()
  })

  it('quote viser tekst og kilde', () => {
    vis({ type: 'quote', text: 'Et citat', source: 'Kilde' })
    expect(screen.getByText('Et citat')).toBeInTheDocument()
    expect(screen.getByText('Kilde')).toBeInTheDocument()
  })

  it('quote uden tekst kasseres', () => {
    expect(parseNativeRichSpec(spec({ type: 'quote', source: 'Kilde' }))).toBeNull()
  })

  it('code nummererer linjerne fra start', () => {
    vis({ type: 'code', path: 'a.py', code: 'x = 1\ny = 2', start: 10 })
    expect(screen.getByText('a.py')).toBeInTheDocument()
    expect(screen.getByText('10')).toBeInTheDocument()
    expect(screen.getByText('11')).toBeInTheDocument()
  })

  it('code uden indhold kasseres', () => {
    expect(parseNativeRichSpec(spec({ type: 'code', path: 'a.py' }))).toBeNull()
  })

  it('tabs viser kun den valgte fane', () => {
    vis({
      type: 'tabs',
      tabs: [
        { label: 'A', children: [{ type: 'callout', title: 'x', body: 'Fra A' }] },
        { label: 'B', children: [{ type: 'callout', title: 'y', body: 'Fra B' }] },
      ],
    })
    expect(screen.getByText('Fra A')).toBeInTheDocument()
    expect(screen.queryByText('Fra B')).not.toBeInTheDocument()
  })

  it('tabs med én fane er ikke faner', () => {
    expect(parseNativeRichSpec(spec({
      type: 'tabs', tabs: [{ label: 'A', children: [{ type: 'callout', title: 'x', body: 'y' }] }],
    }))).toBeNull()
  })

  it('en ny type i et box-barn bevarer boksen', () => {
    const s = parseNativeRichSpec(spec({
      type: 'box', title: 'S', children: [{ type: 'keyvalue', items: [{ key: 'K', value: 'V' }] }],
    }))
    expect(s?.type).toBe('box')
  })
})
