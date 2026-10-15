import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'

/**
 * Opret-sideopgave-boksen (Bjørn 15/10-2026: «jeg mangler et sted i desk jeg
 * kan oprette side-opgaver selv»).
 *
 * Det der er værd at holde fast her er ikke at boksen kan åbnes — det er at et
 * manglende felt ikke bliver en rundtur til serveren, og at en FEJL fra
 * serveren ikke lukker boksen. En lukket boks efter et afvist kald ville se ud
 * som en succes.
 */
const opretSideTask = vi.fn()
vi.mock('../lib/sideTasksApi', () => ({
  opretSideTask: (...a: unknown[]) => opretSideTask(...a),
}))

import { SideOpgaveDialog } from './SideOpgaveDialog'

const cfg = { apiBaseUrl: 'http://x', authToken: 't' }

function felt() {
  return {
    titel: screen.getByLabelText('Titel') as HTMLInputElement,
    beskrivelse: screen.getByLabelText('Beskrivelse') as HTMLTextAreaElement,
  }
}

describe('SideOpgaveDialog', () => {
  beforeEach(() => { opretSideTask.mockReset().mockResolvedValue('side-abc123') })

  it('forudfylder beskrivelsen med teksten efter /side', () => {
    render(<SideOpgaveDialog config={cfg} startTekst="ret CI-badgen" onClose={() => {}} />)
    expect(felt().beskrivelse.value).toBe('ret CI-badgen')
  })

  it('uden titel eller beskrivelse: siger det, og kalder IKKE serveren', async () => {
    render(<SideOpgaveDialog config={cfg} startTekst="" onClose={() => {}} />)
    fireEvent.click(screen.getByRole('button', { name: 'Opret sideopgave' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Både titel og beskrivelse')
    expect(opretSideTask).not.toHaveBeenCalled()
  })

  it('kun mellemrum tæller ikke som udfyldt', async () => {
    render(<SideOpgaveDialog config={cfg} startTekst="" onClose={() => {}} />)
    fireEvent.change(felt().titel, { target: { value: '   ' } })
    fireEvent.change(felt().beskrivelse, { target: { value: '  ' } })
    fireEvent.click(screen.getByRole('button', { name: 'Opret sideopgave' }))
    expect(await screen.findByRole('alert')).toBeInTheDocument()
    expect(opretSideTask).not.toHaveBeenCalled()
  })

  it('opretter med trimmede felter og lukker med den nye id', async () => {
    const onClose = vi.fn()
    const onOprettet = vi.fn()
    render(<SideOpgaveDialog config={cfg} startTekst="" onClose={onClose} onOprettet={onOprettet} />)
    fireEvent.change(felt().titel, { target: { value: '  Ret badgen  ' } })
    fireEvent.change(felt().beskrivelse, { target: { value: '  README viser et gammelt workflow  ' } })
    fireEvent.click(screen.getByRole('button', { name: 'Opret sideopgave' }))
    await waitFor(() => expect(opretSideTask).toHaveBeenCalledWith(
      cfg, 'Ret badgen', 'README viser et gammelt workflow',
    ))
    await waitFor(() => expect(onOprettet).toHaveBeenCalledWith('side-abc123'))
    expect(onClose).toHaveBeenCalled()
  })

  it('en afvist oprettelse LUKKER IKKE boksen — fejlen skal kunne læses', async () => {
    const onClose = vi.fn()
    opretSideTask.mockRejectedValue(new Error('titel og beskrivelse er påkrævet'))
    render(<SideOpgaveDialog config={cfg} startTekst="noget" onClose={onClose} />)
    fireEvent.change(felt().titel, { target: { value: 'A' } })
    fireEvent.click(screen.getByRole('button', { name: 'Opret sideopgave' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('titel og beskrivelse er påkrævet')
    expect(onClose).not.toHaveBeenCalled()
  })

  it('Annullér lukker uden at kalde serveren', () => {
    const onClose = vi.fn()
    render(<SideOpgaveDialog config={cfg} startTekst="x" onClose={onClose} />)
    fireEvent.click(screen.getByRole('button', { name: 'Annullér' }))
    expect(onClose).toHaveBeenCalled()
    expect(opretSideTask).not.toHaveBeenCalled()
  })
})
