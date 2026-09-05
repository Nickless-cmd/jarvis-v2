import { fetchDispatchDiff, fetchWorkReviews, summarizeDiff } from './workReviewApi'
import type { ApiConfig } from './types'

const config: ApiConfig = { apiBaseUrl: 'https://api.srvlab.dk/', authToken: 'token' }
const ok = (body: unknown) => ({ ok: true, status: 200, json: async () => body })

beforeEach(() => {
  global.fetch = jest.fn()
})

it('normaliserer dispatches til review-kort med branch og diff-tal', async () => {
  ;(global.fetch as jest.Mock).mockResolvedValue(ok({
    dispatches: [{
      task_id: 'task-1',
      status: 'running',
      started_at: '2026-09-05T10:00:00Z',
      branch: 'claude/task-1',
      prompt: 'Ret mobil review',
      diff_summary: ' apps/mobile/src/App.tsx | 10 +++++-----\n 1 file changed, 5 insertions(+), 5 deletions(-)'
    }]
  }))

  const reviews = await fetchWorkReviews(config)

  expect((global.fetch as jest.Mock).mock.calls[0][0]).toContain('/api/dispatches?limit=30')
  expect(reviews).toEqual([{
    id: 'task-1',
    kind: 'dispatch',
    title: 'Ret mobil review',
    status: 'running',
    branch: 'claude/task-1',
    updatedAt: '2026-09-05T10:00:00Z',
    summary: '1 file changed, 5 insertions(+), 5 deletions(-)',
    filesChanged: 1,
    additions: 5,
    deletions: 5
  }])
})

it('henter en dispatch-diff med url-enkodet id', async () => {
  ;(global.fetch as jest.Mock).mockResolvedValue(ok({ diff: 'diff --git a/a b/a', diff_summary: '1 file changed' }))

  const diff = await fetchDispatchDiff(config, 'task/1')

  expect((global.fetch as jest.Mock).mock.calls[0][0]).toContain('/api/dispatches/task%2F1/diff')
  expect(diff.diff).toContain('diff --git')
})

it('opsummerer diff-statistik uden at kræve et bestemt git-format', () => {
  expect(summarizeDiff('2 files changed, 38 insertions(+), 12 deletions(-)')).toEqual({
    filesChanged: 2,
    additions: 38,
    deletions: 12,
    summary: '2 files changed, 38 insertions(+), 12 deletions(-)'
  })
  expect(summarizeDiff('')).toEqual({ filesChanged: 0, additions: 0, deletions: 0, summary: '' })
})
