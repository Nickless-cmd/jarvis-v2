import { render } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { ContentBlock } from '../../lib/sseProtocol'
import { BilledPart } from './BilledPart'

type Part = Extract<ContentBlock, { type: 'image_generation_call' }>

function part(over: Partial<Part> = {}): Part {
  return {
    type: 'image_generation_call',
    id: 'tu-1',
    navn: 'openrouter_image',
    status: 'running',
    forventet_antal: 1,
    billeder: [],
    ...over,
  }
}

describe('BilledPart — én plads gennem hele livscyklussen', () => {
  it('reserverer den PRÆCISE højde når kaldet oplyste et aspekt', () => {
    const { container } = render(<BilledPart part={part({ aspekt: '16:9' })} />)
    const plads = container.querySelector('.billed-part-plads') as HTMLElement | null
    expect(plads).not.toBeNull()
    // 16:9 bliver `16 / 9` — CSS regner resten.
    expect(plads?.style.aspectRatio).toBe('16 / 9')
  })

  it('markerer aspektet som ukendt når kaldet ikke oplyste det', () => {
    // Kontrakten: uden aspekt reserveres den MAKSIMALE højde via CSS
    // (`[data-aspekt="ukendt"]`), ikke nul. Tom plads der bliver stående er
    // ikke et hop — tom plads der forsvinder er.
    const { container } = render(<BilledPart part={part()} />)
    const rod = container.querySelector('.billed-part') as HTMLElement | null
    expect(rod?.dataset.aspekt).toBe('ukendt')
    const plads = container.querySelector('.billed-part-plads') as HTMLElement | null
    // Ingen inline aspect-ratio: CSS' faste højde styrer.
    expect(plads?.style.aspectRatio).toBe('')
  })

  it('tegner animationen mens kaldet kører', () => {
    const { container } = render(<BilledPart part={part()} />)
    expect(container.querySelector('.image-generation')).not.toBeNull()
  })

  it('viser billedet og fjerner pladsen når det er ankommet', () => {
    const { container } = render(<BilledPart part={part({
      status: 'done',
      billeder: [{ src: 'data:image/png;base64,AAA', alt: 'et billede' }],
    })} />)
    expect(container.querySelector('.billed-part-plads')).toBeNull()
    expect(container.querySelectorAll('.billed-part-billeder img')).toHaveLength(1)
  })

  it('viser en ærlig linje når genereringen fejlede uden billede', () => {
    const { container, getByText } = render(<BilledPart part={part({ status: 'error' })} />)
    expect(container.querySelector('.billed-part-fejl')).not.toBeNull()
    expect(getByText('Billedet kunne ikke genereres')).toBeTruthy()
  })

  it('bærer kaldets id som anker — samme plads før og efter turen', () => {
    const { container } = render(<BilledPart part={part({ id: 'tu-abc' })} />)
    const rod = container.querySelector('.billed-part') as HTMLElement | null
    expect(rod?.dataset.billedPart).toBe('tu-abc')
  })

  it('viser flere billeder når kaldet bad om flere', () => {
    const { container } = render(<BilledPart part={part({
      status: 'done',
      forventet_antal: 3,
      billeder: [
        { src: 'data:image/png;base64,A' },
        { src: 'data:image/png;base64,B' },
        { src: 'data:image/png;base64,C' },
      ],
    })} />)
    expect(container.querySelectorAll('.billed-part-billeder img')).toHaveLength(3)
  })
})
