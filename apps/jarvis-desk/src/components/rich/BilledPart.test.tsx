import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import type { ContentBlock } from '../../lib/sseProtocol'
import { BilledPart } from './BilledPart'
import { WidgetPrompt } from './WidgetBlock'

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

  it('reserverer én flise per forventet billede mens flere genereres', () => {
    const { container } = render(<BilledPart part={part({
      forventet_antal: 4,
      aspekt: '16:9',
    })} />)
    const fliser = container.querySelectorAll('.billed-grid-flise')
    expect(fliser).toHaveLength(4)
    expect(container.querySelectorAll('.billed-grid-pladsholder')).toHaveLength(4)
    expect(Array.from(fliser).every((flise) => (flise as HTMLElement).style.aspectRatio === '16 / 9')).toBe(true)
  })

  it('bevarer det forventede antal pladser når billeder lander løbende', () => {
    const { container } = render(<BilledPart part={part({
      forventet_antal: 4,
      billeder: [
        { src: 'data:image/png;base64,A' },
        { src: 'data:image/png;base64,B' },
      ],
    })} />)
    expect(container.querySelectorAll('.billed-grid-flise')).toHaveLength(4)
    expect(container.querySelectorAll('.billed-grid-flise img')).toHaveLength(2)
    expect(container.querySelectorAll('.billed-grid-pladsholder')).toHaveLength(2)
  })

  it('viser landet og forventet antal mens et flerbilledkald kører', () => {
    render(<BilledPart part={part({
      forventet_antal: 4,
      billeder: [
        { src: 'data:image/png;base64,A' },
        { src: 'data:image/png;base64,B' },
      ],
    })} />)
    expect(screen.getByText('2/4')).toBeInTheDocument()
  })

  it('viser ingen tælling for et enkelt færdigt billede', () => {
    const { container } = render(<BilledPart part={part({
      status: 'done',
      billeder: [{ src: 'data:image/png;base64,A' }],
    })} />)
    expect(container.querySelector('.billed-part-taelling')).toBeNull()
  })

  it.each(['done', 'error'] as const)('viser regenerering når status er %s', (status) => {
    render(<BilledPart part={part({ status })} />)
    expect(screen.getByRole('button', { name: 'Regenerér billede' })).toBeInTheDocument()
  })

  it('viser ikke regenerering mens kaldet kører', () => {
    render(<BilledPart part={part()} />)
    expect(screen.queryByRole('button', { name: 'Regenerér billede' })).toBeNull()
  })

  it('sender regenerering gennem den eksisterende rich-blok-kanal', () => {
    const send = vi.fn()
    render(
      <WidgetPrompt.Provider value={send}>
        <BilledPart part={part({ status: 'done', id: 'tu-42', navn: 'openrouter_image' })} />
      </WidgetPrompt.Provider>,
    )
    fireEvent.click(screen.getByRole('button', { name: 'Regenerér billede' }))
    expect(send).toHaveBeenCalledWith('[fra billedpart] Regenerér billedet fra værktøjskald tu-42 med openrouter_image.')
  })
})
