import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { useRef } from 'react'
import { MessageRail } from './MessageRail'

function Harness({ ids }: { ids: string[] }) {
  const ref = useRef<HTMLDivElement>(null)
  return (
    <div ref={ref} style={{ position: 'relative' }}>
      <MessageRail containerRef={ref} anchors={ids.map((id) => ({ id, label: `besked ${id}` }))} />
      {ids.map((id) => <div key={id} data-rail-id={id}>m{id}</div>)}
    </div>
  )
}

describe('MessageRail', () => {
  it('skjuler sig ved <2 ankre', () => {
    render(<Harness ids={['a']} />)
    expect(screen.queryByRole('navigation', { name: 'Spring til besked' })).not.toBeInTheDocument()
  })

  it('viser en række pr. anker (≥2) + klik scroller', () => {
    const scroll = vi.fn()
    Element.prototype.scrollIntoView = scroll
    render(<Harness ids={['a', 'b', 'c']} />)
    const rows = screen.getAllByRole('button')
    expect(rows.length).toBe(3)
    fireEvent.click(rows[1]!)
    expect(scroll).toHaveBeenCalled()
  })

  it('markerer det afsnit man STÅR I — ikke bare det sidste', () => {
    // Før var `is-active` hardkodet til det SIDSTE anker. Det fortalte ikke
    // hvor man var, men hvor samtalen sluttede — noget man i forvejen ved
    // (Bjørn 8/9-2026: «rimelig useriøst og ufunktionelt»).
    //
    // I jsdom er alle rects 0, så alle ankre tæller som «rullet forbi», og det
    // sidste vinder. Pointen testen holder på er at markeringen KOMMER fra
    // positionen — ikke fra en hardkodet indeks.
    render(<Harness ids={['a', 'b', 'c']} />)
    const rows = screen.getAllByRole('button')
    const aktive = rows.filter((r) => r.className.includes('is-active'))
    expect(aktive.length).toBe(1)
    expect(rows[2]!.getAttribute('aria-current')).toBe('true')
  })
})
