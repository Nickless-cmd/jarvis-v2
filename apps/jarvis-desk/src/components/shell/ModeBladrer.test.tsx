import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { ModeBladrer } from './ModeBladrer'

describe('ModeBladrer', () => {
  it('bladrer til naboen i hver sin retning', () => {
    const skift = vi.fn()
    render(<ModeBladrer active="cowork" onChange={skift} />)

    fireEvent.click(screen.getByLabelText(/Forrige tilstand/))
    expect(skift).toHaveBeenLastCalledWith('chat')

    fireEvent.click(screen.getByLabelText(/Næste tilstand/))
    expect(skift).toHaveBeenLastCalledWith('code')
  })

  it('er cyklisk i begge ender — et bladre-greb må ikke stå dødt', () => {
    const skift = vi.fn()
    const { rerender } = render(<ModeBladrer active="chat" onChange={skift} />)
    fireEvent.click(screen.getByLabelText(/Forrige tilstand/))
    expect(skift).toHaveBeenLastCalledWith('code')

    rerender(<ModeBladrer active="code" onChange={skift} />)
    fireEvent.click(screen.getByLabelText(/Næste tilstand/))
    expect(skift).toHaveBeenLastCalledWith('chat')
  })

  it('navngiver destinationen, så man ved hvor pilen fører hen', () => {
    render(<ModeBladrer active="chat" onChange={() => {}} />)
    expect(screen.getByLabelText('Forrige tilstand: Code')).toBeTruthy()
    expect(screen.getByLabelText('Næste tilstand: Arbejde')).toBeTruthy()
  })
})
