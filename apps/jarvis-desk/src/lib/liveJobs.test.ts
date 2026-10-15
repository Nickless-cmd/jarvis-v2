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

  it('bruger live-eventets menneskelige titel frem for værktøjsnavnet', () => {
    const state = applyJobEvent(emptyLiveJobs(), event('job_started', {
      run_id: 'r', tool: 'edit_file', tool_use_id: 'x',
      title: 'Redigerer fil: jobsApi.ts', command: '/workspace/jobsApi.ts',
    }))
    expect(state.byKey['tool:x']).toMatchObject({
      navn: 'Redigerer fil: jobsApi.ts', kommando: '/workspace/jobsApi.ts',
    })
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

  it('genopliver IKKE et faerdigt job naar stroemmen replayer job_started', () => {
    // Maalt 12/10-2026: stroemmen genoptager fra sin cursor efter et afbrudt
    // forloeb, og et sent `job_started` satte status tilbage til 'running'.
    // Tre server-shells blinkede frem i panelet mens ingen skrev noget.
    let state = emptyLiveJobs()
    state = applyJobEvent(state, event('job_started', { tool: 'bash' }, 1))
    state = applyJobEvent(state, event('job_finished', {
      status: 'error', exit_code: 2, result_text: 'exit code 2: fil mangler',
    }, 2))
    state = applyJobEvent(state, event('job_started', { tool: 'bash' }, 3))
    expect(state.byKey['tool:x']).toMatchObject({ status: 'error', exit_code: 2 })
  })

  it('lader et job med en ANDEN noegle starte uanset guarden', () => {
    let state = emptyLiveJobs()
    state = applyJobEvent(state, event('job_started', { tool: 'bash' }, 1))
    state = applyJobEvent(state, event('job_finished', { status: 'exited', exit_code: 0 }, 2))
    state = applyJobEvent(state, {
      cursor: 3, type: 'job_started', job_key: 'tool:y', session_id: 's', source: 'tool',
      payload: { tool: 'bash', tool_use_id: 'y' },
    })
    expect(state.byKey['tool:y']).toMatchObject({ status: 'running' })
    expect(state.byKey['tool:x']).toMatchObject({ status: 'exited' })
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
