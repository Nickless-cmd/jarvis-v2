import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, screen, fireEvent, act } from '@testing-library/react'
import { ThinkingLine, formatSek } from './ThinkingLine'
import { foldToolResults } from '../../lib/foldToolResults'

afterEach(() => { vi.useRealTimers() })

describe('ThinkingLine', () => {
  it('live: én linje med løbende tid — monologen står IKKE i tråden', () => {
    vi.useFakeTimers()
    render(<ThinkingLine text="intern monolog" live />)
    expect(screen.getByRole('button', { name: 'Tænker' })).toBeInTheDocument()
    // Monologen står ikke som tekst i tråden — kun dens sidste linje, dæmpet, som metadata.
    expect(screen.queryByText('intern monolog')).not.toBeInTheDocument()
    act(() => { vi.advanceTimersByTime(4200) })
    expect(screen.getByTestId('tanke-meta')).toHaveTextContent('· 4 s · intern monolog')
  })

  it('færdig: «Tænkte i X s» og klik folder tanken ud', () => {
    render(<ThinkingLine text="intern monolog" seconds={12.4} live={false} />)
    const knap = screen.getByRole('button', { name: /Tænkte i 12 s/ })
    expect(screen.queryByText('intern monolog')).not.toBeInTheDocument()
    fireEvent.click(knap)
    expect(screen.getByText('intern monolog')).toBeInTheDocument()
  })

  it('kort tanke BEHOLDER sit tal (Bjørn 17/9-2026: tiden «var ikke persistet»)', () => {
    render(<ThinkingLine text="kort" seconds={1.1} live={false} />)
    expect(screen.getByRole('button', { name: 'Tænkte i 1,1 s' })).toBeInTheDocument()
  })

  it('live → færdig fryser tiden', () => {
    vi.useFakeTimers()
    const { rerender } = render(<ThinkingLine text="x" live />)
    act(() => { vi.advanceTimersByTime(5000) })
    rerender(<ThinkingLine text="x" live={false} />)
    act(() => { vi.advanceTimersByTime(60000) })
    expect(screen.getByText('Tænkte i 5 s')).toBeInTheDocument()
  })

  it('gemt blok uden tekst og tid: intet', () => {
    const { container } = render(<ThinkingLine text="" live={false} />)
    expect(container).toBeEmptyDOMElement()
  })

  it('formatSek', () => {
    expect(formatSek(3.44)).toBe('3,4 s')
    expect(formatSek(12.4)).toBe('12 s')
    expect(formatSek(75)).toBe('1 min 15 s')
  })
})

describe('gemt tanke-blok', () => {
  it('læser `text` + `seconds` (serverens form) — før var den altid tom efter reload', () => {
    const [b] = foldToolResults([{ type: 'thinking', text: 'Lad mig tjekke', seconds: 0.4 }])
    expect(b).toEqual({ type: 'thinking', thinking: 'Lad mig tjekke', seconds: 0.4 })
  })
})
