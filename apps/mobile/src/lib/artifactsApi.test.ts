import { fetchArtifacts } from './artifactsApi'
import type { ApiConfig } from './types'

const config: ApiConfig = { apiBaseUrl: 'https://api.srvlab.dk/', authToken: 'token' }

beforeEach(() => {
  global.fetch = jest.fn()
})

it('bygger patch-artifacts ud fra dispatch diff summaries', async () => {
  ;(global.fetch as jest.Mock).mockResolvedValue({
    ok: true,
    status: 200,
    json: async () => ({
      dispatches: [{
        task_id: 'task-1',
        status: 'completed',
        started_at: '2026-09-05T10:00:00Z',
        prompt: 'Byg memory-skærm',
        diff_summary: '2 files changed, 20 insertions(+), 4 deletions(-)'
      }]
    })
  })

  const items = await fetchArtifacts(config)

  expect(items).toEqual([{
    id: 'dispatch:task-1',
    kind: 'patch',
    title: 'Byg memory-skærm',
    detail: '2 files changed, 20 insertions(+), 4 deletions(-)',
    createdAt: '2026-09-05T10:00:00Z'
  }])
})

it('returnerer tom liste når serveren ikke har artifacts endnu', async () => {
  ;(global.fetch as jest.Mock).mockResolvedValue({ ok: false, status: 404, json: async () => ({}) })
  await expect(fetchArtifacts(config)).resolves.toEqual([])
})
