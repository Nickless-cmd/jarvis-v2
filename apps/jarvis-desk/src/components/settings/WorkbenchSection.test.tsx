import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { WorkbenchSection } from './WorkbenchSection'
import { getCheckpoints, rollbackCheckpoint } from '../../lib/coworkApi'

const cfg = { apiBaseUrl: 'http://x', authToken: 't' }

vi.mock('../../lib/coworkApi', () => ({
  getOperatorChannel: vi.fn(async () => ({ open: true, udloeber_om_s: 7200 })),
  setOperatorChannel: vi.fn(async () => ({ open: false })),
  getCheckpoints: vi.fn(async () => ({ antal: 1, punkter: [{ sha: 'abc1234567', note: 'edit_file' }] })),
  rollbackCheckpoint: vi.fn(async () => ({ status: 'ok', gendannet: 'abc1234567' })),
  getRuntimeSwitches: vi.fn(async () => ({
    bash_sandbox: { tændt: false, bwrap_findes: true, aktiv: false, note: 'slukket (standard)' },
    env_block: { tændt: true },
  })),
  setRuntimeSwitch: vi.fn(async () => undefined),
}))

describe('WorkbenchSection', () => {
  it('siger tydeligt hvad en åben kanal betyder', async () => {
    render(<WorkbenchSection config={cfg} />)
    await waitFor(() => {
      expect(screen.getByText(/bash kører på DIN maskine/i)).toBeTruthy()
    })
    expect(screen.getByText('Luk')).toBeTruthy()
  })

  it('viser hvad der kan fortrydes', async () => {
    render(<WorkbenchSection config={cfg} />)
    await waitFor(() => expect(screen.getByText('edit_file')).toBeTruthy())
  })

  it('viser sandkassen som slukket med en begrundelse', async () => {
    render(<WorkbenchSection config={cfg} />)
    await waitFor(() => expect(screen.getByText(/slukket \(standard\)/)).toBeTruthy())
  })
})

describe('WorkbenchSection · session', () => {
  it('sender den aktive session med, ellers står listen altid tom', async () => {
    // Uden session_id svarer /workbench/checkpoints for '_default' og
    // returnerer 0 — selvom der lå 576 checkpoints på de rigtige sessioner.
    render(<WorkbenchSection config={cfg} sessionId="visible-42" />)
    await waitFor(() => expect(vi.mocked(getCheckpoints)).toHaveBeenCalledWith(cfg, 'visible-42'))
  })

  it('ruller tilbage på den samme session som den viser', async () => {
    render(<WorkbenchSection config={cfg} sessionId="visible-42" />)
    const knap = await screen.findByRole('button', { name: /fortryd/i })
    fireEvent.click(knap)
    await waitFor(() => expect(vi.mocked(rollbackCheckpoint)).toHaveBeenCalledWith(cfg, 'visible-42'))
  })
})
