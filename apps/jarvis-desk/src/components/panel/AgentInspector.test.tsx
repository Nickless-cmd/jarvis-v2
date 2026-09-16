import { beforeEach, describe, expect, it, vi } from 'vitest'
import { act, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { AgentInspector } from './AgentInspector'
import * as api from '../../lib/agentPoolApi'

const config = { apiBaseUrl: 'http://x', authToken: 't' }
const reference = {
  agentId: 'agent-1', role: 'researcher', goal: 'Find dokumentationen',
  status: 'active', dispatchToolUseId: 'tool-1',
}
const detail: api.AgentDetail = {
  agent_id: 'agent-1', role: 'researcher', goal: 'Find dokumentationen',
  status: 'active', model: 'deepseek-v4.1', tokens_burned: 1200,
  runs: [{ run_id: 'run-1', status: 'active', output_summary: 'Tre kilder fundet' }],
  messages: [{ message_id: 'message-1', role: 'assistant', content: 'Jeg undersøger det.', direction: 'ud' }],
}

beforeEach(() => {
  vi.restoreAllMocks()
  vi.spyOn(api, 'getAgentDetalje').mockResolvedValue(detail)
})

describe('AgentInspector', () => {
  it('henter først detaljen når inspectoren monteres', async () => {
    expect(api.getAgentDetalje).not.toHaveBeenCalled()
    render(<AgentInspector config={config} agent={reference} canMessage />)
    await waitFor(() => expect(api.getAgentDetalje).toHaveBeenCalledWith(config, 'agent-1'))
    expect(await screen.findByText('Tre kilder fundet')).toBeInTheDocument()
    expect(screen.getByText('Jeg undersøger det.')).toBeInTheDocument()
  })

  it('viser ikke composer når fladen er read-only', async () => {
    render(<AgentInspector config={config} agent={reference} canMessage={false} />)
    await screen.findByText('Tre kilder fundet')
    expect(screen.queryByRole('textbox', { name: 'Besked til agenten' })).not.toBeInTheDocument()
  })

  it('bevarer kladden og viser fejlen når afsendelse fejler', async () => {
    vi.spyOn(api, 'sendTilAgent').mockRejectedValue(new Error('forbindelsen faldt'))
    const user = userEvent.setup()
    render(<AgentInspector config={config} agent={reference} canMessage />)
    const input = await screen.findByRole('textbox', { name: 'Besked til agenten' })
    await user.type(input, 'Følg også linket')
    await user.click(screen.getByRole('button', { name: 'Send' }))
    expect(await screen.findByText('forbindelsen faldt')).toBeInTheDocument()
    expect(input).toHaveValue('Følg også linket')
  })

  it('rydder først kladden efter succes og genindlæser detaljen', async () => {
    vi.spyOn(api, 'sendTilAgent').mockResolvedValue({ status: 'ok' })
    const user = userEvent.setup()
    render(<AgentInspector config={config} agent={reference} canMessage />)
    const input = await screen.findByRole('textbox', { name: 'Besked til agenten' })
    await user.type(input, 'Fortsæt')
    await user.click(screen.getByRole('button', { name: 'Send' }))
    await waitFor(() => expect(api.sendTilAgent).toHaveBeenCalledWith(config, 'agent-1', 'Fortsæt'))
    await waitFor(() => expect(input).toHaveValue(''))
    expect(api.getAgentDetalje).toHaveBeenCalledTimes(2)
  })

  it('viser afsluttede agenter uden handlinger eller composer', async () => {
    vi.spyOn(api, 'getAgentDetalje').mockResolvedValue({ ...detail, status: 'completed' })
    render(<AgentInspector config={config} agent={reference} canMessage />)
    expect(await screen.findByText('Agenten er afsluttet og kan ikke modtage beskeder.')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Stop' })).not.toBeInTheDocument()
    expect(screen.queryByRole('textbox', { name: 'Besked til agenten' })).not.toBeInTheDocument()
  })

  it('poller kun mens en aktiv agent er synlig og monteret', async () => {
    vi.useFakeTimers()
    try {
      const { unmount } = render(<AgentInspector config={config} agent={reference} canMessage />)
      await act(async () => { await Promise.resolve() })
      expect(api.getAgentDetalje).toHaveBeenCalledTimes(1)
      await act(async () => { await vi.advanceTimersByTimeAsync(3000) })
      expect(api.getAgentDetalje).toHaveBeenCalledTimes(2)
      unmount()
      await act(async () => { await vi.advanceTimersByTimeAsync(3000) })
      expect(api.getAgentDetalje).toHaveBeenCalledTimes(2)
    } finally {
      vi.useRealTimers()
    }
  })
})

describe('AgentInspector — skift af agent og fejl', () => {
  it('viser ALDRIG den forrige agents data under den nyes id', async () => {
    const anden: api.AgentDetail = { ...detail, agent_id: 'agent-2', runs: [{ run_id: 'r2', status: 'completed', output_summary: 'Anden agents arbejde' }] }
    const hent = vi.spyOn(api, 'getAgentDetalje')
      .mockResolvedValueOnce(detail)
      .mockResolvedValueOnce(anden)

    const { rerender } = render(<AgentInspector config={config} agent={reference} canMessage />)
    expect(await screen.findByText('Tre kilder fundet')).toBeInTheDocument()

    rerender(<AgentInspector config={config} agent={{ ...reference, agentId: 'agent-2' }} canMessage />)
    // Tavlen skal vaere toem MED DET SAMME — ikke foerst naar svaret lander.
    expect(screen.queryByText('Tre kilder fundet')).not.toBeInTheDocument()
    expect(await screen.findByText('Anden agents arbejde')).toBeInTheDocument()
    expect(hent).toHaveBeenCalledWith(config, 'agent-2')
  })

  it('et SENT svar fra den forrige agent overskriver ikke den nye', async () => {
    let slipForrige: (v: api.AgentDetail) => void = () => {}
    vi.spyOn(api, 'getAgentDetalje')
      .mockImplementationOnce(() => new Promise((r) => { slipForrige = r }))
      .mockResolvedValueOnce({ ...detail, agent_id: 'agent-2', runs: [{ run_id: 'r2', status: 'completed', output_summary: 'Den NYE agent' }] })

    const { rerender } = render(<AgentInspector config={config} agent={reference} canMessage />)
    rerender(<AgentInspector config={config} agent={{ ...reference, agentId: 'agent-2' }} canMessage />)
    expect(await screen.findByText('Den NYE agent')).toBeInTheDocument()

    // Den gamle hentning lander FOERST nu — den skal ignoreres.
    await act(async () => { slipForrige(detail) })
    expect(screen.getByText('Den NYE agent')).toBeInTheDocument()
    expect(screen.queryByText('Tre kilder fundet')).not.toBeInTheDocument()
  })

  it('en fejlet FØRSTE hentning er ikke en blindgyde', async () => {
    const hent = vi.spyOn(api, 'getAgentDetalje')
      .mockRejectedValueOnce(new Error('agenten findes ikke længere'))
      .mockResolvedValueOnce(detail)
    render(<AgentInspector config={config} agent={reference} canMessage />)
    expect(await screen.findByText('agenten findes ikke længere')).toBeInTheDocument()
    // Uden detail poller ingenting — der SKAL være en vej tilbage.
    await userEvent.click(screen.getByRole('button', { name: 'Prøv igen' }))
    expect(await screen.findByText('Tre kilder fundet')).toBeInTheDocument()
    expect(hent).toHaveBeenCalledTimes(2)
  })
})

describe('AgentInspector — hvem må hvad', () => {
  it('read-only skjuler OGSÅ kontrol-knapperne, ikke kun composeren', async () => {
    render(<AgentInspector config={config} agent={reference} canMessage={false} />)
    await screen.findByText('Tre kilder fundet')
    // Stop og «Luk som udløbet» afbryder en kørsel. De er farligere end en
    // besked, og de var de eneste der IKKE var gated.
    for (const navn of ['Stop', 'Marker pauset', 'Genoptag', 'Luk som udløbet']) {
      expect(screen.queryByRole('button', { name: navn }), navn).not.toBeInTheDocument()
    }
  })

  it('ejeren har knapperne', async () => {
    render(<AgentInspector config={config} agent={reference} canMessage />)
    expect(await screen.findByRole('button', { name: 'Stop' })).toBeInTheDocument()
  })

  it('viser agentens fejl når der er en', async () => {
    vi.spyOn(api, 'getAgentDetalje').mockResolvedValue({ ...detail, last_error: 'udbyderen svarede 429' })
    render(<AgentInspector config={config} agent={reference} canMessage />)
    expect(await screen.findByText(/udbyderen svarede 429/)).toBeInTheDocument()
  })

  it('tokens viser «—» mens detaljen hentes — ikke 0', async () => {
    let slip: (v: api.AgentDetail) => void = () => {}
    vi.spyOn(api, 'getAgentDetalje').mockImplementation(() => new Promise((r) => { slip = r }))
    render(<AgentInspector config={config} agent={reference} canMessage />)
    expect(screen.getByText('—')).toBeInTheDocument()
    await act(async () => { slip({ ...detail, tokens_burned: 0 }) })
    // 0 ER ægte data når det først er hentet — kolonnen er NOT NULL DEFAULT 0.
    await waitFor(() => expect(screen.getByText('0')).toBeInTheDocument())
  })
})
