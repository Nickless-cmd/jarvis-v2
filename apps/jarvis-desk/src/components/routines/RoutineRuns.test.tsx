import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

const listRoutineRuns = vi.fn().mockResolvedValue([{
  run_id: 'run-1', routine_id: 'routine-1', owner_user_id: 'member-1',
  access_scope: 'user_private', routine_version: 1, status: 'succeeded',
  lease_holder: null, lease_generation: 1, idempotency_key: 'manual:1',
  created_at: '2026-10-13T08:00:00Z',
}])
const listRoutineEvents = vi.fn().mockResolvedValue([
  { event_id: 'event-1', run_id: 'run-1', seq: 1, kind: 'model_fragment',
    payload: { text: 'Det private resultat' }, terminal: false,
    created_at: '2026-10-13T08:00:01Z' },
  { event_id: 'event-2', run_id: 'run-1', seq: 2, kind: 'tool_result',
    payload: { output: 'Værktøjets svar', name: 'safe_tool' }, terminal: false,
    created_at: '2026-10-13T08:00:02Z' },
])

vi.mock('../../lib/routinesApi', async (original) => ({
  ...(await original<typeof import('../../lib/routinesApi')>()),
  listRoutineRuns: (...args: unknown[]) => listRoutineRuns(...args),
  listRoutineEvents: (...args: unknown[]) => listRoutineEvents(...args),
}))

import { RoutineRuns } from './RoutineRuns'

describe('RoutineRuns', () => {
  it('shows the observable model and tool output for the authorized run', async () => {
    render(<RoutineRuns
      config={{ apiBaseUrl: 'http://desk.test', authToken: 'token' }}
      routineId="routine-1"
    />)
    const row = await screen.findByRole('button', { name: /succeeded/i })
    fireEvent.click(row)

    await waitFor(() => expect(listRoutineEvents).toHaveBeenCalledWith(
      expect.anything(), 'run-1',
    ))
    expect(await screen.findByText('Det private resultat')).toBeVisible()
    expect(screen.getByText('Værktøjets svar')).toBeVisible()
  })
})
