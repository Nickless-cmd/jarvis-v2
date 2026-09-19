import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

vi.mock('../../lib/api', async (orig) => ({
  ...(await orig() as object),
  getGitStatus: vi.fn().mockResolvedValue(null),
}))

import { EnvironmentPanel } from './EnvironmentPanel'

/**
 * Bjørn 8/9-2026: «agenter fra hans explore tool vises ikke i miljøfeltet».
 *
 * Listen navngav fire dispatch-værktøjer — hvoraf ét slet ikke findes — og
 * manglede `explore`, som er ordret «send a read-only research agent» og
 * kaldes hele tiden. «Underagenter» var derfor tom næsten altid.
 */
const agent = (id: string, goal: string, status = 'active') => ({
  agentId: id, role: 'researcher', goal, status, dispatchToolUseId: `tool-${id}`,
})

const vis = (agents: ReturnType<typeof agent>[], onOpenAgent = vi.fn()) => ({
  ...render(<EnvironmentPanel kind="workstation" root="/x" working
    evidence={{ agents, tools: [], sources: [] }} onOpenAgent={onOpenAgent} />),
  onOpenAgent,
})

describe('underagenter i miljø-feltet', () => {
  it('viser kun en agent når evidence har et rigtigt agent-id', async () => {
    const { onOpenAgent } = vis([agent('agent-1', 'hvor håndteres token-fornyelse')])
    expect(screen.getByText('Underagenter')).toBeInTheDocument()
    expect(screen.getByText('hvor håndteres token-fornyelse')).toBeInTheDocument()
    expect(screen.getByText('kører')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: /researcher/ }))
    expect(onOpenAgent).toHaveBeenCalledWith(expect.objectContaining({ agentId: 'agent-1' }))
  })

  it('et task-tool uden agent-id bliver ikke opfundet som agent', () => {
    render(<EnvironmentPanel kind="workstation" root="/x" working evidence={{
      agents: [], sources: [],
      tools: [{ id: 'task-1', name: 'task', input: { prompt: 'ryd op' }, status: 'done' }],
    }} />)
    expect(screen.queryByText('Underagenter')).not.toBeInTheDocument()
    // Før stod kaldet som en tool-chip; Tool-kald-sektionen er fjernet
    // (Bjørn 19/9-2026), så nu vises det slet ikke i miljø-feltet.
    expect(screen.queryByText(/ryd op/)).not.toBeInTheDocument()
  })

  it('to parallelle explore-agenter er TO agenter', () => {
    vis([
      agent('agent-1', 'første'),
      agent('agent-2', 'anden'),
    ])
    expect(screen.getByText('første')).toBeInTheDocument()
    expect(screen.getByText('anden')).toBeInTheDocument()
  })
})
