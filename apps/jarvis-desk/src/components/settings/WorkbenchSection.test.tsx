import { render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { WorkbenchSection } from './WorkbenchSection'

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
