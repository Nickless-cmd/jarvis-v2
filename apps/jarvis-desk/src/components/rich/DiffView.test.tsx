import { describe, it, expect } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { DiffView } from './DiffView'

describe('DiffView', () => {
  it('viser add/del-statistik + filnavn', () => {
    render(<DiffView filename="a.txt" oldText={'linje1\nlinje2'} newText={'linje1\nlinje2 ændret'} />)
    expect(screen.getByText('a.txt')).toBeInTheDocument()
    expect(screen.getByText('+1')).toBeInTheDocument()
    expect(screen.getByText('−1')).toBeInTheDocument()
  })

  it('"kun ændringer" skjuler uændrede linjer', () => {
    render(<DiffView oldText={'fælles\ngammel'} newText={'fælles\nny'} />)
    expect(screen.getByText('fælles')).toBeInTheDocument()
    fireEvent.click(screen.getByLabelText(/Kun ændringer/))
    expect(screen.queryByText('fælles')).not.toBeInTheDocument()
  })

  it('viser ingen-ændringer ved identisk tekst', () => {
    render(<DiffView oldText={'samme'} newText={'samme'} />)
    fireEvent.click(screen.getByLabelText(/Kun ændringer/))
    expect(screen.getByText('Ingen ændringer.')).toBeInTheDocument()
  })
})
