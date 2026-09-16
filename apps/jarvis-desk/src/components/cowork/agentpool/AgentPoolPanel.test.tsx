import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { AgentPoolPanel } from './AgentPoolPanel'
import * as api from '../../../lib/agentPoolApi'

/**
 * De tre ting der kan gå galt uden at nogen ser det:
 *  1. listen viser loftet som om det var antallet
 *  2. detaljen hentes for alle på forhånd (den tunge vej)
 *  3. «pause» læses som «stop» — den sætter kun databasestatus
 */
const config = { apiBaseUrl: 'http://x', authToken: 't' }

const agent = {
  agent_id: 'agent-1', role: 'researcher', goal: 'find noget om broen',
  status: 'active', model: 'qwen3:4b', koersler: 2, beskeder: 3,
  pris_usd: 0.0123, tokens: 1500, varighed_s: 95, er_aktiv: true,
  created_at: '2026-09-16T10:00:00Z',
}

beforeEach(() => {
  vi.restoreAllMocks()
  vi.spyOn(api, 'getPoolListe').mockResolvedValue({
    agenter: [agent], vist: 1, i_alt: 306, offset: 0, limit: 50,
  })
  vi.spyOn(api, 'getPoolOpsummering').mockResolvedValue({
    agenter_i_alt: 306, aktive_nu: 1,
    pr_status: { completed: 271, cancelled: 17, expired: 17, active: 1 },
    pr_rolle: [{ rolle: 'researcher', antal: 149 }],
    vindue: { koersler: 20, fejlede: 4, fejlrate: 0.2, pris_usd: 0.42, tokens: 90000 },
    raad: { completed: 498 }, graenser: { samtidige: 12, dybde: 4 },
  })
  vi.spyOn(api, 'getPoolArbejde').mockResolvedValue({
    koersler: [{
      run_id: 'r1', role: 'researcher', model: 'qwen3:4b', status: 'failed',
      failure_reason: 'timeout mod udbyder', started_at: '2026-09-16T12:00:00Z', varighed_s: 42,
    }],
  })
  vi.spyOn(api, 'getAgentDetalje').mockResolvedValue({
    ...agent,
    runs: [{ run_id: 'r1', status: 'completed', model: 'qwen3:4b', input_tokens: 1000, output_tokens: 500, output_summary: 'fandt tre kilder' }],
    messages: [{ message_id: 'm1', role: 'user', content: 'kom i gang', created_at: '2026-09-16T10:01:00Z' }],
  })
})

describe('AgentPoolPanel', () => {
  it('oversigten viser puljen og grænserne', async () => {
    render(<AgentPoolPanel config={config} />)
    await waitFor(() => expect(screen.getByText('306')).toBeInTheDocument())
    expect(screen.getByText('1 aktive nu')).toBeInTheDocument()
    expect(screen.getByText('20 %')).toBeInTheDocument()                 // fejlrate
    expect(screen.getByText('samtidige · dybde 4')).toBeInTheDocument()
  })

  it('listen siger hvor mange der ER, ikke hvor mange der vises', async () => {
    const bruger = userEvent.setup()
    render(<AgentPoolPanel config={config} />)
    await waitFor(() => expect(screen.getByRole('button', { name: /Agenter \(306\)/ })).toBeInTheDocument())
    await bruger.click(screen.getByRole('button', { name: /Agenter \(306\)/ }))
    expect(screen.getByText('Viser 1 af 306.')).toBeInTheDocument()
  })

  it('detaljen hentes FØRST når en agent åbnes', async () => {
    const bruger = userEvent.setup()
    render(<AgentPoolPanel config={config} />)
    await waitFor(() => expect(screen.getByRole('button', { name: /Agenter/ })).toBeInTheDocument())
    // Listen er hentet — men ikke detaljen. Det er hele pointen med den lette vej.
    expect(api.getAgentDetalje).not.toHaveBeenCalled()

    await bruger.click(screen.getByRole('button', { name: /Agenter/ }))
    await bruger.click(screen.getByText('find noget om broen'))
    await waitFor(() => expect(api.getAgentDetalje).toHaveBeenCalledWith(config, 'agent-1'))
    expect(await screen.findByText('fandt tre kilder')).toBeInTheDocument()
  })

  it('«marker pauset» siger hvad den GØR — den stopper ikke en kørende tråd', async () => {
    const h = vi.spyOn(api, 'agentHandling').mockResolvedValue({ status: 'ok' })
    const bruger = userEvent.setup()
    render(<AgentPoolPanel config={config} />)
    await waitFor(() => expect(screen.getByRole('button', { name: /Agenter/ })).toBeInTheDocument())
    await bruger.click(screen.getByRole('button', { name: /Agenter/ }))
    await bruger.click(screen.getByText('find noget om broen'))
    await bruger.click(await screen.findByRole('button', { name: 'Marker pauset' }))
    expect(h).toHaveBeenCalledWith(config, 'agent-1', 'suspend')
    // Ordvalget er testet med vilje: «Pause» alene ville love for meget.
    expect(screen.getByRole('button', { name: 'Stop' })).toBeInTheDocument()
  })

  it('en agent der ikke er aktiv har intet at stoppe', async () => {
    vi.spyOn(api, 'getPoolListe').mockResolvedValue({
      agenter: [{ ...agent, status: 'completed', er_aktiv: false }], vist: 1, i_alt: 1,
    })
    vi.spyOn(api, 'getAgentDetalje').mockResolvedValue({
      ...agent, status: 'completed', er_aktiv: false, runs: [], messages: [],
    })
    const bruger = userEvent.setup()
    render(<AgentPoolPanel config={config} />)
    await waitFor(() => expect(screen.getByRole('button', { name: /Agenter/ })).toBeInTheDocument())
    await bruger.click(screen.getByRole('button', { name: /Agenter/ }))
    await bruger.click(screen.getByText('find noget om broen'))
    expect(await screen.findByText('Agenten er afsluttet og kan ikke modtage beskeder.')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Stop' })).not.toBeInTheDocument()
  })

  it('en kilde der fejler tømmer ikke de andre', async () => {
    vi.spyOn(api, 'getPoolArbejde').mockRejectedValue(new Error('nede'))
    render(<AgentPoolPanel config={config} />)
    await waitFor(() => expect(screen.getByText('1 af 3 kilder svarede ikke')).toBeInTheDocument())
    expect(screen.getByText('306')).toBeInTheDocument()
  })
})
