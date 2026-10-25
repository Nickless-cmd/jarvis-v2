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
const opdaterSideTask = vi.fn()
vi.mock('../lib/sideTasksApi', () => ({
  opretSideTask: (...a: unknown[]) => opretSideTask(...a),
  opdaterSideTask: (...a: unknown[]) => opdaterSideTask(...a),
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
      cfg, 'Ret badgen', 'README viser et gammelt workflow', '',
      // Reglerne sendes ALTID med (25/10-2026): `none` er default, så en
      // oprettelse uden valg er den samme anmodning som før.
      { autonomy_mode: 'none', max_minutes: 20, max_tool_calls: 12 },
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

/**
 * Redigering (25/10-2026). Bjørn: «jeg har ikke mulighed for at redigere en
 * eksisterende opgave eller saette regler eller autonomi». Boksen er den samme
 * som ved oprettelse — det er KALDET der er et andet, og det er praecis hvad
 * disse proever.
 */
describe('SideOpgaveDialog — redigering', () => {
  const opgave = {
    side_task_id: 'side-abc123',
    title: 'Ret badgen',
    prompt: 'README viser et gammelt workflow',
    tldr: '',
    status: 'pending' as const,
    session_id: 'chat-1',
    created_at: '2026-10-25T12:00:00+00:00',
    autonomy_mode: 'none' as const,
    max_minutes: 20,
    max_tool_calls: 12,
  }

  beforeEach(() => {
    opretSideTask.mockReset().mockResolvedValue('side-ny')
    opdaterSideTask.mockReset().mockResolvedValue(undefined)
  })

  it('forudfylder felterne fra opgaven', () => {
    render(<SideOpgaveDialog config={cfg} opgave={opgave} onClose={() => {}} />)
    expect((screen.getByLabelText('Titel') as HTMLInputElement).value).toBe('Ret badgen')
    expect((screen.getByLabelText('Beskrivelse') as HTMLTextAreaElement).value)
      .toBe('README viser et gammelt workflow')
    expect(screen.getByRole('heading')).toHaveTextContent('Redigér sideopgave')
  })

  it('gemmer via opdaterSideTask — og opretter IKKE en ny', async () => {
    const onClose = vi.fn()
    render(<SideOpgaveDialog config={cfg} opgave={opgave} onClose={onClose} />)
    fireEvent.change(screen.getByLabelText('Titel'), { target: { value: 'Ret CI-badgen' } })
    fireEvent.click(screen.getByRole('button', { name: 'Gem ændringer' }))
    await waitFor(() => expect(opdaterSideTask).toHaveBeenCalledWith(
      cfg, 'side-abc123',
      expect.objectContaining({ title: 'Ret CI-badgen' }),
    ))
    expect(opretSideTask).not.toHaveBeenCalled()
    await waitFor(() => expect(onClose).toHaveBeenCalled())
  })

  it('en afvist ændring LUKKER IKKE boksen — grunden skal kunne læses', async () => {
    const onClose = vi.fn()
    opdaterSideTask.mockRejectedValue(
      new Error('sideopgaven er i gang og kan ikke redigeres'),
    )
    render(<SideOpgaveDialog config={cfg} opgave={opgave} onClose={onClose} />)
    fireEvent.click(screen.getByRole('button', { name: 'Gem ændringer' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('i gang')
    expect(onClose).not.toHaveBeenCalled()
  })

  it('autonomi-valget sender modus og budget med', async () => {
    render(<SideOpgaveDialog config={cfg} opgave={opgave} onClose={() => {}} />)
    fireEvent.change(screen.getByLabelText('Autonomi'), { target: { value: 'inspect' } })
    fireEvent.click(screen.getByRole('button', { name: 'Gem ændringer' }))
    await waitFor(() => expect(opdaterSideTask).toHaveBeenCalledWith(
      cfg, 'side-abc123',
      expect.objectContaining({ autonomy_mode: 'inspect' }),
    ))
  })

  it('budget-felterne vises kun naar autonomi er slaaet til', () => {
    render(<SideOpgaveDialog config={cfg} opgave={opgave} onClose={() => {}} />)
    expect(screen.queryByLabelText('Minutter')).toBeNull()
    fireEvent.change(screen.getByLabelText('Autonomi'), { target: { value: 'local_write' } })
    expect(screen.getByLabelText('Minutter')).toBeInTheDocument()
    expect(screen.getByLabelText('Værktøjskald')).toBeInTheDocument()
  })
})
