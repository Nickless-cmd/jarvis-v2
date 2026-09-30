import { describe, expect, it } from 'vitest'
import { remoteRunHasVisibleActivity } from './remoteLiveness'
import { initialStreamState } from './streamReducer'

describe('remoteRunHasVisibleActivity', () => {
  it('keeps empty and stale follow streams out of liveness', () => {
    const empty = { ...initialStreamState(), status: 'working' as const, activeRunId: 'new' }
    expect(remoteRunHasVisibleActivity(empty, 'new')).toBe(false)
    expect(remoteRunHasVisibleActivity({ ...empty, blocks: [{ type: 'text', text: 'old answer' }] }, 'old')).toBe(false)
    expect(remoteRunHasVisibleActivity({ ...empty, status: 'done', blocks: [{ type: 'text', text: 'answer' }] }, 'new')).toBe(false)
  })

  it('lights up for the current run once it actually streams work', () => {
    const base = { ...initialStreamState(), status: 'working' as const, activeRunId: 'new' }
    expect(remoteRunHasVisibleActivity({ ...base, blocks: [{ type: 'text', text: 'Svar' }] }, 'new')).toBe(true)
    expect(remoteRunHasVisibleActivity({ ...base, blocks: [{ type: 'text', text: 'Svar' }] }, null)).toBe(true)
    expect(remoteRunHasVisibleActivity({ ...base, blocks: [{ type: 'tool_use', id: 't', name: 'bash', input: {} }] }, 'new')).toBe(true)
  })
})
