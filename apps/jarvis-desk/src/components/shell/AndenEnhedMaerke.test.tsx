import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { AndenEnhedMaerke } from './AndenEnhedMaerke'

describe('AndenEnhedMaerke', () => {
  it('er helt væk når intet kører på en anden enhed', () => {
    const { container } = render(<AndenEnhedMaerke aktiv={false} />)
    expect(container).toBeEmptyDOMElement()
  })

  it('viser sig som ét mærke — ikke en linje med tekst og et kryds', () => {
    render(<AndenEnhedMaerke aktiv />)
    const m = screen.getByTestId('anden-enhed')
    expect(m).toBeTruthy()
    // Banneret havde en lukkeknap. Et mærke der forsvinder af sig selv, når
    // kørslen slutter, har ikke brug for at kunne lukkes — og «skjult» var en
    // tilstand vi skulle huske og nulstille.
    expect(m.querySelector('button')).toBeNull()
  })

  it('siger hvad den betyder til både mus og skærmlæser', () => {
    render(<AndenEnhedMaerke aktiv />)
    const m = screen.getByTestId('anden-enhed')
    expect(m.getAttribute('title')).toContain('anden enhed')
    expect(m.getAttribute('role')).toBe('status')
    // Ikonet alene siger intet uden syn; teksten står der, bare ikke synligt.
    expect(m.textContent).toContain('anden enhed')
  })
})
