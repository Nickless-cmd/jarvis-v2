import { beforeEach, describe, expect, it, vi } from 'vitest'

const apiFetch = vi.fn()
vi.mock('./api', () => ({ apiFetch: (...args: unknown[]) => apiFetch(...args) }))

import {
  createRoutine,
  deleteRoutine,
  listRoutineEvents,
  listRoutines,
  updateRoutine,
} from './routinesApi'

const config = { apiBaseUrl: 'http://desk.test', authToken: 'token' }

describe('routines API', () => {
  beforeEach(() => apiFetch.mockReset().mockResolvedValue({}))

  it('uses the authenticated routine collection', async () => {
    await listRoutines(config)
    expect(apiFetch).toHaveBeenCalledWith(config, '/api/routines')
  })

  it('creates an active routine without accepting an owner from the client', async () => {
    await createRoutine(config, {
      name: 'Morgenblik', instruction: 'Saml dagens aftaler', capability_scope: 'chat',
      trigger_kind: 'schedule', trigger_config: { cron: '0 8 * * *' },
    })
    const body = apiFetch.mock.calls[0]![2].body
    expect(body).not.toHaveProperty('owner_user_id')
    expect(apiFetch).toHaveBeenCalledWith(config, '/api/routines', expect.objectContaining({ method: 'POST' }))
  })

  it('sends the observed version on edits and does not reactivate paused or stopped routines', async () => {
    await updateRoutine(config, 'routine-1', 7, { name: 'Nyt navn' })
    expect(apiFetch).toHaveBeenCalledWith(config, '/api/routines/routine-1', {
      method: 'PATCH', body: { expected_version: 7, name: 'Nyt navn' },
    })
    expect(apiFetch.mock.calls[0]![2].body).not.toHaveProperty('reactivate')
  })

  it('keeps permanent deletion and run events on explicit endpoints', async () => {
    await deleteRoutine(config, 'routine-1')
    await listRoutineEvents(config, 'run-1')
    expect(apiFetch).toHaveBeenNthCalledWith(1, config, '/api/routines/routine-1', { method: 'DELETE' })
    expect(apiFetch).toHaveBeenNthCalledWith(2, config, '/api/routines/runs/run-1/events')
  })
})
