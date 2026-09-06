import { intentFromUrl, intentFromPushData, routePathForIntent } from './deepLink'

it('parses app links into precise mobile intents', () => {
  expect(intentFromUrl('jarvis://run/r1?session=s1')).toEqual({ kind: 'run', runId: 'r1', sessionId: 's1' })
  expect(intentFromUrl('https://jarvis.local/mobile/approval/ap1')).toEqual({ kind: 'approval', approvalId: 'ap1' })
  expect(intentFromUrl('jarvis://settings/sensors')).toEqual({ kind: 'settings', section: 'sensors' })
})

it('maps push payloads to the same routing model', () => {
  expect(intentFromPushData({ kind: 'approval_requested', request_id: 'a1', session_id: 's1' }))
    .toEqual({ kind: 'approval', approvalId: 'a1', sessionId: 's1' })
  expect(intentFromPushData({ kind: 'run_in_progress', run_id: 'r1', session_id: 's1' }))
    .toEqual({ kind: 'run', runId: 'r1', sessionId: 's1' })
  expect(intentFromPushData({ kind: 'artifact_ready', artifact_id: 'art1' }))
    .toEqual({ kind: 'artifact', artifactId: 'art1' })
})

it('returns compact display paths for diagnostics and tests', () => {
  expect(routePathForIntent({ kind: 'memory', memoryId: 'm1' })).toBe('memory/m1')
  expect(routePathForIntent(null)).toBe('')
})
