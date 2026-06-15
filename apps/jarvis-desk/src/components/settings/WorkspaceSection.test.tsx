import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'

const getAccountWorkspace = vi.fn()
vi.mock('../../lib/coworkApi', () => ({ getAccountWorkspace: (...a: unknown[]) => getAccountWorkspace(...a) }))

import { WorkspaceSection } from './WorkspaceSection'

const cfg = { apiBaseUrl: 'http://x', authToken: 't' }

describe('WorkspaceSection', () => {
  beforeEach(() => getAccountWorkspace.mockReset())

  it('viser fil-antal, disk og krypterings-status', async () => {
    getAccountWorkspace.mockResolvedValue({
      path_name: 'bjorn', files: 12, disk_bytes: 2_500_000, encrypted: false, trusted: true,
    })
    render(<WorkspaceSection config={cfg} />)
    await waitFor(() => expect(screen.getByText('12')).toBeTruthy())
    expect(screen.getByText(/2[.,]4 MB|2[.,]5 MB/)).toBeTruthy()
    expect(screen.getByText(/ukrypteret/i)).toBeTruthy()
    expect(screen.getByText(/betroet/i)).toBeTruthy()
  })

  it('viser krypteret når encrypted=true', async () => {
    getAccountWorkspace.mockResolvedValue({ path_name: 'm', files: 0, disk_bytes: 0, encrypted: true, trusted: false })
    render(<WorkspaceSection config={cfg} />)
    await waitFor(() => expect(screen.getByText(/krypteret/i)).toBeTruthy())
  })
})
