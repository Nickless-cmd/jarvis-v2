/**
 * Balanceren: HVORFOR et slot ikke bliver valgt.
 *
 * Bjørn 16/9-2026: «jeg ander intet om hvordan cheap lane eller
 * load_balanceren klarer sig». En vægt på 0 uden en grund er præcis den slags
 * tal han ikke kan bruge til noget — det er en oplysning om at noget er galt,
 * uden at sige hvad.
 *
 * Derfor er rækkefølgen en del af kravet: hårde afvisninger (køling, slået
 * fra, breaker) står FØR de bløde faktorer (succesrate, latens, hovedrum).
 * Er der en hård afvisning, er de bløde faktorer uden betydning — og at vise
 * dem ligeværdigt ville invitere til at rette på det forkerte.
 *
 * Simuleringen er en LÆSNING. Den skal sige det selv, for en knap der hedder
 * «simulér» ved siden af knapper der pauser og nulstiller, kan ikke bære
 * tvivlen.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { CheapLaneBalancer } from './CheapLaneBalancer'
import type { BalancerSlot } from '../../../lib/cheapLaneApi'

const køling: BalancerSlot = {
  slot_id: 'groq::llama::primary', provider: 'groq', model: 'llama',
  auth_profile: 'primary', egress: 'direct', status: 'cooldown',
  weight: 0, success_rate: 0.2, rpm_used: 3, rpm_limit: 10,
  daily_used: 40, daily_limit: 100, headroom_pct: 0.6,
  breaker_level: 2, consecutive_failures: 4,
  cooldown_until: '2026-09-18T12:00:00Z', cooldown_reason: 'for mange fejl',
}
const rask: BalancerSlot = {
  slot_id: 'kilo::mixtral::primary', provider: 'kilo', model: 'mixtral',
  auth_profile: 'primary', egress: 'vpn', status: 'healthy',
  weight: 0.8, success_rate: 0.98, rpm_used: 1, rpm_limit: 30,
  headroom_pct: 0.97, breaker_level: 0, consecutive_failures: 0,
}

let udfoer: ReturnType<typeof vi.fn>
let simuler: ReturnType<typeof vi.fn>

function opsæt(slots = [køling, rask]) {
  udfoer = vi.fn().mockResolvedValue({ status: 'ok', revision: 'rev-7' })
  simuler = vi.fn().mockResolvedValue({
    candidates: [{ provider: 'kilo', model: 'mixtral', slot_id: rask.slot_id, weight: 0.8, eligible: true }],
    chosen: rask.slot_id,
  })
  render(<CheapLaneBalancer slots={slots} udfoer={udfoer} simuler={simuler} />)
  return { bruger: userEvent.setup() }
}

beforeEach(() => { vi.restoreAllMocks() })

describe('CheapLaneBalancer', () => {
  it('forklarer vægt 0 med den HÅRDE grund — ikke med de bløde faktorer', async () => {
    const { bruger } = opsæt()
    await bruger.click(screen.getByRole('button', { name: /groq.*llama/i }))
    const forklaring = screen.getByRole('region', { name: /forklaring/i })
    expect(forklaring.textContent).toContain('Køling aktiv')
    expect(forklaring.textContent).toContain('for mange fejl')
    // Den hårde grund står FØR de bløde: står succesraten først, retter man
    // på det forkerte.
    const t = forklaring.textContent ?? ''
    expect(t.indexOf('Køling aktiv')).toBeLessThan(t.indexOf('Succesrate'))
  })

  it('et rask slot forklares med de bløde faktorer', async () => {
    const { bruger } = opsæt()
    await bruger.click(screen.getByRole('button', { name: /kilo.*mixtral/i }))
    const forklaring = screen.getByRole('region', { name: /forklaring/i })
    expect(forklaring.textContent).toContain('Ingen hård afvisning')
    expect(forklaring.textContent).toContain('Succesrate')
  })

  it('simulering siger selv at den ikke sender noget', async () => {
    const { bruger } = opsæt()
    await bruger.click(screen.getByRole('button', { name: /simulér/i }))
    expect(screen.getByText(/der sendes intet provider-kald/i)).toBeTruthy()
    expect(udfoer).not.toHaveBeenCalled()
  })

  it('simuleringen viser hvem der ville blive valgt', async () => {
    const { bruger } = opsæt()
    await bruger.click(screen.getByRole('button', { name: /simulér/i }))
    // «mixtral» staar ogsaa i tabellen; svaret laeses dér hvor valget staar.
    const svar = await screen.findByText(/Ville vælge/)
    expect(svar.textContent).toContain('mixtral')
    expect(simuler).toHaveBeenCalled()
  })

  it('filtrerer på status', async () => {
    const { bruger } = opsæt()
    await bruger.selectOptions(screen.getByLabelText(/status/i), 'cooldown')
    expect(screen.getByRole('button', { name: /groq.*llama/i })).toBeTruthy()
    expect(screen.queryByRole('button', { name: /kilo.*mixtral/i })).toBeNull()
  })

  it('en udført handling viser revisionen fra serveren', async () => {
    const { bruger } = opsæt()
    await bruger.click(screen.getByRole('button', { name: /groq.*llama/i }))
    await bruger.click(screen.getByRole('button', { name: /^Frigiv køling/ }))
    expect(await screen.findByText(/rev-7/)).toBeTruthy()
    expect(udfoer).toHaveBeenCalledWith(expect.objectContaining({
      action: 'slot.release-cooldown', target: køling.slot_id,
    }))
  })
})
