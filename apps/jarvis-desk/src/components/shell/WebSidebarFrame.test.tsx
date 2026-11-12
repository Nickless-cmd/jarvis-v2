import { fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { WebSidebarFrame } from './WebSidebarFrame'

/**
 * jsdom har ingen rigtig media query-motor. Vi sætter den ene query panelet
 * spørger om, så «telefon» og «bred flade» kan testes hver for sig — CSS'en
 * vælger overlay eller kolonne ud fra den, men start-tilstanden må ikke gøre
 * det (Bjørn 18/10-2026: pwa starter foldet ind uanset bredde).
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
  it('starter foldet IND i pwa — på en telefon', () => {
    saetSkærm(true)
    tegn()

    expect(screen.queryByText('Mine samtaler')).not.toBeInTheDocument()
    expect(screen.getByText('Samtale')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Åbn sidepanel' })).toHaveAttribute(
      'aria-expanded',
      'false',
    )
  })

  // Regressionsvagt: panelet stod ÅBENT i browseren på 1920px, fordi starten var
  // bundet til `max-width: 600px` i stedet for til buildet.
  it('starter foldet IND i pwa — også på en bred flade', () => {
    saetSkærm(false)
    tegn()

    expect(screen.queryByText('Mine samtaler')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Åbn sidepanel' })).toHaveAttribute(
      'aria-expanded',
      'false',
    )
  })

  it('kan foldes ud og ind med knappen', () => {
    saetSkærm(false)
    tegn()

    fireEvent.click(screen.getByRole('button', { name: 'Åbn sidepanel' }))
    expect(screen.getByText('Mine samtaler')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Luk sidepanel' })).toHaveAttribute(
      'aria-expanded',
      'true',
    )

    fireEvent.click(screen.getByRole('button', { name: 'Luk sidepanel' }))
    expect(screen.queryByText('Mine samtaler')).not.toBeInTheDocument()
  })

  it('lukker panelet når man trykker udenfor det i pwa — på en telefon', () => {
    saetSkærm(true)
    tegn()

    fireEvent.click(screen.getByRole('button', { name: 'Åbn sidepanel' }))
    expect(screen.getByText('Mine samtaler')).toBeInTheDocument()

    fireEvent.pointerDown(screen.getByText('Samtale'))
    expect(screen.queryByText('Mine samtaler')).not.toBeInTheDocument()
  })

  // 12/11-2026 (Bjørn): «i web buildt skal venstre panel ikk forsvinde naar man
  // trykker uden for som det goer i pwa mobil view». Over 600px staar panelet
  // som kolonne ved siden af samtalen — et klik i chatten er saa et klik i
  // chatten, ikke en anmodning om at lukke panelet.
  it('beholder panelet naar man trykker udenfor paa en bred flade', () => {
    saetSkærm(false)
    tegn()

    fireEvent.click(screen.getByRole('button', { name: 'Åbn sidepanel' }))
    expect(screen.getByText('Mine samtaler')).toBeInTheDocument()

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
