import { describe, it, expect, vi, beforeEach } from 'vitest'

const apiFetch = vi.fn()
vi.mock('./api', () => ({ apiFetch: (...a: unknown[]) => apiFetch(...a) }))

import { getSideTasks, setSideTaskStatus } from './sideTasksApi'

const cfg = { apiBaseUrl: 'http://x', authToken: 't' }

describe('sideTasksApi', () => {
  beforeEach(() => apiFetch.mockReset())

  it('henter de aabne opgaver', async () => {
    apiFetch.mockResolvedValue({ side_tasks: [{ side_task_id: 'side-1', title: 'A' }], count: 1 })
    expect(await getSideTasks(cfg)).toEqual([{ side_task_id: 'side-1', title: 'A' }])
    expect(apiFetch).toHaveBeenCalledWith(cfg, '/cowork/side-tasks', { retries: 0 })
  })

  it('sender status som objekt til den rigtige rute', async () => {
    apiFetch.mockResolvedValue({ status: 'ok', new_status: 'completed' })
    await setSideTaskStatus(cfg, 'side 1', 'completed')
    expect(apiFetch).toHaveBeenCalledWith(cfg, '/cowork/side-tasks/side%201/status', { method: 'POST', body: { status: 'completed' } })
  })

  it('et 200-svar med status error er en FEJL, ikke en succes', async () => {
    apiFetch.mockResolvedValue({ status: 'error', error: 'side task side-1 is already completed' })
    await expect(setSideTaskStatus(cfg, 'side-1', 'dismissed')).rejects.toThrow('already completed')
  })
})
