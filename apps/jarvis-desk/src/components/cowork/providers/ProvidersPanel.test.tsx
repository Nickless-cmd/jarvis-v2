import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ProvidersPanel } from './ProvidersPanel'
import * as api from '../../../lib/cheapLaneApi'

/**
 * Det der kan gå galt uden at nogen ser det:
 *  1. «Fjern» kører uden at nogen har sagt ja
 *  2. nøglen bliver stående i formularen eller havner i en log
 *  3. «flyt lane» og «slå fra» bytter plads — de gør ikke det samme
 */
const config = { apiBaseUrl: 'http://x', authToken: 't' }

beforeEach(() => {
  vi.restoreAllMocks()
  vi.spyOn(api, 'getRegistret').mockResolvedValue({
    udbydere: [
      { provider: 'zai', auth_mode: 'api_key', auth_profile: 'default', base_url: 'https://zai/v1',
        enabled: true, credentials_ready: true, model_count: 2, enabled_model_count: 1 },
      { provider: 'doed', auth_mode: 'api_key', auth_profile: 'default',
        enabled: false, credentials_ready: false, model_count: 1, enabled_model_count: 0 },
    ],
    modeller: [
      { provider: 'zai', model: 'glm-4', lane: 'cheap', enabled: true },
      { provider: 'zai', model: 'glm-x', lane: 'cheap', enabled: false, disabled_reason: 'udgået' },
      { provider: 'doed', model: 'm1', lane: 'local', enabled: false },
    ],
    lanes: { cheap: { i_alt: 2, aktive: 1 }, local: { i_alt: 1, aktive: 0 } },
    opsummering: { udbydere: 2, modeller: 3, aktive_modeller: 1 },
  })
  vi.spyOn(api, 'getUdbyderHelbred').mockResolvedValue({
    providers: [{ provider: 'zai', ok: false, latency_ms: 0 }],
  })
  vi.spyOn(api, 'getBackups').mockResolvedValue({
    backups: [{ navn: 'provider_router-20260916T150000_000000Z.json', tid: '2026-09-16T15:00:00Z', bytes: 4096 }],
  })
  vi.spyOn(api, 'getHistorik').mockResolvedValue({
    udbydere: [{
      provider: 'zai', model: 'glm-4', kald: 40, ok: 10, fejl: 30, succesrate: 0.25,
      latens_p50_ms: 900, latens_p95_ms: 3000, pris_usd: 0, fejlkoder: [],
    }],
  })
})

