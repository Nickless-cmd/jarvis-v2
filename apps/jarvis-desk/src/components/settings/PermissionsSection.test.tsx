import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'

const getAccountPermissions = vi.fn()
const setComputerUse = vi.fn().mockResolvedValue(undefined)
vi.mock('../../lib/coworkApi', () => ({
  getAccountPermissions: (...a: unknown[]) => getAccountPermissions(...a),
  setComputerUse: (...a: unknown[]) => setComputerUse(...a),
}))

import { PermissionsSection } from './PermissionsSection'

const cfg = { apiBaseUrl: 'http://x', authToken: 't' }

describe('PermissionsSection', () => {
  beforeEach(() => { getAccountPermissions.mockReset(); setComputerUse.mockClear() })

  it('viser rolle + tool-matrix og computer-use', async () => {
    getAccountPermissions.mockResolvedValue({
      role: 'owner', computer_use_enabled: true,
      modes: [
        { mode: 'chat', all: true, tools: [] },
        { mode: 'cowork', all: false, tools: ['todo_add', 'list_plans'] },
      ],
    })
    render(<PermissionsSection config={cfg} />)
    await waitFor(() => expect(screen.getByText(/owner/i)).toBeTruthy())
    expect(screen.getByText(/alle værktøjer/i)).toBeTruthy()  // chat all
    expect(screen.getByText(/todo_add/)).toBeTruthy()
  })

  it('toggler computer-use', async () => {
    getAccountPermissions.mockResolvedValue({ role: 'owner', computer_use_enabled: true, modes: [] })
    render(<PermissionsSection config={cfg} />)
    const toggle = await screen.findByRole('checkbox', { name: /computer/i })
    fireEvent.click(toggle)
    await waitFor(() => expect(setComputerUse).toHaveBeenCalledWith(cfg, false))
  })
})
