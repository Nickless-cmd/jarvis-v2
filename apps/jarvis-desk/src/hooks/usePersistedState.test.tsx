import { describe, it, expect, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { usePersistedState } from './usePersistedState'

function Probe({ k, start }: { k: string; start: boolean }) {
  const [v, setV] = usePersistedState(k, start)
  return <button onClick={() => setV((p) => !p)}>{v ? 'til' : 'fra'}</button>
}

function PrivateProbe({ persist }: { persist: boolean }) {
  const [value, setValue] = usePersistedState('private-draft', '', persist)
  return <input aria-label="private-draft" value={value} onChange={(e) => setValue(e.target.value)} />
}

/**
 * Hooken findes fordi Bjørn 4/10-2026 mistede sin tekst ved mode-skift og sine
 * paneler ved genstart: «appen husker ikk om de var åbne».
 */
describe('usePersistedState', () => {
  beforeEach(() => localStorage.clear())

  it('læser den GEMTE værdi ved mount — ikke standardværdien', () => {
    localStorage.setItem('k1', 'true')
    render(<Probe k="k1" start={false} />)
    expect(screen.getByText('til')).toBeInTheDocument()
  })

  it('falder tilbage ved en ulæselig værdi i stedet for at kaste', () => {
    // En UI-præference må aldrig vælte fladen.
    localStorage.setItem('k2', '{ikke json')
    render(<Probe k="k2" start={false} />)
    expect(screen.getByText('fra')).toBeInTheDocument()
  })

  it('husker en ændring', async () => {
    render(<Probe k="k3" start={false} />)
    fireEvent.click(screen.getByText('fra'))
    await waitFor(() => expect(localStorage.getItem('k3')).toBe('true'))
  })

  it('skriver ved UNMOUNT — et mode-skift kan ske inden debounce-vinduet', () => {
    // Uden denne ville skrivningen ligge i en 150 ms-timer der blev ryddet ved
    // unmount, og kladden nåede aldrig disken. Målt: unmount sker efter 0 ms.
    const { unmount } = render(<Probe k="k4" start={false} />)
    fireEvent.click(screen.getByText('fra'))
    unmount()
    expect(localStorage.getItem('k4')).toBe('true')
  })

  it('skriver ikke en tidligere ejers kladde igen ved skift til medlemsmode', () => {
    const { rerender, unmount } = render(<PrivateProbe persist />)
    fireEvent.change(screen.getByRole('textbox', { name: 'private-draft' }), {
      target: { value: 'ejerens tekst' },
    })
    localStorage.removeItem('private-draft')
    rerender(<PrivateProbe persist={false} />)
    expect(screen.getByRole('textbox', { name: 'private-draft' })).toHaveValue('')
    unmount()
    expect(localStorage.getItem('private-draft')).toBeNull()
  })

  it('indlæser ejerens kladde når rollen bliver kendt efter whoami', () => {
    localStorage.setItem('private-draft', JSON.stringify('ejerens gemte kladde'))
    const { rerender } = render(<PrivateProbe persist={false} />)
    expect(screen.getByRole('textbox', { name: 'private-draft' })).toHaveValue('')
    rerender(<PrivateProbe persist />)
    expect(screen.getByRole('textbox', { name: 'private-draft' })).toHaveValue('ejerens gemte kladde')
  })
})
