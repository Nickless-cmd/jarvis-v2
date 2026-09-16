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
