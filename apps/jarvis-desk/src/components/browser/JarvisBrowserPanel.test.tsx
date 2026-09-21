import { render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { JarvisBrowserPanel } from './JarvisBrowserPanel'

/**
 * Panelet tegner IKKE siden — den er en WebContentsView som Electron lægger
 * oven på vinduet. Det panelet skal kunne, er at MELDE hvor hullet er, og at
 * vise fanerne. Derfor måles netop de to ting her.
 */
// jsdom har ingen ResizeObserver. Komponenten bruger den til at melde
// hullets rektangel ved ENHVER ændring — et window-resize-lytteord ville
// misse et sidepanel der folder ud. Manglen er testmiljøets, så den stubbes
// her frem for at svække komponenten.
class _ResizeObserverStub {
  constructor(private cb: () => void) {}
  observe() { this.cb() }
  disconnect() {}
  unobserve() {}
}
;(globalThis as unknown as { ResizeObserver: unknown }).ResizeObserver = _ResizeObserverStub

const saetRect = vi.fn(async () => true)
const saetSynlig = vi.fn(async () => true)
const faner = vi.fn(async () => [
  { id: 1, url: 'https://eksempel.dk/a', titel: 'Side A', aktiv: true },
  { id: 2, url: 'https://eksempel.dk/b', titel: '', aktiv: false },
])

function broPaa() {
  ;(window as unknown as { jarvisDesk?: unknown }).jarvisDesk = {
    browser: { saetRect, saetSynlig, faner, vaelg: vi.fn(), luk: vi.fn(), aabn: vi.fn(), naviger: vi.fn() },
  }
}

describe('JarvisBrowserPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    delete (window as unknown as { jarvisDesk?: unknown }).jarvisDesk
  })

  it('er helt væk når panelet er lukket', () => {
    broPaa()
    const { container } = render(<JarvisBrowserPanel aaben={false} />)
    expect(container).toBeEmptyDOMElement()
  })

  it('siger fra uden desk-broen i stedet for at tegne et tomt hul', () => {
    render(<JarvisBrowserPanel aaben />)
    expect(screen.getByText(/kraever desk-appen/i)).toBeTruthy()
  })

  it('melder hullets rektangel til main — ellers ved visningen ikke hvor den skal ligge', async () => {
    broPaa()
    render(<JarvisBrowserPanel aaben />)
    await waitFor(() => expect(saetRect).toHaveBeenCalled())
    const arg = saetRect.mock.calls.at(0)?.at(0) as unknown as Record<string, number>
    expect(arg).toBeTruthy()
    for (const n of ['x', 'y', 'width', 'height']) {
      expect(typeof arg[n]).toBe('number')
    }
  })

  it('taender visningen når panelet åbnes', async () => {
    broPaa()
    render(<JarvisBrowserPanel aaben />)
    await waitFor(() => expect(saetSynlig).toHaveBeenCalledWith(true))
  })

  it('viser fanerne, og en fane uden titel falder tilbage på sin url', async () => {
    broPaa()
    render(<JarvisBrowserPanel aaben />)
    expect(await screen.findByText('Side A')).toBeTruthy()
    expect(await screen.findByText('https://eksempel.dk/b')).toBeTruthy()
  })
})
