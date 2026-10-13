import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'

const createRoutine = vi.fn()
const updateRoutine = vi.fn()
vi.mock('../../lib/routinesApi', async (original) => ({
  ...(await original<typeof import('../../lib/routinesApi')>()),
  createRoutine: (...args: unknown[]) => createRoutine(...args),
  updateRoutine: (...args: unknown[]) => updateRoutine(...args),
}))

import { RoutineEditor } from './RoutineEditor'
import type { Routine } from '../../lib/routinesApi'

const config = { apiBaseUrl: 'http://desk.test', authToken: 'token' }
const paused: Routine = {
  routine_id: 'r-1', owner_user_id: 'bjorn', access_scope: 'user_private', name: 'Morgenblik',
  instruction: 'Saml dagen', capability_scope: 'chat', trigger_kind: 'manual', trigger_config: {},
  permission_policy: {}, delivery_policy: {}, inbox_policy: {}, retention_policy: {}, failure_policy: {},
  jarvis_restart_allowed: false, status: 'paused', version: 4,
  created_at: '2026-10-12T08:00:00Z', updated_at: '2026-10-12T08:00:00Z',
}

describe('RoutineEditor', () => {
  beforeEach(() => {
    createRoutine.mockReset().mockResolvedValue({ ...paused, status: 'active' })
    updateRoutine.mockReset().mockResolvedValue(paused)
  })

  it('is a dedicated selected tab and creation says that save activates', () => {
    render(<RoutineEditor config={config} onSaved={() => {}} onClose={() => {}} />)
    expect(screen.getByRole('tab', { name: 'Opret rutine' })).toHaveAttribute('aria-selected', 'true')
    expect(screen.getByRole('button', { name: 'Gem og aktivér' })).toBeEnabled()
  })

  it.each(['paused', 'stopped'] as const)('preserves %s state when editing', async (status) => {
    render(<RoutineEditor config={config} routine={{ ...paused, status }} onSaved={() => {}} onClose={() => {}} />)
    fireEvent.change(screen.getByLabelText('Navn'), { target: { value: 'Opdateret' } })
    fireEvent.click(screen.getByRole('button', { name: 'Gem ændringer' }))
    await waitFor(() => expect(updateRoutine).toHaveBeenCalled())
    expect(updateRoutine.mock.calls[0]![2]).toBe(4)
    expect(updateRoutine.mock.calls[0]![3]).not.toHaveProperty('reactivate')
    expect(screen.getByText(new RegExp(`forbliver ${status === 'paused' ? 'pauset' : 'stoppet'}`, 'i'))).toBeVisible()
  })

  it('lets the user choose which routine events reach their inbox', async () => {
    render(<RoutineEditor config={config} routine={paused} onSaved={() => {}} onClose={() => {}} />)
    fireEvent.click(screen.getByLabelText('Kørsel fejlede'))
    fireEvent.click(screen.getByRole('button', { name: 'Gem ændringer' }))
    await waitFor(() => expect(updateRoutine).toHaveBeenCalled())
    expect(updateRoutine.mock.calls[0]![3].inbox_policy.failed).toBe(false)
    expect(updateRoutine.mock.calls[0]![3].inbox_policy.created).toBe(true)
  })
})
