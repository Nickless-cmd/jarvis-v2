import { describe, expect, it, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'

const getAgentArbejde = vi.fn()
vi.mock('../../lib/coworkApi', () => ({ getAgentArbejde: (...a: unknown[]) => getAgentArbejde(...a) }))

import { AgentWork } from './AgentWork'

const cfg = { apiBaseUrl: 'http://x', authToken: 't' }
const kørsel = (o: Record<string, unknown> = {}) => ({
  run_id: 'r1', agent_id: 'a1', role: 'researcher', kind: 'subagent',
  goal: 'find kilder til netværksfejlen', status: 'completed',
  execution_mode: 'solo-task', model: 'm', input_summary: 'ind',
  output_summary: 'Fandt tre kilder', started_at: '', finished_at: '',
  tokens: 1500, cost_usd: 0.0123, ...o,
})

describe('AgentWork', () => {
  beforeEach(() => { getAgentArbejde.mockReset() })

  it('viser rolle, mål, udfald og pris — ikke skjult magi', async () => {
    getAgentArbejde.mockResolvedValue({ runs: [kørsel()], antal: 1 })
    render(<AgentWork config={cfg} />)
    expect(await screen.findByText('researcher')).toBeTruthy()
    expect(screen.getByText(/find kilder til netværksfejlen/)).toBeTruthy()
    expect(screen.getByText(/Fandt tre kilder/)).toBeTruthy()
    expect(screen.getByText(/1.5k tokens · \$0.012/)).toBeTruthy()
  })

  it('siger «uden rolle» frem for at digte en titel', async () => {
    getAgentArbejde.mockResolvedValue({ runs: [kørsel({ role: '' })], antal: 1 })
    render(<AgentWork config={cfg} />)
    expect(await screen.findByText('uden rolle')).toBeTruthy()
  })

  it('markerer en fejlet kørsel', async () => {
    getAgentArbejde.mockResolvedValue({ runs: [kørsel({ status: 'failed' })], antal: 1 })
    const { container } = render(<AgentWork config={cfg} />)
    await screen.findByText('researcher')
    expect(container.querySelector('.aw-kort.st-failed')).toBeTruthy()
  })

  it('siger til når intet har kørt', async () => {
    getAgentArbejde.mockResolvedValue({ runs: [], antal: 0 })
    render(<AgentWork config={cfg} />)
    expect(await screen.findByText(/Ingen subagenter har kørt/)).toBeTruthy()
  })

  it('siger til når kaldet fejler', async () => {
    getAgentArbejde.mockImplementation(() => Promise.reject(new Error('nede')))
    render(<AgentWork config={cfg} />)
    expect(await screen.findByText(/Kunne ikke hente agent-arbejdet/)).toBeTruthy()
  })
})
