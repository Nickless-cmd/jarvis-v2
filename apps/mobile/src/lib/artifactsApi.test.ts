import { fetchArtifacts } from './artifactsApi'
import type { ApiConfig } from './types'

const config: ApiConfig = { apiBaseUrl: 'https://api.srvlab.dk/', authToken: 'token' }

beforeEach(() => {
  global.fetch = jest.fn()
})

// Formen er den serveren FAKTISK sender — kørt mod CT105's data 18/9-2026.
it('læser filerne ud af /chat/artifacts for den valgte mappe', async () => {
  ;(global.fetch as jest.Mock).mockResolvedValue({
    ok: true,
    status: 200,
    json: async () => ({
      ok: true, root: '/media/projects/jarvis-v2', scanned: 1463, total: 188,
      artifacts: [{
        path: '/media/projects/jarvis-v2/core/services/decision_review_daemon.py',
        rel: 'core/services/decision_review_daemon.py',
        last_at: '2026-09-18T17:40:00+00:00', session_id: 'chat-1',
        session_title: 'yo... du må lige samle op', last_tool: 'edit_file',
        edits: 2, session_count: 1, add: 42, del: 19,
      }],
    }),
  })

  const r = await fetchArtifacts(config, '/media/projects/jarvis-v2')

  const url = String((global.fetch as jest.Mock).mock.calls[0][0])
  expect(url).toContain('/chat/artifacts?root=%2Fmedia%2Fprojects%2Fjarvis-v2')
  expect(r.ok).toBe(true)
  expect(r.scanned).toBe(1463)
  expect(r.items[0]).toEqual({
    path: '/media/projects/jarvis-v2/core/services/decision_review_daemon.py',
    rel: 'core/services/decision_review_daemon.py',
    lastAt: '2026-09-18T17:40:00+00:00', sessionId: 'chat-1',
    sessionTitle: 'yo... du må lige samle op', edits: 2, sessionCount: 1, add: 42, del: 19,
  })
})

// Den gamle udgave havde `catch { return [] }`: en 500 og en tom database gav
// præcis samme skærm, og derfor blev en brækket rute aldrig set i fem dage.
it('en fejl er IKKE en tom liste', async () => {
  ;(global.fetch as jest.Mock).mockResolvedValue({ ok: false, status: 500, json: async () => ({ detail: 'boom' }) })
  const r = await fetchArtifacts(config, 'repo')
  expect(r.ok).toBe(false)
  expect(r.error).toBeTruthy()
})

it('serverens egen afvisning kommer med op', async () => {
  ;(global.fetch as jest.Mock).mockResolvedValue({
    ok: true, status: 200,
    json: async () => ({ ok: false, root: '', error: 'ingen gyldig mappe', artifacts: [], scanned: 0 }),
  })
  const r = await fetchArtifacts(config, '')
  expect(r.ok).toBe(false)
  expect(r.error).toBe('ingen gyldig mappe')
})
