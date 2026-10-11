import { describe, expect, it } from 'vitest'
import {
  applyJobEvent, emptyLiveJobs, fromSnapshot, type LiveJobEvent,
} from './liveJobs'
import type { BackgroundJob } from './jobsApi'

const running: BackgroundJob = {
  id: 'x', job_key: 'tool:x', kilde: 'tool', navn: 'bash', kommando: 'test',
  status: 'running', can_stop: false,
}

const event = (type: string, payload: Record<string, unknown>, cursor = 11): LiveJobEvent => ({
  cursor, type, job_key: 'tool:x', session_id: 's', source: 'tool', payload,
})

describe('liveJobs', () => {
  it('starter og opdaterer et job', () => {
    const state = applyJobEvent(emptyLiveJobs(), event('job_started', {
      run_id: 'r', tool: 'bash', tool_use_id: 'x',
    }))
    expect(state.byKey['tool:x']).toMatchObject({ id: 'x', status: 'running', navn: 'bash' })
  })

  it('ignorerer replayet output med samme seq', () => {
    let state = fromSnapshot({ jobs: [running], bridge_ok: true }, 10)
    state = applyJobEvent(state, event('job_output', { seq: 1, chunk: 'a' }, 11))
    state = applyJobEvent(state, event('job_output', { seq: 1, chunk: 'a' }, 12))
    expect(state.byKey['tool:x']!.liveOutput).toBe('a')
  })

  it('holder kun de sidste 65.536 tegn', () => {
    let state = fromSnapshot({ jobs: [running], bridge_ok: true }, 1)
    state = applyJobEvent(state, event('job_output', { seq: 1, chunk: 'a'.repeat(70_000) }, 2))
    expect(state.byKey['tool:x']!.liveOutput).toHaveLength(65_536)
    expect(state.byKey['tool:x']!.liveOutputTruncated).toBe(true)
  })

  it('beholder et kort job som færdigt med konkret fejl', () => {
    let state = emptyLiveJobs()
    state = applyJobEvent(state, event('job_started', { tool: 'bash' }, 1))
    state = applyJobEvent(state, event('job_finished', {
      status: 'error', exit_code: 2, result_text: 'exit code 2: fil mangler',
    }, 2))
    expect(state.byKey['tool:x']).toMatchObject({
      status: 'error', exit_code: 2, error: 'exit code 2: fil mangler',
    })
  })

  it('et snapshot erstatter listen og brostatus', () => {
    const state = fromSnapshot({ jobs: [running], bridge_ok: false, uspecificeret: 2 }, 20)
    const next = applyJobEvent(state, {
      type: 'snapshot', cursor: 30,
      jobs: [{ ...running, id: 'y', job_key: 'tool:y' }], bridge_ok: true,
    })
    expect(Object.keys(next.byKey)).toEqual(['tool:y'])
    expect(next.bridgeOk).toBe(true)
    expect(next.cursor).toBe(30)
  })
})
