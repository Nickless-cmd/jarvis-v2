/**
 * Fejl-rapporten — midt på skærmen, og til bug-endpointet.
 *
 * Bjørn 4/10-2026: «bug icon laves om til et felt midt på skærmen hvor man kan
 * melde faktisk bug til dit bug endpoint».
 *
 * Den vigtigste påstand her er ikke at feltet findes. Det er HVOR rapporten
 * ender. Før gik den til skrivefeltet via `jarvis-bug`, hvor den blev en besked
 * i samtalen; nu skal den til `POST /chat/inbox/flag`. En test der kun tjekkede
 * at der findes et felt ville have været grøn hele tiden — også i den gamle
 * udgave, hvor feltet bare lå et andet sted.
 */
import { describe, expect, it, vi, beforeEach } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'

vi.mock('../lib/bugApi', () => ({ rapporterBug: vi.fn() }))

import { rapporterBug } from '../lib/bugApi'
import { BugRapport } from './BugRapport'

const rb = vi.mocked(rapporterBug)
const cfg = { apiBaseUrl: 'http://x', authToken: 't' }

describe('fejl-rapporten', () => {
  beforeEach(() => { rb.mockReset() })

  it('er et felt med titel og beskrivelse', () => {
    render(<BugRapport config={cfg} onClose={() => {}} />)
    expect(screen.getByRole('dialog', { name: 'Rapportér en fejl' })).toBeInTheDocument()
    expect(screen.getByLabelText('Hvad gik galt?')).toBeInTheDocument()
    expect(screen.getByLabelText('Beskrivelse (valgfri)')).toBeInTheDocument()
  })

  it('kan ikke sende uden titel — serveren afviser tomme titler med 400', () => {
    // Kontrakten er serverens: en post der ikke kan navngives i visningen må
    // ikke oprettes. Hellere en disabled knap end et klik vi VED bliver en fejl.
    render(<BugRapport config={cfg} onClose={() => {}} />)
    expect(screen.getByRole('button', { name: 'Send til Jarvis' })).toBeDisabled()
  })

  it('sender titel og beskrivelse til bug-endpointet', async () => {
    rb.mockResolvedValue({ id: 'inbox-1' })
    render(<BugRapport config={cfg} onClose={() => {}} />)
    fireEvent.change(screen.getByLabelText('Hvad gik galt?'), { target: { value: 'Streamen stopper' } })
    fireEvent.change(screen.getByLabelText('Beskrivelse (valgfri)'), { target: { value: 'ved genstart' } })
    fireEvent.click(screen.getByRole('button', { name: 'Send til Jarvis' }))
    await waitFor(() => expect(rb).toHaveBeenCalledWith(cfg, 'Streamen stopper', 'ved genstart'))
  })

  it('bekræfter at rapporten ligger i indbakken', async () => {
    rb.mockResolvedValue({ id: 'inbox-1' })
    render(<BugRapport config={cfg} onClose={() => {}} />)
    fireEvent.change(screen.getByLabelText('Hvad gik galt?'), { target: { value: 'Streamen stopper' } })
    fireEvent.click(screen.getByRole('button', { name: 'Send til Jarvis' }))
    expect(await screen.findByRole('status')).toHaveTextContent(/indbakken/i)
  })

  it('viser serverens forklaring når kaldet fejler — og taber ikke teksten', async () => {
    // `apiFetch` pakker `{"detail": …}` ud, så «titel kraeves» når frem i
    // stedet for «HTTP 400». Et felt der fejler tavst er den fejlklasse vi
    // har brugt hele dagen på at fjerne.
    rb.mockRejectedValue(new Error('titel kraeves'))
    render(<BugRapport config={cfg} onClose={() => {}} />)
    fireEvent.change(screen.getByLabelText('Hvad gik galt?'), { target: { value: 'Streamen stopper' } })
    fireEvent.click(screen.getByRole('button', { name: 'Send til Jarvis' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('titel kraeves')
    // Formen står stadig med teksten i — man skal ikke skrive forfra.
    expect(screen.getByLabelText('Hvad gik galt?')).toHaveValue('Streamen stopper')
  })

  it('sender ikke to gange når et kald er i gang', async () => {
    // Uden guarden ville et dobbeltklik oprette TO poster i indbakken for
    // samme fejl. `rapporterBug` har ingen idempotens-nøgle, og `apiFetch`
    // gentager ikke et POST — men det gør et dobbeltklik. Guarden har to lag:
    // `disabled` på knappen og `if (!t || sender) return` i handleren.
    let slip: (v: { id: string }) => void = () => {}
    rb.mockReturnValue(new Promise((res) => { slip = res }))
    render(<BugRapport config={cfg} onClose={() => {}} />)
    fireEvent.change(screen.getByLabelText('Hvad gik galt?'), { target: { value: 'Streamen stopper' } })
    const knap = screen.getByRole('button', { name: 'Send til Jarvis' })
    fireEvent.click(knap)
    fireEvent.click(knap)
    expect(rb).toHaveBeenCalledTimes(1)
    // Knappen er låst imens kaldet kører — man kan se at den arbejder.
    expect(screen.getByRole('button', { name: 'Sender …' })).toBeDisabled()
    slip({ id: 'inbox-1' })
    expect(await screen.findByRole('status')).toHaveTextContent(/indbakken/i)
  })

  it('siger til når der ikke er nogen server at sende til', async () => {
    // `config` er valgfri i props (App sender `cfg`, som kan være undefined før
    // indstillingerne er læst). Uden denne gren ville kaldet gå af sted med
    // `undefined` og fejle som en typefejl i stedet for en besked til brugeren.
    render(<BugRapport onClose={() => {}} />)
    fireEvent.change(screen.getByLabelText('Hvad gik galt?'), { target: { value: 'x' } })
    fireEvent.click(screen.getByRole('button', { name: 'Send til Jarvis' }))
    expect(await screen.findByRole('alert')).toHaveTextContent(/ingen forbindelse/i)
    expect(rb).not.toHaveBeenCalled()
  })

  it('lukker via Luk-knappen i bekræftelsen', async () => {
    rb.mockResolvedValue({ id: 'inbox-1' })
    const luk = vi.fn()
    render(<BugRapport config={cfg} onClose={luk} />)
    fireEvent.change(screen.getByLabelText('Hvad gik galt?'), { target: { value: 'x' } })
    fireEvent.click(screen.getByRole('button', { name: 'Send til Jarvis' }))
    fireEvent.click(await screen.findByRole('button', { name: 'Luk' }))
    expect(luk).toHaveBeenCalledOnce()
  })
})
