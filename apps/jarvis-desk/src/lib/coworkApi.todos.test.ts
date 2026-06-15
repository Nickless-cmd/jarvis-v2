import { describe, it, expect, vi, beforeEach } from 'vitest'

const fetchMock = vi.fn()
vi.mock('./api', () => ({ apiFetch: (...a: unknown[]) => fetchMock(...a) }))

import { createCoworkTodo, setCoworkTodoStatus, deleteCoworkTodo } from './coworkApi'

const cfg = { apiBaseUrl: 'http://x', authToken: 't' }

describe('cowork todo mutations', () => {
  beforeEach(() => { fetchMock.mockReset(); fetchMock.mockResolvedValue({ status: 'ok' }) })

  it('createCoworkTodo POSTer content', async () => {
    await createCoworkTodo(cfg, 'ny')
    expect(fetchMock).toHaveBeenCalledWith(cfg, '/cowork/todos', { method: 'POST', body: { content: 'ny' } })
  })
  it('setCoworkTodoStatus POSTer status', async () => {
    await setCoworkTodoStatus(cfg, 'td-1', 'completed')
    expect(fetchMock).toHaveBeenCalledWith(cfg, '/cowork/todos/td-1/status', { method: 'POST', body: { status: 'completed' } })
  })
  it('deleteCoworkTodo DELETEr', async () => {
    await deleteCoworkTodo(cfg, 'td-1')
    expect(fetchMock).toHaveBeenCalledWith(cfg, '/cowork/todos/td-1', { method: 'DELETE' })
  })
})