describe('ProvidersPanel', () => {
  it('bruger de fælles fanestile i stedet for browserens standardknapper', async () => {
    render(<ProvidersPanel config={config} />)
    await waitFor(() => expect(screen.getByRole('button', { name: /Udbydere \(2\)/ })).toBeInTheDocument())
    expect(screen.getByRole('button', { name: /Udbydere \(2\)/ })).toHaveClass('mc-tab', 'active')
  })

  it('viser HELE registret, ikke de første otte', async () => {
    render(<ProvidersPanel config={config} />)
    await waitFor(() => expect(screen.getByRole('button', { name: /Udbydere \(2\)/ })).toBeInTheDocument())
    expect(screen.getByRole('button', { name: /Modeller \(3\)/ })).toBeInTheDocument()
    expect(screen.getByText('zai')).toBeInTheDocument()
    expect(screen.getByText('doed')).toBeInTheDocument()
  })

  it('brugen står ved siden af knappen, så «slå fra» ikke er et blindt valg', async () => {
    render(<ProvidersPanel config={config} />)
    await waitFor(() => expect(screen.getByText('40 (30 fejl)')).toBeInTheDocument())
  })

  it('«Fjern» spørger FØRST — og kalder intet før man siger ja', async () => {
    const fjern = vi.spyOn(api, 'fjernUdbyder').mockResolvedValue({ status: 'ok' })
    const bruger = userEvent.setup()
    render(<ProvidersPanel config={config} />)
    await waitFor(() => expect(screen.getAllByRole('button', { name: 'Fjern' })[0]).toBeInTheDocument())

    await bruger.click(screen.getAllByRole('button', { name: 'Fjern' })[0]!)
    expect(fjern).not.toHaveBeenCalled()
    expect(screen.getByText(/Nøglen bliver liggende/)).toBeInTheDocument()

    await bruger.click(screen.getByRole('button', { name: 'Fortryd' }))
    expect(fjern).not.toHaveBeenCalled()
  })

  it('bekræftet fjernelse rammer den rigtige udbyder', async () => {
    const fjern = vi.spyOn(api, 'fjernUdbyder').mockResolvedValue({ status: 'ok' })
    const bruger = userEvent.setup()
    render(<ProvidersPanel config={config} />)
    await waitFor(() => expect(screen.getAllByRole('button', { name: 'Fjern' })[0]).toBeInTheDocument())
    await bruger.click(screen.getAllByRole('button', { name: 'Fjern' })[0]!)
    await bruger.click(screen.getByRole('button', { name: 'Ja, gør det' }))
    expect(fjern).toHaveBeenCalledWith(config, 'zai')
  })

  it('lane-skift er en FLYTNING, ikke en slukning', async () => {
    const lane = vi.spyOn(api, 'saetLane').mockResolvedValue({ status: 'ok', fra: 'cheap', til: 'local' })
    const slaaFra = vi.spyOn(api, 'saetModel').mockResolvedValue({ status: 'ok' })
    const bruger = userEvent.setup()
    render(<ProvidersPanel config={config} />)
    await waitFor(() => expect(screen.getByRole('button', { name: /Modeller/ })).toBeInTheDocument())
    await bruger.click(screen.getByRole('button', { name: /Modeller/ }))
    await bruger.selectOptions(screen.getByLabelText('Lane for glm-4'), 'coding')
    expect(lane).toHaveBeenCalledWith(config, 'zai', 'glm-4', 'coding')
    expect(slaaFra).not.toHaveBeenCalled()
  })

  it('nøglen ryddes efter tilføjelse og står i et password-felt', async () => {
    const tilfoej = vi.spyOn(api, 'tilfoejUdbyder').mockResolvedValue({ status: 'ok', noegle_gemt: true })
    const bruger = userEvent.setup()
    render(<ProvidersPanel config={config} />)
    await waitFor(() => expect(screen.getByRole('button', { name: /^Tilføj$/ })).toBeInTheDocument())
    await bruger.click(screen.getByRole('button', { name: /^Tilføj$/ }))   // fanen

    const noegle = screen.getByLabelText(/Nøgle/) as HTMLInputElement
    expect(noegle.type).toBe('password')          // ikke synlig paa skaermen
    await bruger.type(screen.getByLabelText('Udbyder'), 'groq')
    await bruger.type(screen.getByLabelText('Model'), 'llama-3.3')
    await bruger.type(noegle, 'hemmelig')
    await bruger.click(screen.getByRole('button', { name: 'Tilføj udbyder' }))

    await waitFor(() => expect(tilfoej).toHaveBeenCalled())
    expect(tilfoej.mock.calls[0]![1]!.api_key).toBe('hemmelig')
    // Feltet ryddes med det samme — en noegle skal ikke blive staaende i en formular.
    await waitFor(() => expect((screen.getByLabelText(/Nøgle/) as HTMLInputElement).value).toBe(''))
  })

  it('en kilde der fejler tømmer ikke de andre', async () => {
    vi.spyOn(api, 'getBackups').mockRejectedValue(new Error('nede'))
    render(<ProvidersPanel config={config} />)
    await waitFor(() => expect(screen.getByText('1 af 4 kilder svarede ikke')).toBeInTheDocument())
    expect(screen.getByText('zai')).toBeInTheDocument()
  })
})
