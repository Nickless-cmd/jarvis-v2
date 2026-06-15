import { describe, it, expect } from 'vitest'
import { diffStat } from './diffStat'

describe('diffStat', () => {
  it('edit_file → add/del from line diff', () => {
    const r = diffStat('edit_file', { old_string: 'a\nb\nc', new_string: 'a\nX\nc\nd' })
    expect(r).not.toBeNull()
    expect(r!.add).toBeGreaterThan(0)
    expect(r!.del).toBeGreaterThan(0)
  })

  it('operator_edit_file is recognised', () => {
    const r = diffStat('operator_edit_file', { old: 'x', new: 'y' })
    expect(r).not.toBeNull()
  })

  it('write_file → all lines are additions', () => {
    const r = diffStat('write_file', { content: 'l1\nl2\nl3' })
    expect(r).toEqual({ add: 3, del: 0 })
  })

  it('returns null for non-edit tools', () => {
    expect(diffStat('web_search', { query: 'x' })).toBeNull()
  })

  it('returns null when edit args are empty', () => {
    expect(diffStat('edit_file', {})).toBeNull()
  })
})
