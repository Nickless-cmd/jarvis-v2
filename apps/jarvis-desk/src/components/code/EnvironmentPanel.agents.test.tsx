import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'

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
const vis = (tools: Array<{ name: string; input: Record<string, unknown>; status?: 'running' | 'done' | 'error' }>) =>
  render(<EnvironmentPanel kind="workstation" root="/x" working tools={tools} totalToolCalls={tools.length} />)

describe('underagenter i miljø-feltet', () => {
  it('explore ER en agent', () => {
    vis([{ name: 'explore', input: { query: 'hvor håndteres token-fornyelse' }, status: 'running' }])
    expect(screen.getByText('Underagenter')).toBeInTheDocument()
    // Opgaven står ved siden af navnet — «(worker)» sagde ingenting om hvad
    // agenten var sat til.
    expect(screen.getByText('hvor håndteres token-fornyelse')).toBeInTheDocument()
    expect(screen.getByText('kører')).toBeInTheDocument()
  })

  it('task og council er også agenter', () => {
    vis([
      { name: 'task', input: { prompt: 'ryd op i x' } },
      { name: 'convene_council', input: { question: 'skal vi?' } },
    ])
    expect(screen.getByText('ryd op i x')).toBeInTheDocument()
    expect(screen.getByText('skal vi?')).toBeInTheDocument()
  })

  it('list_agents er IKKE en agent — den slår agenter op', () => {
    // Tager man de agent-STYRENDE værktøjer med, kommer et opslag til at se ud
    // som en agent i listen.
    vis([{ name: 'list_agents', input: {} }])
    expect(screen.queryByText('Underagenter')).not.toBeInTheDocument()
  })

  it('to parallelle explore-agenter er TO agenter', () => {
    vis([
      { name: 'explore', input: { query: 'første' }, status: 'running' },
      { name: 'explore', input: { query: 'anden' }, status: 'running' },
    ])
    expect(screen.getByText('første')).toBeInTheDocument()
    expect(screen.getByText('anden')).toBeInTheDocument()
  })
})
