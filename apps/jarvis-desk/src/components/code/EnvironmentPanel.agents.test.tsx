import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

vi.mock('../../lib/api', async (orig) => ({
  ...(await orig() as object),
  getGitStatus: vi.fn().mockResolvedValue(null),
}))

// Agent-listen kommer fra den LEVENDE projektion — ikke fra transkriptet.
const kontrakt = vi.fn()
vi.mock('../../lib/agentContractApi', () => ({
  getKontraktOverblik: (...a: unknown[]) => kontrakt(...a),
}))

import { EnvironmentPanel } from './EnvironmentPanel'

/**
 * Bjørn 8/9-2026: «agenter fra hans explore tool vises ikke i miljøfeltet».
 *
 * Listen navngav fire dispatch-værktøjer — hvoraf ét slet ikke findes — og
 * manglede `explore`, som er ordret «send a read-only research agent» og
 * kaldes hele tiden. «Underagenter» var derfor tom næsten altid.
 *
 * 11/11-2026 (Bjørn: «hvorfor vises de selv om de er færdig? og med status
 * kører?»): kilden blev flyttet. Transkriptet kan ikke vide om en agent kører
 * NU — `Task` svarer `queued` ved dispatch og er færdig som kald sekunder
 * senere. Målt: 41 Task-kald i én session bar alle "queued", så hver række
 * påstod «kører» resten af samtalen. Projektionen læser de levende tabeller.
 */
const rad = (id: string, goal: string, bucket = 'active', attention = false) => ({
  agent_id: id, assignment_id: `asg-${id}`, role: 'researcher', goal, bucket,
  attention, assignment_status: 'active', run_status: 'running',
})

const overblik = (rows: ReturnType<typeof rad>[]) => ({
  status: 'ok',
  capability: { enabled: true, reason: '', contract_version: 'agent-contract-v1' },
  agents: rows,
  counts: {
    active: rows.length, queued: 0, waiting: 0, blocked: 0,
    attention: rows.filter((r) => r.attention).length, open: 0,
  },
  groups: [],
  contract_version: 'agent-contract-v1',
})

const cfg = { apiBaseUrl: 'http://t', authToken: 't' }

const vis = (rows: ReturnType<typeof rad>[], onOpenAgent = vi.fn()) => {
  kontrakt.mockResolvedValue(overblik(rows))
  return {
    ...render(<EnvironmentPanel kind="workstation" root="/x" working config={cfg}
      evidence={{ agents: [], tools: [], sources: [] }} onOpenAgent={onOpenAgent} />),
    onOpenAgent,
  }
}

beforeEach(() => { kontrakt.mockReset() })

describe('underagenter i miljø-feltet', () => {
  it('viser en agent der kører lige nu — fra projektionen', async () => {
    const { onOpenAgent } = vis([rad('agent-1', 'hvor håndteres token-fornyelse')])
    expect(await screen.findByText('Underagenter')).toBeInTheDocument()
    expect(screen.getByText('hvor håndteres token-fornyelse')).toBeInTheDocument()
    expect(screen.getByText('kører')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: /researcher/ }))
    expect(onOpenAgent).toHaveBeenCalledWith(expect.objectContaining({ agentId: 'agent-1' }))
  })

  it('en FROSSET koe-status i transkriptet giver ikke «kører»', async () => {
    // Selve fejlen Bjørn så 11/11-2026. Transkriptet bærer 41 rækker med
    // `assignment_status: "queued"` fra Task-dispatch; `queued` står i AKTIVE,
    // så de stod som kørende længe efter de var færdige. Projektionen er tom
    // her — altså kører der ingenting, og feltet skal være tomt.
    kontrakt.mockResolvedValue(overblik([]))
    render(<EnvironmentPanel kind="workstation" root="/x" working config={cfg}
      evidence={{
        agents: [
          { agentId: 'agent-task-1', role: 'researcher', goal: 'gammel dispatch', status: 'queued', dispatchToolUseId: 't1' },
        ],
        tools: [], sources: [],
      }} />)
    await waitFor(() => { expect(kontrakt).toHaveBeenCalled() })
    expect(screen.queryByText('Underagenter')).not.toBeInTheDocument()
    expect(screen.queryByText('gammel dispatch')).not.toBeInTheDocument()
  })

  it('en fejlet agent bliver hængende — det er hele pointen med listen', async () => {
    vis([rad('agent-2', 'døde undervejs', 'failed', true)])
    expect(await screen.findByText('døde undervejs')).toBeInTheDocument()
    // Fejl er ikke «kører»: den skal stå som fejlet, ikke som aktiv.
    expect(screen.queryByText('kører')).not.toBeInTheDocument()
  })

  it('to parallelle agenter er TO rækker', async () => {
    vis([rad('agent-1', 'første'), rad('agent-2', 'anden')])
    expect(await screen.findByText('første')).toBeInTheDocument()
    expect(screen.getByText('anden')).toBeInTheDocument()
  })
})
