/**
 * Udbyder-administrationen — fladen hvor man kan komme til at gøre skade.
 *
 * Tre ting adskiller knapperne, og de skal kunne skelnes UDEN at læse
 * dokumentationen, fordi de rammer hver sit lag og har hver sin varighed:
 *
 *   Pause      balancerens egen tilstand — væk til næste opbygning
 *   Deaktivér  registret — overlever en genstart
 *   Fjern      registret, uigenkaldeligt — bag en bekræftelse
 *
 * Og fladen må aldrig vise andet end cheap lane. Den almindelige
 * udbyder-side findes stadig; blandes de to, kan man komme til at slukke for
 * Bjørns synlige lane fra et panel der hedder «cheap».
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { CheapLaneProviders } from './CheapLaneProviders'
import type { Registret } from '../../../lib/cheapLaneApi'

const registret: Registret = {
  udbydere: [
    { provider: 'groq', enabled: true, model_count: 2, enabled_model_count: 2 },
    { provider: 'anthropic', enabled: true, model_count: 1, enabled_model_count: 1 },
  ],
  modeller: [
    { provider: 'groq', model: 'llama-3.3-70b', lane: 'cheap', enabled: true },
    { provider: 'groq', model: 'mixtral', lane: 'cheap', enabled: false },
    { provider: 'anthropic', model: 'claude-visible', lane: 'visible', enabled: true },
  ],
}

let kontrol: ReturnType<typeof vi.fn>

function opsæt() {
  kontrol = vi.fn().mockResolvedValue({ status: 'ok', revision: 'r2' })
  render(<CheapLaneProviders registret={registret} udfoer={kontrol} />)
  return { bruger: userEvent.setup() }
}

beforeEach(() => { vi.restoreAllMocks() })

describe('CheapLaneProviders', () => {
  it('viser KUN cheap lane — den synlige lane hører ikke til her', () => {
    opsæt()
    expect(screen.getByText('llama-3.3-70b')).toBeTruthy()
    expect(screen.queryByText('claude-visible')).toBeNull()
  })

  it('søgning filtrerer på udbyder og model', async () => {
    const { bruger } = opsæt()
    await bruger.type(screen.getByLabelText(/søg/i), 'mixtral')
    expect(screen.getByText('mixtral')).toBeTruthy()
    expect(screen.queryByText('llama-3.3-70b')).toBeNull()
  })

  it('pause og deaktivér er IKKE det samme — og siger det', async () => {
    const { bruger } = opsæt()
    await bruger.click(screen.getAllByRole('button', { name: /^Pause/ })[0]!)
    expect(kontrol).toHaveBeenCalledWith(expect.objectContaining({ action: 'model.pause' }))
    const kald = kontrol.mock.calls[0]![0]
    expect(kald.action).not.toContain('deactivate')
  })

  it('en vedvarende handling kræver en grund — serveren afviser den ellers', async () => {
    const { bruger } = opsæt()
    await bruger.click(screen.getAllByRole('button', { name: /^Deaktivér/ })[0]!)
    // Ingen grund skrevet endnu → intet kald.
    expect(kontrol).not.toHaveBeenCalled()
    await bruger.type(screen.getByLabelText(/grund/i), 'for dyr')
    await bruger.click(screen.getByRole('button', { name: 'Bekræft' }))
    expect(kontrol).toHaveBeenCalledWith(expect.objectContaining({
      action: 'model.deactivate', reason: 'for dyr',
    }))
  })

  it('fjern kræver bekræftelse og siger hvad der sker med nøglen', async () => {
    const { bruger } = opsæt()
    await bruger.click(screen.getAllByRole('button', { name: /^Fjern/ })[0]!)
    const dialog = screen.getByRole('dialog')
    expect(dialog.textContent).toContain('Legitimationen bevares')
    expect(kontrol).not.toHaveBeenCalled()
  })

  it('en serverfejl bliver stående — den må ikke forsvinde af sig selv', async () => {
    const { bruger } = opsæt()
    kontrol.mockRejectedValueOnce(new Error('409 revisionen er ændret'))
    await bruger.click(screen.getAllByRole('button', { name: /^Pause/ })[0]!)
    expect(await screen.findByText(/409 revisionen er ændret/)).toBeTruthy()
  })

  it('handlingen er låst mens den er undervejs — ét klik, ét kald', async () => {
    const { bruger } = opsæt()
    let løs: (v: unknown) => void = () => {}
    kontrol.mockReturnValueOnce(new Promise((r) => { løs = r }))
    const knap = screen.getAllByRole('button', { name: /^Pause/ })[0]!
    await bruger.click(knap)
    expect(knap).toBeDisabled()
    await bruger.click(knap)
    expect(kontrol).toHaveBeenCalledTimes(1)
    løs({ status: 'ok' })
  })
})
