import { fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { WebSidebarFrame } from './WebSidebarFrame'

/**
 * jsdom har ingen rigtig media query-motor. Vi sætter den ene query panelet
 * spørger om, så «telefon» og «bred flade» kan testes hver for sig — det er
 * netop forskellen Bjørn bad om 18/10-2026.
 */
function saetSkærm(smal: boolean) {
  vi.stubGlobal('matchMedia', (query: string) => ({
    matches: smal && query === '(max-width: 600px)',
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  }))
}

function tegn(web = true) {
  return render(
    <WebSidebarFrame web={web} sidebar={<aside>Mine samtaler</aside>}>
      <main>Samtale</main>
    </WebSidebarFrame>,
  )
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('WebSidebarFrame', () => {
  it('starter foldet IND på en telefon og kan foldes ud med knappen', () => {
    saetSkærm(true)
    tegn()

    expect(screen.queryByText('Mine samtaler')).not.toBeInTheDocument()
    expect(screen.getByText('Samtale')).toBeInTheDocument()
    const open = screen.getByRole('button', { name: 'Åbn sidepanel' })
    expect(open).toHaveAttribute('aria-expanded', 'false')

    fireEvent.click(open)
    expect(screen.getByText('Mine samtaler')).toBeInTheDocument()
    const close = screen.getByRole('button', { name: 'Luk sidepanel' })
    expect(close).toHaveAttribute('aria-expanded', 'true')

    fireEvent.click(close)
    expect(screen.queryByText('Mine samtaler')).not.toBeInTheDocument()
  })

  it('starter foldet UD på en bred flade', () => {
    saetSkærm(false)
    tegn()

    expect(screen.getByText('Mine samtaler')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Luk sidepanel' })).toHaveAttribute(
      'aria-expanded',
      'true',
    )
  })

  it('lukker panelet når man trykker udenfor det i pwa', () => {
    saetSkærm(true)
    tegn()

    fireEvent.click(screen.getByRole('button', { name: 'Åbn sidepanel' }))
    expect(screen.getByText('Mine samtaler')).toBeInTheDocument()

    fireEvent.pointerDown(screen.getByText('Samtale'))
    expect(screen.queryByText('Mine samtaler')).not.toBeInTheDocument()
  })

  it('lukker IKKE når man trykker udenfor i kolonne-layoutet', () => {
    saetSkærm(false)
    tegn()

    fireEvent.pointerDown(screen.getByText('Samtale'))
    expect(screen.getByText('Mine samtaler')).toBeInTheDocument()
  })

  it('keeps the desktop sidebar visible without a web toggle', () => {
    saetSkærm(true)
    tegn(false)

    expect(screen.getByText('Mine samtaler')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Luk sidepanel' })).not.toBeInTheDocument()
  })
})
